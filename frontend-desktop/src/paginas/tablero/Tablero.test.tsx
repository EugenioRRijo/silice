import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaTablero from "./index";
import { datosDeVersiones, detalleDeTarjeta, rolDeSerie, seriesDeCurva } from "./logica";
import type { TableroRespuesta } from "./logica";

interface Ejes {
  axes?: { bottom?: { ticks?: { formatter?: (n: number) => string } } };
  pie?: { labels?: { formatter?: (d: { data: { group: string } }) => string } };
  donut?: { center?: { numberFormatter?: (n: number) => string } };
}

vi.mock("../../comun/GraficoCarbon", () => ({
  default: ({ tipo, datos, opciones }: { tipo: string; datos: unknown[]; opciones: unknown }) => (
    <div data-testid={`grafico-${tipo}`} data-filas={datos.length} data-opciones={JSON.stringify(opciones)}
      data-eje={(opciones as Ejes).axes?.bottom?.ticks?.formatter?.(4131)}
      data-etiqueta={(opciones as Ejes).pie?.labels?.formatter?.({ data: { group: "Costo directo" } })}
      data-centro={(opciones as Ejes).donut?.center?.numberFormatter?.(5060.000000001)}
    />
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
  desglose: [{ rubro: "Costo directo", monto: "4000.00", peso: "79.0 %", valor: "4000" }],
  pareto: [
    { partida: "P-01", descripcion: "Concreto", total: "3000.00", peso: "59.3 %", acumulado: "61.4 %", valor: "3000" },
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
    // VB-19: la fecha se lee dd/mm/aaaa
    expect(screen.getByText("Versión OB-001 del 02/11/2026 · 3 renglones · USD")).toBeInTheDocument();
    const versiones = screen.getByRole("table", { name: "Versiones del presupuesto" });
    // VD-5: la fecha no lleva su forma ISO en el title; las cifras si llevan su exacto
    expect(within(versiones).getByText("02/11/2026")).not.toHaveAttribute("title");
    expect([...versiones.querySelectorAll("[title]")].every((e) => /^-?[0-9]+(\.[0-9]+)?$/.test(e.getAttribute("title") ?? ""))).toBe(true);
    // V-21: un indice (SPI 0,98) no es una parte de un todo: no hay donas de avance, SPI ni CPI, solo los indicadores
    expect(screen.queryByLabelText(/SPI \(plazo\)/)).toBeNull();
    expect(screen.getByText("EAC")).toBeInTheDocument();
    expect(await screen.findAllByTestId("grafico-anillo")).toHaveLength(1); // solo el desglose del contrato
    expect(await screen.findByTestId("grafico-linea")).toBeInTheDocument();
    expect(await screen.findAllByTestId("grafico-barras")).toHaveLength(2); // Pareto y versiones
    // cada grafico tiene su tabla con los montos exactos
    const pareto = screen.getByRole("table", { name: "Partidas que más pesan" });
    expect(within(pareto).getByText("3.000,00")).toBeInTheDocument();
    expect(within(pareto).getByTitle("3000.00")).toBeInTheDocument(); // el exacto, a un toque (V-19)
    expect(screen.getByRole("table", { name: "Versiones del presupuesto" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Montos de Valor ganado (PV, EV, AC)" })).toBeInTheDocument();
  });

  test("los graficos usan la paleta de DESIGN.md: una escala por grupo y nada de morado (V-21)", async () => {
    fetchFalso.mockImplementation(async () => json(TABLERO));
    montar("OB-S2");
    const graficos = await screen.findAllByTestId(/grafico-(anillo|barras)/);
    expect(graficos.length).toBeGreaterThan(0);
    for (const g of graficos) {
      const opciones = JSON.parse(g.getAttribute("data-opciones")!) as { color?: { scale: Record<string, string> } };
      expect(opciones.color?.scale).toBeDefined();
      expect(Object.values(opciones.color!.scale).join(" ")).not.toMatch(/8a3ffc|6929c4|a56eff|be95ff/i);
    }
  });

  test("cifras y ejes en es-VE, con el exacto en el title (V-19)", async () => {
    fetchFalso.mockImplementation(async () =>
      json({ ...TABLERO, tarjetas: [{ rotulo: "Total del contrato", valor: "95066.60 USD", detalle: "" }] }),
    );
    montar("OB-S2");
    const tarjeta = await screen.findByText("95.066,60 USD");
    expect(tarjeta).toHaveAttribute("title", "95066.60 USD");
    const barras = await screen.findAllByTestId("grafico-barras");
    for (const b of barras) expect(b).toHaveAttribute("data-eje", "4.131");
  });

  test("porcentajes del desglose y del Pareto con coma es-VE, tambien en el anillo (VB-21)", async () => {
    fetchFalso.mockImplementation(async () => json(TABLERO));
    montar("OB-S2");
    const desglose = await screen.findByRole("table", { name: "Desglose del contrato" });
    expect(within(desglose).getByText("79,0 %")).toHaveAttribute("title", "79.0 %");
    const pareto = screen.getByRole("table", { name: "Partidas que más pesan" });
    expect(within(pareto).getByText("59,3 %")).toHaveAttribute("title", "59.3 %");
    expect(within(pareto).getByText("61,4 %")).toHaveAttribute("title", "61.4 %");
    // la etiqueta de la porcion es el peso de la API, no un porcentaje recalculado por el grafico
    const [anillo] = await screen.findAllByTestId("grafico-anillo");
    expect(anillo).toHaveAttribute("data-etiqueta", "79,0 %");
  });

  test("el total lleva el exacto de la API en el title y el centro del anillo no muestra decimales de float (VB-21)", async () => {
    fetchFalso.mockImplementation(async () =>
      json({
        ...TABLERO,
        tarjetas: [{ rotulo: "Total del contrato", valor: "95066.60 USD", detalle: "", exacto: "95066.60006250" }],
      }),
    );
    montar("OB-S2");
    const tarjeta = await screen.findByText("95.066,60 USD");
    expect(tarjeta).toHaveAttribute("title", "Valor exacto: 95066.60006250 USD");
    const [anillo] = await screen.findAllByTestId("grafico-anillo");
    expect(anillo).toHaveAttribute("data-centro", "95.066,60");
  });

  test("el punto de equilibrio nombra el período con el mismo arreglo que el eje de la curva: «Día 1» (VD-8)", async () => {
    // El texto tal como lo manda la API para DEMO-001 (core/budget/equilibrio.py arma «se alcanza en {periodo}» y
    // core/budget/curva.py nombra el periodo «Dia N [partida]»).
    const equilibrio = { rotulo: "Punto de equilibrio", valor: "82.10 %", detalle: "se alcanza en Dia 1 [DEMO-01-INST]" };
    fetchFalso.mockImplementation(async () => json({ ...TABLERO, tarjetas: [...TABLERO.tarjetas, equilibrio] }));
    montar("DEMO-001");
    expect(await screen.findByText("se alcanza en Día 1 [DEMO-01-INST]")).toBeInTheDocument();
    expect(screen.queryByText(/Dia 1/)).toBeNull();
  });

  test("sin control de obra lo dice con su motivo", async () => {
    fetchFalso.mockImplementation(async () =>
      json({ ...TABLERO, control: { disponible: false, motivo: "No hay linea base declarada.", anillos: [], tarjetas: [] } }),
    );
    montar("OB-S2");
    expect(await screen.findByText("Aún no hay control de obra")).toBeInTheDocument();
    expect(screen.getByText("No hay linea base declarada.")).toBeInTheDocument();
  });

  test("un proyecto sin version guardada explica que hacer", async () => {
    fetchFalso.mockImplementation(async () =>
      json({ ...TABLERO, version: null, fecha: null, moneda: null, tarjetas: [], control: null, curvas: null, desglose: [], pareto: [], versiones: [] }),
    );
    montar("OB-S2");
    expect(await screen.findByText("Este proyecto aún no tiene presupuesto guardado")).toBeInTheDocument();
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
  test("detalleDeTarjeta solo toca el período de la frase fija del punto de equilibrio (VD-8)", () => {
    const pe = (detalle: string) => ({ rotulo: "Punto de equilibrio", valor: "50.00 %", detalle });
    expect(detalleDeTarjeta(pe("se alcanza en Dia 12 [A-1]"))).toBe("se alcanza en Día 12 [A-1]");
    // un periodo que escribio el usuario y que no es «Dia N» queda igual
    expect(detalleDeTarjeta(pe("se alcanza en Mes 3"))).toBe("se alcanza en Mes 3");
    expect(detalleDeTarjeta(pe("se alcanza en Diario 1"))).toBe("se alcanza en Diario 1");
    // otras frases del nucleo y otras tarjetas no se tocan aunque digan «Dia 1»
    const sinCurva = "sin curva de inversion: el punto de equilibrio no se ubica en el plan";
    expect(detalleDeTarjeta(pe(sinCurva))).toBe(sinCurva);
    expect(detalleDeTarjeta(pe("Dia 1 se alcanza en Dia 1"))).toBe("Dia 1 se alcanza en Dia 1");
    expect(detalleDeTarjeta({ rotulo: "Auditoría", valor: "Cumple", detalle: "se alcanza en Dia 1" })).toBe("se alcanza en Dia 1");
  });

  test("detalleDeTarjeta devuelve en menos de un segundo un detalle hostil de 100 000 caracteres (VD-8)", () => {
    const hostiles = ["se alcanza en " + "Dia 1 ".repeat(20_000), "Dia ".repeat(25_000), "se alcanza en Dia " + "9".repeat(100_000)];
    for (const detalle of hostiles) {
      const inicio = performance.now();
      const visto = detalleDeTarjeta({ rotulo: "Punto de equilibrio", valor: "", detalle });
      const ms = performance.now() - inicio;
      console.log(`detalleDeTarjeta ${detalle.length} car.: ${ms.toFixed(1)} ms`);
      expect(ms).toBeLessThan(1_000);
      // mas largo que el tope, sale tal cual
      expect(visto).toBe(detalle);
    }
  }, 120_000);

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
