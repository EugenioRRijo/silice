import { act, render, renderHook, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test } from "vitest";
import { DialogoSalida } from "./DialogoSalida";
import { cancelarSalida, confirmarSalida } from "./salida";
import { formulariosSucios, olvidarFormularios, useFormularioSucio } from "./sucio";

afterEach(() => {
  cancelarSalida();
  olvidarFormularios();
});

function dialogo() {
  return screen.getByRole("dialog", { name: "Cambios sin guardar" });
}

// Los titulos son los de rutas.ts, escritos a mano: «componer» es «Componer una partida» y «hoja», «Hoja de la obra».
describe("confirmarSalida y DialogoSalida", () => {
  test("sin nada sucio ni extras resuelve true sin pintar el diálogo", async () => {
    render(<DialogoSalida />);
    let respuesta: boolean | null = null;
    await act(async () => {
      respuesta = await confirmarSalida("salir");
    });
    expect(respuesta).toBe(true);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("una pantalla sucia: «A»; título, texto, botones y foco inicial en «Quedarme»", async () => {
    render(<DialogoSalida />);
    renderHook(() => useFormularioSucio("componer", true));
    let promesa!: Promise<boolean>;
    act(() => {
      promesa = confirmarSalida("salir");
    });
    const caja = dialogo();
    expect(caja).toHaveAttribute("aria-modal", "true");
    expect(caja).toHaveAccessibleDescription(
      "Tiene cambios sin guardar en Componer una partida. Si sale de esta pantalla, se perderán.",
    );
    expect(within(caja).getByRole("button", { name: "Quedarme" })).toHaveFocus();
    expect(within(caja).getByRole("button", { name: "Salir y descartar" })).toBeInTheDocument();
    await userEvent.click(within(caja).getByRole("button", { name: "Quedarme" }));
    await expect(promesa).resolves.toBe(false);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    // Quedarse no descarta nada.
    expect(formulariosSucios()).toEqual(["componer"]);
  });

  test("dos pantallas sucias: «A y B»; «Salir y descartar» resuelve true y olvida los formularios", async () => {
    render(<DialogoSalida />);
    renderHook(() => useFormularioSucio("componer", true));
    renderHook(() => useFormularioSucio("hoja", true));
    let promesa!: Promise<boolean>;
    act(() => {
      promesa = confirmarSalida("salir");
    });
    expect(dialogo()).toHaveAccessibleDescription(
      "Tiene cambios sin guardar en Componer una partida y Hoja de la obra. Si sale de esta pantalla, se perderán.",
    );
    await userEvent.click(screen.getByRole("button", { name: "Salir y descartar" }));
    await expect(promesa).resolves.toBe(true);
    expect(formulariosSucios()).toEqual([]);
  });

  test("dos pantallas y un extra: «A, B y C», con el extra al final", async () => {
    render(<DialogoSalida />);
    renderHook(() => useFormularioSucio("componer", true));
    renderHook(() => useFormularioSucio("hoja", true));
    act(() => {
      void confirmarSalida("salir", ["la obra nueva"]);
    });
    expect(dialogo()).toHaveAccessibleDescription(
      "Tiene cambios sin guardar en Componer una partida, Hoja de la obra y la obra nueva. Si sale de esta pantalla, se perderán.",
    );
  });

  test("solo un extra, sin pantallas sucias, tambien pregunta", async () => {
    render(<DialogoSalida />);
    act(() => {
      void confirmarSalida("salir", ["la obra nueva"]);
    });
    expect(dialogo()).toHaveAccessibleDescription(
      "Tiene cambios sin guardar en la obra nueva. Si sale de esta pantalla, se perderán.",
    );
  });

  test("al cambiar de carpeta el texto y el botón lo dicen", async () => {
    render(<DialogoSalida />);
    renderHook(() => useFormularioSucio("componer", true));
    let promesa!: Promise<boolean>;
    act(() => {
      promesa = confirmarSalida("carpeta");
    });
    expect(dialogo()).toHaveAccessibleDescription(
      "Tiene cambios sin guardar en Componer una partida. Si cambia de carpeta, se perderán.",
    );
    expect(screen.queryByRole("button", { name: "Salir y descartar" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Cambiar y descartar" }));
    await expect(promesa).resolves.toBe(true);
  });

  test("Esc en el diálogo es «Quedarme»", async () => {
    render(<DialogoSalida />);
    renderHook(() => useFormularioSucio("componer", true));
    let promesa!: Promise<boolean>;
    act(() => {
      promesa = confirmarSalida("salir");
    });
    await userEvent.keyboard("{Escape}");
    await expect(promesa).resolves.toBe(false);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(formulariosSucios()).toEqual(["componer"]);
  });

  test("el foco queda atrapado entre los dos botones", async () => {
    const u = userEvent.setup();
    render(<DialogoSalida />);
    renderHook(() => useFormularioSucio("componer", true));
    act(() => {
      void confirmarSalida("salir");
    });
    const quedarme = screen.getByRole("button", { name: "Quedarme" });
    const salir = screen.getByRole("button", { name: "Salir y descartar" });
    expect(quedarme).toHaveFocus();
    await u.tab();
    expect(salir).toHaveFocus();
    await u.tab();
    expect(quedarme).toHaveFocus();
    await u.tab({ shift: true });
    expect(salir).toHaveFocus();
  });

  test("«Quedarme» devuelve el foco a donde estaba", async () => {
    render(
      <>
        <a href="#/auditoria">Auditoría</a>
        <DialogoSalida />
      </>,
    );
    renderHook(() => useFormularioSucio("componer", true));
    const enlace = screen.getByRole("link", { name: "Auditoría" });
    enlace.focus();
    act(() => {
      void confirmarSalida("salir");
    });
    await userEvent.click(screen.getByRole("button", { name: "Quedarme" }));
    expect(enlace).toHaveFocus();
  });
});
