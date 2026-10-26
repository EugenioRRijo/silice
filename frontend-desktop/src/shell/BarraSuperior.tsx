import { ChevronDown } from "@carbon/icons-react";
import { Header, HeaderGlobalBar, HeaderMenuButton, HeaderName, HeaderNavigation } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import type { FocusEvent, KeyboardEvent, ReactNode } from "react";
import { NavLink, useLocation } from "react-router";
import { areaActual, type EntradaNav } from "./navegacion";
import { PanelDeArea } from "./PanelDeArea";
import { rutaDe, type ModuloDef } from "./rutas";
import "./BarraSuperior.scss";

interface Props {
  // Modulo abierto: su nombre va junto a «Sílice» y sus areas son las `entradas`. null si la cuenta no ve ninguno.
  modulo: ModuloDef | null;
  entradas: readonly EntradaNav[];
  // Lado derecho (carpeta y proyecto, recorrido, tamano de letra, cuenta): va dentro de `HeaderGlobalBar`.
  derecha: ReactNode;
  // Boton del menu en capa (ancho estrecho o letra grande); el CSS lo muestra solo por debajo del umbral.
  menu: { abierto: boolean; alternar: () => void };
}

// Barra superior: «Sílice», el nombre del modulo abierto, sus areas y el lado derecho. El nombre del modulo es texto, no
// enlace (no es un tercer camino al inicio: ya estan «Sílice» y el area «Inicio»). Un area con una sola pantalla es un enlace; con varias, un boton
// que abre su panel (patron «disclosure» de navegacion, nunca al pasar el raton). Un solo panel abierto; se cierra con Esc
// (el foco vuelve al boton), con un clic fuera, cuando el foco sale de la navegacion, al elegir una pantalla, al abrir
// otra area, al cambiar de ruta (tambien atras/adelante del navegador) y al cambiar el tamano de letra.
export function BarraSuperior({ modulo, entradas, derecha, menu }: Props) {
  const ubicacion = useLocation();
  const [abierta, setAbierta] = useState<string | null>(null);
  const [clave, setClave] = useState(ubicacion.key);
  const itemAbierto = useRef<HTMLLIElement>(null);
  // Hay un boton del raton apretado dentro de la navegacion (se suelta en cualquier parte del documento).
  const apretadoDentro = useRef(false);

  // Cambio de ruta: el panel se cierra (se ajusta el estado durante el render, sin efecto).
  if (clave !== ubicacion.key) {
    setClave(ubicacion.key);
    setAbierta(null);
  }

  useEffect(() => {
    function soltar() {
      apretadoDentro.current = false;
    }
    document.addEventListener("mouseup", soltar);
    return () => document.removeEventListener("mouseup", soltar);
  }, []);

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
  // Moverse entre areas y enlaces dentro de la navegacion no lo cierra. Un foco que se pierde sin destino mientras el raton
  // esta apretado dentro de la navegacion tampoco: es un clic dentro (p. ej. Safari, donde el boton no toma el foco), y de
  // ese clic se ocupan su `onClick` o el clic fuera.
  function alSalirFoco(e: FocusEvent<HTMLElement>) {
    if (!abierta || e.currentTarget.contains(e.relatedTarget as Node | null)) return;
    if (e.relatedTarget === null && apretadoDentro.current) return;
    setAbierta(null);
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
      {modulo && (
        <span className="silice-barra__modulo cds--type-heading-compact-01" title={modulo.titulo}>
          {modulo.titulo}
        </span>
      )}
      <HeaderNavigation
        aria-label="Menú principal"
        className="silice-barra__nav"
        onBlur={alSalirFoco}
        onMouseDown={() => {
          apretadoDentro.current = true;
        }}
      >
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
