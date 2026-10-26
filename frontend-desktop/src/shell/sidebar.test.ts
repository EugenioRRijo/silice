import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import {
  ID_BOTON_SILICE,
  abrirSidebar,
  alternarSidebar,
  cerrarSidebar,
  esEscParaElSidebar,
  estadoSidebar,
  fijarSidebar,
  iniciarSidebar,
  useSidebar,
} from "./sidebar";

// Eventos armados a mano: el destino es el elemento sobre el que se teclea (plan de modulos, MOD-2, foco 2).
function esc(destino: Element, opciones: { tecla?: string; prevenido?: boolean } = {}): KeyboardEvent {
  const e = new KeyboardEvent("keydown", { key: opciones.tecla ?? "Escape", bubbles: true, cancelable: true });
  if (opciones.prevenido) e.preventDefault();
  Object.defineProperty(e, "target", { value: destino });
  return e;
}

function montar(html: string): HTMLElement {
  const caja = document.createElement("div");
  caja.innerHTML = html;
  document.body.append(caja);
  return caja;
}

afterEach(() => {
  document.body.innerHTML = "";
  iniciarSidebar(false);
});

describe("esEscParaElSidebar", () => {
  test("Esc sobre <main> abre el sidebar", () => {
    const caja = montar("<main>contenido</main>");
    expect(esEscParaElSidebar(esc(caja.querySelector("main")!))).toBe(true);
  });

  test("Esc sobre el body (nada con el foco) tambien", () => {
    expect(esEscParaElSidebar(esc(document.body))).toBe(true);
  });

  test.each([
    ["un <input>", "<input id='d' />"],
    ["un <textarea>", "<textarea id='d'></textarea>"],
    ["un <select>", "<select id='d'><option>a</option></select>"],
    ["un campo editable", "<div contenteditable='true' id='d'>x</div>"],
    ["una celda dentro de role=grid", "<div role='grid'><div role='row'><div role='gridcell' id='d' tabindex='0'>1</div></div></div>"],
    ["un role=combobox", "<div role='combobox' id='d' tabindex='0'></div>"],
    ["una lista desplegada (role=listbox)", "<ul role='listbox'><li role='option' id='d'>a</li></ul>"],
    ["un menu (role=menu)", "<ul role='menu'><li role='menuitem' id='d'>a</li></ul>"],
    ["algo dentro de un role=dialog", "<div role='dialog'><button id='d'>Cancelar</button></div>"],
  ])("Esc sobre %s no lo abre (nunca le roba el Esc a un formulario)", (_nombre, html) => {
    const caja = montar(html);
    expect(esEscParaElSidebar(esc(caja.querySelector("#d")!))).toBe(false);
  });

  test("con un [aria-modal=true] en el documento no lo abre aunque el foco este fuera", () => {
    const caja = montar("<main>x</main><div aria-modal='true' role='alertdialog'>¿Seguro?</div>");
    expect(esEscParaElSidebar(esc(caja.querySelector("main")!))).toBe(false);
  });

  test("con un control de la barra abierto (aria-expanded=true) no lo abre: Esc es de ese control", () => {
    const caja = montar(
      "<header class='silice-barra'><button aria-expanded='true'>Obras</button></header><main>x</main>",
    );
    expect(esEscParaElSidebar(esc(caja.querySelector("main")!))).toBe(false);
  });

  test("el propio «Sílice» abierto (aria-expanded=true) no cuenta como control de la barra abierto", () => {
    const caja = montar(
      `<header class='silice-barra'><button id='${ID_BOTON_SILICE}' aria-expanded='true'>Sílice</button><button aria-expanded='false'>Obras</button></header><main>x</main>`,
    );
    expect(esEscParaElSidebar(esc(caja.querySelector("main")!))).toBe(true);
  });

  test("un aria-expanded=true fuera de la barra (p. ej. un acordeon de la pagina) no lo impide", () => {
    const caja = montar("<main><button aria-expanded='true'>Detalle</button></main>");
    expect(esEscParaElSidebar(esc(caja.querySelector("button")!))).toBe(true);
  });

  test("si alguien ya atendio el Esc (defaultPrevented) no lo abre", () => {
    const caja = montar("<main>x</main>");
    expect(esEscParaElSidebar(esc(caja.querySelector("main")!, { prevenido: true }))).toBe(false);
  });

  test.each(["Enter", "Tab", "a", "Esc"])("la tecla «%s» no es Escape", (tecla) => {
    const caja = montar("<main>x</main>");
    expect(esEscParaElSidebar(esc(caja.querySelector("main")!, { tecla }))).toBe(false);
  });
});

describe("almacen del sidebar", () => {
  test("empieza oculto y sin fijar; iniciar toma el fijado de la cuenta y siempre cierra la capa", () => {
    iniciarSidebar(false);
    expect(estadoSidebar()).toEqual({ abierto: false, fijado: false });
    abrirSidebar();
    iniciarSidebar(true);
    expect(estadoSidebar()).toEqual({ abierto: false, fijado: true });
  });

  test("abrir, cerrar y alternar", () => {
    abrirSidebar();
    expect(estadoSidebar().abierto).toBe(true);
    cerrarSidebar();
    expect(estadoSidebar().abierto).toBe(false);
    alternarSidebar();
    expect(estadoSidebar().abierto).toBe(true);
    alternarSidebar();
    expect(estadoSidebar().abierto).toBe(false);
  });

  test("fijar cierra la capa (fijado ya esta a la vista) y ocultar lo devuelve al estado oculto", () => {
    abrirSidebar();
    fijarSidebar(true);
    expect(estadoSidebar()).toEqual({ abierto: false, fijado: true });
    fijarSidebar(false);
    expect(estadoSidebar()).toEqual({ abierto: false, fijado: false });
  });

  test("useSidebar sigue al almacen", () => {
    const { result } = renderHook(() => useSidebar());
    expect(result.current).toEqual({ abierto: false, fijado: false });
    act(() => abrirSidebar());
    expect(result.current).toEqual({ abierto: true, fijado: false });
    act(() => fijarSidebar(true));
    expect(result.current).toEqual({ abierto: false, fijado: true });
  });
});
