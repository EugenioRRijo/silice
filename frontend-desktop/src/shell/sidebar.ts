import { useSyncExternalStore } from "react";

// Sidebar de modulos (diseno 2026-10-25-modulos-design.md §4 y §12.4; plan de modulos, MOD-2). Vive fuera del arbol de
// React, como el recorrido guiado (recorrido.ts): lo abren el boton «Sílice» de la barra y Esc, y lo cierran el propio
// sidebar, la capa y elegir una pantalla. `fijado` es la preferencia de la cuenta (PUT /v1/sesion/preferencias); si se
// ve fijado o no lo decide ademas el ancho (useFijadoPosible), que no vive aqui.
export interface EstadoSidebar {
  // Abierto encima del contenido (en capa).
  abierto: boolean;
  // La cuenta lo quiere siempre a la vista.
  fijado: boolean;
}

// Id del sidebar: lo nombra el `aria-controls` del boton «Sílice».
export const ID_SIDEBAR = "silice-sidebar";

// Id del boton «Sílice» de la barra: el foco vuelve a el al cerrar, y no cuenta como «control de la barra abierto».
export const ID_BOTON_SILICE = "silice-boton-modulos";

let estado: EstadoSidebar = { abierto: false, fijado: false };
const oyentes = new Set<() => void>();

function cambiar(cambio: Partial<EstadoSidebar>): void {
  const siguiente = { ...estado, ...cambio };
  if (siguiente.abierto === estado.abierto && siguiente.fijado === estado.fijado) return;
  estado = siguiente;
  for (const oyente of oyentes) oyente();
}

export function estadoSidebar(): EstadoSidebar {
  return estado;
}

function suscribir(oyente: () => void): () => void {
  oyentes.add(oyente);
  return () => {
    oyentes.delete(oyente);
  };
}

export function useSidebar(): EstadoSidebar {
  return useSyncExternalStore(suscribir, estadoSidebar, estadoSidebar);
}

// Al entrar (o al salir de la sesion): oculto en capa, con el fijado que recuerda la cuenta.
export function iniciarSidebar(fijado: boolean): void {
  cambiar({ abierto: false, fijado });
}

export function abrirSidebar(): void {
  cambiar({ abierto: true });
}

export function cerrarSidebar(): void {
  cambiar({ abierto: false });
}

export function alternarSidebar(): void {
  cambiar({ abierto: !estado.abierto });
}

// Fijar lo deja a la vista sin capa; «Ocultar» lo devuelve al estado oculto. En los dos casos la capa se cierra.
export function fijarSidebar(fijo: boolean): void {
  cambiar({ abierto: false, fijado: fijo });
}

// Donde Esc es de otro: un campo de texto o de seleccion, una celda o tabla editable, un control desplegable o un dialogo.
const DESTINOS_CON_ESC_PROPIO = [
  "input",
  "textarea",
  "select",
  '[contenteditable="true"]',
  '[contenteditable=""]',
  '[contenteditable="plaintext-only"]',
  '[role="grid"]',
  '[role="combobox"]',
  '[role="listbox"]',
  '[role="menu"]',
  '[role="dialog"]',
].join(", ");

// Esc abre el sidebar solo si no es de nadie mas (diseno §4: «nunca roba Esc a un formulario»; choque 9 del plan): la
// tecla es Escape, nadie la atendio ya, el foco no esta en un campo, una tabla editable, un control desplegable ni un
// dialogo, no hay ningun dialogo modal abierto y ningun control de la barra (panel de area, carpeta, cuenta) esta
// desplegado, salvo el propio «Sílice».
export function esEscParaElSidebar(e: KeyboardEvent): boolean {
  if (e.key !== "Escape" || e.defaultPrevented) return false;
  const destino = e.target;
  if (destino instanceof Element && destino.closest(DESTINOS_CON_ESC_PROPIO)) return false;
  if (document.querySelector('[aria-modal="true"]')) return false;
  const desplegados = document.querySelectorAll('header.silice-barra [aria-expanded="true"]');
  return Array.from(desplegados).every((control) => control.id === ID_BOTON_SILICE);
}
