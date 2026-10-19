import { Button, InlineNotification, Select, SelectItem, TextArea, TextInput } from "@carbon/react";
import { useState } from "react";
import { pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { TablaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import { errorDeCarga, rutaDe, useAccion, useCargaSuave } from "./logica";
import type { LineaBase } from "./logica";

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
  const campo = (k: keyof typeof v) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });
  const declarar = () =>
    ejecutar(async () => {
      await pedir("/v1/control/linea-base", { metodo: "POST", cuerpo: { proyecto, ...v } });
      return "Linea base declarada.";
    });
  return (
    <div className="silice-control__formulario">
      <Select id="lb-version" labelText="Version del contrato" value={v.version} onChange={campo("version")}>
        {versiones.map((c) => (
          <SelectItem key={c} value={c} text={c} />
        ))}
      </Select>
      <TextInput id="lb-desde" labelText="Vigente desde (AAAA-MM-DD)" value={v.desde} onChange={campo("desde")} />
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
      <TextInput id="lb-inicio" labelText="Inicio de obra (AAAA-MM-DD)" value={v.inicio} onChange={campo("inicio")} />
      <TextInput
        id="lb-dias"
        labelText="Dias habiles por periodo"
        value={v.dias_por_periodo}
        onChange={campo("dias_por_periodo")}
      />
      <TextArea id="lb-feriados" labelText="Feriados (AAAA-MM-DD, separados por comas)" value={v.feriados} onChange={campo("feriados")} />
      <TextInput id="lb-fuente" labelText="Fuente de la linea base" value={v.fuente} onChange={campo("fuente")} />
      <div>
        <Button kind="primary" size="md" disabled={estado.enviando} onClick={() => void declarar()}>
          Declarar linea base
        </Button>
      </div>
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
      return `${r.cambiados} parametro(s) cambiado(s).`;
    });
  return (
    <section className="silice-control__bloque" aria-labelledby="control-parametros">
      <h2 id="control-parametros" className="cds--type-heading-compact-02">
        Parametros de control
      </h2>
      <p className="silice-control__nota cds--type-body-compact-01">
        Umbrales de las alertas y supuestos de las opciones. Son SUPUESTO_DECLARADO, sin fuente normativa, salvo la
        penalizacion (dato del contrato). Cambiarlos deja su registro.
      </p>
      <TablaDensa
        etiqueta="Parametros de control"
        columnas={[
          { clave: "parametro", titulo: "Parametro", ordenable: false },
          { clave: "que_es", titulo: "Que es", ordenable: false },
          { clave: "valor", titulo: "Valor", ordenable: false },
          { clave: "naturaleza", titulo: "Naturaleza", ordenable: false },
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
          labelText="Parametro a cambiar"
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
            <SelectItem key={p.parametro} value={p.parametro} text={p.parametro} />
          ))}
        </Select>
        {Object.entries(editados).map(([nombre, valor]) => (
          <TextInput
            key={nombre}
            id={`par-${nombre}`}
            labelText={`Nuevo valor de ${nombre}`}
            value={valor}
            onChange={(e) => setEditados({ ...editados, [nombre]: e.target.value })}
          />
        ))}
        <TextInput id="par-fuente" labelText="Fuente del cambio de parametros" value={fuente} onChange={(e) => setFuente(e.target.value)} />
        <div>
          <Button
            kind="primary"
            size="md"
            disabled={estado.enviando || Object.keys(editados).length === 0}
            onClick={() => void guardar()}
          >
            Guardar parametros
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
  if (carga.estado === "cargando") return <EsqueletoPagina etiqueta="Cargando la linea base" />;
  if (carga.estado !== "listo") return <AvisoError error={errorDeCarga(carga)} titulo="No se pudo cargar la linea base" />;
  const datos = carga.datos;
  return (
    <>
      <section className="silice-control__bloque" aria-labelledby="control-lb">
        <h2 id="control-lb" className="cds--type-heading-compact-02">
          Linea base vigente
        </h2>
        <p className="cds--type-body-compact-01">
          {datos.descripcion ?? "El proyecto no tiene linea base de control. Declarela abajo."}
        </p>
        <details open={!datos.tiene_linea_base}>
          <summary className="cds--type-body-compact-01">Declarar una linea base</summary>
          <Declarar proyecto={proyecto} versiones={datos.versiones} alCambiar={alCambiar} />
        </details>
      </section>
      <Parametros proyecto={proyecto} datos={datos} alCambiar={alCambiar} />
    </>
  );
}
