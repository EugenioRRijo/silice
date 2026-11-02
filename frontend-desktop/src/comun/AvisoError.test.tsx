import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { ErrorDeApi } from "../api/cliente";
import { alertaConTexto } from "../test/ayudas";
import { AvisoError } from "./AvisoError";

describe("AvisoError", () => {
  test("muestra el detalle de la API como alerta, con el titulo", async () => {
    render(<AvisoError titulo="No se pudo guardar" error={new ErrorDeApi(422, "La cantidad debe ser positiva.")} />);
    const alerta = await alertaConTexto();
    expect(alerta).toHaveTextContent("No se pudo guardar");
    expect(alerta).toHaveTextContent("La cantidad debe ser positiva.");
  });

  test("sin error no dibuja nada", () => {
    const { container } = render(<AvisoError error={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  test("acepta un texto", async () => {
    render(<AvisoError error="Falta el archivo." />);
    expect(await alertaConTexto()).toHaveTextContent("Falta el archivo.");
  });

  test("con alCerrar ofrece cerrar el aviso", async () => {
    const usuario = userEvent.setup();
    const alCerrar = vi.fn();
    render(<AvisoError error="Algo falló." alCerrar={alCerrar} />);
    await usuario.click(screen.getByRole("button", { name: /cerrar|close/i }));
    expect(alCerrar).toHaveBeenCalled();
  });
});
