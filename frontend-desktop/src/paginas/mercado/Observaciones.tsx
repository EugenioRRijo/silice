import { Button } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";
import { fechaEsVe, formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { nombreDeFuente, rutaDeAnular } from "./logica";
import type { Estudio, Observacion } from "./logica";

interface Props {
  estudio: Estudio;
  // Tras anular, el estudio se vuelve a leer (las cifras cambian).
  alCambiar: () => void;
}

// La tabla de observaciones de la ventana: cada una con su fuente, fecha, precio en su moneda y si entra en las cifras
// (las de otra moneda se ven, no se esconden). «Anular» pide confirmarlo: la observacion sale de las cifras y queda su
// contraasiento (quien y cuando).
export function Observaciones({ estudio, alCambiar }: Props) {
  const { alExpirar } = useAplicacion();
  const { lado, observaciones, estadisticas, moneda } = estudio;
  const [pidiendo, setPidiendo] = useState<Observacion | null>(null);
  const [anulando, setAnulando] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [hecho, setHecho] = useState<string | null>(null);
  const pregunta = useRef<HTMLDivElement>(null);
  const titulo = useRef<HTMLHeadingElement>(null);
  const idTitulo = `mercado-${lado}-observaciones`;
  const nombreDeTabla = `Observaciones de los últimos ${estadisticas.dias} días`;

  useEffect(() => {
    if (pidiendo) pregunta.current?.focus();
  }, [pidiendo]);

  async function anular(o: Observacion) {
    setAnulando(true);
    setError(null);
    try {
      await pedir(rutaDeAnular(o.id), { metodo: "POST" });
      setHecho(`Observación n.º ${o.id} anulada. Queda constancia de quién y cuándo.`);
      setPidiendo(null);
      titulo.current?.focus();
      alCambiar();
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      setError(e);
    } finally {
      setAnulando(false);
    }
  }

  const porId = new Map(observaciones.map((o) => [String(o.id), o]));
  const columnas: ColumnaDensa[] = [
    { clave: "fecha", titulo: "Fecha", presentar: fechaEsVe },
    { clave: "tipo", titulo: "De dónde sale" },
    { clave: "fuente", titulo: "Fuente" },
    {
      clave: "precio",
      titulo: "Precio",
      numerica: true,
      celda: (f: FilaDensa) => (
        <span title={f.precio}>{`${formatoEsVe(f.precio)} ${f.moneda}`}</span>
      ),
    },
    { clave: "nota", titulo: "Nota", ordenable: false },
    { clave: "responsable", titulo: "Anotó" },
    { clave: "cuenta", titulo: "En las cifras" },
    {
      clave: "accion",
      titulo: "Acción",
      ordenable: false,
      celda: (f: FilaDensa) => (
        <Button
          kind="ghost"
          size="sm"
          aria-label={`Anular la observación n.º ${f.id}`}
          disabled={anulando}
          onClick={() => {
            setHecho(null);
            setError(null);
            setPidiendo(porId.get(f.id) ?? null);
          }}
        >
          Anular
        </Button>
      ),
    },
  ];
  const filas: FilaDensa[] = observaciones.map((o) => ({
    id: String(o.id),
    fecha: o.fecha,
    tipo: nombreDeFuente(o.fuente_tipo),
    fuente: o.fuente,
    precio: o.precio,
    moneda: o.moneda,
    nota: o.nota,
    responsable: o.responsable,
    cuenta: o.cuenta ? "Sí" : `No: está en ${o.moneda}`,
    accion: "",
  }));

  return (
    <section className="silice-mercado__bloque" aria-labelledby={idTitulo}>
      <h2 id={idTitulo} ref={titulo} tabIndex={-1} className="cds--type-heading-compact-02">
        {nombreDeTabla}
      </h2>
      {observaciones.length > 0 ? (
        <>
          <TablaDensa etiqueta={nombreDeTabla} columnas={columnas} filas={filas} />
          <p className="silice-mercado__nota cds--type-helper-text-01">
            {`Las cifras usan las observaciones en ${moneda}, la moneda de la carpeta de trabajo.`}
          </p>
        </>
      ) : (
        <p className="silice-mercado__nota cds--type-body-compact-01">No hay observaciones vigentes en estos días.</p>
      )}
      {pidiendo && (
        <div ref={pregunta} tabIndex={-1} className="silice-mercado__pregunta" role="group" aria-label="Confirmar la anulación">
          <p className="cds--type-body-compact-01">
            {`¿Anular la observación n.º ${pidiendo.id} (${pidiendo.fuente}, ${fechaEsVe(pidiendo.fecha)}, ${formatoEsVe(pidiendo.precio)} ${pidiendo.moneda})? Sale de las cifras y queda constancia de quién y cuándo.`}
          </p>
          <div className="silice-mercado__botones">
            <Button kind="danger" size="md" disabled={anulando} onClick={() => void anular(pidiendo)}>
              Anular la observación
            </Button>
            <Button
              kind="secondary"
              size="md"
              disabled={anulando}
              onClick={() => {
                const boton = document.querySelector<HTMLElement>(`[aria-label="Anular la observación n.º ${pidiendo.id}"]`);
                setPidiendo(null);
                boton?.focus();
              }}
            >
              Cancelar
            </Button>
          </div>
        </div>
      )}
      <AvisoError error={error} titulo="No se anuló la observación" />
      <p role="status" className="silice-mercado__estado cds--type-body-compact-01">
        {hecho ?? ""}
      </p>
    </section>
  );
}
