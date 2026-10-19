import { Button, InlineNotification, Select, SelectItem, TextInput } from "@carbon/react";
import { useState } from "react";
import { pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { TablaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import { COLUMNAS_VALUACIONES, LINEA_VACIA, columnasDe, conId, errorDeCarga, rutaDe, sinLineasVacias, useAccion, useCargaSuave } from "./logica";
import type { LineaEditable, Valuaciones } from "./logica";

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

function Registrar({ proyecto, alCambiar }: { proyecto: string; alCambiar: () => void }) {
  const { alExpirar } = useAplicacion();
  const { estado, ejecutar } = useAccion(alExpirar, alCambiar);
  const [v, setV] = useState({ numero: "", desde: "", hasta: "", fecha: "", inspector: "", fuente: "" });
  const [lineas, setLineas] = useState<LineaEditable[]>([{ ...LINEA_VACIA }]);
  const campo = (k: keyof typeof v) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });
  const cambiarLinea = (i: number, k: keyof LineaEditable, valor: string) =>
    setLineas(lineas.map((l, j) => (j === i ? { ...l, [k]: valor } : l)));
  const registrar = () =>
    ejecutar(async () => {
      const r = await pedir<{ corte: string; hallazgos: number; errores: number }>("/v1/control/valuaciones", {
        metodo: "POST",
        cuerpo: { proyecto, ...v, lineas: sinLineasVacias(lineas) },
      });
      return `Valuacion registrada: corte ${r.corte}, ${r.hallazgos} hallazgo(s) de R13-R14 (${r.errores} ERROR).`;
    });
  return (
    <details open>
      <summary className="cds--type-body-compact-01">Registrar una valuacion</summary>
      <div className="silice-control__formulario">
        <TextInput id="val-numero" labelText="Numero" value={v.numero} onChange={campo("numero")} />
        <TextInput id="val-desde" labelText="Periodo desde (AAAA-MM-DD)" value={v.desde} onChange={campo("desde")} />
        <TextInput id="val-hasta" labelText="Periodo hasta (AAAA-MM-DD)" value={v.hasta} onChange={campo("hasta")} />
        <TextInput id="val-fecha" labelText="Fecha de la valuacion (AAAA-MM-DD)" value={v.fecha} onChange={campo("fecha")} />
        <TextInput id="val-inspector" labelText="Inspector" value={v.inspector} onChange={campo("inspector")} />
        <fieldset className="silice-control__lineas">
          <legend className="cds--type-label-01">Lineas medidas</legend>
          {lineas.map((l, i) => (
            <div key={i} className="silice-control__linea">
              <TextInput id={`val-p-${i}`} labelText={`Partida ${i + 1}`} value={l.partida} onChange={(e) => cambiarLinea(i, "partida", e.target.value)} />
              <TextInput id={`val-c-${i}`} labelText={`Cantidad ${i + 1}`} value={l.cantidad} onChange={(e) => cambiarLinea(i, "cantidad", e.target.value)} />
              <TextInput id={`val-m-${i}`} labelText={`Fecha de medicion ${i + 1}`} value={l.fecha_medicion} onChange={(e) => cambiarLinea(i, "fecha_medicion", e.target.value)} />
              <TextInput id={`val-o-${i}`} labelText={`Observacion ${i + 1}`} value={l.observacion} onChange={(e) => cambiarLinea(i, "observacion", e.target.value)} />
            </div>
          ))}
          <Button kind="ghost" size="sm" onClick={() => setLineas([...lineas, { ...LINEA_VACIA }])}>
            Agregar linea
          </Button>
        </fieldset>
        <TextInput id="val-fuente" labelText="Fuente (acta, oficio)" value={v.fuente} onChange={campo("fuente")} />
        <div>
          <Button kind="primary" size="md" disabled={estado.enviando} onClick={() => void registrar()}>
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
      return `${r.importadas} valuacion(es) importada(s).`;
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
            <TextInput id="imp-fuente" labelText="Fuente de la importacion" value={fuente} onChange={(e) => setFuente(e.target.value)} />
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
      return "Valuacion anulada: se conserva y ya no cuenta.";
    });
  return (
    <details>
      <summary className="cds--type-body-compact-01">Anular una valuacion</summary>
      <div className="silice-control__formulario" data-proyecto={proyecto}>
        <Select id="anu-valuacion" labelText="Valuacion" value={elegida} onChange={(e) => setElegida(e.target.value)}>
          {datos.anulables.map((a) => (
            <SelectItem key={a.id} value={String(a.id)} text={a.rotulo} />
          ))}
        </Select>
        <TextInput id="anu-motivo" labelText="Motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
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
  const campo = (k: keyof typeof v) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });
  const anotar = () =>
    ejecutar(async () => {
      await pedir("/v1/control/costos", { metodo: "POST", cuerpo: { proyecto, ...v } });
      return "Costo anotado: se convierte con la tasa de su fecha al calcular.";
    });
  return (
    <details>
      <summary className="cds--type-body-compact-01">Anotar un costo incurrido</summary>
      <div className="silice-control__formulario">
        <TextInput id="cos-monto" labelText="Monto" value={v.monto} onChange={campo("monto")} />
        <Select id="cos-moneda" labelText="Moneda" value={v.moneda} onChange={campo("moneda")}>
          <SelectItem value="USD" text="USD" />
          <SelectItem value="Bs" text="Bs" />
        </Select>
        <TextInput id="cos-fecha" labelText="Fecha (AAAA-MM-DD)" value={v.fecha} onChange={campo("fecha")} />
        <TextInput id="cos-partida" labelText="Partida (opcional)" value={v.partida} onChange={campo("partida")} />
        <TextInput id="cos-fuente" labelText="Fuente del costo" value={v.fuente} onChange={campo("fuente")} />
        <div>
          <Button kind="primary" size="md" disabled={estado.enviando} onClick={() => void anotar()}>
            Anotar costo
          </Button>
        </div>
        <Resultado exito={estado.exito} error={estado.error} />
      </div>
    </details>
  );
}

export function PestanaValuaciones({ proyecto, clave, alCambiar }: Props) {
  const { alExpirar } = useAplicacion();
  const carga = useCargaSuave<Valuaciones>(rutaDe("/v1/control/valuaciones", proyecto, { n: String(clave) }), alExpirar);
  if (carga.estado === "cargando") return <EsqueletoPagina etiqueta="Cargando las valuaciones" />;
  if (carga.estado !== "listo") return <AvisoError error={errorDeCarga(carga)} titulo="No se pudieron cargar las valuaciones" />;
  const datos = carga.datos;
  if (!datos.tiene_linea_base) {
    return <EstadoVacio titulo="Declare primero la linea base de control" descripcion="Se hace en la pestaña «Línea base»." />;
  }
  return (
    <>
      <section className="silice-control__bloque" aria-labelledby="control-valuaciones">
        <h2 id="control-valuaciones" className="cds--type-heading-03">
          Valuaciones registradas (cuentan desde su registro)
        </h2>
        {datos.aviso && <InlineNotification kind="warning" lowContrast hideCloseButton role="status" title={datos.aviso} />}
        {datos.filas.length === 0 ? (
          <p className="cds--type-body-compact-01">Aun no hay valuaciones registradas.</p>
        ) : (
          <TablaDensa etiqueta="Valuaciones registradas" columnas={columnasDe(COLUMNAS_VALUACIONES)} filas={conId(datos.filas)} />
        )}
        <p className="silice-control__nota cds--type-helper-text-01">
          Una valuacion registrada cuenta desde su registro; solo anularla la saca del calculo (S2-R14). Si el cliente no
          la aprueba, anulela.
        </p>
      </section>
      <section className="silice-control__bloque" aria-labelledby="control-escribir">
        <h2 id="control-escribir" className="cds--type-heading-03">
          Registrar, importar, anular y anotar costos
        </h2>
        <Registrar proyecto={proyecto} alCambiar={alCambiar} />
        <Importar proyecto={proyecto} alCambiar={alCambiar} />
        <Anular proyecto={proyecto} datos={datos} alCambiar={alCambiar} />
        <Costo proyecto={proyecto} alCambiar={alCambiar} />
      </section>
    </>
  );
}
