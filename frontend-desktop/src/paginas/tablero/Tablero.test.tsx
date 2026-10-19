import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaTablero from "./index";
import { datosDeAnillo, datosDeVersiones, rolDeSerie, seriesDeCurva } from "./logica";
import type { TableroRespuesta } from "./logica";

vi.mock("../../comun/GraficoCarbon", () => ({
  default: ({ tipo, datos }: { tipo: string; datos: unknown[] }) => (
    <div data-testid={`grafico-${tipo}`} data-filas={datos.length} />
  ),
}));

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["leer_proyecto"],
  modo_entrega: false,
};

const TABLERO: TableroRespuesta = {
  proyecto: "OB-S2",
  version: "OB-001",
  fecha: "2026-11-02",
  moneda: "USD",
  renglones: 3,
  tarjetas: [{ rotulo: "Total del contrato", valor: "5060.00", detalle: "" }],
  control: {
    disponible: true,
    motivo: "",
    anillos: [
      { rotulo: "Avance fisico", fraccion: "0.3", texto: "30,0 %", favorable: null },
      { rotulo: "SPI (plazo)", fraccion: "0.8", texto: "0,80", favorable: false },
      { rotulo: "CPI (costo)", fraccion: null, texto: "—", favorable: false },
    ],
    tarjetas: [{ rotulo: "EAC", valor: "4266.67", detalle: "" }],
  },
  curvas: {
    titulo: "Valor ganado (PV, EV, AC)",
    series: [
      { serie: "PV", puntos: [{ orden: 2, periodo: "M2", valor: "2000" }, { orden: 1, periodo: "M1", valor: "1000" }] },
      { serie: "EV", puntos: [{ orden: 1, periodo: "M1", valor: "800" }] },
    ],
  },
  desglose: [{ rubro: "Costo directo", monto: "4000.00", peso: "79,0 %", valor: "4000" }],
  pareto: [
    { partida: "P-01", descripcion: "Concreto", total: "3000.00", peso: "59,3 %", acumulado: "59,3 %", valor: "3000" },
  ],
  versiones: [
    { version: "OB-001", fecha: "2026-11-02", motivo: "Inicial", costo_directo: "4000.00", total: "5060.00", vigente: true, valor: "5060" },
  ],
};

describe("Tablero del proyecto", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
  });
  afterEach(() => vi.unstubAllGlobals());

  function montar(proyecto: string | null) {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto,
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    render(
      <ContextoAplicacion.Provider value={valor}>
        <PaginaTablero />
      </ContextoAplicacion.Provider>,
    );
  }

  test("sin proyecto invita a elegirlo y no pide nada a la API", () => {
    montar(null);
    expect(screen.getByText("Elija un proyecto")).toBeInTheDocument();
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("pide el tablero del proyecto y muestra tarjetas, anillos, curva, desglose, Pareto y versiones", async () => {
    fetchFalso.mockImplementation(async () => json(TABLERO));
    montar("OB-S2");
    expect(await screen.findByText("Total del contrato")).toBeInTheDocument();
    expect(String(fetchFalso.mock.calls[0]![0])).toContain("/v1/tablero?proyecto=OB-S2");
    expect(screen.getByText("Version OB-001 del 2026-11-02 · 3 renglones · USD")).toBeInTheDocument();
    // tres anillos con su texto; el que no tiene dato no dibuja grafico
    expect(screen.getByLabelText("SPI (plazo): 0,80 (desfavorable)")).toBeInTheDocument();
    expect(await screen.findAllByTestId("grafico-anillo")).toHaveLength(2 + 1); // 2 anillos con dato + el desglose
    expect(await screen.findByTestId("grafico-linea")).toBeInTheDocument();
    expect(await screen.findAllByTestId("grafico-barras")).toHaveLength(2); // Pareto y versiones
    // cada grafico tiene su tabla con los montos exactos
    const pareto = screen.getByRole("table", { name: "Partidas que mas pesan" });
    expect(within(pareto).getByText("3000.00")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Versiones del presupuesto" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Montos de Valor ganado (PV, EV, AC)" })).toBeInTheDocument();
  });

  test("sin control de obra lo dice con su motivo", async () => {
    fetchFalso.mockImplementation(async () =>
      json({ ...TABLERO, control: { disponible: false, motivo: "No hay linea base declarada.", anillos: [], tarjetas: [] } }),
    );
    montar("OB-S2");
    expect(await screen.findByText("Aun no hay control de obra")).toBeInTheDocument();
    expect(screen.getByText("No hay linea base declarada.")).toBeInTheDocument();
  });

  test("un proyecto sin version guardada explica que hacer", async () => {
    fetchFalso.mockImplementation(async () =>
      json({ ...TABLERO, version: null, fecha: null, moneda: null, tarjetas: [], control: null, curvas: null, desglose: [], pareto: [], versiones: [] }),
    );
    montar("OB-S2");
    expect(await screen.findByText("Este proyecto aun no tiene presupuesto guardado")).toBeInTheDocument();
  });

  test("403 y 404 se dicen con palabras, no como error", async () => {
    fetchFalso.mockImplementation(async () => json({ detalle: "no" }, 403));
    montar("OB-S2");
    expect(await screen.findByText("Su cuenta no puede ver el tablero")).toBeInTheDocument();
  });

  test("404 dice que el proyecto no existe en el caso", async () => {
    fetchFalso.mockImplementation(async () => json({ detalle: "no existe" }, 404));
    montar("X");
    expect(await screen.findByText("Ese proyecto no existe en este caso")).toBeInTheDocument();
  });
});

describe("logica del tablero", () => {
  test("el anillo es una dona de dos porciones con tope en 100 %", () => {
    expect(datosDeAnillo({ rotulo: "a", fraccion: "0.25", texto: "", favorable: null })).toEqual([
      { group: "Logrado", value: 0.25 },
      { group: "Falta", value: 0.75 },
    ]);
    expect(datosDeAnillo({ rotulo: "a", fraccion: "1.4", texto: "", favorable: true })).toEqual([
      { group: "Logrado", value: 1 },
      { group: "Falta", value: 0 },
    ]);
    expect(datosDeAnillo({ rotulo: "a", fraccion: null, texto: "", favorable: null })).toBeNull();
  });

  test("EV y AC son lo real; PV y Plan, lo previsto", () => {
    expect(["PV", "Plan", "EV", "AC"].map(rolDeSerie)).toEqual(["plan", "plan", "real", "real"]);
  });

  test("las series salen ordenadas por el orden del periodo", () => {
    const series = seriesDeCurva(TABLERO.curvas!);
    expect(series[0]!.puntos.map((p) => p.periodo)).toEqual(["M1", "M2"]);
  });

  test("la version vigente se rotula en el grafico", () => {
    expect(datosDeVersiones(TABLERO.versiones)).toEqual([{ group: "OB-001 (vigente)", value: 5060 }]);
  });
});
