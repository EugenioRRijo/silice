import { render, screen, within } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import {
  aplicarTrazos,
  CurvaPlanAvance,
  filasDeGrafico,
  globoDelPunto,
  periodoLegible,
  periodos,
  rotulosDeCurva,
  TRAZO_DE_GASTADO,
  TRAZO_DE_PLAN,
  TRAZO_DE_PRONOSTICO,
} from "./CurvaPlanAvance";
import type { SerieDeCurva } from "./CurvaPlanAvance";

interface OpcionesFalsas {
  axes?: { left?: { ticks?: { formatter?: (n: number) => string } }; bottom?: { thresholds?: { value: unknown; label?: string }[] } };
  tooltip?: { valueFormatter?: (n: number) => string; customHTML?: (data: unknown, html: string, datum: unknown) => string };
  color?: { scale: Record<string, string> };
  points?: { enabled?: boolean; radius?: number };
}

vi.mock("./GraficoCarbon", () => ({
  default: ({ tipo, datos, opciones }: { tipo: string; datos: unknown[]; opciones: OpcionesFalsas }) => (
    <div
      data-testid="grafico"
      data-tipo={tipo}
      data-filas={datos.length}
      data-eje={opciones.axes?.left?.ticks?.formatter?.(4131)}
      data-tooltip={opciones.tooltip?.valueFormatter?.(95066.6)}
      data-colores={JSON.stringify(opciones.color?.scale ?? null)}
      data-cortes={JSON.stringify(opciones.axes?.bottom?.thresholds ?? null)}
      data-puntos={JSON.stringify(opciones.points ?? null)}
      data-globo={opciones.tooltip?.customHTML?.([{ group: "PV", key: "Día 2", value: 100 }], "", {})}
    />
  ),
}));

const SERIES: SerieDeCurva[] = [
  { nombre: "PV", rol: "plan", puntos: [{ periodo: "M1", valor: "1000.00" }, { periodo: "M2", valor: "2500.50" }] },
  { nombre: "EV", rol: "real", puntos: [{ periodo: "M1", valor: "800.00" }] },
  { nombre: "EAC", rol: "pronostico", puntos: [{ periodo: "M2", valor: "2600.00" }] },
];

describe("CurvaPlanAvance", () => {
  test("pasa al grafico una fila por punto, con el valor como numero", () => {
    expect(filasDeGrafico(SERIES)).toHaveLength(4);
    expect(filasDeGrafico(SERIES)[1]).toEqual({ group: "PV", key: "M2", value: 2500.5 });
  });

  test("«Dia N» de la API se lee «Día N» y lo demas queda igual (V-20)", () => {
    expect(periodoLegible("Dia 1")).toBe("Día 1");
    expect(periodoLegible("Dia 12 [LB-01-EXC]")).toBe("Día 12 [LB-01-EXC]");
    expect(periodoLegible("M2")).toBe("M2");
    expect(filasDeGrafico([{ nombre: "PV", rol: "plan", puntos: [{ periodo: "Dia 3", valor: "1" }] }])[0]!.key).toBe("Día 3");
  });

  test("los periodos salen una sola vez y en orden", () => {
    expect(periodos(SERIES)).toEqual(["M1", "M2"]);
  });

  test("dibuja el grafico y deja la tabla con los montos exactos y un guion donde no hay dato", async () => {
    render(<CurvaPlanAvance titulo="Valor ganado" series={SERIES} unidad="USD" />);
    expect(await screen.findByTestId("grafico")).toHaveAttribute("data-tipo", "linea");
    expect(screen.getByRole("table", { name: "Montos de Valor ganado" })).toBeInTheDocument();
    expect(screen.getByText("Ver como tabla")).toBeInTheDocument();
    expect(screen.getByText("2.500,50")).toBeInTheDocument();
    expect(screen.getAllByText("—")).toHaveLength(2);
    expect(
      screen.getByText("Línea punteada gris: planificado · Línea continua: ejecutado (EV) · Línea discontinua larga: pronóstico."),
    ).toBeInTheDocument();
  });

  test("el eje y el tooltip salen en es-VE y las series tienen su color sin morado (V-19, V-21)", async () => {
    render(<CurvaPlanAvance titulo="Valor ganado" series={SERIES} unidad="USD" />);
    const g = await screen.findByTestId("grafico");
    expect(g).toHaveAttribute("data-eje", "4.131");
    expect(g).toHaveAttribute("data-tooltip", "95.066,6");
    const colores = JSON.parse(g.getAttribute("data-colores")!) as Record<string, string>;
    expect(Object.keys(colores)).toEqual(["PV", "EV", "EAC"]);
    // El plan es neutro; lo real, la serie 1; el pronóstico, la serie 3 (modo claro).
    expect(colores).toEqual({ PV: "#9A9184", EV: "#2A78D6", EAC: "#EB6834" });
  });

  test("el plan va punteado y neutro, lo real continuo, el pronóstico con raya larga; todas a 2 px salvo el plan", () => {
    const raiz = document.createElement("div");
    raiz.innerHTML = '<svg><path class="line"></path><path class="line"></path><path class="line"></path></svg>';
    const trazos = [...raiz.querySelectorAll<SVGPathElement>("path.line")];
    ["PV", "EV", "EAC"].forEach((name, i) => Object.assign(trazos[i]!, { __data__: { name } }));
    aplicarTrazos(raiz, SERIES);
    expect(trazos.map((t) => t.style.strokeDasharray)).toEqual([TRAZO_DE_PLAN, "none", TRAZO_DE_PRONOSTICO]);
    expect(TRAZO_DE_PLAN).not.toBe(TRAZO_DE_PRONOSTICO);
    expect(trazos.map((t) => t.style.strokeWidth)).toEqual(["1.5", "2", "2"]);
  });

  // Pasada goldfish N1.6: EV y AC compartían el trazo y la leyenda no decía cuál era cuál.
  test("lo gastado (AC) va de puntos redondos, distinto de lo ejecutado (EV) y del pronóstico", () => {
    const series: SerieDeCurva[] = [...SERIES, { nombre: "AC", rol: "gastado", puntos: [{ periodo: "M1", valor: "900.00" }] }];
    const raiz = document.createElement("div");
    raiz.innerHTML = '<svg><path class="line"></path><path class="line"></path></svg>';
    const trazos = [...raiz.querySelectorAll<SVGPathElement>("path.line")];
    ["EV", "AC"].forEach((name, i) => Object.assign(trazos[i]!, { __data__: { name } }));
    aplicarTrazos(raiz, series);
    expect(trazos.map((t) => t.style.strokeWidth)).toEqual(["2", "2"]);
    expect(trazos[0]!.style.strokeDasharray).toBe("none");
    expect(trazos[1]!.style.strokeDasharray).toBe(TRAZO_DE_GASTADO);
    expect(TRAZO_DE_GASTADO).not.toBe(TRAZO_DE_PRONOSTICO);
    render(<CurvaPlanAvance titulo="Valor ganado" series={series} unidad="USD" />);
    expect(
      screen.getByText(
        "Línea punteada gris: planificado · Línea continua: ejecutado (EV) · Línea de puntos: gastado (AC) · Línea discontinua larga: pronóstico.",
      ),
    ).toBeInTheDocument();
  });
});

const DIAS: SerieDeCurva[] = [
  {
    nombre: "PV",
    rol: "plan",
    puntos: [
      { periodo: "Dia 1", valor: "0.00" },
      { periodo: "Dia 2", valor: "100.00" },
      { periodo: "Dia 3", valor: "200.00" },
    ],
  },
  {
    nombre: "EV",
    rol: "real",
    puntos: [
      { periodo: "Dia 1", valor: "0.00" },
      { periodo: "Dia 2", valor: "80.00" },
    ],
  },
];

describe("filasDeGrafico: la cifra del servidor pasa a geometría solo por valorParaDibujar", () => {
  test("un decimal de la API se dibuja; lo que no es un decimal con punto no se dibuja (NaN) en vez de leerse como número", () => {
    const filas = filasDeGrafico([
      { nombre: "PV", rol: "plan", puntos: [{ periodo: "Dia 1", valor: "100.50" }, { periodo: "Dia 2", valor: "1e3" }, { periodo: "Dia 3", valor: "0x10" }] },
    ]);
    expect(filas.map((f) => f.value)).toEqual([100.5, Number.NaN, Number.NaN]);
  });
});

describe("el detalle a lo largo de la curva", () => {
  test("rotula el inicio, el corte y el final con el valor de cada serie en es-VE", () => {
    const r = rotulosDeCurva(DIAS, "USD");
    expect(r.map((x) => [x.etiqueta, x.periodo, x.partes])).toEqual([
      ["Inicio", "Día 1", ["planificado 0,00 USD", "real 0,00 USD"]],
      ["Corte", "Día 2", ["planificado 100,00 USD", "real 80,00 USD"]],
      ["Final", "Día 3", ["planificado 200,00 USD"]],
    ]);
  });

  test("si el corte es el último período, un solo rótulo dice «Corte y final»; sin serie real no hay corte", () => {
    const completa: SerieDeCurva[] = [
      { nombre: "PV", rol: "plan", puntos: [{ periodo: "M1", valor: "1" }, { periodo: "M2", valor: "2" }] },
      { nombre: "EV", rol: "real", puntos: [{ periodo: "M1", valor: "1" }, { periodo: "M2", valor: "2" }] },
    ];
    expect(rotulosDeCurva(completa, "").map((x) => x.etiqueta)).toEqual(["Inicio", "Corte y final"]);
    expect(rotulosDeCurva([completa[0]!], "").map((x) => x.etiqueta)).toEqual(["Inicio", "Final"]);
  });

  test("el globo del punto dice lo planificado y lo real tal como los manda el servidor, sin restarlos", () => {
    const html = globoDelPunto(DIAS, "Día 2", "USD", { PV: "#9A9184", EV: "#2A78D6" });
    expect(html).toContain("Día 2");
    expect(html).toContain("100,00 USD");
    expect(html).toContain("80,00 USD");
    expect(html).toContain("Planificado");
    expect(html).toContain("Real");
    // La pantalla no calcula cifras (DESIGN.md): ni la línea «Diferencia» ni el resultado de la resta.
    expect(html).not.toContain("Diferencia");
    expect(html).not.toContain("-20,00");
    expect(html).toContain("#2A78D6");
  });

  test("el globo de un punto sin dato real solo dice lo que hay", () => {
    const html = globoDelPunto(DIAS, "Día 3", "USD", {});
    expect(html).toContain("200,00 USD");
    expect(html).not.toContain("Real (");
  });

  test("el globo no deja pasar HTML de un nombre de serie", () => {
    const html = globoDelPunto([{ nombre: "<img src=x onerror=1>", rol: "real", puntos: [{ periodo: "M1", valor: "1" }] }], "M1", "", {});
    expect(html).not.toContain("<img");
    expect(html).toContain("&lt;img");
  });

  test("el corte se marca en el grafico con su rotulo y los valores se rotulan debajo", async () => {
    render(<CurvaPlanAvance titulo="Avance" series={DIAS} unidad="USD" />);
    const g = await screen.findByTestId("grafico");
    expect(JSON.parse(g.getAttribute("data-cortes")!)).toEqual([expect.objectContaining({ value: "Día 2", label: "Corte: Día 2" })]);
    const rotulos = screen.getByRole("list", { name: "Valores del inicio, el corte y el final" });
    expect(within(rotulos).getAllByRole("listitem")).toHaveLength(3);
    expect(within(rotulos).getByText(/real 80,00 USD/)).toBeInTheDocument();
    expect(g.getAttribute("data-globo")).not.toContain("Diferencia");
  });

  test("el grafico tiene nombre accesible y la tabla trae las mismas cifras", () => {
    render(<CurvaPlanAvance titulo="Avance" series={DIAS} unidad="USD" />);
    expect(screen.getByRole("group", { name: /^Gráfico: Avance/ })).toBeInTheDocument();
    const tabla = screen.getByRole("table", { name: "Montos de Avance" });
    for (const cifra of ["0,00", "100,00", "80,00", "200,00"]) expect(within(tabla).getAllByText(cifra).length).toBeGreaterThan(0);
    expect(within(tabla).getByText("Día 3")).toBeInTheDocument();
  });

  test("con pocos períodos cada uno lleva su punto (de 4 px de radio) para apuntar a él", async () => {
    render(<CurvaPlanAvance titulo="Avance" series={DIAS} unidad="USD" />);
    const g = await screen.findByTestId("grafico");
    expect(JSON.parse(g.getAttribute("data-puntos")!)).toEqual({ enabled: true, radius: 4 });
  });
});
