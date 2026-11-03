import { useRef } from "react";
import type { FocusEvent, JSX, KeyboardEvent } from "react";
import { PanelLateral } from "../../comun/PanelLateral";
import { enfocables, useAtraparFoco } from "../../shell/useAtraparFoco";
import { ComponerPartida } from "../componer/ComponerPartida";
import type { PartidaCompuesta } from "../componer/ComponerPartida";

const AVISO_DEL_CATALOGO = "Esto cambia el catálogo de la empresa: la partida queda para todas las obras.";

// Con qué se pidió componer: el código escrito en «Partida» o, si lo escrito no parecía un código, su descripción (y el
// código vacío, por elegir en el panel; pulido F5, Tarea 1).
export interface PartidaPorComponer {
  codigo: string;
  descripcion: string;
}

interface Props {
  // Con qué se pidió componer, o null con el panel cerrado.
  partida: PartidaPorComponer | null;
  alCerrar: () => void;
  alGuardar: (partida: PartidaCompuesta) => void;
}

type CampoDeTexto = HTMLInputElement | HTMLTextAreaElement;

// Los campos que se escriben (no los botones, casillas ni listas desplegables): los que Esc puede devolver a su valor.
const TIPOS_SIN_TEXTO = new Set(["button", "checkbox", "radio", "submit", "reset", "file", "range", "color", "image"]);
function campoDeTexto(elemento: EventTarget): CampoDeTexto | null {
  if (elemento instanceof HTMLTextAreaElement) return elemento;
  if (elemento instanceof HTMLInputElement && !TIPOS_SIN_TEXTO.has(elemento.type)) return elemento;
  return null;
}

// Devuelve un campo controlado por React a `valor`: el valor se pone con el `set` nativo y el evento `input` hace que React
// lo lea como lo escrito (su `onChange` actualiza el estado de quien lo pinta).
function restaurar(campo: CampoDeTexto, valor: string) {
  const prototipo = campo instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(prototipo, "value")?.set?.call(campo, valor);
  campo.dispatchEvent(new Event("input", { bubbles: true }));
}

// Por qué existe (plan F4, Tarea 9, baja 21): «Componer una partida nueva» ya no sale de la obra; se abre en el panel
// ancho, junto al diálogo «Agregar partida», que espera oculto y queda con la partida guardada elegida. El aviso del
// catálogo va siempre a la vista: lo que se guarda aquí sirve a todas las obras. Solo lo usa ese diálogo; la composición
// es la misma de la pantalla `componer` (`ComponerPartida`).
//
// Foco (WCAG 2.4.3): el panel va en la capa modal del diálogo, con un velo a pantalla completa, y `PanelLateral` no atrapa
// el foco (las Tareas 6 y 7 lo usan sin velo). Aquí se atrapa con un contenedor `display: contents` (no cambia la
// maquetación): Tab y Mayús+Tab circulan solo dentro del panel. Mayús+Tab desde el título (el foco inicial, que no está
// en el orden de tabulación) también da la vuelta. Los eventos del diálogo «Precios distintos…» (otro sitio del DOM) llegan
// aquí por el árbol de React, pero su foco no es ni el primero ni el último del panel, así que no los toca.
//
// Capa (pasada de navegador del cierre de F4, H1): el panel va «en-capa», siempre por encima del velo, fijo bajo la barra
// superior, opaco y con su propio desplazamiento, con cualquier letra. Antes eso lo daba una regla de hijo directo del
// fondo que nunca aplicaba por este envoltorio, y con letra Normal el panel salía transparente y de 2190 px de alto.
//
// Esc (pulido F5, Tarea 2; H6 de la pasada): el contenedor lo atiende antes que nadie. Con una lista de sugerencias abierta
// la deja cerrarse; en un campo de texto que cambió desde que recibió el foco, lo devuelve a ese valor (como las celdas de
// la Hoja) y el panel sigue; en cualquier otro caso cierra el panel de una vez (un campo con lo elegido ya no lo borra
// antes). Solo lo que nace dentro del panel en el DOM: el Esc de «Precios distintos…» es de su diálogo.
export function ComponerEnPanel({ partida, alCerrar, alGuardar }: Props): JSX.Element | null {
  const contenedor = useRef<HTMLDivElement>(null);
  const atrapar = useAtraparFoco(contenedor);
  // El valor de cada campo al recibir el foco: a él vuelve el primer Esc.
  const alEntrar = useRef(new WeakMap<CampoDeTexto, string>());

  const alEnfocar = (e: FocusEvent<HTMLDivElement>) => {
    const campo = campoDeTexto(e.target);
    if (campo !== null) alEntrar.current.set(campo, campo.value);
  };

  const alEsc = (e: KeyboardEvent<HTMLDivElement>) => {
    const caja = contenedor.current;
    if (e.key !== "Escape" || caja === null || !caja.contains(e.target as Node)) return;
    const objetivo = e.target as HTMLElement;
    if (objetivo.getAttribute("role") === "combobox" && objetivo.getAttribute("aria-expanded") === "true") return;
    e.preventDefault();
    e.stopPropagation();
    const campo = campoDeTexto(objetivo);
    const previo = campo === null ? undefined : alEntrar.current.get(campo);
    if (campo !== null && previo !== undefined && campo.value !== previo) {
      restaurar(campo, previo);
      return;
    }
    alCerrar();
  };

  const alTeclear = (e: KeyboardEvent<HTMLDivElement>) => {
    const caja = contenedor.current;
    const activo = document.activeElement;
    if (
      e.key === "Tab" &&
      e.shiftKey &&
      caja &&
      activo instanceof HTMLElement &&
      activo.tagName === "H2" &&
      caja.contains(activo)
    ) {
      e.preventDefault();
      enfocables(caja).at(-1)?.focus();
      return;
    }
    atrapar(e);
  };
  return (
    <div ref={contenedor} style={{ display: "contents" }} onKeyDown={alTeclear} onKeyDownCapture={alEsc} onFocusCapture={alEnfocar}>
      <PanelLateral titulo="Componer una partida" abierto={partida !== null} alCerrar={alCerrar} ancho="ancho" modo="en-capa">
        <p role="note" className="silice-hoja__aviso-catalogo cds--type-body-compact-01">
          {AVISO_DEL_CATALOGO}
        </p>
        {partida !== null && (
          <ComponerPartida
            codigoInicial={partida.codigo}
            descripcionInicial={partida.descripcion}
            nivelDelTitulo={2}
            alGuardar={alGuardar}
          />
        )}
      </PanelLateral>
    </div>
  );
}
