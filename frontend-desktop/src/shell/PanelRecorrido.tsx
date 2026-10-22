import { Button } from "@carbon/react";
import { NavLink, useLocation } from "react-router";
import { paginaPorId, rutaDe, visible } from "./rutas";
import type { PaginaDef } from "./rutas";
import { pasoDeRuta, terminarRecorrido, useRecorrido } from "./recorrido";

interface Props {
  paginas: readonly PaginaDef[];
  acciones: readonly string[];
  modoEntrega: boolean;
}

// «Recorrido en curso» del panel izquierdo (spec §2.3): los pasos, el actual con su «que hacer» y «sabra que termino
// cuando». El paso sale de la pantalla abierta; fuera de ellas ninguno es el actual y los pasos siguen siendo enlaces.
// Al terminar, el panel (y con el su boton) desaparece: el foco pasa al primer enlace del menu (VD-7).
function alTerminar() {
  terminarRecorrido();
  document.querySelector<HTMLElement>('nav[aria-label="Menú principal"] a[href]')?.focus();
  // Con el menu cerrado (pantalla angosta) ese enlace no recibe el foco: va al boton que abre el menu.
  if (document.activeElement === document.body) document.querySelector<HTMLElement>(".cds--header__menu-toggle")?.focus();
}

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
          const enlazable = pagina !== undefined && visible(pagina, acciones, modoEntrega);
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
      <Button kind="ghost" size="sm" onClick={alTerminar}>
        Terminar recorrido
      </Button>
    </section>
  );
}
