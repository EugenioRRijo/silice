import { configure, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { DialogoSalida } from "../../shell/DialogoSalida";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { cancelarSalida } from "../../shell/salida";
import { olvidarFormularios } from "../../shell/sucio";
import PaginaHoja from "./index";
import type { BorradorAbierto, FilaPresupuesto, VersionesRespuesta, VistaPresupuesto } from "./logica";

// Tarea 16 del plan de montar un presupuesto: la Hoja muestra, junto al precio unitario de cada partida, el precio de
// venta objetivo que se guardó en «Estudio de mercado» y el margen contra ese precio unitario (diseño §5.1: «APU
// 2.074,44 · objetivo de mercado 1.980,00 · margen −4,6 %»). El margen lo calcula la API (`GET /v1/mercado/objetivos`
// con `pu` y `moneda`, `api/rutas/mercado.py`); la interfaz solo lo formatea. El servidor se simula con la forma de ese
// contrato: montos con punto decimal, `margen` con una cifra decimal o null. Obra y partidas ficticias (la vivienda de
// 80 m²).
configure({ asyncUtilTimeout: 5000 });

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja"],
  modo_entrega: false,
};

const ID = "id-borrador-vivienda-objetivo";
const COLUMNA = "Objetivo de mercado";
const AYUDA =
  "Objetivo de mercado: el precio de venta que guardó en «Estudio de mercado». El margen lo compara con el precio unitario " +
  "(con utilidad, sin IVA): negativo si el objetivo queda por debajo.";

const VERSIONES: VersionesRespuesta = {
  proyecto: "VIV-80",
  moneda: "Bs",
  por_omision: "VIV-001",
  versiones: [{ codigo: "VIV-001", fecha: "2026-10-25", motivo: "", origen: "", vigente: true, descartada: false, cambios: 0 }],
};

const ABIERTO: BorradorAbierto = {
  id: ID,
  base: { proyecto: "VIV-80", version: "VIV-001", vigente: "VIV-001", lista: "Lista de la carpeta", espacio_de: "VIV-001", solo_lectura: false, moneda: "Bs" },
  resumen: {
    rev: 0,
    moneda: "Bs",
    total: { texto: "0.00", exacto: "0" },
    cambios: 0,
    pendientes_catalogo: 0,
    hallazgos: [],
    hay_plan: false,
    version_mas_nueva: null,
    guardado_como: null,
    espacio_vacio: true,
  },
  instantanea: { creadas: 0, mensaje: null },
};

function fila(partida: string, pu: { texto: string; exacto: string } | null, extra: Partial<FilaPresupuesto> = {}): FilaPresupuesto {
  return {
    clave: `${partida}|a-mano:1`,
    partida,
    descripcion: `Partida ficticia ${partida}`,
    unidad: "m3",
    cantidad: "1",
    cantidad_calculada: "1",
    escrita: false,
    pu,
    total: pu,
    estado: { severidad: null, texto: "OK" },
    quitable: true,
    nota: null,
    calculo: null,
    ...extra,
  };
}

// OBRA-04: el ejemplo del diseño (el exacto lleva más decimales que el texto: viaja el exacto). OBRA-02: sin objetivo.
// OBRA-03: precio pendiente, con objetivo. OBRA-05: objetivo por encima. OBRA-06: objetivo en USD con la obra en Bs.
const FILAS: FilaPresupuesto[] = [
  fila("OBRA-04", { texto: "2074.44", exacto: "2074.4449" }),
  fila("OBRA-02", { texto: "30.00", exacto: "30" }),
  fila("OBRA-03", null),
  fila("OBRA-05", { texto: "1800.00", exacto: "1800" }),
  fila("OBRA-06", { texto: "1000.00", exacto: "1000" }),
];

const OBJETIVOS = {
  objetivos: [
    { codigo: "OBRA-04", precio: "1980.00", moneda: "Bs", margen: "-4.6" },
    { codigo: "OBRA-03", precio: "1500.00", moneda: "Bs", margen: null },
    { codigo: "OBRA-05", precio: "1980.00", moneda: "Bs", margen: "10.0" },
    { codigo: "OBRA-06", precio: "31.50", moneda: "USD", margen: null },
  ],
};

function vista(filas: FilaPresupuesto[]): VistaPresupuesto {
  return { filas, total: { texto: "0.00", exacto: "0" }, moneda: "Bs", vacio_mensaje: filas.length === 0 ? "El presupuesto no tiene renglones todavía." : null };
}

describe("Hoja: objetivo de mercado junto al precio unitario (Tarea 16)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();
  let filas: FilaPresupuesto[];
  let alObjetivos: (url: URL) => Response | Promise<Response>;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    filas = FILAS;
    alObjetivos = () => json(OBJETIVOS);
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/hoja/versiones")) return json(VERSIONES);
      if (url.startsWith("/v1/hoja/borradores") && !url.includes(ID) && metodo === "GET") return json({ borradores: [] });
      if (url === "/v1/hoja/borradores" && metodo === "POST") return json(ABIERTO, 201);
      if (url === `/v1/hoja/borradores/${ID}` && metodo === "GET") return json({ id: ID, base: ABIERTO.base, resumen: ABIERTO.resumen });
      if (url.endsWith("/vistas/presupuesto")) return json(vista(filas));
      if (url.startsWith("/v1/mercado/objetivos") && metodo === "GET") return alObjetivos(new URL(url, "http://local"));
      return json({ detalle: `ruta inesperada ${metodo} ${url}` }, 500);
    });
  });
  afterEach(() => {
    cancelarSalida();
    olvidarFormularios();
    vi.unstubAllGlobals();
  });

  const pedidasDeObjetivos = () =>
    fetchFalso.mock.calls.map(([r]) => String(r)).filter((r) => r.startsWith("/v1/mercado/objetivos")).map((r) => new URL(r, "http://local"));

  function montar() {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: "VIV-80",
      nombreProyecto: "Vivienda de 80 m²",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter initialEntries={["/hoja"]}>
          <Routes>
            <Route path="/hoja" element={<PaginaHoja />} />
          </Routes>
          <DialogoSalida />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  // La celda de la columna «Objetivo de mercado» en la fila de `partida`, y la fila entera.
  async function celdaDe(partida: string) {
    const tabla = await screen.findByRole("table", { name: "Presupuesto" });
    const titulos = within(tabla).getAllByRole("columnheader").map((c) => c.textContent?.trim());
    const indice = titulos.indexOf(COLUMNA);
    expect(indice).toBeGreaterThan(-1);
    const fila = within(tabla)
      .getAllByRole("row")
      .find((r) => within(r).queryByText(partida) !== null)!;
    expect(fila).toBeDefined();
    return { fila, celda: within(fila).getAllByRole("cell")[indice]! };
  }

  const texto = (el: HTMLElement) => (el.textContent ?? "").replace(/\s+/g, " ").trim();

  test("la fila de OBRA-04 dice «APU 2.074,44 · objetivo de mercado 1.980,00 · margen −4,6 %»", async () => {
    montar();
    await waitFor(async () => expect(texto((await celdaDe("OBRA-04")).celda)).toContain("1.980,00"));
    const { fila, celda } = await celdaDe("OBRA-04");
    // El precio unitario de la fila (la columna de al lado) y, en la nueva, el objetivo y su margen.
    const titulos = within(screen.getByRole("table", { name: "Presupuesto" }))
      .getAllByRole("columnheader")
      .map((c) => c.textContent?.trim());
    expect(titulos.indexOf(COLUMNA)).toBe(titulos.indexOf("Precio unitario") + 1);
    expect(texto(within(fila).getAllByRole("cell")[titulos.indexOf("Precio unitario")]!)).toContain("2.074,44");
    expect(texto(celda)).toBe("1.980,00 · margen −4,6 %");
    // El signo es el menos tipográfico (U+2212), no el guion, y no hay color que lo sustituya.
    expect(texto(celda)).not.toContain("-");
    expect(celda.querySelector("[class*='danger'], [class*='error'], [style*='color']")).toBeNull();
    // Sin `title` con el decimal con punto.
    expect(celda.querySelector("[title]")).toBeNull();
    expect(screen.getByText(AYUDA)).toBeInTheDocument();
  });

  test("pide los objetivos una vez, con los precios unitarios exactos de la Hoja y su moneda", async () => {
    montar();
    await waitFor(async () => expect(texto((await celdaDe("OBRA-04")).celda)).toContain("1.980,00"));
    const pedidas = pedidasDeObjetivos();
    expect(pedidas).toHaveLength(1);
    const p = pedidas[0]!.searchParams;
    expect(p.get("partidas")).toBe("OBRA-04,OBRA-02,OBRA-03,OBRA-05,OBRA-06");
    // OBRA-03 no tiene precio unitario: no viaja en `pu`. Viaja el exacto, no el texto a dos decimales.
    expect(p.get("pu")).toBe("OBRA-04:2074.4449,OBRA-02:30,OBRA-05:1800,OBRA-06:1000");
    expect(p.get("moneda")).toBe("Bs");
  });

  test("la misma partida en dos renglones viaja una vez y las dos filas dicen su margen", async () => {
    filas = [
      fila("OBRA-04", { texto: "2074.44", exacto: "2074.4449" }, { clave: "OBRA-04|esp_muros:M1", quitable: false }),
      fila("OBRA-04", { texto: "2074.44", exacto: "2074.4449" }),
    ];
    montar();
    const tabla = await screen.findByRole("table", { name: "Presupuesto" });
    await waitFor(() => expect(within(tabla).getAllByText("1.980,00 · margen −4,6 %", { exact: false })).toHaveLength(2));
    const p = pedidasDeObjetivos()[0]!.searchParams;
    expect(p.get("partidas")).toBe("OBRA-04");
    expect(p.get("pu")).toBe("OBRA-04:2074.4449");
  });

  test("sin objetivo la columna queda vacía", async () => {
    montar();
    await waitFor(async () => expect(texto((await celdaDe("OBRA-04")).celda)).toContain("1.980,00"));
    expect(texto((await celdaDe("OBRA-02")).celda)).toBe("");
  });

  test("un margen positivo lleva su signo más", async () => {
    montar();
    await waitFor(async () => expect(texto((await celdaDe("OBRA-05")).celda)).toBe("1.980,00 · margen +10,0 %"));
  });

  test("sin precio unitario se muestra el objetivo y se dice que no hay margen", async () => {
    montar();
    await waitFor(async () => expect(texto((await celdaDe("OBRA-03")).celda)).toBe("1.500,00 · sin precio unitario, sin margen"));
  });

  test("un objetivo en otra moneda se dice con su moneda y no se compara", async () => {
    montar();
    await waitFor(async () =>
      expect(texto((await celdaDe("OBRA-06")).celda)).toBe("31,50 USD · en otra moneda que la obra (Bs), sin margen"),
    );
  });

  test("sin ningún objetivo, la columna queda vacía y no hay ayuda", async () => {
    alObjetivos = () => json({ objetivos: [] });
    montar();
    await waitFor(() => expect(pedidasDeObjetivos()).toHaveLength(1));
    for (const partida of ["OBRA-04", "OBRA-02", "OBRA-03", "OBRA-05", "OBRA-06"]) {
      expect(texto((await celdaDe(partida)).celda)).toBe("");
    }
    expect(screen.queryByText(AYUDA)).toBeNull();
  });

  test("si no se pueden leer los objetivos, la Hoja sigue y lo dice con el detalle de la API", async () => {
    alObjetivos = () => json({ detalle: "No se pudo leer ni guardar el estudio de mercado de la carpeta de trabajo." }, 503);
    montar();
    expect(
      await screen.findByText(
        "No se pudieron leer los objetivos de mercado: No se pudo leer ni guardar el estudio de mercado de la carpeta de trabajo.",
      ),
    ).toBeInTheDocument();
    expect(texto((await celdaDe("OBRA-04")).celda)).toBe("");
    expect(screen.getByRole("textbox", { name: "Cantidad, Presupuesto fila 1" })).toBeInTheDocument();
  });

  test("con la sesión vencida (401) avisa al armazón", async () => {
    alObjetivos = () => json({ detalle: "La sesión venció." }, 401);
    montar();
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("muchas partidas se piden por tandas que caben en los límites de la API", async () => {
    // 60 partidas de 40 caracteres: 60 × 41 − 1 = 2.459 > 2.000 caracteres de `partidas`.
    const codigos = Array.from({ length: 60 }, (_, i) => `PARTIDA-${String(i).padStart(2, "0")}`.padEnd(40, "X"));
    filas = codigos.map((c) => fila(c, { texto: "100.00", exacto: "100" }));
    alObjetivos = (url) => {
      const pedidas = (url.searchParams.get("partidas") ?? "").split(",");
      return json({
        objetivos: pedidas.includes(codigos[59]!) ? [{ codigo: codigos[59]!, precio: "90.00", moneda: "Bs", margen: "-10.0" }] : [],
      });
    };
    montar();
    await waitFor(() => expect(pedidasDeObjetivos().length).toBeGreaterThan(1));
    const tandas = pedidasDeObjetivos().map((u) => u.searchParams);
    for (const t of tandas) {
      expect((t.get("partidas") ?? "").length).toBeLessThanOrEqual(2000);
      expect((t.get("pu") ?? "").length).toBeLessThanOrEqual(4000);
      expect(t.get("moneda")).toBe("Bs");
    }
    expect(tandas.flatMap((t) => (t.get("partidas") ?? "").split(","))).toEqual(codigos);
    // La fila 60 está en la segunda página de la tabla (50 por página); su objetivo llega igual a la Hoja.
    await waitFor(() => expect(screen.getByText(AYUDA)).toBeInTheDocument());
  });
});
