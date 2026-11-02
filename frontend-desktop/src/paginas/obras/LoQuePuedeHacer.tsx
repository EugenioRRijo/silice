import { useId } from "react";
import type { JSX } from "react";
import { Link } from "react-router";
import { ofertaDe } from "../../marco/oferta";
import { useAplicacion } from "../../shell/contexto";
import { rutaDe } from "../../shell/rutas";
import "./LoQuePuedeHacer.scss";

// Para quien no lee obras (el administrador), la mesa no queda en blanco: las pantallas que su cuenta puede usar y que
// no tienen sitio en la barra lateral (las mismas que ofrece el buscador), cada una con su línea de ayuda. Una lista
// sencilla con divisores, no mosaicos. Reemplaza a los accesos del módulo (Tarea 8 del plan del marco).
export function LoQuePuedeHacer(): JSX.Element {
  const { sesion } = useAplicacion();
  const base = useId();
  const pantallas = ofertaDe(sesion.acciones, sesion.modo_entrega).sueltas;
  const idTitulo = `${base}-titulo`;

  return (
    <section className="silice-accesos" aria-labelledby={idTitulo}>
      <h2 id={idTitulo} className="cds--type-heading-compact-02">
        Lo que puede hacer aquí
      </h2>
      {pantallas.length === 0 ? (
        <p className="silice-accesos__nota cds--type-body-compact-01">
          Lo que su cuenta puede usar está en la barra lateral. Si falta algo, pídale a quien administra Sílice que revise
          su rol.
        </p>
      ) : (
        <ul className="silice-accesos__lista" aria-labelledby={idTitulo}>
          {pantallas.map((p) => {
            const idNombre = `${base}-${p.id}-t`;
            const idAyuda = `${base}-${p.id}-a`;
            return (
              <li key={p.id}>
                <Link to={rutaDe(p)} className="silice-accesos__enlace" aria-labelledby={idNombre} aria-describedby={idAyuda}>
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
      )}
    </section>
  );
}
