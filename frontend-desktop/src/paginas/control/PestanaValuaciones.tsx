import { Button, InlineNotification, Select, SelectItem } from "@carbon/react";
import { useState } from "react";
import { pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { TablaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { AYUDA_CIFRAS } from "../../indicadores/cifraEscrita";
import {
  COLUMNAS_VALUACIONES,
  LINEA_VACIA,
  NUMERICAS_VALUACIONES,
  cifraParaApi,
  columnasDe,
  conId,
  errorDeCarga,
  errorDeCifra,
  lineaParaApi,
  porcentajeDeAlicuota,
  rutaDe,
  sinLineasVacias,
  useAccion,
  useCargaSuave,
} from "./logica";
import type { CausaDeRetraso, LineaEditable, Valuaciones } from "./logica";
import { fechaDeRanura, periodoCompacto } from "./fechas";
import { CampoTexto } from "../../comun/CampoTexto";
import { AYUDA_CAUSA_SUGERIDA, causaDeLinea, sugeridasPorPartida } from "./procura";
import type { Procura } from "./procura";

interface Props {
  proyecto: string;
  clave: number;
  alCambiar: () => void;
}

function Resultado({ exito, error }: { exito: string; error: unknown }) {
  return (
    <>
      <AvisoError error={error} />
      {exito && <InlineNotification kind="success" lowContrast hideCloseButton role="status" title={exito} />}
    </>
  );
}

function Registrar({ proyecto, causas, alCambiar }: { proyecto: string; causas: CausaDeRetraso[]; alCambiar: () => void }) {
  const { alExpirar } = useAplicacion();
  const { estado, ejecutar } = useAccion(alExpirar, alCambiar);
  const [v, setV] = useState({ numero: "", desde: "", hasta: "", fecha: "", inspector: "", fuente: "" });
  const [lineas, setLineas] = useState<LineaEditable[]>([{ ...LINEA_VACIA }]);
  // MP-7, Tarea 24: la procura sugiere una causa por partida al «hasta» de la valuacion (sin él, a hoy). Una linea cuyo
  // selector no ha tocado la persona lleva la sugerida para su partida; en cuanto lo toca, vale lo que eligio (tambien
  // «Sin causa»). Si la procura no responde, no se sugiere nada: la valuacion se registra igual. Mientras recarga (la persona cambia el
  // «hasta») se conserva la sugerencia anterior en vez de vaciar los selectores.
  const [elegidas, setElegidas] = useState<Record<number, true>>({});
  const sugerencia = useCargaSuave<Procura>(rutaDe("/v1/procura", proyecto, v.hasta ? { corte: v.hasta } : {}), alExpirar);
  const sugeridas =
    sugerencia.estado === "listo" ? sugeridasPorPartida(sugerencia.datos.causas_sugeridas ?? [], causas.map((c) => c.clave)) : {};
  const causaDe = (l: LineaEditable, i: number) => causaDeLinea(l, i in elegidas, sugeridas);
  // El error de la cantidad de cada linea (por posicion), si no sigue la regla de la coma decimal.
  const [errores, setErrores] = useState<Record<number, string>>({});
  const campo = (k: keyof typeof v) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });
  const cambiarLinea = (i: number, k: keyof LineaEditable, valor: string) =>
    setLineas(lineas.map((l, j) => (j === i ? { ...l, [k]: valor } : l)));
  const registrar = () => {
    const nuevos: Record<number, string> = {};
    lineas.forEach((l, i) => {
      const error = errorDeCifra(l.cantidad);
      if (error) nuevos[i] = error;
    });
    setErrores(nuevos);
    if (Object.keys(nuevos).length > 0) return;
    void ejecutar(async () => {
      const r = await pedir<{ corte: string; hallazgos: number; errores: number }>("/v1/control/valuaciones", {
        metodo: "POST",
        cuerpo: {
          proyecto,
          ...v,
          lineas: sinLineasVacias(lineas.map((l, i) => ({ ...l, causa: causaDe(l, i) }))).map(lineaParaApi),
        },
      });
      return `Valuación registrada: corte ${fechaDeRanura(r.corte)}, ${r.hallazgos} hallazgo(s) en la revisión de la valuación (${r.errores} con severidad Error).`;
    });
  };
  return (
    <details open>
      <summary className="cds--type-body-compact-01">Registrar una valuación</summary>
      <div className="silice-control__formulario">
        <CampoTexto id="val-numero" labelText="Número" value={v.numero} onChange={campo("numero")} />
        <CampoTexto id="val-desde" type="date" labelText="Período desde" value={v.desde} onChange={campo("desde")} />
        <CampoTexto id="val-hasta" type="date" labelText="Período hasta" value={v.hasta} onChange={campo("hasta")} />
        <CampoTexto id="val-fecha" type="date" labelText="Fecha de la valuación" value={v.fecha} onChange={campo("fecha")} />
        <CampoTexto id="val-inspector" labelText="Inspector" value={v.inspector} onChange={campo("inspector")} />
        <fieldset className="silice-control__lineas">
          <legend className="cds--type-label-01">Líneas medidas</legend>
          <p className="silice-control__nota cds--type-helper-text-01">{AYUDA_CIFRAS}</p>
          {lineas.map((l, i) => (
            <div key={i} className="silice-control__linea">
              <CampoTexto id={`val-p-${i}`} labelText={`Partida ${i + 1}`} value={l.partida} onChange={(e) => cambiarLinea(i, "partida", e.target.value)} />
              <CampoTexto
                id={`val-c-${i}`}
                labelText={`Cantidad ${i + 1}`}
                invalid={i in errores}
                invalidText={errores[i]}
                value={l.cantidad}
                onChange={(e) => cambiarLinea(i, "cantidad", e.target.value)}
              />
              <CampoTexto id={`val-m-${i}`} type="date" labelText={`Fecha de medición ${i + 1}`} value={l.fecha_medicion} onChange={(e) => cambiarLinea(i, "fecha_medicion", e.target.value)} />
              <CampoTexto id={`val-o-${i}`} labelText={`Observación ${i + 1}`} value={l.observacion} onChange={(e) => cambiarLinea(i, "observacion", e.target.value)} />
              <Select
                id={`val-r-${i}`}
                labelText={`Causa del retraso ${i + 1}`}
                value={causaDe(l, i)}
                helperText={!(i in elegidas) && causaDe(l, i) !== "" ? AYUDA_CAUSA_SUGERIDA : undefined}
                onChange={(e) => {
                  setElegidas({ ...elegidas, [i]: true });
                  cambiarLinea(i, "causa", e.target.value);
                }}
              >
                <SelectItem value="" text="Sin causa" />
                {causas.map((c) => (
                  <SelectItem key={c.clave} value={c.clave} text={c.nombre} />
                ))}
              </Select>
            </div>
          ))}
          <Button kind="ghost" size="sm" onClick={() => setLineas([...lineas, { ...LINEA_VACIA }])}>
            Agregar línea
          </Button>
        </fieldset>
        <CampoTexto id="val-fuente" labelText="Fuente (acta, oficio)" value={v.fuente} onChange={campo("fuente")} />
        <div>
          <Button kind="primary" size="md" disabled={estado.enviando} onClick={registrar}>
            Registrar y controlar
          </Button>
        </div>
        <Resultado exito={estado.exito} error={estado.error} />
      </div>
    </details>
  );
}

function Importar({ proyecto, alCambiar }: { proyecto: string; alCambiar: () => void }) {
  const { alExpirar } = useAplicacion();
  const lectura = useAccion(alExpirar);
  const importacion = useAccion(alExpirar, alCambiar);
  const [archivo, setArchivo] = useState<File | null>(null);
  const [informe, setInforme] = useState<string[] | null>(null);
  const [fuente, setFuente] = useState("");
  const elegir = (f: File) => {
    setArchivo(f);
    setInforme(null);
    const cuerpo = new FormData();
    cuerpo.append("archivo", f);
    void lectura.ejecutar(async () => {
      const r = await pedir<{ informe: string[] }>("/v1/control/importar/informe", { metodo: "POST", cuerpo });
      setInforme(r.informe);
      return "";
    });
  };
  const importar = () =>
    importacion.ejecutar(async () => {
      if (!archivo) return "";
      const cuerpo = new FormData();
      cuerpo.append("archivo", archivo);
      cuerpo.append("proyecto", proyecto);
      cuerpo.append("fuente", fuente);
      const r = await pedir<{ importadas: number }>("/v1/control/importar", { metodo: "POST", cuerpo });
      setInforme(null);
      setArchivo(null);
      return `${r.importadas} valuación(es) importada(s).`;
    });
  return (
    <details>
      <summary className="cds--type-body-compact-01">Importar valuaciones de un XLSX</summary>
      <div className="silice-control__formulario">
        <p className="silice-control__nota cds--type-body-compact-01">
          Hojas Valuaciones (numero, desde, hasta, fecha, inspector), Lineas (numero, codigo_partida, cantidad,
          fecha_medicion, observacion) y Costos (opcional). Un archivo malformado se rechaza entero.
        </p>
        <SubidaArchivo id="control-xlsx" etiqueta="Suelte aquí el libro .xlsx o haga clic para elegirlo" extensiones={[".xlsx"]} alElegir={elegir} />
        <AvisoError error={lectura.estado.error} titulo="No se pudo leer el archivo" />
        {informe && (
          <>
            <p className="cds--type-body-compact-01">Informe previo de {archivo?.name}:</p>
            <ul>
              {informe.map((linea, i) => (
                <li key={i} className="cds--type-body-compact-01">
                  {linea}
                </li>
              ))}
            </ul>
            <CampoTexto id="imp-fuente" labelText="Fuente de la importación" value={fuente} onChange={(e) => setFuente(e.target.value)} />
            <div>
              <Button kind="primary" size="md" disabled={importacion.estado.enviando} onClick={() => void importar()}>
                Importar
              </Button>
            </div>
          </>
        )}
        <Resultado exito={importacion.estado.exito} error={importacion.estado.error} />
      </div>
    </details>
  );
}

function Anular({ proyecto, datos, alCambiar }: { proyecto: string; datos: Valuaciones; alCambiar: () => void }) {
  const { alExpirar } = useAplicacion();
  const { estado, ejecutar } = useAccion(alExpirar, alCambiar);
  const [elegida, setElegida] = useState("");
  const [motivo, setMotivo] = useState("");
  if (datos.anulables.length === 0) return null;
  const anular = () =>
    ejecutar(async () => {
      await pedir(`/v1/control/valuaciones/${elegida || datos.anulables[0]!.id}/anular`, {
        metodo: "POST",
        cuerpo: { motivo },
      });
      setMotivo("");
      return "Valuación anulada: se conserva y ya no cuenta.";
    });
  return (
    <details>
      <summary className="cds--type-body-compact-01">Anular una valuación</summary>
      <div className="silice-control__formulario" data-proyecto={proyecto}>
        <Select id="anu-valuacion" labelText="Valuación" value={elegida} onChange={(e) => setElegida(e.target.value)}>
          {datos.anulables.map((a) => (
            <SelectItem key={a.id} value={String(a.id)} text={a.rotulo} />
          ))}
        </Select>
        <CampoTexto id="anu-motivo" labelText="Motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
        <div>
          <Button kind="danger--tertiary" size="md" disabled={estado.enviando} onClick={() => void anular()}>
            Anular
          </Button>
        </div>
        <Resultado exito={estado.exito} error={estado.error} />
      </div>
    </details>
  );
}

function Costo({ proyecto, alCambiar }: { proyecto: string; alCambiar: () => void }) {
  const { alExpirar } = useAplicacion();
  const { estado, ejecutar } = useAccion(alExpirar, alCambiar);
  const [v, setV] = useState({ monto: "", moneda: "USD", fecha: "", partida: "", fuente: "" });
  const [errorMonto, setErrorMonto] = useState<string | null>(null);
  const campo = (k: keyof typeof v) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });
  const anotar = () => {
    const error = errorDeCifra(v.monto);
    setErrorMonto(error);
    if (error) return;
    void ejecutar(async () => {
      await pedir("/v1/control/costos", { metodo: "POST", cuerpo: { proyecto, ...v, monto: cifraParaApi(v.monto) } });
      return "Costo anotado: se convierte con la tasa de su fecha al calcular.";
    });
  };
  return (
    <details>
      <summary className="cds--type-body-compact-01">Anotar un costo incurrido</summary>
      <div className="silice-control__formulario">
        <CampoTexto
          id="cos-monto"
          labelText="Monto"
          helperText={AYUDA_CIFRAS}
          invalid={errorMonto !== null}
          invalidText={errorMonto ?? undefined}
          value={v.monto}
          onChange={campo("monto")}
        />
        <Select id="cos-moneda" labelText="Moneda" value={v.moneda} onChange={campo("moneda")}>
          <SelectItem value="USD" text="USD" />
          <SelectItem value="Bs" text="Bs" />
        </Select>
        <CampoTexto id="cos-fecha" type="date" labelText="Fecha" value={v.fecha} onChange={campo("fecha")} />
        <CampoTexto id="cos-partida" labelText="Partida (opcional)" value={v.partida} onChange={campo("partida")} />
        <CampoTexto id="cos-fuente" labelText="Fuente del costo" value={v.fuente} onChange={campo("fuente")} />
        <div>
          <Button kind="primary" size="md" disabled={estado.enviando} onClick={anotar}>
            Anotar costo
          </Button>
        </div>
        <Resultado exito={estado.exito} error={estado.error} />
      </div>
    </details>
  );
}

// A 1366 px las nueve columnas no caben con el período en dos fechas completas: se lee «02/11 a 06/11/2026» y el texto
// completo queda en el title. Es solo presentación; el orden y el valor de la fila no cambian.
const COLUMNAS_DE_VALUACIONES = columnasDe(COLUMNAS_VALUACIONES, NUMERICAS_VALUACIONES).map((c) =>
  c.clave === "Periodo"
    ? {
        ...c,
        celda: (fila: { Periodo?: string }) => {
          const completo = fila.Periodo ?? "";
          return <span title={completo}>{periodoCompacto(completo)}</span>;
        },
      }
    : c,
);

export function PestanaValuaciones({ proyecto, clave, alCambiar }: Props) {
  const { alExpirar } = useAplicacion();
  const carga = useCargaSuave<Valuaciones>(rutaDe("/v1/control/valuaciones", proyecto, { n: String(clave) }), alExpirar);
  if (carga.estado === "cargando") return <EsqueletoPagina etiqueta="Cargando las valuaciones" />;
  if (carga.estado !== "listo") return <AvisoError error={errorDeCarga(carga)} titulo="No se pudieron cargar las valuaciones" />;
  const datos = carga.datos;
  if (!datos.tiene_linea_base) {
    return <EstadoVacio titulo="Declare primero la línea base de control" descripcion="Se hace en la pestaña «Línea base»." />;
  }
  return (
    <>
      <section className="silice-control__bloque" aria-labelledby="control-valuaciones">
        <h2 id="control-valuaciones" className="cds--type-heading-compact-02">
          Valuaciones registradas (cuentan desde su registro)
        </h2>
        {datos.aviso && <InlineNotification kind="warning" lowContrast hideCloseButton role="status" title={datos.aviso} />}
        {datos.filas.length === 0 ? (
          <p className="cds--type-body-compact-01">Aún no hay valuaciones registradas.</p>
        ) : (
          <div className="silice-control__valuaciones">
            <TablaDensa etiqueta="Valuaciones registradas" columnas={COLUMNAS_DE_VALUACIONES} filas={conId(datos.filas)} />
          </div>
        )}
        {datos.filas.length > 0 && (
          <p className="silice-control__nota cds--type-helper-text-01">
            {`Lo medido hasta hoy: ${formatoEsVe(datos.impuestos.subtotal)} sin IVA; IVA al ${porcentajeDeAlicuota(datos.impuestos.alicuota)} %: ${formatoEsVe(datos.impuestos.iva)}; total con IVA: ${formatoEsVe(datos.impuestos.total)}. Fuente de la alícuota: ${datos.impuestos.fuente_alicuota}.${datos.perspectiva === "costo" ? " La línea base está en costo directo: este IVA no es una cifra facturable." : ""}`}
          </p>
        )}
        <p className="silice-control__nota cds--type-helper-text-01">
          Una valuación registrada cuenta desde su registro; solo anularla la saca del cálculo. Si el cliente no la
          aprueba, anúlela.
        </p>
      </section>
      <section className="silice-control__bloque" aria-labelledby="control-escribir">
        <h2 id="control-escribir" className="cds--type-heading-compact-02">
          Registrar, importar, anular y anotar costos
        </h2>
        <Registrar proyecto={proyecto} causas={datos.causas} alCambiar={alCambiar} />
        <Importar proyecto={proyecto} alCambiar={alCambiar} />
        <Anular proyecto={proyecto} datos={datos} alCambiar={alCambiar} />
        <Costo proyecto={proyecto} alCambiar={alCambiar} />
      </section>
    </>
  );
}
