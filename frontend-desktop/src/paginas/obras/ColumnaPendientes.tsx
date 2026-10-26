import { Button, SkeletonText } from "@carbon/react";
import { useId } from "react";
import type { JSX, ReactNode } from "react";
import { AvisoError } from "../../comun/AvisoError";
import type { Carga } from "../inicio/useCarga";
import { gruposConItems } from "./logica";
import type { GrupoRespuesta, PendientesRespuesta } from "./logica";

interface Props {
  carga: Carga<PendientesRespuesta>;
  puedeIr: (pagina: string) => boolean;
  alIr: (codigo: string, pagina: string) => void;
}

// «Pendientes»: lo que requiere atencion en las obras, en los grupos y el orden de la API (Aprobar, Compras, Precios,
// Calidad; reglas deterministas de `aplicacion/mesa.py`). Un grupo sin nada no se muestra; cada pendiente dice su obra,
// que pasa y lleva su accion (solo si la cuenta puede abrir esa pantalla).
export function ColumnaPendientes({ carga, puedeIr, alIr }: Props): JSX.Element | null {
  const idTitulo = useId();
  if (carga.estado === "sin_permiso") return null;

  let cuerpo: ReactNode;
  if (carga.estado === "cargando") {
    cuerpo = (
      <div className="silice-mesa__grupos" role="status" aria-busy="true" aria-label="Cargando los pendientes">
        <SkeletonText width="30%" />
        <SkeletonText paragraph lineCount={4} />
      </div>
    );
  } else if (carga.estado !== "listo") {
    cuerpo = <AvisoError error={carga.error} titulo="No se pudieron leer los pendientes" />;
  } else {
    const grupos = gruposConItems(carga.datos.grupos);
    cuerpo =
      grupos.length === 0 ? (
        <p className="silice-mesa__nota cds--type-body-compact-01">Nada pendiente por ahora.</p>
      ) : (
        <div className="silice-mesa__grupos">
          {grupos.map((g) => (
            <Grupo key={g.clave} grupo={g} puedeIr={puedeIr} alIr={alIr} />
          ))}
        </div>
      );
  }

  return (
    <section className="silice-mesa__bloque silice-mesa__pendientes" aria-labelledby={idTitulo}>
      <h2 id={idTitulo} className="cds--type-heading-compact-02">
        Pendientes
      </h2>
      {cuerpo}
    </section>
  );
}

function Grupo({ grupo, puedeIr, alIr }: { grupo: GrupoRespuesta } & Omit<Props, "carga">) {
  const base = useId();
  const idTitulo = `${base}-titulo`;
  return (
    <div className="silice-mesa__grupo">
      <h3 id={idTitulo} className="silice-mesa__grupo-titulo cds--type-heading-compact-01">
        {grupo.titulo}
      </h3>
      <ul className="silice-mesa__lista" aria-labelledby={idTitulo}>
        {grupo.items.map((item, i) => {
          const idTexto = `${base}-${i}`;
          return (
            <li key={`${item.obra}-${i}`} className="silice-mesa__pendiente">
              <span className="silice-mesa__pendiente-obra cds--type-label-01">{item.obra_nombre}</span>
              <span id={idTexto} className="silice-mesa__pendiente-texto cds--type-body-compact-01">
                {item.texto}
              </span>
              {puedeIr(item.accion.pagina) && (
                <Button kind="ghost" size="sm" aria-describedby={idTexto} onClick={() => alIr(item.obra, item.accion.pagina)}>
                  {item.accion.texto}
                </Button>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
