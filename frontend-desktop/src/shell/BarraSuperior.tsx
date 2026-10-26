import { ChevronDown, Menu } from "@carbon/icons-react";
import { Header, HeaderGlobalBar, HeaderNavigation } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import type { FocusEvent, KeyboardEvent, ReactNode } from "react";
import { useLocation } from "react-router";
import { EnlaceSeguro } from "./EnlaceSeguro";
import { areaActual, type EntradaNav } from "./navegacion";
import { PanelDeArea } from "./PanelDeArea";
import { rutaDe, type ModuloDef } from "./rutas";
import { ID_BOTON_SILICE, ID_SIDEBAR } from "./sidebar";
import "./BarraSuperior.scss";

interface Props {
  // Modulo abierto: su nombre va junto a «Sílice» y sus areas son las `entradas`. null si la cuenta no ve ninguno.
  modulo: ModuloDef | null;
  entradas: readonly EntradaNav[];
  // Lado derecho (carpeta y proyecto, recorrido, tamano de letra, cuenta): va dentro de `HeaderGlobalBar`.
  derecha: ReactNode;
  // El sidebar de modulos que abre «Sílice»: `abierto` = en capa encima del contenido; `visible` = en capa o fijado.
  sidebar: { abierto: boolean; visible: boolean; alternar: () => void };
}

// El nombre accesible dice lo que hace el boton (empieza por «Sílice», el texto que se ve): abrir los modulos (oculto),
// cerrarlos (en capa) o, fijado, ir a ellos (pulsarlo lleva el foco al modulo actual; ocultarlo es «Ocultar», al pie).
function nombreDeSilice(sidebar: Props["sidebar"]): string {
  if (!sidebar.visible) return "Sílice, abrir los módulos";
  return sidebar.abierto ? "Sílice, cerrar los módulos" : "Sílice, ir a los módulos";
}

// Barra superior: el boton «Sílice» (abre el sidebar de modulos), el nombre del modulo abierto, sus areas y el lado
// derecho. El nombre del modulo es texto, no enlace (no es otro camino al inicio: ya estan el sidebar y el area
// «Inicio»). Las areas son enlaces seguros (preguntan antes de perder trabajo). Un area con una sola pantalla es un enlace; con varias, un boton
// que abre su panel (patron «disclosure» de navegacion, nunca al pasar el raton). Un solo panel abierto; se cierra con Esc
// (el foco vuelve al boton), con un clic fuera, cuando el foco sale de la navegacion, al elegir una pantalla, al abrir
// otra area, al cambiar de ruta (tambien atras/adelante del navegador) y al cambiar el tamano de letra.
export function BarraSuperior({ modulo, entradas, derecha, sidebar }: Props) {
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
      <button
        type="button"
        id={ID_BOTON_SILICE}
        className="silice-barra__silice"
        aria-label={nombreDeSilice(sidebar)}
        aria-expanded={sidebar.visible}
        aria-controls={sidebar.visible ? ID_SIDEBAR : undefined}
        onClick={sidebar.alternar}
      >
        <Menu size={20} aria-hidden="true" />
        <span>Sílice</span>
      </button>
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
                <EnlaceSeguro to={rutaDe(e.pagina)} className={`cds--header__menu-item ${claseArea(e.area)}`}>
                  {e.titulo}
                </EnlaceSeguro>
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
