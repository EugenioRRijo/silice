import { ChevronDown, ChevronUp, Launch } from "@carbon/icons-react";
import { SideNav, SideNavItems, SideNavLink } from "@carbon/react";
import { useState } from "react";
import { NavLink, useLocation } from "react-router";
import { PanelRecorrido } from "./PanelRecorrido";
import { useRecorrido } from "./recorrido";
import { areasVisibles, enlaceClasico, estaMigrada, herramientasVisibles, rutaDe } from "./rutas";
import type { AreaVisible, PaginaDef } from "./rutas";

interface Props {
  paginas: readonly PaginaDef[];
  acciones: readonly string[];
  modoEntrega: boolean;
  // Base de la interfaz Streamlit, si se conoce.
  urlClasica?: string | null;
  abierto: boolean;
  alCerrar: () => void;
}

// Una linea por pagina (32 px): el texto «En la interfaz clásica» se dice una vez, visible, sobre el grupo, y en cada
// elemento va oculto a la vista para quien lee con un lector de pantalla.
function PaginaSinMigrar({ pagina, urlClasica }: { pagina: PaginaDef; urlClasica?: string | null }) {
  const enlace = enlaceClasico(urlClasica, pagina);
  return (
    <li className="silice-menu__pendiente cds--side-nav__item">
      {enlace ? (
        <a href={enlace} target="_blank" rel="noopener noreferrer" className="silice-menu__clasica cds--type-body-compact-01">
          <span>{pagina.titulo}</span>
          <Launch size={16} aria-hidden="true" />
          <span className="cds--visually-hidden">En la interfaz clásica</span>
        </a>
      ) : (
        <span className="silice-menu__titulo cds--type-body-compact-01" aria-disabled="true">
          {pagina.titulo}
          <span className="cds--visually-hidden"> En la interfaz clásica</span>
        </span>
      )}
    </li>
  );
}

// tabIndex 0 a proposito: Carbon lo pone en -1 si el menu no esta "expandido", pero en pantalla ancha esta siempre a
// la vista; en angosta, cerrado, el propio SideNav lo marca inert.
function EnlaceDePagina({ pagina, alCerrar }: { pagina: PaginaDef; alCerrar: () => void }) {
  return (
    <SideNavLink as={NavLink} to={rutaDe(pagina)} onClick={alCerrar} tabIndex={0}>
      {pagina.titulo}
    </SideNavLink>
  );
}

interface PropsArea {
  area: AreaVisible;
  urlClasica?: string | null;
  alCerrar: () => void;
  // Solo «Más»: su lista se pliega con el boton del rotulo.
  plegable?: { abierto: boolean; alternar: () => void };
}

function Area({ area, urlClasica, alCerrar, plegable }: PropsArea) {
  // Las ya migradas arriba, que son las que se pueden abrir aqui.
  const migradas = area.paginas.filter(estaMigrada);
  const pendientes = area.paginas.filter((p) => !estaMigrada(p));
  const idRotulo = `menu-area-${area.id}`;
  const idLista = `menu-lista-${area.id}`;
  return (
    <li className="silice-menu__seccion">
      <h2 id={idRotulo} className="silice-menu__rotulo cds--type-label-01">
        {plegable ? (
          <button
            type="button"
            className="silice-menu__plegar cds--type-label-01"
            aria-expanded={plegable.abierto}
            aria-controls={idLista}
            onClick={plegable.alternar}
          >
            {area.titulo}
            {plegable.abierto ? <ChevronUp size={16} aria-hidden="true" /> : <ChevronDown size={16} aria-hidden="true" />}
          </button>
        ) : (
          area.titulo
        )}
      </h2>
      <p id={`${idRotulo}-ayuda`} className="silice-menu__descripcion cds--type-helper-text-01">
        {area.descripcion}
      </p>
      <ul id={idLista} aria-labelledby={idRotulo} className="silice-menu__lista" hidden={plegable ? !plegable.abierto : undefined}>
        {migradas.map((pagina) => (
          <EnlaceDePagina key={pagina.id} pagina={pagina} alCerrar={alCerrar} />
        ))}
        {pendientes.length > 0 && (
          <li className="silice-menu__grupo cds--type-label-01" aria-hidden="true">
            En la interfaz clásica
          </li>
        )}
        {pendientes.map((pagina) => (
          <PaginaSinMigrar key={pagina.id} pagina={pagina} urlClasica={urlClasica} />
        ))}
      </ul>
    </li>
  );
}

// Menu por rol y modo entrega, en cinco areas con su descripcion (spec del Inicio, §2.2) y, arriba, las tres
// herramientas principales (§2.3). Un solo menu lateral: la barra superior del spec nacio para Streamlit; aqui su
// equivalente es este SideNav. Las paginas aun no migradas se ven deshabilitadas (que la persona sepa que existen) y,
// si se conoce, enlazan a la interfaz clasica.
export function MenuLateral({ paginas, acciones, modoEntrega, urlClasica, abierto, alCerrar }: Props) {
  const { pathname } = useLocation();
  const recorrido = useRecorrido();
  const areas = areasVisibles(acciones, modoEntrega, paginas);
  const herramientas = herramientasVisibles(acciones, modoEntrega, paginas);
  const mas = areas.find((a) => a.id === "mas");
  const enMas = mas?.paginas.some((p) => rutaDe(p) === pathname) ?? false;
  // «Más» empieza plegado y se abre solo al llegar a una de sus paginas.
  const [masAbierto, setMasAbierto] = useState(enMas);
  const [rutaPrevia, setRutaPrevia] = useState(pathname);
  if (rutaPrevia !== pathname) {
    setRutaPrevia(pathname);
    if (enMas) setMasAbierto(true);
  }

  return (
    <SideNav aria-label="Menú principal" expanded={abierto} onSideNavBlur={alCerrar} onOverlayClick={alCerrar} isPersistent>
      <SideNavItems>
        {herramientas.length > 0 && (
          <li className="silice-menu__seccion silice-menu__herramientas">
            <h2 id="menu-herramientas" className="silice-menu__rotulo cds--type-label-01">
              Herramientas principales
            </h2>
            <ul aria-labelledby="menu-herramientas" className="silice-menu__lista">
              {herramientas.map((h) => (
                <SideNavLink
                  key={h.pagina}
                  as={NavLink}
                  to={`/${h.pagina}`}
                  onClick={alCerrar}
                  tabIndex={0}
                  aria-label={h.titulo}
                  aria-describedby={`menu-herramienta-${h.pagina}`}
                >
                  <span className="silice-menu__herramienta">
                    <span className="silice-menu__herramienta-nombre">{h.titulo}</span>
                    <span id={`menu-herramienta-${h.pagina}`} className="silice-menu__ayuda cds--type-helper-text-01">
                      {h.ayuda}
                    </span>
                  </span>
                </SideNavLink>
              ))}
            </ul>
          </li>
        )}
        {recorrido && (
          <li className="silice-menu__recorrido">
            <PanelRecorrido paginas={paginas} acciones={acciones} modoEntrega={modoEntrega} />
          </li>
        )}
        {areas.map((area) => (
          <Area
            key={area.id}
            area={area}
            urlClasica={urlClasica}
            alCerrar={alCerrar}
            plegable={area.id === "mas" ? { abierto: masAbierto, alternar: () => setMasAbierto((a) => !a) } : undefined}
          />
        ))}
      </SideNavItems>
    </SideNav>
  );
}
