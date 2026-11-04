import { Button } from "@carbon/react";
import { Close } from "@carbon/icons-react";
import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import type { JSX, KeyboardEvent, ReactNode } from "react";
import "./PanelLateral.scss";

export interface PropsDelPanelLateral {
  titulo: string;
  abierto: boolean;
  alCerrar: () => void;
  // «normal» mide 24 rem; «ancho», 40 rem (el APU de una partida, con sus tablas por rubro).
  ancho?: "normal" | "ancho";
  // «acoplado» (por omisión): junto al contenido si cabe; si no, por encima y lo que tapa queda inerte. «en-capa»: dentro de
  // la capa de un diálogo (Componer), siempre por encima; la capa ya deja inerte la página y quien lo usa atrapa el foco.
  modo?: "acoplado" | "en-capa";
  children: ReactNode;
}

// Lo que el contenido de la izquierda necesita, como mínimo, para que su tabla se lea junto al panel (pasada de navegador
// del cierre de F4, H2): a 1366 px con letra Normal el panel ancho dejaba la tabla en 251 px, solo su columna fija.
const MINIMO_DEL_CONTENIDO_REM = 32;
const ESPACIO_REM = 1;
const ANCHO_REM = { normal: 24, ancho: 40 } as const;

function remEnPx(): number {
  const px = Number.parseFloat(getComputedStyle(document.documentElement).fontSize);
  return Number.isFinite(px) && px > 0 ? px : 16;
}

// Si el panel, el espacio y el mínimo del contenido no caben en el contenedor. Sin medida (0: jsdom, o aún sin maquetar)
// no se decide nada y el panel se queda acoplado.
function noCabe(anchoDelContenedor: number, ancho: "normal" | "ancho"): boolean {
  if (anchoDelContenedor <= 0) return false;
  return anchoDelContenedor < (ANCHO_REM[ancho] + ESPACIO_REM + MINIMO_DEL_CONTENIDO_REM) * remEnPx();
}

// Lo fijo (la barra superior, la barra lateral pegada) tapa según su caja en la ventana. Lo que va en el flujo se desplaza
// por debajo del panel, que ocupa toda la altura: basta con que se crucen a lo ancho.
function loTapa(panel: DOMRect, elemento: Element): boolean {
  const r = elemento.getBoundingClientRect();
  if (r.right - r.left <= 0 || r.bottom - r.top <= 0) return false;
  const aLoAncho = r.left < panel.right - 1 && r.right > panel.left + 1;
  if (!aLoAncho) return false;
  const posicion = getComputedStyle(elemento).position;
  if (posicion !== "fixed" && posicion !== "sticky") return true;
  return r.top < panel.bottom - 1 && r.bottom > panel.top + 1;
}

// Pone `inert` en lo que el panel tapa: los hermanos del panel y de cada antepasado hasta `body`, enteros, si se cruzan con
// él. Un envoltorio `display: contents` no tiene caja: se miran sus hijos. No toca lo que ya era inerte (un diálogo abierto
// lo deja así y lo suelta él). Devuelve lo que puso, para quitarlo.
function volverInerteLoTapado(panel: HTMLElement): Element[] {
  const caja = panel.getBoundingClientRect();
  const puestos: Element[] = [];
  const mirar = (elemento: Element) => {
    if (elemento.hasAttribute("inert") || elemento.tagName === "SCRIPT" || elemento.tagName === "STYLE") return;
    if (getComputedStyle(elemento).display === "contents") {
      for (const hijo of Array.from(elemento.children)) mirar(hijo);
      return;
    }
    if (loTapa(caja, elemento)) {
      elemento.setAttribute("inert", "");
      puestos.push(elemento);
    }
  };
  let nodo: Element = panel;
  while (nodo.parentElement !== null && nodo !== document.body) {
    const padre: Element = nodo.parentElement;
    for (const hermano of Array.from(padre.children)) if (hermano !== nodo) mirar(hermano);
    nodo = padre;
  }
  return puestos;
}

// Por qué existe (plan F4, Tareas 6 y 7): el inventario pide un panel acoplado a la derecha en las cuatro secciones de la
// obra: el APU de una partida (Tarea 7, el primero que lo usa), el registro de cambios de una versión (Tarea 6), Componer
// (Tarea 9) y el informe de importación (Tarea 11). No es un diálogo (RNF-22: los diálogos son los propios del proyecto):
// es una región que se queda junto al contenido, como la columna del recorrido, y no atrapa el foco. Quien lo usa lo pone
// en un contenedor `silice-con-panel` (el contenido a la izquierda, el panel a la derecha). Al abrirse el foco va a su h2;
// Esc o «Cerrar» lo cierran y el foco vuelve al control que lo abrió (el último, si se abrió otra vez con otro título).
// Sin animación.
//
// Pasada de navegador del cierre de F4 (H1, H2 y H3): si el contenedor no tiene ancho para el panel y 32 rem de contenido
// (el ancho real, con cualquier letra), el panel pasa por encima, fijo bajo la barra superior, y lo que tapa queda `inert`
// mientras tanto: Tab no llega a controles que no se ven. Junto al contenido no tapa nada y no se toca nada.
export function PanelLateral({ titulo, abierto, alCerrar, ancho = "normal", modo = "acoplado", children }: PropsDelPanelLateral): JSX.Element | null {
  const idTitulo = useId();
  const panel = useRef<HTMLElement>(null);
  const encabezado = useRef<HTMLHeadingElement>(null);
  const disparador = useRef<HTMLElement | null>(null);
  const enCapa = modo === "en-capa";
  const [superpuesto, setSuperpuesto] = useState(false);

  // Al abrirse, o al cambiar de título (otra fila lo abrió), se recuerda quién tenía el foco y el foco pasa al h2. Si el
  // foco ya estaba dentro del panel, el disparador sigue siendo el de antes. Va antes de volver inerte lo tapado (el
  // disparador suele estar ahí y un elemento inerte pierde el foco).
  useLayoutEffect(() => {
    if (!abierto) return;
    const activo = document.activeElement;
    if (activo instanceof HTMLElement && !panel.current?.contains(activo)) disparador.current = activo;
    encabezado.current?.focus();
  }, [abierto, titulo]);

  // Junto al contenido o por encima, según el ancho real del contenedor; se vuelve a medir al cambiar la ventana, el
  // contenedor o la letra. Por encima, lo tapado queda inerte hasta cerrar o volver a caber. Es de maquetación: corre antes
  // de pintar y su limpieza (quitar el inerte) antes de que el foco vuelva al disparador.
  useLayoutEffect(() => {
    const elemento = panel.current;
    if (!abierto || enCapa || elemento === null) return;
    const contenedor = elemento.closest<HTMLElement>(".silice-con-panel") ?? elemento.parentElement;
    let puestos: Element[] = [];
    const soltar = () => {
      for (const e of puestos) e.removeAttribute("inert");
      puestos = [];
    };
    const medir = () => {
      const encima = contenedor !== null && noCabe(contenedor.clientWidth, ancho);
      if (encima !== superpuesto) {
        setSuperpuesto(encima);
        return;
      }
      soltar();
      if (encima) puestos = volverInerteLoTapado(elemento);
    };
    medir();
    window.addEventListener("resize", medir);
    const tamano = typeof ResizeObserver === "undefined" || contenedor === null ? null : new ResizeObserver(medir);
    if (tamano !== null && contenedor !== null) tamano.observe(contenedor);
    const letra = new MutationObserver(medir);
    letra.observe(document.documentElement, { attributes: true, attributeFilter: ["data-silice-letra"] });
    return () => {
      window.removeEventListener("resize", medir);
      tamano?.disconnect();
      letra.disconnect();
      soltar();
    };
  }, [abierto, ancho, enCapa, superpuesto, titulo]);

  // Al cerrarse (o al desmontarse abierto) el foco vuelve al disparador, si sigue en la página.
  useEffect(() => {
    if (!abierto) return;
    return () => {
      const anterior = disparador.current;
      disparador.current = null;
      if (anterior?.isConnected) anterior.focus();
    };
  }, [abierto]);

  if (!abierto) return null;

  // Esc cierra solo si nació dentro del panel (en el DOM: un diálogo abierto desde aquí se pinta en otro sitio) y si ningún
  // control de dentro lo usó ya (un campo de celda lo usa para volver a su valor).
  const alTeclear = (e: KeyboardEvent<HTMLElement>) => {
    if (e.key !== "Escape" || e.defaultPrevented || !e.currentTarget.contains(e.target as Node)) return;
    e.preventDefault();
    alCerrar();
  };

  const clases = ["silice-panel-lateral"];
  if (ancho === "ancho") clases.push("silice-panel-lateral--ancho");
  if (enCapa || superpuesto) clases.push("silice-panel-lateral--superpuesto");

  return (
    <aside ref={panel} aria-labelledby={idTitulo} className={clases.join(" ")} onKeyDown={alTeclear}>
      <div className="silice-panel-lateral__cabecera">
        <h2 id={idTitulo} ref={encabezado} tabIndex={-1} className="silice-panel-lateral__titulo cds--type-heading-compact-02">
          {titulo}
        </h2>
        <Button kind="ghost" size="sm" renderIcon={Close} onClick={alCerrar}>
          Cerrar
        </Button>
      </div>
      {children}
    </aside>
  );
}
