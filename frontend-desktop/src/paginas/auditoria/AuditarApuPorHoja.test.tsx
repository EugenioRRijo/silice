import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import { AuditarApuPorHoja } from "./AuditarApuPorHoja";

// F5 vial, tarea 6: subir el libro con un APU por hoja y, si viene, el de presupuesto (`POST /v1/libros/apu-por-hoja`).
// Datos ficticios (los del libro de `tests/fixtures/libro_apu_por_hoja.py`). La pantalla no calcula: los precios y los
// hallazgos los manda el servidor (los precios ya presentados a dos decimales) y aquí solo se escriben con coma decimal
// y punto de miles.
const INFORME = {
  libro: { nombre: "frente.xlsx", sha256: "a".repeat(64) },
  perfil: "apu_por_hoja",
  origen_perfil: "paquete",
  presupuesto: "presupuesto.xlsx",
  cumple: false,
  por_severidad: { ERROR: 1, INFO: 1 },
  apus: [
    { hoja: "APU 1", numero: 1, codigo: "VF-001", descripcion: "Riego ficticio", unidad: "m2", precio_impreso: "2.08", precio_silice: "2.08", precio_silice_exacto: "2.0777625", celda_precio: "APU 1!G33" },
    { hoja: "APU 4", numero: 4, codigo: "VF-004", descripcion: "Movilización ficticia", unidad: "viaje", precio_impreso: "1820.00", precio_silice: null, precio_silice_exacto: null, celda_precio: "APU 4!G29" },
  ],
  hallazgos: [
    { codigo: "AH5", severidad: "ERROR", descripcion: "Renglón 5 (VF-005): el presupuesto dice un precio unitario de 0,25 y su APU (APU 5!G28) imprime 0,20.", celda: "PRESUPUESTO!F8", impacto: "0.05", accion: "informado" },
    { codigo: "AH3", severidad: "INFO", descripcion: "APU 4 (VF-004) no evaluable: tiene un financiamiento del 2 %.", celda: "APU 4!F27", impacto: null, accion: "informado" },
  ],
  desperdicios: [{ descripcion: "Emulsión ficticia", unidad: "l", cantidad_neta: "0.5", desperdicio_pct: "4", cantidad: "0.52" }],
};

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

describe("Auditar un libro con un APU por hoja", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let usuario: ReturnType<typeof userEvent.setup>;
  const campos = () => Array.from(document.querySelectorAll<HTMLInputElement>('input[type="file"]'));

  beforeEach(() => {
    usuario = userEvent.setup({ applyAccept: false });
    fijarCsrf("tok");
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fetchFalso.mockImplementation(async () => json(INFORME));
  });
  afterEach(() => vi.unstubAllGlobals());

  test("sube los dos libros y muestra el informe del servidor con coma decimal", async () => {
    render(<AuditarApuPorHoja alExpirar={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "Libro con un APU por hoja" })).toBeInTheDocument();
    const boton = screen.getByRole("button", { name: "Auditar el libro de APU" });
    expect(boton).toBeDisabled();
    const [apu, presupuesto] = campos();
    await usuario.upload(apu, new File(["x"], "frente.xlsx"));
    await usuario.upload(presupuesto, new File(["y"], "presupuesto.xlsx"));
    await usuario.click(boton);

    await screen.findByRole("table", { name: "Precio unitario de cada hoja" });
    const [ruta, opciones] = fetchFalso.mock.calls[0];
    expect(ruta).toBe("/v1/libros/apu-por-hoja");
    const cuerpo = opciones?.body as FormData;
    expect((cuerpo.get("libro") as File).name).toBe("frente.xlsx");
    expect((cuerpo.get("presupuesto") as File).name).toBe("presupuesto.xlsx");

    const precios = screen.getByRole("table", { name: "Precio unitario de cada hoja" });
    const filas = within(precios).getAllByRole("row").slice(1);
    expect(filas.map((f) => within(f).getAllByRole("cell").map((c) => c.textContent))).toEqual([
      ["APU 1", "VF-001", "Riego ficticio", "2,08", "2,08"],
      ["APU 4", "VF-004", "Movilización ficticia", "1.820,00", "No evaluable"],
    ]);
    const hallazgos = screen.getByRole("table", { name: "Hallazgos del libro" });
    expect(within(hallazgos).getByText("PRESUPUESTO!F8")).toBeInTheDocument();
    expect(screen.getByText(/Perfil apu_por_hoja \(del paquete\)/)).toBeInTheDocument();
    expect(screen.getByText("Emulsión ficticia: 0,52 l (0,5 + 4 %)")).toBeInTheDocument();
  });

  test("sin presupuesto manda solo el libro de APU", async () => {
    render(<AuditarApuPorHoja alExpirar={vi.fn()} />);
    await usuario.upload(campos()[0], new File(["x"], "frente.xlsx"));
    await usuario.click(screen.getByRole("button", { name: "Auditar el libro de APU" }));
    await waitFor(() => expect(fetchFalso).toHaveBeenCalled());
    const cuerpo = fetchFalso.mock.calls[0][1]?.body as FormData;
    expect(cuerpo.get("presupuesto")).toBeNull();
  });

  test("el mensaje del servidor se muestra si rechaza el libro", async () => {
    fetchFalso.mockImplementation(async () => json({ detalle: "El libro «frente.xlsx» no tiene ninguna hoja de APU." }, 422));
    render(<AuditarApuPorHoja alExpirar={vi.fn()} />);
    await usuario.upload(campos()[0], new File(["x"], "frente.xlsx"));
    await usuario.click(screen.getByRole("button", { name: "Auditar el libro de APU" }));
    expect(await screen.findByText(/no tiene ninguna hoja de APU/)).toBeInTheDocument();
  });
});
