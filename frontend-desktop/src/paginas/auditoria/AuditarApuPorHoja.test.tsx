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
    expect(within(precios).getByText("Precio unitario del Excel")).toBeInTheDocument();
    expect(within(precios).getByText("Precio unitario según Sílice")).toBeInTheDocument();
    const filas = within(precios).getAllByRole("row").slice(1);
    expect(filas.map((f) => within(f).getAllByRole("cell").map((c) => c.textContent))).toEqual([
      ["APU 1", "VF-001", "Riego ficticio", "2,08", "2,08"],
      ["APU 4", "VF-004", "Movilización ficticia", "1.820,00", "No evaluable"],
    ]);
    const hallazgos = screen.getByRole("table", { name: "Hallazgos del libro" });
    expect(within(hallazgos).getByText("Qué revisó Sílice")).toBeInTheDocument();
    expect(within(hallazgos).getByText("PRESUPUESTO!F8")).toBeInTheDocument();
    expect(screen.getByText(/Perfil apu_por_hoja \(del paquete\)/)).toBeInTheDocument();
    expect(screen.getByText(/con presupuesto\.xlsx \(hoja PRESUPUESTO\)/)).toBeInTheDocument();
    expect(screen.getByText("Emulsión ficticia: 0,52 l (0,5 + 4 %)")).toBeInTheDocument();
  });

  test("ordena los hallazgos por severidad de forma estable y muestra el nombre de la regla si viene", async () => {
    fetchFalso.mockImplementation(async (ruta) =>
      String(ruta) === "/v1/libros/perfiles-apu-por-hoja"
        ? json(PERFILES)
        : json({
            ...INFORME,
            hallazgos: [
              { codigo: "AH3", nombre_regla: "", severidad: "INFO", descripcion: "Primero informativo", celda: "APU 4!F27", impacto: null, accion: "informado" },
              { codigo: "AH6", nombre_regla: "Cantidad del presupuesto contra su APU", severidad: "ADVERTENCIA", descripcion: "Primera advertencia", celda: "PRESUPUESTO!D5", impacto: null, accion: "informado" },
              { codigo: "AH5", nombre_regla: "Precio unitario del presupuesto contra su APU", severidad: "ERROR", descripcion: "Error de precio", celda: "PRESUPUESTO!F8", impacto: "0.05", accion: "informado" },
              { codigo: "AH1", nombre_regla: "Precio unitario del APU contra el recalculado", severidad: "CRITICO", descripcion: "Crítico de recálculo", celda: "APU 1!G33", impacto: "10.00", accion: "informado" },
              { codigo: "AH4", severidad: "ADVERTENCIA", descripcion: "Segunda advertencia", celda: "APU 2!F28", impacto: null, accion: "informado" },
            ],
          }),
    );
    render(<AuditarApuPorHoja alExpirar={vi.fn()} />);
    await usuario.upload(campos()[0], new File(["x"], "frente.xlsx"));
    await usuario.click(screen.getByRole("button", { name: "Auditar el libro de APU" }));
    const tabla = await screen.findByRole("table", { name: "Hallazgos del libro" });
    const filas = within(tabla).getAllByRole("row").slice(1);
    expect(filas.map((f) => within(f).getAllByRole("cell").map((c) => c.textContent))).toEqual([
      ["Crítico", "Precio unitario del APU contra el recalculado (AH1)", "APU 1!G33", "Crítico de recálculo"],
      ["Error", "Precio unitario del presupuesto contra su APU (AH5)", "PRESUPUESTO!F8", "Error de precio"],
      ["Advertencia", "Cantidad del presupuesto contra su APU (AH6)", "PRESUPUESTO!D5", "Primera advertencia"],
      ["Advertencia", "AH4", "APU 2!F28", "Segunda advertencia"],
      ["Información", "AH3", "APU 4!F27", "Primero informativo"],
    ]);
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
    const selector = await screen.findByRole("combobox", { name: "Formato del archivo de Excel" });
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
    expect(await screen.findByText("No se pudo leer la lista de formatos: se audita con el formato estándar (un APU por hoja).")).toBeInTheDocument();
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
    // Ola 2 (2026-11-13): el aviso se nombra por su título, no por todo su texto (que se leería dos veces) ni sin nombre
    // (lo que dejó, sin declararlo, el verde `2b436af1`); el texto completo es su contenido.
    const nota = await screen.findByRole("status", { name: "La hoja del presupuesto parece de otra obra" });
    expect(nota).toHaveTextContent(aviso);
  });

  // Libro por frentes (ola 2, línea 3, 2026-11-13): las hojas del presupuesto se eligen aparte del perfil. Al elegir el
  // libro del presupuesto, la pantalla pide sus hojas (`POST /v1/libros/hojas`, solo los nombres) y marca las del perfil
  // que el libro tiene; lo marcado viaja como `hoja_presupuesto`, una vez por hoja. Datos FICTICIOS.
  const PERFILES_FRENTES = [
    ...PERFILES.slice(0, 1),
    { nombre: "por_frentes", origen: "local", hoja_presupuesto: "FRENTE A", hojas_presupuesto: ["FRENTE A", "FRENTE B"], motivo: null },
  ];
  const conHojas = (hojas: string[], perfiles: unknown = PERFILES_FRENTES) =>
    fetchFalso.mockImplementation(async (ruta) => {
      if (String(ruta) === "/v1/libros/perfiles-apu-por-hoja") return json(perfiles);
      if (String(ruta) === "/v1/libros/hojas") return json({ hojas });
      return json({ ...INFORME, presupuesto: "frentes.xlsx", hoja_presupuesto: "FRENTE A", hojas_presupuesto: ["FRENTE A", "FRENTE B"] });
    });
  const hojasPedidas = () => fetchFalso.mock.calls.filter(([ruta]) => String(ruta) === "/v1/libros/hojas");

  test("libro por frentes: el perfil de varias hojas las dice todas", async () => {
    conHojas([]);
    render(<AuditarApuPorHoja alExpirar={vi.fn()} />);
    const selector = await screen.findByRole("combobox", { name: "Formato del archivo de Excel" });
    await waitFor(() => expect(within(selector).getAllByRole("option")).toHaveLength(2));
    expect(within(selector).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "apu_por_hoja · lee la hoja PRESUPUESTO (del paquete)",
      "por_frentes · lee las hojas FRENTE A y FRENTE B (de esta instalación)",
    ]);
  });

  test("libro por frentes: al elegir el presupuesto se ofrecen sus hojas, con las del perfil marcadas, y se mandan", async () => {
    conHojas(["RESUMEN", "FRENTE A", "FRENTE B"]);
    render(<AuditarApuPorHoja alExpirar={vi.fn()} />);
    const selector = await screen.findByRole("combobox", { name: "Formato del archivo de Excel" });
    await waitFor(() => expect(within(selector).getAllByRole("option")).toHaveLength(2));
    await usuario.selectOptions(selector, "por_frentes");
    const [apu, presupuesto] = campos();
    await usuario.upload(apu, new File(["x"], "obra.xlsx"));
    await usuario.upload(presupuesto, new File(["y"], "frentes.xlsx"));
    const grupo = await screen.findByRole("group", { name: "Hojas del presupuesto que se comparan" });
    expect(hojasPedidas()).toHaveLength(1);
    expect(((hojasPedidas()[0]![1]?.body as FormData).get("libro") as File).name).toBe("frentes.xlsx");
    const casillas = within(grupo).getAllByRole("checkbox") as HTMLInputElement[];
    expect(casillas.map((c) => [c.labels?.[0]?.textContent, c.checked])).toEqual([
      ["RESUMEN", false],
      ["FRENTE A", true],
      ["FRENTE B", true],
    ]);
    await usuario.click(within(grupo).getByRole("checkbox", { name: "FRENTE A" }));
    await usuario.click(screen.getByRole("button", { name: "Auditar el libro de APU" }));
    await waitFor(() => expect(auditorias()).toHaveLength(1));
    expect((auditorias()[0]![1]?.body as FormData).getAll("hoja_presupuesto")).toEqual(["FRENTE B"]);
    expect(await screen.findByText(/con frentes\.xlsx \(hojas FRENTE A y FRENTE B\)/)).toBeInTheDocument();
  });

  test("libro por frentes: si el libro no tiene la hoja del perfil, lo dice y no marca ninguna", async () => {
    conHojas(["FRENTE A", "FRENTE B"]);
    render(<AuditarApuPorHoja alExpirar={vi.fn()} />);
    await screen.findByRole("combobox", { name: "Formato del archivo de Excel" });
    await usuario.upload(campos()[1], new File(["y"], "frentes.xlsx"));
    const grupo = await screen.findByRole("group", { name: "Hojas del presupuesto que se comparan" });
    expect((within(grupo).getAllByRole("checkbox") as HTMLInputElement[]).every((c) => !c.checked)).toBe(true);
    expect(screen.getByText("El perfil lee la hoja PRESUPUESTO, que este libro no tiene: marque las hojas que quiere comparar.")).toBeInTheDocument();
  });

  // P7 (decisión del 2026-11-18): las hojas que la persona marcó a mano valen para el perfil con que las marcó; al cambiar
  // de perfil se reinician y valen las hojas por omisión del perfil nuevo.
  test("P7: cambiar de perfil reinicia las hojas marcadas a mano y se mandan las del perfil nuevo", async () => {
    conHojas(["PRESUPUESTO", "FRENTE A", "FRENTE B"]);
    render(<AuditarApuPorHoja alExpirar={vi.fn()} />);
    const selector = await screen.findByRole("combobox", { name: "Formato del archivo de Excel" });
    await waitFor(() => expect(within(selector).getAllByRole("option")).toHaveLength(2));
    await usuario.upload(campos()[0], new File(["x"], "obra.xlsx"));
    await usuario.upload(campos()[1], new File(["y"], "frentes.xlsx"));
    const grupo = await screen.findByRole("group", { name: "Hojas del presupuesto que se comparan" });
    const marcadas = () => within(grupo).getAllByRole("checkbox").map((c) => [(c as HTMLInputElement).labels?.[0]?.textContent, (c as HTMLInputElement).checked]);
    // Con el perfil de siempre solo está marcada PRESUPUESTO; la persona marca además FRENTE A a mano.
    expect(marcadas()).toEqual([["PRESUPUESTO", true], ["FRENTE A", false], ["FRENTE B", false]]);
    await usuario.click(within(grupo).getByRole("checkbox", { name: "FRENTE A" }));
    expect(marcadas()).toEqual([["PRESUPUESTO", true], ["FRENTE A", true], ["FRENTE B", false]]);

    await usuario.selectOptions(selector, "por_frentes");
    // Valen las hojas por omisión del perfil nuevo (FRENTE A y FRENTE B), no las del anterior.
    expect(marcadas()).toEqual([["PRESUPUESTO", false], ["FRENTE A", true], ["FRENTE B", true]]);
    await usuario.click(screen.getByRole("button", { name: "Auditar el libro de APU" }));
    await waitFor(() => expect(auditorias()).toHaveLength(1));
    const cuerpo = auditorias()[0]![1]?.body as FormData;
    expect(cuerpo.get("perfil")).toBe("por_frentes");
    expect([...cuerpo.getAll("hoja_presupuesto")].sort()).toEqual(["FRENTE A", "FRENTE B"]);
  });

  // Dos presupuestos seguidos: la lectura de las hojas del primero puede llegar después de elegir el segundo. Las hojas
  // que se ofrecen tienen que ser las del presupuesto que se nombra, nunca las de uno anterior.
  function hojasEnVuelo() {
    const pendientes = new Map<string, (r: Response) => void>();
    fetchFalso.mockImplementation((ruta, init) => {
      if (String(ruta) === "/v1/libros/perfiles-apu-por-hoja") return Promise.resolve(json(PERFILES));
      if (String(ruta) === "/v1/libros/hojas") {
        const nombre = ((init?.body as FormData).get("libro") as File).name;
        return new Promise<Response>((resolver) => pendientes.set(nombre, resolver));
      }
      return Promise.resolve(json(INFORME));
    });
    return pendientes;
  }

  test("mientras lee las hojas del presupuesto, su subida está deshabilitada", async () => {
    const pendientes = hojasEnVuelo();
    render(<AuditarApuPorHoja alExpirar={vi.fn()} />);
    await screen.findByRole("combobox", { name: "Formato del archivo de Excel" });
    await usuario.upload(campos()[1], new File(["y"], "a.xlsx"));
    await waitFor(() => expect(pendientes.has("a.xlsx")).toBe(true));
    expect(campos()[1]).toBeDisabled();
    pendientes.get("a.xlsx")!(json({ hojas: ["DE A"] }));
    await screen.findByRole("group", { name: "Hojas del presupuesto que se comparan" });
    expect(campos()[1]).not.toBeDisabled();
  });

  test("la lectura tardía de las hojas de un presupuesto anterior no se pinta con otro elegido", async () => {
    const pendientes = hojasEnVuelo();
    render(<AuditarApuPorHoja alExpirar={vi.fn()} />);
    await screen.findByRole("combobox", { name: "Formato del archivo de Excel" });
    await usuario.upload(campos()[1], new File(["y"], "a.xlsx"));
    await waitFor(() => expect(pendientes.has("a.xlsx")).toBe(true));
    await usuario.upload(campos()[1], new File(["z"], "b.xlsx"));
    pendientes.get("b.xlsx")?.(json({ hojas: ["DE B"] }));
    pendientes.get("a.xlsx")!(json({ hojas: ["DE A"] }));
    const grupo = await screen.findByRole("group", { name: "Hojas del presupuesto que se comparan" });
    const nombrado = screen.getByText(/Presupuesto: /).textContent ?? "";
    const ofrecidas = within(grupo).getAllByRole("checkbox").map((c) => (c as HTMLInputElement).labels?.[0]?.textContent);
    expect(ofrecidas).toEqual([nombrado.includes("b.xlsx") ? "DE B" : "DE A"]);
  });

  // P13 (auditoría 2026-11-15): mientras se leen las hojas del presupuesto no se puede auditar; si no, la auditoría sale
  // sin hojas marcadas y el servidor elige por el perfil.
  test("no deja auditar mientras se leen las hojas del presupuesto y manda las leídas al terminar", async () => {
    let entregarHojas: (r: Response) => void = () => undefined;
    fetchFalso.mockImplementation(async (ruta) => {
      if (String(ruta) === "/v1/libros/perfiles-apu-por-hoja") return json(PERFILES_FRENTES);
      if (String(ruta) === "/v1/libros/hojas") return new Promise<Response>((resolver) => (entregarHojas = resolver));
      return json({ ...INFORME, presupuesto: "frentes.xlsx", hoja_presupuesto: "FRENTE A", hojas_presupuesto: ["FRENTE A", "FRENTE B"] });
    });
    render(<AuditarApuPorHoja alExpirar={vi.fn()} />);
    const selector = await screen.findByRole("combobox", { name: "Formato del archivo de Excel" });
    await waitFor(() => expect(within(selector).getAllByRole("option")).toHaveLength(2));
    await usuario.selectOptions(selector, "por_frentes");
    const [apu, presupuesto] = campos();
    await usuario.upload(apu, new File(["x"], "obra.xlsx"));
    await usuario.upload(presupuesto, new File(["y"], "frentes.xlsx"));
    const boton = screen.getByRole("button", { name: "Auditar el libro de APU" });
    await waitFor(() => expect(hojasPedidas()).toHaveLength(1));
    expect(boton).toBeDisabled();
    expect(screen.getByText("Leyendo las hojas del presupuesto...")).toBeInTheDocument();
    entregarHojas(json({ hojas: ["RESUMEN", "FRENTE A", "FRENTE B"] }));
    await screen.findByRole("group", { name: "Hojas del presupuesto que se comparan" });
    expect(boton).toBeEnabled();
    expect(screen.queryByText("Leyendo las hojas del presupuesto...")).not.toBeInTheDocument();
    await usuario.click(boton);
    await waitFor(() => expect(auditorias()).toHaveLength(1));
    expect((auditorias()[0]![1]?.body as FormData).getAll("hoja_presupuesto")).toEqual(["FRENTE A", "FRENTE B"]);
  });

  test("si las hojas no se pueden leer, se puede auditar y decide el perfil", async () => {
    fetchFalso.mockImplementation(async (ruta) => {
      if (String(ruta) === "/v1/libros/perfiles-apu-por-hoja") return json(PERFILES_FRENTES);
      if (String(ruta) === "/v1/libros/hojas") return json({ detail: "no se pudo leer" }, 422);
      return json(INFORME);
    });
    render(<AuditarApuPorHoja alExpirar={vi.fn()} />);
    await screen.findByRole("combobox", { name: "Formato del archivo de Excel" });
    const [apu, presupuesto] = campos();
    await usuario.upload(apu, new File(["x"], "obra.xlsx"));
    await usuario.upload(presupuesto, new File(["y"], "roto.xlsx"));
    await waitFor(() => expect(hojasPedidas()).toHaveLength(1));
    await waitFor(() => expect(screen.queryByText("Leyendo las hojas del presupuesto...")).not.toBeInTheDocument());
    await usuario.click(screen.getByRole("button", { name: "Auditar el libro de APU" }));
    await waitFor(() => expect(auditorias()).toHaveLength(1));
    expect((auditorias()[0]![1]?.body as FormData).getAll("hoja_presupuesto")).toEqual([]);
  });

  // Libro por frentes: llevar a la Hoja el libro auditado (`POST /v1/hoja/libro`). La pantalla vuelve a mandar los dos
  // libros, el perfil y las hojas, más la obra y la moneda de los precios; el servidor dice cada partida con el P.U. del
  // libro y el de la Hoja (ya presentados) y si casan. Datos FICTICIOS.
  const LLEVADO = {
    borrador_id: "b".repeat(20),
    renglones: 10,
    partidas: [
      { codigo: "VF-001", codigo_libro: "VF-001", hoja: "APU 1", nueva: true, precio_impreso: "2.08", precio_hoja: "2.08", casa: true },
      { codigo: "VF-002-B", codigo_libro: "VF-002", hoja: "APU 2", nueva: true, precio_impreso: "4.50", precio_hoja: "4.13", casa: false },
    ],
    sin_apu: ["FRENTE A, renglón 6"],
    sin_cantidad: [],
    lista: "Lista ficticia",
    moneda: "Bs",
  };
  const conLlevar = () =>
    fetchFalso.mockImplementation(async (ruta) => {
      if (String(ruta) === "/v1/libros/perfiles-apu-por-hoja") return json(PERFILES_FRENTES);
      if (String(ruta) === "/v1/libros/hojas") return json({ hojas: ["FRENTE A", "FRENTE B"] });
      if (String(ruta) === "/v1/hoja/libro") return json(LLEVADO);
      return json({ ...INFORME, presupuesto: "frentes.xlsx", hoja_presupuesto: "FRENTE A", hojas_presupuesto: ["FRENTE A", "FRENTE B"] });
    });
  const llevadas = () => fetchFalso.mock.calls.filter(([ruta]) => String(ruta) === "/v1/hoja/libro");

  async function auditarLosDos() {
    const selector = await screen.findByRole("combobox", { name: "Formato del archivo de Excel" });
    await waitFor(() => expect(within(selector).getAllByRole("option")).toHaveLength(2));
    await usuario.selectOptions(selector, "por_frentes");
    const [apu, presupuesto] = campos();
    await usuario.upload(apu, new File(["x"], "obra.xlsx"));
    await usuario.upload(presupuesto, new File(["y"], "frentes.xlsx"));
    await screen.findByRole("group", { name: "Hojas del presupuesto que se comparan" });
    await usuario.click(screen.getByRole("button", { name: "Auditar el libro de APU" }));
    await screen.findByRole("table", { name: "Precio unitario de cada hoja" });
  }

  test("libro por frentes: lleva el libro auditado al Presupuesto de la obra y dice qué coincide", async () => {
    conLlevar();
    render(<AuditarApuPorHoja alExpirar={vi.fn()} obra="Vía ficticia" puedeLlevar />);
    await auditarLosDos();
    const llevar = screen.getByRole("button", { name: "Llevar partidas al Presupuesto de «Vía ficticia»" });
    expect(llevar).toHaveClass("cds--btn--primary");
    expect(screen.getByRole("button", { name: "Auditar el libro de APU" })).toHaveClass("cds--btn--secondary");
    expect(llevar).toBeDisabled(); // falta la moneda de los precios
    await usuario.selectOptions(screen.getByRole("combobox", { name: "Moneda de los precios del libro" }), "Bs");
    await usuario.click(llevar);
    await waitFor(() => expect(llevadas()).toHaveLength(1));
    const cuerpo = llevadas()[0]![1]?.body as FormData;
    expect((cuerpo.get("libro") as File).name).toBe("obra.xlsx");
    expect((cuerpo.get("presupuesto") as File).name).toBe("frentes.xlsx");
    expect([cuerpo.get("proyecto"), cuerpo.get("moneda"), cuerpo.get("perfil")]).toEqual(["Vía ficticia", "Bs", "por_frentes"]);
    expect(cuerpo.getAll("hoja_presupuesto")).toEqual(["FRENTE A", "FRENTE B"]);
    const aviso = await screen.findByRole("status", { name: /Se llevaron 10 partidas al Presupuesto de «Vía ficticia», sin guardar/ });
    // Pasada en navegador de la ola 2 (D11): el aviso lleva a la Hoja de la obra (la dirección corta abre la de la obra de
    // la sesión) y dice que un borrador sin guardar no sobrevive a la salida, y cómo recuperarlo.
    // (Carbon no admite controles dentro de un aviso en línea: el enlace va justo debajo.)
    expect(screen.getByRole("link", { name: "Abrir el Presupuesto de «Vía ficticia»" })).toHaveAttribute("href", "#/hoja");
    expect(aviso).toHaveTextContent(/se pierde al salir de Sílice/);
    expect(aviso).toHaveTextContent(/vuelva a llevar el libro: no duplica nada/);
    const tabla = screen.getByRole("table", { name: "Partidas llevadas al Presupuesto" });
    expect(within(tabla).getByText("¿Coincide?")).toBeInTheDocument();
    const filas = within(tabla).getAllByRole("row").slice(1);
    expect(filas.map((f) => within(f).getAllByRole("cell").map((c) => c.textContent))).toEqual([
      ["VF-001", "APU 1", "2,08", "2,08", "Sí coincide"],
      ["VF-002-B (del libro: VF-002)", "APU 2", "4,50", "4,13", "No coincide"],
    ]);
    expect(screen.getByText("No se llevaron, sin hoja de APU: FRENTE A, renglón 6.")).toBeInTheDocument();
  });

  test("libro por frentes: sin obra elegida no se lleva y lo dice; sin permiso no se ofrece", async () => {
    conLlevar();
    const { unmount } = render(<AuditarApuPorHoja alExpirar={vi.fn()} obra={null} puedeLlevar />);
    await auditarLosDos();
    expect(screen.getByText("Elija una obra en «Obras» de la barra lateral, o búsquela con Ctrl+K, para llevar las partidas a su Presupuesto.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Llevar partidas al Presupuesto/ })).toBeNull();
    unmount();
    render(<AuditarApuPorHoja alExpirar={vi.fn()} obra="Vía ficticia" puedeLlevar={false} />);
    await auditarLosDos();
    expect(screen.queryByRole("button", { name: /Llevar partidas al Presupuesto/ })).toBeNull();
  });

  test("el mensaje del servidor se muestra si rechaza el libro", async () => {
    fetchFalso.mockImplementation(async () => json({ detalle: "El libro «frente.xlsx» no tiene ninguna hoja de APU." }, 422));
    render(<AuditarApuPorHoja alExpirar={vi.fn()} />);
    await usuario.upload(campos()[0], new File(["x"], "frente.xlsx"));
    await usuario.click(screen.getByRole("button", { name: "Auditar el libro de APU" }));
    expect(await screen.findByText(/no tiene ninguna hoja de APU/)).toBeInTheDocument();
  });

  test("F7: elegir un nuevo libro limpia el informe anterior y el botón de llevar", async () => {
    conLlevar();
    render(<AuditarApuPorHoja alExpirar={vi.fn()} obra="Vía ficticia" puedeLlevar />);
    await auditarLosDos();
    expect(screen.getByRole("button", { name: /Llevar partidas al Presupuesto/ })).toBeInTheDocument();
    await usuario.upload(campos()[0], new File(["y"], "nuevo.xlsx"));
    expect(screen.queryByRole("button", { name: /Llevar partidas al Presupuesto/ })).toBeNull();
  });
});
