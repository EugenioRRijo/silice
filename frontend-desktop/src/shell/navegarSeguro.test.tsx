import { act, render, renderHook, screen } from "@testing-library/react";
import { useEffect } from "react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { afterEach, describe, expect, test } from "vitest";
import { DialogoSalida } from "./DialogoSalida";
import { esClicSimple, useNavegarSeguro } from "./navegarSeguro";
import { cancelarSalida } from "./salida";
import { olvidarFormularios, useFormularioSucio } from "./sucio";

afterEach(() => {
  cancelarSalida();
  olvidarFormularios();
});

function Ruta() {
  return <output data-testid="ruta">{useLocation().pathname}</output>;
}

const ruta = () => screen.getByTestId("ruta").textContent;

describe("useNavegarSeguro", () => {
  test("sin sucios navega y resuelve true; con sucios y «Quedarme», false sin navegar", async () => {
    const capturado: { navegar: ((to: string) => Promise<boolean>) | null } = { navegar: null };
    function Captura() {
      const navegar = useNavegarSeguro();
      useEffect(() => {
        capturado.navegar = navegar;
      }, [navegar]);
      return null;
    }
    const navegar = (to: string) => capturado.navegar!(to);
    render(
      <MemoryRouter initialEntries={["/componer"]}>
        <Captura />
        <Ruta />
        <DialogoSalida />
      </MemoryRouter>,
    );
    let r: boolean | null = null;
    await act(async () => {
      r = await navegar("/hoja");
    });
    expect(r).toBe(true);
    expect(ruta()).toBe("/hoja");

    renderHook(() => useFormularioSucio("hoja", true));
    let promesa!: Promise<boolean>;
    act(() => {
      promesa = navegar("/auditoria");
    });
    await userEvent.click(screen.getByRole("button", { name: "Quedarme" }));
    await expect(promesa).resolves.toBe(false);
    expect(ruta()).toBe("/hoja");
  });
});

// La guarda de los enlaces del marco y de las barras de espacio: solo el clic principal sin teclas modificadoras ni
// `preventDefault` previo se intercepta; Ctrl/Cmd/Mayús/Alt y el botón del medio los resuelve el navegador (abrir en otra
// pestaña o ventana).
describe("esClicSimple", () => {
  const base = { defaultPrevented: false, button: 0, metaKey: false, ctrlKey: false, shiftKey: false, altKey: false };

  test("el clic principal sin modificadores es simple", () => {
    expect(esClicSimple(base)).toBe(true);
  });

  test.each([
    ["ya cancelado (defaultPrevented)", { defaultPrevented: true }],
    ["botón del medio", { button: 1 }],
    ["botón secundario", { button: 2 }],
    ["con Cmd", { metaKey: true }],
    ["con Ctrl", { ctrlKey: true }],
    ["con Mayús", { shiftKey: true }],
    ["con Alt", { altKey: true }],
  ])("no es simple: %s", (_nombre, cambio) => {
    expect(esClicSimple({ ...base, ...cambio })).toBe(false);
  });
});
