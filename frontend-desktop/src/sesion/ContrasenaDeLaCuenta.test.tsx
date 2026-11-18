import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { ErrorDeApi } from "../api/cliente";
import { ContextoAplicacion } from "../shell/contexto";
import { sesionDe } from "../shell/obras/datosDePrueba";
import { alertaConTexto } from "../test/ayudas";
import { ContrasenaDeLaCuenta } from "./ContrasenaDeLaCuenta";

// Prueba en vivo del 2026-11-18: nadie podía cambiar su propia contraseña cuando quería (el formulario solo salía con la
// contraseña provisional). Ahora es una sección de la Cuenta. La API cierra todas las sesiones de la cuenta y abre otra:
// la persona debe saberlo antes de confirmar y quedar con la sesión abierta en este navegador.

function pintar(alCambiar: (actual: string, nueva: string) => Promise<void>) {
  return render(
    <ContextoAplicacion.Provider
      value={{ sesion: sesionDe("ana"), proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn(), cambiarContrasena: alCambiar }}
    >
      <ContrasenaDeLaCuenta />
    </ContextoAplicacion.Provider>,
  );
}

async function llenar(usuario: ReturnType<typeof userEvent.setup>, actual: string, nueva: string, confirmar: string) {
  if (actual) await usuario.type(screen.getByLabelText("Contraseña actual"), actual);
  if (nueva) await usuario.type(screen.getByLabelText("Contraseña nueva"), nueva);
  if (confirmar) await usuario.type(screen.getByLabelText("Confirme la contraseña nueva"), confirmar);
  await usuario.click(screen.getByRole("button", { name: "Cambiar contraseña" }));
}

describe("ContrasenaDeLaCuenta", () => {
  test("antes de confirmar dice qué pasa con las otras sesiones y que esta sigue abierta", () => {
    pintar(vi.fn());
    expect(
      screen.getByText("Al cambiarla se cierran las sesiones de su cuenta abiertas en otros navegadores o pestañas. En este seguirá con la sesión abierta."),
    ).toBeInTheDocument();
    for (const etiqueta of ["Contraseña actual", "Contraseña nueva", "Confirme la contraseña nueva"]) {
      expect(screen.getByLabelText(etiqueta)).toHaveAttribute("type", "password");
    }
  });

  test("manda la actual y la nueva, lo dice al terminar y deja los campos limpios", async () => {
    const usuario = userEvent.setup();
    const alCambiar = vi.fn().mockResolvedValue(undefined);
    pintar(alCambiar);
    await llenar(usuario, "vieja-1", "nueva-segura-2", "nueva-segura-2");
    expect(alCambiar).toHaveBeenCalledWith("vieja-1", "nueva-segura-2");
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Contraseña cambiada."));
    expect(screen.getByLabelText("Contraseña actual")).toHaveValue("");
    expect(screen.getByLabelText("Contraseña nueva")).toHaveValue("");
    expect(screen.getByLabelText("Confirme la contraseña nueva")).toHaveValue("");
  });

  test("si la confirmación no coincide lo dice y no llama a la API", async () => {
    const usuario = userEvent.setup();
    const alCambiar = vi.fn();
    pintar(alCambiar);
    await llenar(usuario, "vieja-1", "nueva-segura-2", "otra-cosa");
    expect(screen.getByText("Las contraseñas nuevas no coinciden.")).toBeInTheDocument();
    expect(alCambiar).not.toHaveBeenCalled();
  });

  test("el rechazo de la API se muestra con su detalle y el formulario sigue disponible", async () => {
    const usuario = userEvent.setup();
    const alCambiar = vi.fn().mockRejectedValue(new ErrorDeApi(422, "La contraseña nueva debe tener al menos 12 caracteres."));
    pintar(alCambiar);
    await llenar(usuario, "vieja-1", "corta", "corta");
    expect(await alertaConTexto()).toHaveTextContent("La contraseña nueva debe tener al menos 12 caracteres.");
    await waitFor(() => expect(screen.getByRole("button", { name: "Cambiar contraseña" })).toBeEnabled());
    expect(screen.queryByText("Contraseña cambiada.")).toBeNull();
  });

  test("al volver a escribir se quita el aviso de «Contraseña cambiada»", async () => {
    const usuario = userEvent.setup();
    pintar(vi.fn().mockResolvedValue(undefined));
    await llenar(usuario, "vieja-1", "nueva-segura-2", "nueva-segura-2");
    await screen.findByText("Contraseña cambiada.");
    await usuario.type(screen.getByLabelText("Contraseña actual"), "x");
    expect(screen.queryByText("Contraseña cambiada.")).toBeNull();
  });
});
