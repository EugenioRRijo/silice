import { act, render, renderHook, screen } from "@testing-library/react";
import { useEffect } from "react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { afterEach, describe, expect, test } from "vitest";
import { DialogoSalida } from "./DialogoSalida";
import { useNavegarSeguro } from "./navegarSeguro";
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
