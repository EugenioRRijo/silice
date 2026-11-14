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
  hoja_presupuesto: "PRESUPUESTO",
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

// E2E-2: los perfiles que se pueden elegir (`GET /v1/libros/perfiles-apu-por-hoja`), ficticios.
const PERFILES = [
  { nombre: "apu_por_hoja", origen: "paquete", hoja_presupuesto: "PRESUPUESTO", motivo: null },
  { nombre: "frente_b", origen: "local", hoja_presupuesto: "FRENTE B", motivo: null },
  { nombre: "roto", origen: "local", hoja_presupuesto: null, motivo: "perfil 'roto': JSON mal formado" },
];

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
    fetchFalso.mockImplementation(async (ruta) =>
      String(ruta) === "/v1/libros/perfiles-apu-por-hoja" ? json(PERFILES) : json(INFORME),
    );
  });
  const auditorias = () => fetchFalso.mock.calls.filter(([ruta]) => String(ruta) === "/v1/libros/apu-por-hoja");
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
    const [ruta, opciones] = auditorias()[0]!;
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
    expect(screen.getByText(/con presupuesto\.xlsx \(hoja PRESUPUESTO\)/)).toBeInTheDocument();
    expect(screen.getByText("Emulsión ficticia: 0,52 l (0,5 + 4 %)")).toBeInTheDocument();
  });

  test("sin presupuesto manda solo el libro de APU", async () => {
    render(<AuditarApuPorHoja alExpirar={vi.fn()} />);
    await usuario.upload(campos()[0], new File(["x"], "frente.xlsx"));
    await usuario.click(screen.getByRole("button", { name: "Auditar el libro de APU" }));
    await waitFor(() => expect(auditorias()).toHaveLength(1));
    const cuerpo = auditorias()[0]![1]?.body as FormData;
    expect(cuerpo.get("presupuesto")).toBeNull();
  });

  test("E2E-2: se elige el perfil de la lista del servidor y se manda; el mal escrito dice por qué y no se elige", async () => {
    render(<AuditarApuPorHoja alExpirar={vi.fn()} />);
    const selector = await screen.findByRole("combobox", { name: "Perfil del libro" });
    await waitFor(() => expect(within(selector).getAllByRole("option")).toHaveLength(3));
    expect((selector as HTMLSelectElement).value).toBe("apu_por_hoja");
    const opciones = within(selector).getAllByRole("option") as HTMLOptionElement[];
    expect(opciones.map((o) => [o.textContent, o.disabled])).toEqual([
      ["apu_por_hoja · lee la hoja PRESUPUESTO (del paquete)", false],
      ["frente_b · lee la hoja FRENTE B (de esta instalación)", false],
      ["roto · no se puede usar: perfil 'roto': JSON mal formado", true],
    ]);
    await usuario.selectOptions(selector, "frente_b");
    await usuario.upload(campos()[0], new File(["x"], "frente.xlsx"));
    await usuario.click(screen.getByRole("button", { name: "Auditar el libro de APU" }));
    await waitFor(() => expect(auditorias()).toHaveLength(1));
    expect((auditorias()[0]![1]?.body as FormData).get("perfil")).toBe("frente_b");
  });

  test("E2E-2: si no se lee la lista de perfiles, audita con el de siempre y lo dice", async () => {
    fetchFalso.mockImplementation(async (ruta) =>
      String(ruta) === "/v1/libros/perfiles-apu-por-hoja" ? json({ detalle: "fallo" }, 500) : json(INFORME),
    );
    render(<AuditarApuPorHoja alExpirar={vi.fn()} />);
    expect(await screen.findByText("No se pudo leer la lista de perfiles: se audita con apu_por_hoja.")).toBeInTheDocument();
    await usuario.upload(campos()[0], new File(["x"], "frente.xlsx"));
    await usuario.click(screen.getByRole("button", { name: "Auditar el libro de APU" }));
    await waitFor(() => expect(auditorias()).toHaveLength(1));
    expect((auditorias()[0]![1]?.body as FormData).get("perfil")).toBeNull();
  });

  test("E2E-2: el aviso AH11 de una hoja de otra obra sale arriba del informe", async () => {
    const aviso =
      "La hoja FRENTE B del presupuesto parece de otra obra: de 5 renglones enlazados con su APU, solo 1 tiene la misma cantidad. Revise el perfil: frente_b lee la hoja FRENTE B.";
    fetchFalso.mockImplementation(async (ruta) =>
      String(ruta) === "/v1/libros/perfiles-apu-por-hoja"
        ? json(PERFILES)
        : json({
            ...INFORME,
            perfil: "frente_b",
            origen_perfil: "local",
            hoja_presupuesto: "FRENTE B",
            hallazgos: [{ codigo: "AH11", severidad: "ADVERTENCIA", descripcion: aviso, celda: "FRENTE B!E3", impacto: null, accion: "informado" }, ...INFORME.hallazgos],
          }),
    );
    render(<AuditarApuPorHoja alExpirar={vi.fn()} />);
    await usuario.upload(campos()[0], new File(["x"], "frente.xlsx"));
    await usuario.click(screen.getByRole("button", { name: "Auditar el libro de APU" }));
    await screen.findByRole("table", { name: "Hallazgos del libro" });
    const nota = screen.getAllByRole("status").find((n) => n.textContent?.includes("parece de otra obra"));
    expect(nota).toHaveTextContent("La hoja del presupuesto parece de otra obra");
    expect(nota).toHaveTextContent(aviso);
  });

  test("el mensaje del servidor se muestra si rechaza el libro", async () => {
    fetchFalso.mockImplementation(async () => json({ detalle: "El libro «frente.xlsx» no tiene ninguna hoja de APU." }, 422));
    render(<AuditarApuPorHoja alExpirar={vi.fn()} />);
    await usuario.upload(campos()[0], new File(["x"], "frente.xlsx"));
    await usuario.click(screen.getByRole("button", { name: "Auditar el libro de APU" }));
    expect(await screen.findByText(/no tiene ninguna hoja de APU/)).toBeInTheDocument();
  });
});
