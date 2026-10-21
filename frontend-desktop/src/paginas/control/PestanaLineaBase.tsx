import { Button, InlineNotification, Select, SelectItem } from "@carbon/react";
import { useState } from "react";
import { pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { TablaDensa } from "../../comun/TablaDensa";
import { formatoMontoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { leerFeriados } from "./fechas";
import { errorDeCarga, etiquetaDeCodigo, rutaDe, sinTitulo, textoLlano, useAccion, useCargaSuave } from "./logica";
import type { LineaBase } from "./logica";
import { CampoTexto } from "../../comun/CampoTexto";
import { AreaTexto } from "../../comun/AreaTexto";

interface Props {
  proyecto: string;
  // Cambia cuando otra pestaña escribio algo: vuelve a pedir la linea base.
  clave: number;
  alCambiar: () => void;
}

function Aviso({ exito, error }: { exito: string; error: unknown }) {
  return (
    <>
      <AvisoError error={error} />
      {exito && (
        <InlineNotification kind="success" lowContrast hideCloseButton role="status" title={exito} />
      )}
    </>
  );
}

function Declarar({ proyecto, versiones, alCambiar }: { proyecto: string; versiones: string[]; alCambiar: () => void }) {
  const { alExpirar } = useAplicacion();
  const { estado, ejecutar } = useAccion(alExpirar, alCambiar);
  const [v, setV] = useState({
    version: versiones[0] ?? "",
    desde: "",
    perspectiva: "costo",
    inicio: "",
    dias_por_periodo: "5",
    feriados: "",
    fuente: "",
  });
  const [errorFeriados, setErrorFeriados] = useState("");
  const campo = (k: keyof typeof v) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });
  const declarar = () => {
    // Los feriados se validan aquí: la API los recibe en AAAA-MM-DD y diría otro valor que el escrito.
    const lectura = leerFeriados(v.feriados);
    setErrorFeriados("error" in lectura ? lectura.error : "");
    if ("error" in lectura) return;
    void ejecutar(async () => {
      await pedir("/v1/control/linea-base", { metodo: "POST", cuerpo: { proyecto, ...v, feriados: lectura.feriados } });
      return "Línea base declarada.";
    });
  };
  return (
    <div className="silice-control__formulario">
      <Select id="lb-version" labelText="Versión del contrato" value={v.version} onChange={campo("version")}>
        {versiones.map((c) => (
          <SelectItem key={c} value={c} text={c} />
        ))}
      </Select>
      <CampoTexto id="lb-desde" type="date" labelText="Vigente desde" value={v.desde} onChange={campo("desde")} />
      <Select
        id="lb-perspectiva"
        labelText="Perspectiva"
        helperText="costo: quien arma (contratista); precio: quien revisa (contratante)."
        value={v.perspectiva}
        onChange={campo("perspectiva")}
      >
        <SelectItem value="costo" text="costo" />
        <SelectItem value="precio" text="precio" />
      </Select>
      <CampoTexto id="lb-inicio" type="date" labelText="Inicio de obra" value={v.inicio} onChange={campo("inicio")} />
      <CampoTexto
        id="lb-dias"
        labelText="Días hábiles por período"
        value={v.dias_por_periodo}
        onChange={campo("dias_por_periodo")}
      />
      <AreaTexto id="lb-feriados" labelText="Feriados (fechas como 25/12/2026, separadas por comas)" value={v.feriados} onChange={campo("feriados")} />
      <CampoTexto id="lb-fuente" labelText="Fuente de la línea base" value={v.fuente} onChange={campo("fuente")} />
      <div>
        <Button kind="primary" size="md" disabled={estado.enviando} onClick={declarar}>
          Declarar línea base
        </Button>
      </div>
      <AvisoError error={errorFeriados || null} titulo="Revise los feriados" />
      <Aviso exito={estado.exito} error={estado.error} />
    </div>
  );
}

function Parametros({ proyecto, datos, alCambiar }: { proyecto: string; datos: LineaBase; alCambiar: () => void }) {
  const { alExpirar } = useAplicacion();
  const { estado, ejecutar } = useAccion(alExpirar, alCambiar);
  const [editados, setEditados] = useState<Record<string, string>>({});
  const [fuente, setFuente] = useState("");
  const guardar = () =>
    ejecutar(async () => {
      const parametros = Object.entries(editados).map(([parametro, valor]) => ({ parametro, valor }));
      const r = await pedir<{ cambiados: number }>("/v1/control/parametros", {
        metodo: "POST",
        cuerpo: { proyecto, parametros, fuente },
      });
      setEditados({});
      return `${r.cambiados} parámetro(s) cambiado(s).`;
    });
  return (
    <section className="silice-control__bloque" aria-labelledby="control-parametros">
      <h2 id="control-parametros" className="cds--type-heading-compact-02">
        Parámetros de control
      </h2>
      <p className="silice-control__nota cds--type-body-compact-01">
        Umbrales de las alertas y supuestos de las opciones. Son supuestos declarados, sin fuente normativa, salvo la
        penalización (dato del contrato). Cambiarlos deja su registro.
      </p>
      <TablaDensa
        etiqueta="Parámetros de control"
        columnas={[
          // VD-5: el title (el exacto) solo en la cifra; el parametro, el texto y la naturaleza, sin el codigo interno
          { clave: "parametro", titulo: "Parámetro", ordenable: false, celda: sinTitulo("parametro", etiquetaDeCodigo) },
          { clave: "que_es", titulo: "Qué es", ordenable: false, celda: sinTitulo("que_es", textoLlano) },
          { clave: "valor", titulo: "Valor", numerica: true, ordenable: false, presentar: formatoMontoEsVe },
          { clave: "naturaleza", titulo: "Naturaleza", ordenable: false, celda: sinTitulo("naturaleza", etiquetaDeCodigo) },
        ]}
        filas={datos.parametros.map((p) => ({
          id: p.parametro,
          parametro: p.parametro,
          que_es: p.que_es,
          valor: p.valor,
          naturaleza: p.naturaleza,
        }))}
      />
      <div className="silice-control__formulario">
        <Select
          id="par-nombre"
          labelText="Parámetro a cambiar"
          value=""
          onChange={(e) => {
            const nombre = e.target.value;
            if (nombre && !(nombre in editados)) {
              const actual = datos.parametros.find((p) => p.parametro === nombre)?.valor ?? "";
              setEditados({ ...editados, [nombre]: actual });
            }
          }}
        >
          <SelectItem value="" text="Elija uno" />
          {datos.parametros.map((p) => (
            <SelectItem key={p.parametro} value={p.parametro} text={etiquetaDeCodigo(p.parametro)} />
          ))}
        </Select>
        {Object.entries(editados).map(([nombre, valor]) => (
          <CampoTexto
            key={nombre}
            id={`par-${nombre}`}
            labelText={`Nuevo valor de ${etiquetaDeCodigo(nombre)}`}
            value={valor}
            onChange={(e) => setEditados({ ...editados, [nombre]: e.target.value })}
          />
        ))}
        <CampoTexto id="par-fuente" labelText="Fuente del cambio de parámetros" value={fuente} onChange={(e) => setFuente(e.target.value)} />
        <div>
          <Button
            kind="primary"
            size="md"
            disabled={estado.enviando || Object.keys(editados).length === 0}
            onClick={() => void guardar()}
          >
            Guardar parámetros
          </Button>
        </div>
        <Aviso exito={estado.exito} error={estado.error} />
      </div>
    </section>
  );
}

export function PestanaLineaBase({ proyecto, clave, alCambiar }: Props) {
  const { alExpirar } = useAplicacion();
  const carga = useCargaSuave<LineaBase>(rutaDe("/v1/control/linea-base", proyecto, { n: String(clave) }), alExpirar);
  if (carga.estado === "cargando") return <EsqueletoPagina etiqueta="Cargando la línea base" />;
  if (carga.estado !== "listo") return <AvisoError error={errorDeCarga(carga)} titulo="No se pudo cargar la línea base" />;
  const datos = carga.datos;
  return (
    <>
      <section className="silice-control__bloque" aria-labelledby="control-lb">
        <h2 id="control-lb" className="cds--type-heading-compact-02">
          Línea base vigente
        </h2>
        <p className="cds--type-body-compact-01">
          {datos.descripcion ?? "El proyecto no tiene línea base de control. Declárela abajo."}
        </p>
        <details open={!datos.tiene_linea_base}>
          <summary className="cds--type-body-compact-01">Declarar una línea base</summary>
          <Declarar proyecto={proyecto} versiones={datos.versiones} alCambiar={alCambiar} />
        </details>
      </section>
      <Parametros proyecto={proyecto} datos={datos} alCambiar={alCambiar} />
    </>
  );
}
