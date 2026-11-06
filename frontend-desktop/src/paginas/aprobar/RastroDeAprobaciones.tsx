import { CheckmarkFilled, ErrorFilled } from "@carbon/icons-react";
import { useId } from "react";
import { ESTADOS_APROBADOS, nombreDeEstado } from "../../comun/aprobacion";
import type { AprobacionesDeObra, EventoDeAprobacion } from "../../comun/aprobacion";
import { AvisoError } from "../../comun/AvisoError";
import { nombreDeResponsable } from "../../comun/responsable";
import { TablaDensa } from "../../comun/TablaDensa";
import { fechaEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { useCarga } from "../../comun/useCarga";

// Lo que pasó en cada movimiento: un envío queda «En aprobación»; un dictamen, con su desenlace (y, si lo dio quien armó la
// versión, se dice).
function desenlaceDe(e: EventoDeAprobacion): string {
  if (e.tipo === "envio") return "En aprobación";
  if (e.tipo === "retiro") return "Retirada";
  const nombre = nombreDeEstado(e.resultado ?? "");
  return e.armo && e.resultado !== null && ESTADOS_APROBADOS.has(e.resultado) ? `${nombre} · por quien la armó` : nombre;
}

const TIPOS: Record<string, string> = { envio: "Envío", dictamen: "Dictamen", retiro: "Retiro" };

// «Rastro de la obra» (Tarea 20; diseño §5.4): las fases de la obra («VIV-001 devuelta → VIV-002 aprobada»), si su rastro
// está íntegro (ícono y texto: el color nunca va solo) y cada movimiento, de `GET /v1/aprobaciones?proyecto=`. Vivía en la
// pestaña «Trazabilidad» de la Hoja; desde la Tarea 6 del plan F4 es un bloque de la sección Aprobaciones. Un 403 o un 404
// no dicen nada (la pantalla no depende de esto); un fallo del servidor se dice.
function esRastro(valor: unknown): valor is AprobacionesDeObra {
  const r = valor as Partial<AprobacionesDeObra> | null | undefined;
  return typeof r?.rastro?.mensaje === "string" && Array.isArray(r.eventos) && typeof r.fases === "string";
}

export function RastroDeAprobaciones({ proyecto }: { proyecto: string }) {
  const { alExpirar } = useAplicacion();
  const titulo = useId();
  const carga = useCarga<AprobacionesDeObra>(`/v1/aprobaciones?${new URLSearchParams({ proyecto }).toString()}`, alExpirar);
  if (carga.estado === "sin_permiso" || carga.estado === "no_disponible") return null;
  // Un servidor sin la ruta (o con otra forma) no dice nada: la pantalla no depende de esto.
  if (carga.estado === "listo" && !esRastro(carga.datos)) return null;
  return (
    <section className="silice-aprobar__rastro" aria-labelledby={titulo}>
      <h2 id={titulo} className="cds--type-heading-compact-02">
        Rastro de la obra
      </h2>
      {carga.estado === "cargando" && (
        <p className="cds--type-helper-text-01" aria-live="polite">
          Leyendo las aprobaciones…
        </p>
      )}
      {carga.estado === "error" && <AvisoError error={carga.error} titulo="No se pudo leer el rastro de aprobaciones" />}
      {carga.estado === "listo" && <Contenido datos={carga.datos} />}
    </section>
  );
}

function Contenido({ datos }: { datos: AprobacionesDeObra }) {
  const Icono = datos.rastro.integro ? CheckmarkFilled : ErrorFilled;
  return (
    <>
      {datos.eventos.length === 0 ? (
        <p className="cds--type-body-compact-01">Esta obra todavía no envió versiones a aprobación.</p>
      ) : (
        <>
          <p className="cds--type-body-compact-01">{datos.fases}</p>
          <TablaDensa
            etiqueta="Movimientos de aprobación"
            columnas={[
              { clave: "movimiento", titulo: "Movimiento", ordenable: false },
              { clave: "version", titulo: "Versión", ordenable: false },
              { clave: "desenlace", titulo: "Desenlace", ordenable: false },
              { clave: "por", titulo: "Quién", ordenable: false },
              { clave: "el", titulo: "Cuándo", ordenable: false, presentar: fechaEsVe },
              { clave: "notas", titulo: "Notas", ordenable: false },
            ]}
            filas={datos.eventos.map((e) => ({
              id: `aprobacion-${e.id}`,
              movimiento: TIPOS[e.tipo] ?? e.tipo,
              version: e.version,
              desenlace: desenlaceDe(e),
              por: nombreDeResponsable(e.por),
              el: e.el,
              notas: e.notas,
            }))}
          />
        </>
      )}
      <p className="cds--type-body-compact-01 silice-aprobar__rastro-estado" role="status">
        <Icono
          size={16}
          aria-hidden="true"
          className={datos.rastro.integro ? "silice-aprobar__rastro-integro" : "silice-aprobar__rastro-roto"}
        />
        {datos.rastro.mensaje}
      </p>
    </>
  );
}
