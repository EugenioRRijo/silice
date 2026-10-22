import { ChevronDown, ChevronUp } from "@carbon/icons-react";
import { SideNav, SideNavItems, SideNavLink } from "@carbon/react";
import { useState } from "react";
import { NavLink, useLocation } from "react-router";
import { PanelRecorrido } from "./PanelRecorrido";
import { useRecorrido } from "./recorrido";
import { areasVisibles, herramientasVisibles, rutaDe } from "./rutas";
import type { AreaVisible, PaginaDef } from "./rutas";

interface Props {
  paginas: readonly PaginaDef[];
  acciones: readonly string[];
  modoEntrega: boolean;
  abierto: boolean;
  alCerrar: () => void;
  // Quien tiene la sesion: con la letra grande la cabecera no da para su nombre y el menu en capa lo dice al pie.
  nombre?: string;
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
  alCerrar: () => void;
  // Solo «Más»: su lista se pliega con el boton del rotulo.
  plegable?: { abierto: boolean; alternar: () => void };
}

function Area({ area, alCerrar, plegable }: PropsArea) {
  const idRotulo = `menu-area-${area.id}`;
  const idLista = `menu-lista-${area.id}`;
  return (
    <li className="silice-menu__seccion">
      <div id={idRotulo} className="silice-menu__rotulo cds--type-label-01">
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
      </div>
      <p id={`${idRotulo}-ayuda`} className="silice-menu__descripcion cds--type-helper-text-01">
        {area.descripcion}
      </p>
      <ul id={idLista} aria-labelledby={idRotulo} aria-describedby={`${idRotulo}-ayuda`} className="silice-menu__lista" hidden={plegable ? !plegable.abierto : undefined}>
        {area.paginas.map((pagina) => (
          <EnlaceDePagina key={pagina.id} pagina={pagina} alCerrar={alCerrar} />
        ))}
      </ul>
    </li>
  );
}

// Los rotulos de area son texto, no encabezados: el unico h1 de la pagina es lo primero que se anuncia y no hay h2 de
// 12 px antes de el (VB-15).
// Menu por rol y modo entrega, en cinco areas con su descripcion (spec del Inicio, §2.2) y, arriba, las tres
// herramientas principales (§2.3). Un solo menu lateral: la barra superior del spec nacio para Streamlit; aqui su
// equivalente es este SideNav.
export function MenuLateral({ paginas, acciones, modoEntrega, abierto, alCerrar, nombre }: Props) {
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
            <div id="menu-herramientas" className="silice-menu__rotulo cds--type-label-01">
              Herramientas principales
            </div>
            <ul aria-labelledby="menu-herramientas" className="silice-menu__lista">
              {herramientas.map((h) => (
                <SideNavLink
                  key={h.pagina}
                  as={NavLink}
                  to={rutaDe({ id: h.pagina })}
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
            alCerrar={alCerrar}
            plegable={area.id === "mas" ? { abierto: masAbierto, alternar: () => setMasAbierto((a) => !a) } : undefined}
          />
        ))}
        {nombre && <li className="silice-menu__sesion cds--type-helper-text-01">Sesión de {nombre}</li>}
      </SideNavItems>
    </SideNav>
  );
}
