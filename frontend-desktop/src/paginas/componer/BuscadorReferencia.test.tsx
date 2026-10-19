import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { BuscadorReferencia } from "./BuscadorReferencia";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const RESULTADOS = [
  { etiqueta: "Cemento ficticio (saco)", ref_maprex: "REF-FICT-001", fila: { descripcion: "Cemento ficticio", unidad: "saco", cantidad: "", precio: "9.90" } },
  { etiqueta: "Cemento blanco ficticio", ref_maprex: "REF-FICT-002", fila: { descripcion: "Cemento blanco ficticio", unidad: "saco", cantidad: "", precio: "12.00" } },
];

describe("BuscadorReferencia", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fetchFalso.mockImplementation(async (entrada) => {
      const ruta = String(entrada);
      if (ruta.includes("q=cem")) return json(RESULTADOS);
      return json([]);
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  test("rotula el campo con la referencia MaPreX y la tabla en minúsculas", () => {
    render(<BuscadorReferencia tipo="materiales" alUsar={vi.fn()} alExpirar={vi.fn()} />);
    expect(screen.getByLabelText("Buscar en la referencia MaPreX (materiales)")).toBeInTheDocument();
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("busca, muestra el ref_maprex de la fila elegida y la entrega con «Usar esta fila»", async () => {
    const usuario = userEvent.setup();
    const alUsar = vi.fn();
    render(<BuscadorReferencia tipo="materiales" alUsar={alUsar} alExpirar={vi.fn()} />);
    await usuario.type(screen.getByLabelText("Buscar en la referencia MaPreX (materiales)"), "cem");
    expect(await screen.findByText("Referencia MaPreX: REF-FICT-001")).toBeInTheDocument();
    expect(fetchFalso).toHaveBeenCalledWith("/v1/composicion/referencia?tipo=materiales&q=cem", expect.anything());

    await usuario.selectOptions(screen.getByLabelText("Resultado"), "Cemento blanco ficticio");
    expect(screen.getByText("Referencia MaPreX: REF-FICT-002")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Usar esta fila" }));
    expect(alUsar).toHaveBeenCalledWith(RESULTADOS[1].fila);
  });

  test("sin coincidencias lo dice", async () => {
    const usuario = userEvent.setup();
    render(<BuscadorReferencia tipo="equipos" alUsar={vi.fn()} alExpirar={vi.fn()} />);
    await usuario.type(screen.getByLabelText("Buscar en la referencia MaPreX (equipos)"), "zzz");
    expect(await screen.findByText("Sin coincidencias en la referencia MaPreX.")).toBeInTheDocument();
  });

  test("un 401 llama a alExpirar", async () => {
    const usuario = userEvent.setup();
    const alExpirar = vi.fn();
    fetchFalso.mockImplementation(async () => json({ detalle: "Sesión vencida." }, 401));
    render(<BuscadorReferencia tipo="materiales" alUsar={vi.fn()} alExpirar={alExpirar} />);
    await usuario.type(screen.getByLabelText("Buscar en la referencia MaPreX (materiales)"), "c");
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("otro error de la API se muestra", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockImplementation(async () => json({ detalle: "Referencia no disponible." }, 500));
    render(<BuscadorReferencia tipo="materiales" alUsar={vi.fn()} alExpirar={vi.fn()} />);
    await usuario.type(screen.getByLabelText("Buscar en la referencia MaPreX (materiales)"), "c");
    expect(await screen.findByText("Referencia no disponible.")).toBeInTheDocument();
  });
});
