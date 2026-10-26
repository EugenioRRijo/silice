import { act, render, renderHook, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { afterEach, describe, expect, test, vi } from "vitest";
import { DialogoSalida } from "./DialogoSalida";
import { EnlaceSeguro, useNavegarSeguro } from "./EnlaceSeguro";
import { cancelarSalida } from "./salida";
import { formulariosSucios, olvidarFormularios, useFormularioSucio } from "./sucio";

afterEach(() => {
  cancelarSalida();
  olvidarFormularios();
});

function Ruta() {
  return <output data-testid="ruta">{useLocation().pathname}</output>;
}

function pintar(desde: string, alNavegar = vi.fn()) {
  render(
    <MemoryRouter initialEntries={[desde]}>
      <EnlaceSeguro to="/auditoria" alNavegar={alNavegar}>
        Auditoría
      </EnlaceSeguro>
      <EnlaceSeguro to="/componer">Componer</EnlaceSeguro>
      <Ruta />
      <DialogoSalida />
    </MemoryRouter>,
  );
  return alNavegar;
}

const ruta = () => screen.getByTestId("ruta").textContent;

describe("EnlaceSeguro", () => {
  test("sin formularios sucios navega de una vez y avisa con alNavegar", async () => {
    const alNavegar = pintar("/componer");
    await userEvent.click(screen.getByRole("link", { name: "Auditoría" }));
    expect(ruta()).toBe("/auditoria");
    expect(alNavegar).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("con un formulario sucio pregunta; «Quedarme» no navega ni avisa", async () => {
    const alNavegar = pintar("/componer");
    renderHook(() => useFormularioSucio("componer", true));
    await userEvent.click(screen.getByRole("link", { name: "Auditoría" }));
    expect(screen.getByRole("dialog", { name: "Cambios sin guardar" })).toBeInTheDocument();
    expect(ruta()).toBe("/componer");
    await userEvent.click(screen.getByRole("button", { name: "Quedarme" }));
    expect(ruta()).toBe("/componer");
    expect(alNavegar).not.toHaveBeenCalled();
  });

  test("«Salir y descartar» navega, avisa y deja la lista de sucios vacía", async () => {
    const alNavegar = pintar("/componer");
    renderHook(() => useFormularioSucio("componer", true));
    await userEvent.click(screen.getByRole("link", { name: "Auditoría" }));
    await userEvent.click(screen.getByRole("button", { name: "Salir y descartar" }));
    await waitFor(() => expect(ruta()).toBe("/auditoria"));
    expect(alNavegar).toHaveBeenCalledTimes(1);
    expect(formulariosSucios()).toEqual([]);
  });

  test("volver a la misma pantalla no pregunta", async () => {
    pintar("/componer");
    renderHook(() => useFormularioSucio("componer", true));
    await userEvent.click(screen.getByRole("link", { name: "Componer" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(ruta()).toBe("/componer");
  });

  test("es un enlace de navegación: marca aria-current en su pantalla", () => {
    pintar("/auditoria");
    expect(screen.getByRole("link", { name: "Auditoría" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Componer" })).not.toHaveAttribute("aria-current");
  });
});

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
