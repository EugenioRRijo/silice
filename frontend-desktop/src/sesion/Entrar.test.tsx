import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";
import { ErrorDeApi } from "../api/cliente";
import { alertaConTexto } from "../test/ayudas";
import { Entrar } from "./Entrar";

afterEach(() => {
  vi.restoreAllMocks();
});

async function llenarYEnviar(usuario: ReturnType<typeof userEvent.setup>) {
  await usuario.type(screen.getByLabelText("Usuario"), "ana");
  await usuario.type(screen.getByLabelText("Contraseña"), "clave-mala");
  await usuario.click(screen.getByRole("button", { name: "Entrar" }));
}

describe("Entrar", () => {
  // VB-15: «Entrar» es la página; lleva el mismo h1 heading-04 que las demás y su título de documento.
  test("el título es un h1 en heading-04 y el documento se llama «Entrar · Sílice»", () => {
    render(<Entrar onEntrar={vi.fn()} />);
    const h1 = screen.getByRole("heading", { level: 1, name: "Entrar" });
    expect(h1.className).toContain("cds--type-heading-04");
    expect(document.title).toBe("Entrar · Sílice");
  });

  test("manda el usuario y la contrasena a onEntrar", async () => {
    const usuario = userEvent.setup();
    const onEntrar = vi.fn().mockResolvedValue(undefined);
    render(<Entrar onEntrar={onEntrar} />);
    await llenarYEnviar(usuario);
    expect(onEntrar).toHaveBeenCalledWith("ana", "clave-mala");
  });

  test("la contrasena se escribe en un campo de contrasena", () => {
    render(<Entrar onEntrar={vi.fn()} />);
    expect(screen.getByLabelText("Contraseña")).toHaveAttribute("type", "password");
  });

  test("credenciales malas muestran el detalle de la API tal cual", async () => {
    const usuario = userEvent.setup();
    const onEntrar = vi.fn().mockRejectedValue(new ErrorDeApi(401, "Usuario o contraseña incorrectos."));
    render(<Entrar onEntrar={onEntrar} />);
    await llenarYEnviar(usuario);
    expect(await alertaConTexto()).toHaveTextContent("Usuario o contraseña incorrectos.");
  });

  test("un 429 muestra el detalle y los segundos de espera", async () => {
    const usuario = userEvent.setup();
    const onEntrar = vi
      .fn()
      .mockRejectedValue(new ErrorDeApi(429, "Demasiados intentos desde esta red.", 45));
    render(<Entrar onEntrar={onEntrar} />);
    await llenarYEnviar(usuario);
    const alerta = await alertaConTexto();
    expect(alerta).toHaveTextContent("Demasiados intentos desde esta red.");
    expect(alerta).toHaveTextContent("Espere 45 segundos");
  });

  test("con un solo segundo de espera usa el singular", async () => {
    const usuario = userEvent.setup();
    const onEntrar = vi.fn().mockRejectedValue(new ErrorDeApi(429, "Demasiados intentos.", 1));
    render(<Entrar onEntrar={onEntrar} />);
    await llenarYEnviar(usuario);
    expect(await alertaConTexto()).toHaveTextContent("Espere 1 segundo ");
  });

  test("un error que no es de la API se dice en espanol y no se traga", async () => {
    const usuario = userEvent.setup();
    const onEntrar = vi.fn().mockRejectedValue(new Error("boom"));
    render(<Entrar onEntrar={onEntrar} />);
    await llenarYEnviar(usuario);
    expect(await alertaConTexto()).toHaveTextContent(/no se pudo entrar/i);
  });

  test("el formulario no guarda nada en localStorage ni sessionStorage", async () => {
    const usuario = userEvent.setup();
    const espia = vi.spyOn(Storage.prototype, "setItem");
    const onEntrar = vi.fn().mockRejectedValue(new ErrorDeApi(401, "No."));
    render(<Entrar onEntrar={onEntrar} />);
    await llenarYEnviar(usuario);
    await alertaConTexto();
    expect(espia).not.toHaveBeenCalled();
  });

  test("mientras envia, el boton queda desactivado para no repetir el intento", async () => {
    const usuario = userEvent.setup();
    let resolver: () => void = () => {};
    const onEntrar = vi.fn().mockReturnValue(
      new Promise<void>((r) => {
        resolver = r;
      }),
    );
    render(<Entrar onEntrar={onEntrar} />);
    await llenarYEnviar(usuario);
    expect(screen.getByRole("button", { name: /Entrando/ })).toBeDisabled();
    resolver();
  });

  test("con el usuario o la contrasena vacios no llama a la API", async () => {
    const usuario = userEvent.setup();
    const onEntrar = vi.fn();
    render(<Entrar onEntrar={onEntrar} />);
    await usuario.click(screen.getByRole("button", { name: "Entrar" }));
    expect(onEntrar).not.toHaveBeenCalled();
  });

  // F1: con cuentas creadas, «Entrar» ofrece el camino para quien perdió el acceso de administrador.
  test("con alRecuperar ofrece «Perdí el acceso de administrador» y lo llama sin entrar", async () => {
    const usuario = userEvent.setup();
    const alRecuperar = vi.fn();
    const onEntrar = vi.fn();
    render(<Entrar onEntrar={onEntrar} alRecuperar={alRecuperar} />);
    await usuario.click(screen.getByRole("button", { name: "Perdí el acceso de administrador" }));
    expect(alRecuperar).toHaveBeenCalledTimes(1);
    expect(onEntrar).not.toHaveBeenCalled();
  });

  test("sin alRecuperar no pinta el enlace", () => {
    render(<Entrar onEntrar={vi.fn()} />);
    expect(screen.queryByText(/Perdí el acceso/)).not.toBeInTheDocument();
  });

  test("el enlace es un botón que no envía el formulario y viene después de «Entrar»", () => {
    render(<Entrar onEntrar={vi.fn()} alRecuperar={vi.fn()} />);
    const enlace = screen.getByRole("button", { name: "Perdí el acceso de administrador" });
    expect(enlace).toHaveAttribute("type", "button");
    const entrar = screen.getByRole("button", { name: "Entrar" });
    expect(entrar.compareDocumentPosition(enlace) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});
