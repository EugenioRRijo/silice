import { ChevronDown } from "@carbon/icons-react";
import { Header, HeaderGlobalBar, HeaderMenuButton, HeaderName, HeaderNavigation } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import type { FocusEvent, KeyboardEvent, ReactNode } from "react";
import { NavLink, useLocation } from "react-router";
import { areaActual, type EntradaNav } from "./navegacion";
import { PanelDeArea } from "./PanelDeArea";
import { rutaDe } from "./rutas";
import "./BarraSuperior.scss";

interface Props {
  entradas: readonly EntradaNav[];
  // Lado derecho (carpeta y proyecto, recorrido, tamano de letra, cuenta): va dentro de `HeaderGlobalBar`.
  derecha: ReactNode;
  // Boton del menu en capa (ancho estrecho o letra grande); el CSS lo muestra solo por debajo del umbral.
  menu: { abierto: boolean; alternar: () => void };
}

// Barra superior: «Sílice», las areas y el lado derecho. Un area con una sola pantalla es un enlace; con varias, un boton
// que abre su panel (patron «disclosure» de navegacion, nunca al pasar el raton). Un solo panel abierto; se cierra con Esc
// (el foco vuelve al boton), con un clic fuera, cuando el foco sale de la navegacion, al elegir una pantalla, al abrir
// otra area, al cambiar de ruta (tambien atras/adelante del navegador) y al cambiar el tamano de letra.
export function BarraSuperior({ entradas, derecha, menu }: Props) {
  const ubicacion = useLocation();
  const [abierta, setAbierta] = useState<string | null>(null);
  const [clave, setClave] = useState(ubicacion.key);
  const itemAbierto = useRef<HTMLLIElement>(null);

  // Cambio de ruta: el panel se cierra (se ajusta el estado durante el render, sin efecto).
  if (clave !== ubicacion.key) {
    setClave(ubicacion.key);
    setAbierta(null);
  }

  useEffect(() => {
    if (!abierta) return;
    function fuera(e: MouseEvent) {
      if (!itemAbierto.current?.contains(e.target as Node)) setAbierta(null);
    }
    // El tamano de letra lo pone `TamanoLetra` en <html data-silice-letra>: el panel no debe quedar flotando.
    const letra = new MutationObserver(() => setAbierta(null));
    letra.observe(document.documentElement, { attributes: true, attributeFilter: ["data-silice-letra"] });
    document.addEventListener("mousedown", fuera);
    return () => {
      document.removeEventListener("mousedown", fuera);
      letra.disconnect();
    };
  }, [abierta]);

  function alTeclear(e: KeyboardEvent<HTMLLIElement>) {
    if (e.key !== "Escape" || !abierta) return;
    // Esc cierra solo este panel (no el recorrido ni la capa).
    e.stopPropagation();
    setAbierta(null);
    e.currentTarget.querySelector<HTMLButtonElement>(".silice-barra__area")?.focus();
  }

  // Si el foco sale de la navegacion (Tab hacia carpeta, letra o cuenta), el panel se cierra, como en el ejemplo de la APG.
  // Moverse entre areas y enlaces dentro de la navegacion no lo cierra.
  function alSalirFoco(e: FocusEvent<HTMLElement>) {
    if (abierta && !e.currentTarget.contains(e.relatedTarget as Node | null)) setAbierta(null);
  }

  const actual = areaActual(ubicacion.pathname, entradas);
  const claseArea = (area: string) =>
    `silice-barra__area${area === actual ? " silice-barra__area--actual" : ""}`;

  return (
    <Header aria-label="Sílice" className="silice-barra">
      <HeaderMenuButton
        aria-label={menu.abierto ? "Cerrar el menú" : "Abrir el menú"}
        isActive={menu.abierto}
        onClick={menu.alternar}
        aria-expanded={menu.abierto}
      />
      <HeaderName href="#/" prefix="">
        Sílice
      </HeaderName>
      <HeaderNavigation aria-label="Menú principal" className="silice-barra__nav" onBlur={alSalirFoco}>
        {entradas.map((e) => {
          if (e.tipo === "enlace") {
            return (
              <li key={e.area} className="silice-barra__item">
                <NavLink to={rutaDe(e.pagina)} className={`cds--header__menu-item ${claseArea(e.area)}`}>
                  {e.titulo}
                </NavLink>
              </li>
            );
          }
          const abierto = abierta === e.area;
          const idPanel = `silice-panel-area-${e.area}`;
          return (
            <li
              key={e.area}
              className="silice-barra__item"
              ref={abierto ? itemAbierto : undefined}
              onKeyDown={alTeclear}
            >
              <button
                type="button"
                className={claseArea(e.area)}
                aria-expanded={abierto}
                aria-controls={idPanel}
                onClick={() => setAbierta((a) => (a === e.area ? null : e.area))}
              >
                {e.titulo}
                <ChevronDown size={16} aria-hidden="true" className="silice-barra__chevron" />
              </button>
              {abierto && (
                <PanelDeArea id={idPanel} titulo={e.titulo} grupos={e.grupos} alElegir={() => setAbierta(null)} />
              )}
            </li>
          );
        })}
      </HeaderNavigation>
      <HeaderGlobalBar>{derecha}</HeaderGlobalBar>
    </Header>
  );
}
