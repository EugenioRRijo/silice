import { SideNav, SideNavItems, SideNavLink } from "@carbon/react";
import { NavLink } from "react-router";
import { enlaceClasico, estaMigrada, rutaDe, seccionesVisibles } from "./rutas";
import type { PaginaDef } from "./rutas";

interface Props {
  paginas: readonly PaginaDef[];
  acciones: readonly string[];
  modoEntrega: boolean;
  // Base de la interfaz Streamlit, si se conoce.
  urlClasica?: string | null;
  abierto: boolean;
  alCerrar: () => void;
}

function PaginaSinMigrar({ pagina, urlClasica }: { pagina: PaginaDef; urlClasica?: string | null }) {
  const enlace = enlaceClasico(urlClasica, pagina);
  return (
    <li className="silice-menu__pendiente cds--side-nav__item">
      <span className="silice-menu__titulo cds--type-body-compact-01" aria-disabled="true">
        {pagina.titulo}
      </span>
      <span className="silice-menu__nota cds--type-label-01">
        {enlace ? (
          <a href={enlace} target="_blank" rel="noopener noreferrer" className="silice-menu__clasica">
            En la interfaz clásica<span className="cds--visually-hidden">: abrir {pagina.titulo}</span>
          </a>
        ) : (
          "En la interfaz clásica"
        )}
      </span>
    </li>
  );
}

// Menu por rol y modo entrega, con las mismas secciones que Streamlit. Las paginas aun no migradas se ven
// deshabilitadas (que la persona sepa que existen) y, si se conoce, enlazan a la interfaz clasica.
export function MenuLateral({ paginas, acciones, modoEntrega, urlClasica, abierto, alCerrar }: Props) {
  const secciones = seccionesVisibles(acciones, modoEntrega, paginas);
  return (
    <SideNav aria-label="Menú principal" expanded={abierto} onSideNavBlur={alCerrar} onOverlayClick={alCerrar} isPersistent>
      <SideNavItems>
        {secciones.map(({ seccion, paginas: delaSeccion }) => (
          <li key={seccion} className="silice-menu__seccion">
            <h2 id={`menu-${seccion}`} className="silice-menu__rotulo cds--type-label-01">
              {seccion}
            </h2>
            <ul aria-labelledby={`menu-${seccion}`} className="silice-menu__lista">
              {delaSeccion.map((pagina) =>
                estaMigrada(pagina) ? (
                  // tabIndex 0 a proposito: Carbon lo pone en -1 si el menu no esta "expandido", pero en pantalla ancha esta
                  // siempre a la vista; en angosta, cerrado, el propio SideNav lo marca inert y no hay foco posible.
                  <SideNavLink key={pagina.id} as={NavLink} to={rutaDe(pagina)} onClick={alCerrar} tabIndex={0}>
                    {pagina.titulo}
                  </SideNavLink>
                ) : (
                  <PaginaSinMigrar key={pagina.id} pagina={pagina} urlClasica={urlClasica} />
                ),
              )}
            </ul>
          </li>
        ))}
      </SideNavItems>
    </SideNav>
  );
}
