import { useId } from "react";
import type { JSX } from "react";
import { Link } from "react-router";
import "./AccesosDelModulo.scss";
import { useAplicacion } from "./contexto";
import { navegacion } from "./navegacion";
import { rutaDe, type ModuloId, type PaginaDef } from "./rutas";

function areasDe(entradas: ReturnType<typeof navegacion>): { area: string; titulo: string; paginas: PaginaDef[] }[] {
  return entradas
    .filter((e) => e.area !== "inicio")
    .map((e) => ({
      area: e.area,
      titulo: e.titulo,
      paginas: e.tipo === "enlace" ? [e.pagina] : e.grupos.flatMap((g) => g.paginas),
    }));
}

// Las pantallas que la cuenta puede usar en el modulo (sin su inicio), agrupadas por area con un rotulo de texto y cada
// una con su linea de ayuda. Una lista sencilla con divisores, no mosaicos: es el mapa del modulo, no un tablero.
export function AccesosDelModulo({ modulo }: { modulo: ModuloId }): JSX.Element {
  const { sesion } = useAplicacion();
  const base = useId();
  const areas = areasDe(navegacion(modulo, sesion.acciones, sesion.modo_entrega));
  const idTitulo = `${base}-titulo`;

  return (
    <section className="silice-accesos" aria-labelledby={idTitulo}>
      <h2 id={idTitulo} className="cds--type-heading-compact-02">
        Pantallas del módulo
      </h2>
      {areas.length === 0 ? (
        <p className="silice-accesos__nota cds--type-body-compact-01">
          Su cuenta no tiene pantallas en este módulo. Pídale a quien administra Sílice que revise su rol.
        </p>
      ) : (
        areas.map((a) => {
          const idRotulo = `${base}-${a.area}`;
          return (
            <div key={a.area} className="silice-accesos__area">
              <p id={idRotulo} className="silice-accesos__rotulo cds--type-label-01">
                {a.titulo}
              </p>
              <ul className="silice-accesos__lista" aria-labelledby={idRotulo}>
                {a.paginas.map((p) => {
                  const idNombre = `${base}-${p.id}-t`;
                  const idAyuda = `${base}-${p.id}-a`;
                  return (
                    <li key={p.id}>
                      <Link
                        to={rutaDe(p)}
                        className="silice-accesos__enlace"
                        aria-labelledby={idNombre}
                        aria-describedby={idAyuda}
                      >
                        <span id={idNombre} className="silice-accesos__nombre cds--type-body-compact-01">
                          {p.titulo}
                        </span>
                        <span id={idAyuda} className="silice-accesos__ayuda cds--type-helper-text-01">
                          {p.enUnaLinea}
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })
      )}
    </section>
  );
}
