import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { ErrorDeApi } from "../api/cliente";
import { alertaConTexto } from "../test/ayudas";
import { CambiarContrasena } from "./CambiarContrasena";

async function llenar(usuario: ReturnType<typeof userEvent.setup>, actual: string, nueva: string, confirmar: string) {
  if (actual) await usuario.type(screen.getByLabelText("Contraseña actual"), actual);
  if (nueva) await usuario.type(screen.getByLabelText("Contraseña nueva"), nueva);
  if (confirmar) await usuario.type(screen.getByLabelText("Confirme la contraseña nueva"), confirmar);
  await usuario.click(screen.getByRole("button", { name: "Cambiar contraseña" }));
}

describe("CambiarContrasena", () => {
  test("explica por que aparece y pide los tres campos como contrasenas", () => {
    render(<CambiarContrasena alCambiar={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "Cambie su contraseña" })).toBeInTheDocument();
    expect(screen.getByText(/antes de seguir/i)).toBeInTheDocument();
    for (const etiqueta of ["Contraseña actual", "Contraseña nueva", "Confirme la contraseña nueva"]) {
      expect(screen.getByLabelText(etiqueta)).toHaveAttribute("type", "password");
    }
    expect(screen.getByLabelText("Contraseña actual")).toHaveAttribute("autocomplete", "current-password");
    expect(screen.getByLabelText("Contraseña nueva")).toHaveAttribute("autocomplete", "new-password");
  });

  test("manda la actual y la nueva a alCambiar", async () => {
    const usuario = userEvent.setup();
    const alCambiar = vi.fn().mockResolvedValue(undefined);
    render(<CambiarContrasena alCambiar={alCambiar} />);
    await llenar(usuario, "vieja-1", "nueva-segura-2", "nueva-segura-2");
    expect(alCambiar).toHaveBeenCalledWith("vieja-1", "nueva-segura-2");
  });

  test("campos vacios se marcan y no se llama a la API", async () => {
    const usuario = userEvent.setup();
    const alCambiar = vi.fn();
    render(<CambiarContrasena alCambiar={alCambiar} />);
    await usuario.click(screen.getByRole("button", { name: "Cambiar contraseña" }));
    expect(screen.getByText("Escriba su contraseña actual.")).toBeInTheDocument();
    expect(screen.getByText("Escriba la contraseña nueva.")).toBeInTheDocument();
    expect(alCambiar).not.toHaveBeenCalled();
  });

  test("si la confirmacion no coincide lo dice y no llama a la API", async () => {
    const usuario = userEvent.setup();
    const alCambiar = vi.fn();
    render(<CambiarContrasena alCambiar={alCambiar} />);
    await llenar(usuario, "vieja-1", "nueva-segura-2", "otra-cosa");
    expect(screen.getByText("Las contraseñas nuevas no coinciden.")).toBeInTheDocument();
    expect(alCambiar).not.toHaveBeenCalled();
  });

  test("la regla de la contrasena la pone la API: se muestra su detalle tal cual", async () => {
    const usuario = userEvent.setup();
    const alCambiar = vi.fn().mockRejectedValue(new ErrorDeApi(422, "La contraseña nueva debe tener al menos 12 caracteres."));
    render(<CambiarContrasena alCambiar={alCambiar} />);
    await llenar(usuario, "vieja-1", "corta", "corta");
    expect(await alertaConTexto()).toHaveTextContent("La contraseña nueva debe tener al menos 12 caracteres.");
    // El formulario sigue disponible para corregir.
    expect(screen.getByRole("button", { name: "Cambiar contraseña" })).toBeEnabled();
  });

  test("una contrasena actual incorrecta muestra el detalle de la API", async () => {
    const usuario = userEvent.setup();
    const alCambiar = vi.fn().mockRejectedValue(new ErrorDeApi(401, "La contraseña actual no es correcta."));
    render(<CambiarContrasena alCambiar={alCambiar} />);
    await llenar(usuario, "mala", "nueva-segura-2", "nueva-segura-2");
    expect(await alertaConTexto()).toHaveTextContent("La contraseña actual no es correcta.");
  });

  test("mientras se envia el boton queda deshabilitado", async () => {
    const usuario = userEvent.setup();
    render(<CambiarContrasena alCambiar={() => new Promise(() => {})} />);
    await llenar(usuario, "vieja-1", "nueva-segura-2", "nueva-segura-2");
    expect(screen.getByRole("button", { name: "Cambiando…" })).toBeDisabled();
  });
});
