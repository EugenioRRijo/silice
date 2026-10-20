import { Button } from "@carbon/react";
import { NavLink, useLocation } from "react-router";
import { estaMigrada, paginaPorId, rutaDe, visible } from "./rutas";
import type { PaginaDef } from "./rutas";
import { pasoDeRuta, terminarRecorrido, useRecorrido } from "./recorrido";

interface Props {
  paginas: readonly PaginaDef[];
  acciones: readonly string[];
  modoEntrega: boolean;
}

// «Recorrido en curso» del panel izquierdo (spec §2.3): los pasos, el actual con su «que hacer» y «sabra que termino
// cuando». El paso sale de la pantalla abierta; fuera de ellas ninguno es el actual y los pasos siguen siendo enlaces.
export function PanelRecorrido({ paginas, acciones, modoEntrega }: Props) {
  const recorrido = useRecorrido();
  const { pathname } = useLocation();
  if (!recorrido) return null;
  const actual = pasoDeRuta(recorrido, pathname);
  const total = recorrido.pasos.length;

  return (
    <section className="silice-recorrido" aria-labelledby="recorrido-titulo">
      <div id="recorrido-titulo" className="silice-menu__rotulo cds--type-label-01">
        Recorrido en curso
      </div>
      <p className="silice-recorrido__nombre cds--type-body-compact-01">{recorrido.titulo}</p>
      {actual !== null && (
        <p className="silice-recorrido__avance cds--type-label-01">{`Paso ${actual + 1} de ${total}`}</p>
      )}
      <ol className="silice-recorrido__pasos">
        {recorrido.pasos.map((paso, i) => {
          const pagina = paginaPorId(paso.pagina, paginas);
          const enlazable = pagina !== undefined && estaMigrada(pagina) && visible(pagina, acciones, modoEntrega);
          const esActual = i === actual;
          return (
            <li key={paso.pagina} aria-current={esActual ? "step" : undefined} className="silice-recorrido__paso">
              {enlazable ? (
                <NavLink to={rutaDe(pagina)} className="silice-recorrido__enlace cds--type-body-compact-01">
                  {paso.titulo}
                </NavLink>
              ) : (
                <span className="cds--type-body-compact-01">{paso.titulo}</span>
              )}
              {esActual && (
                <div className="silice-recorrido__detalle cds--type-body-compact-01">
                  <p>{paso.queHacer}</p>
                  <p>{paso.sabraQueTermino}</p>
                </div>
              )}
            </li>
          );
        })}
      </ol>
      <Button kind="ghost" size="sm" onClick={terminarRecorrido}>
        Terminar recorrido
      </Button>
    </section>
  );
}
