import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";
import { AnimatedBarChart, AnimatedDonutChart, RadialGauge, RiskRangeMeter } from "./VisualMeters";
import type { DonutSegment } from "./VisualMeters";

// Los medidores dibujan con un número (la fracción o el valor que manda la API, solo para la geometría) y escriben el texto
// que les dan, ya en es-VE: no calculan ni formatean ninguna cifra. Sin dato escriben «—» con «sin dato» para la lectora,
// nunca «0». Crecen al cargar salvo con `prefers-reduced-motion: reduce`, que los pinta ya en su valor final.
// Datos ficticios.

const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const leer = (ruta: string) => nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/${ruta}`, "utf-8");

const matchMediaOriginal = window.matchMedia;
function conMovimientoReducido(reducido: boolean) {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: (consulta: string) => ({
      matches: reducido && consulta.includes("prefers-reduced-motion"),
      media: consulta,
      onchange: null,
      addEventListener() {},
      removeEventListener() {},
      addListener() {},
      removeListener() {},
      dispatchEvent: () => false,
    }),
  });
}

// Los cuadros de animación quedan en una cola que la prueba suelta cuando quiere, con el tiempo que quiere.
let cola: FrameRequestCallback[] = [];
function conCuadrosManuales() {
  cola = [];
  vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
    cola.push(cb);
    return cola.length;
  });
  vi.stubGlobal("cancelAnimationFrame", () => {});
  vi.spyOn(performance, "now").mockReturnValue(0);
}
function soltarCuadros(ms: number) {
  act(() => {
    for (let i = 0; i < 20 && cola.length > 0; i++) {
      const pendientes = cola;
      cola = [];
      pendientes.forEach((cb) => cb(ms));
    }
  });
}

afterEach(() => {
  Object.defineProperty(window, "matchMedia", { configurable: true, value: matchMediaOriginal });
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const arco = (c: HTMLElement) => c.querySelector<SVGCircleElement>(".silice-radial__arco")!;
const desplazamiento = (c: HTMLElement) => Number(arco(c).getAttribute("stroke-dashoffset"));
const circunferencia = (c: HTMLElement) => Number(arco(c).getAttribute("stroke-dasharray"));

describe("RadialGauge: el anillo de un porcentaje del servidor", () => {
  test("escribe el texto que le dan una sola vez, tal cual, y no un número que calcula", () => {
    conMovimientoReducido(true);
    render(<RadialGauge label="Avance fisico" fraccion={0.625} texto="62,5 %" />);
    expect(screen.getAllByText("62,5 %")).toHaveLength(1);
    expect(screen.queryByText(/62\.5/)).toBeNull();
    expect(screen.getByRole("img", { name: "Avance fisico: 62,5 %" })).toBeInTheDocument();
    expect(screen.getByText("Avance fisico")).toBeInTheDocument();
  });

  test("sin texto escribe «—» con «sin dato» para la lectora, nunca «0»", () => {
    conMovimientoReducido(true);
    const { container } = render(<RadialGauge label="Avance fisico" fraccion={null} texto={null} />);
    expect(screen.getByText("—")).toHaveAttribute("aria-hidden", "true");
    expect(screen.getByText("sin dato")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Avance fisico: sin dato" })).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/\b0\b/);
    // Sin fracción no se dibuja arco: queda la pista vacía.
    expect(desplazamiento(container)).toBeCloseTo(circunferencia(container));
  });

  test("la fracción solo dibuja: el arco mide 62,5 % de la vuelta; fuera de 0 a 1 se recorta", () => {
    conMovimientoReducido(true);
    const { container, rerender } = render(<RadialGauge label="Avance" fraccion={0.625} texto="62,5 %" />);
    expect(desplazamiento(container)).toBeCloseTo(circunferencia(container) * 0.375);
    rerender(<RadialGauge label="Avance" fraccion={1.4} texto="140,0 %" />);
    expect(desplazamiento(container)).toBeCloseTo(0);
    expect(screen.getByText("140,0 %")).toBeInTheDocument();
  });

  test("crece al cargar: empieza vacío y llega a su valor; el texto no cuenta hacia arriba", () => {
    conMovimientoReducido(false);
    conCuadrosManuales();
    const { container } = render(<RadialGauge label="Avance" fraccion={0.5} texto="50,0 %" />);
    expect(desplazamiento(container)).toBeCloseTo(circunferencia(container));
    expect(screen.getByText("50,0 %")).toBeInTheDocument();
    soltarCuadros(5_000);
    expect(desplazamiento(container)).toBeCloseTo(circunferencia(container) * 0.5);
  });

  test("con movimiento reducido se pinta ya en su valor, sin pedir cuadros de animación", () => {
    conMovimientoReducido(true);
    conCuadrosManuales();
    const { container } = render(<RadialGauge label="Avance" fraccion={0.5} texto="50,0 %" />);
    expect(desplazamiento(container)).toBeCloseTo(circunferencia(container) * 0.5);
    expect(cola).toHaveLength(0);
  });

  test("el tono por omisión es la tinta (real = relleno oscuro), no el ámbar de la marca", () => {
    conMovimientoReducido(true);
    const { container } = render(<RadialGauge label="Avance" fraccion={0.5} texto="50,0 %" />);
    expect(arco(container)).toHaveClass("silice-radial__arco--charcoal");
    expect(arco(container).getAttribute("stroke")).toBeNull();
  });
});

const SEGMENTOS: DonutSegment[] = [
  { id: "en_elaboracion", label: "En elaboración", value: 2, valueText: "2", color: "#8d8d8d" },
  { id: "en_ejecucion", label: "En ejecución", value: 1, valueText: "1", color: "#161616" },
  { id: "atrasada", label: "Atrasada", value: 1, valueText: "1", color: "var(--silice-sev-error)" },
];

describe("AnimatedDonutChart: el anillo de la cartera por estado", () => {
  test("la leyenda escribe el texto de cada segmento y ningún porcentaje que no le dieron", () => {
    conMovimientoReducido(true);
    const { container } = render(<AnimatedDonutChart segments={SEGMENTOS} centerLabel="Obras" centerValue="4" />);
    const leyenda = screen.getByRole("list", { name: "Detalle de Obras" });
    expect(within(leyenda).getByRole("button", { name: "En elaboración 2" })).toBeInTheDocument();
    expect(within(leyenda).getByRole("button", { name: "En ejecución 1" })).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/%/);
    expect(screen.getByRole("img", { name: "Obras: 4" })).toBeInTheDocument();
  });

  test("con el porcentaje que manda la API lo escribe tal cual", () => {
    conMovimientoReducido(true);
    const conPct = SEGMENTOS.map((s, i) => ({ ...s, pctText: ["50,0 %", "25,0 %", "25,0 %"][i] }));
    render(<AnimatedDonutChart segments={conPct} centerLabel="Obras" centerValue="4" />);
    expect(screen.getByRole("button", { name: "En elaboración 2 50,0 %" })).toBeInTheDocument();
  });

  test("sin valor el segmento dice «—» y «sin dato», y no se dibuja", () => {
    conMovimientoReducido(true);
    const { container } = render(
      <AnimatedDonutChart
        segments={[...SEGMENTOS, { id: "aprobada", label: "Aprobada", value: Number.NaN, valueText: null, color: "#009d9a" }]}
        centerLabel="Obras"
        centerValue={null}
      />,
    );
    // La raya va oculta a la lectora: el nombre dice «sin dato».
    expect(screen.getByRole("button", { name: "Aprobada sin dato" })).toBeInTheDocument();
    expect(container.querySelectorAll(".silice-donut__segmento")).toHaveLength(3);
    expect(screen.getByRole("img", { name: "Obras: sin dato" })).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/\b0\b/);
  });

  test("cada segmento lleva el color de su estado, sin importar el orden ni el tamaño", () => {
    conMovimientoReducido(true);
    const { container } = render(<AnimatedDonutChart segments={SEGMENTOS} centerLabel="Obras" centerValue="4" />);
    const atrasada = container.querySelector<SVGCircleElement>('.silice-donut__segmento[data-id="atrasada"]')!;
    expect(atrasada.style.stroke).toBe("var(--silice-sev-error)");
  });

  test("con el teclado: una sola parada de Tab, las flechas recorren los estados y el foco lo resalta en el centro", async () => {
    conMovimientoReducido(true);
    const usuario = userEvent.setup();
    const { container } = render(
      <>
        <button type="button">antes</button>
        <AnimatedDonutChart segments={SEGMENTOS} centerLabel="Obras" centerValue="4" />
        <button type="button">después</button>
      </>,
    );
    const centro = container.querySelector(".silice-donut__centro")!;
    expect(centro).toHaveTextContent("Obras4");
    await usuario.click(screen.getByRole("button", { name: "antes" }));
    await usuario.tab();
    const elaboracion = screen.getByRole("button", { name: "En elaboración 2" });
    expect(elaboracion).toHaveFocus();
    expect(centro).toHaveTextContent("En elaboración2");
    await usuario.keyboard("{ArrowDown}");
    expect(screen.getByRole("button", { name: "En ejecución 1" })).toHaveFocus();
    expect(centro).toHaveTextContent("En ejecución1");
    await usuario.keyboard("{ArrowRight}");
    expect(screen.getByRole("button", { name: "Atrasada 1" })).toHaveFocus();
    await usuario.keyboard("{ArrowDown}"); // vuelve al primero
    expect(elaboracion).toHaveFocus();
    await usuario.keyboard("{ArrowUp}");
    expect(screen.getByRole("button", { name: "Atrasada 1" })).toHaveFocus();
    await usuario.keyboard("{Home}");
    expect(elaboracion).toHaveFocus();
    await usuario.keyboard("{End}");
    expect(screen.getByRole("button", { name: "Atrasada 1" })).toHaveFocus();
    // Tab sale del grupo de una vez.
    await usuario.tab();
    expect(screen.getByRole("button", { name: "después" })).toHaveFocus();
    expect(centro).toHaveTextContent("Obras4");
  });

  test("Enter fija el estado resaltado (aria-pressed) y lo deja al salir; Esc lo suelta", async () => {
    conMovimientoReducido(true);
    const usuario = userEvent.setup();
    const { container } = render(
      <>
        <AnimatedDonutChart segments={SEGMENTOS} centerLabel="Obras" centerValue="4" />
        <button type="button">después</button>
      </>,
    );
    const centro = container.querySelector(".silice-donut__centro")!;
    await usuario.tab();
    await usuario.keyboard("{ArrowDown}{Enter}");
    const ejecucion = screen.getByRole("button", { name: "En ejecución 1" });
    expect(ejecucion).toHaveAttribute("aria-pressed", "true");
    expect(container.querySelector('.silice-donut__segmento[data-id="en_ejecucion"]')).toHaveClass("silice-donut__segmento--activo");
    await usuario.tab();
    expect(centro).toHaveTextContent("En ejecución1");
    // Al volver, la parada de Tab es la del estado fijado.
    await usuario.tab({ shift: true });
    expect(ejecucion).toHaveFocus();
    await usuario.keyboard("{Escape}");
    expect(ejecucion).toHaveAttribute("aria-pressed", "false");
    await usuario.tab();
    expect(centro).toHaveTextContent("Obras4");
  });

  test("con el ratón sobre un segmento también lo resalta", async () => {
    conMovimientoReducido(true);
    const usuario = userEvent.setup();
    const { container } = render(<AnimatedDonutChart segments={SEGMENTOS} centerLabel="Obras" centerValue="4" />);
    const centro = container.querySelector(".silice-donut__centro")!;
    await usuario.hover(container.querySelector('.silice-donut__segmento[data-id="atrasada"]')!);
    expect(centro).toHaveTextContent("Atrasada1");
    await usuario.unhover(container.querySelector('.silice-donut__segmento[data-id="atrasada"]')!);
    expect(centro).toHaveTextContent("Obras4");
  });

  test("crece al cargar y, con movimiento reducido, se pinta entero de una vez", () => {
    conMovimientoReducido(false);
    conCuadrosManuales();
    const { container, unmount } = render(<AnimatedDonutChart segments={SEGMENTOS} centerLabel="Obras" centerValue="4" />);
    const largo = () => Number(container.querySelector(".silice-donut__segmento")!.getAttribute("stroke-dasharray")!.split(" ")[0]);
    expect(largo()).toBe(0);
    soltarCuadros(5_000);
    const final = largo();
    expect(final).toBeGreaterThan(0);
    unmount();
    conMovimientoReducido(true);
    const otro = render(<AnimatedDonutChart segments={SEGMENTOS} centerLabel="Obras" centerValue="4" />);
    expect(Number(otro.container.querySelector(".silice-donut__segmento")!.getAttribute("stroke-dasharray")!.split(" ")[0])).toBeCloseTo(final);
  });
});

describe("AnimatedBarChart: avance real contra el plan (IBCS)", () => {
  const ITEMS = [
    { id: "a", label: "Casa Demo", real: 62.5, realText: "62,5 %", plan: 70, planText: "70,0 %" },
    { id: "b", label: "Galpón Sur", real: 10, realText: "10,0 %", plan: 25.5, planText: "25,5 %" },
  ];

  test("escribe el texto de cada barra tal cual; sin texto, «—» y «sin dato»", () => {
    conMovimientoReducido(true);
    const { container } = render(
      <AnimatedBarChart
        items={[...ITEMS, { id: "c", label: "Torre B", real: null, realText: null, plan: null, planText: null }]}
        realLegend="Avance real"
        planLegend="Plan acumulado"
      />,
    );
    for (const t of ["62,5 %", "70,0 %", "10,0 %", "25,5 %"]) expect(screen.getByText(t)).toBeInTheDocument();
    expect(screen.getAllByText("sin dato")).toHaveLength(2);
    expect(container.textContent).not.toMatch(/62\.5|25\.5/);
  });

  test("el real es una barra rellena y el plan un contorno, también en la leyenda; ningún color va en línea", () => {
    conMovimientoReducido(true);
    const { container } = render(<AnimatedBarChart items={ITEMS} realLegend="Avance real" planLegend="Plan acumulado" />);
    expect(container.querySelectorAll(".silice-barras-v__barra--real")).toHaveLength(2);
    expect(container.querySelectorAll(".silice-barras-v__barra--plan")).toHaveLength(2);
    expect(container.querySelector(".silice-barras-v__muestra--real")).toBeInTheDocument();
    expect(container.querySelector(".silice-barras-v__muestra--plan")).toBeInTheDocument();
    for (const e of container.querySelectorAll<HTMLElement>(".silice-barras-v__barra, .silice-barras-v__muestra")) {
      expect(e.style.backgroundColor).toBe("");
    }
  });

  test("la escala va de 0 a 100 %: la barra mide su valor y crece al cargar", () => {
    conMovimientoReducido(false);
    conCuadrosManuales();
    const { container } = render(<AnimatedBarChart items={ITEMS} realLegend="Avance real" planLegend="Plan acumulado" height={228} />);
    const real = () => container.querySelector<HTMLElement>(".silice-barras-v__barra--real")!;
    expect(real().style.blockSize).toBe("0px");
    soltarCuadros(5_000);
    // 228 de alto menos 28 de las cifras: 200 px para el 100 %.
    expect(real().style.blockSize).toBe("125px");
    for (const t of ["0 %", "25 %", "50 %", "75 %", "100 %"]) expect(screen.getByText(t)).toBeInTheDocument();
  });
});

describe("la hoja de estilos de los medidores", () => {
  const hoja = leer("src/comun/VisualMeters.scss");
  const editorial = leer("src/estilos/editorial.scss");
  const bloque = (selector: string) => {
    const i = hoja.indexOf(`${selector} {`);
    expect(i, `falta ${selector}`).toBeGreaterThanOrEqual(0);
    return hoja.slice(i, hoja.indexOf("}", i));
  };
  const hexDe = (token: string) => {
    const m = new RegExp(`${token}:\\s*(#[0-9a-fA-F]{6})`).exec(editorial);
    expect(m, `falta ${token} en editorial.scss`).not.toBeNull();
    return m![1]!;
  };
  function luminancia(hex: string): number {
    const canal = (i: number) => {
      const c = parseInt(hex.slice(1 + 2 * i, 3 + 2 * i), 16) / 255;
      return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    };
    return 0.2126 * canal(0) + 0.7152 * canal(1) + 0.0722 * canal(2);
  }
  const contraste = (a: string, b: string) => {
    const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p);
    return (x + 0.05) / (y + 0.05);
  };

  test("el plan va en contorno, sin relleno y sin el ámbar de la marca", () => {
    const plan = bloque(".silice-barras-v__barra--plan");
    expect(plan).toMatch(/background-color:\s*transparent/);
    expect(plan).toMatch(/border:\s*[0-9.]+rem solid var\(--silice-[a-z-]+\)/);
    expect(plan).not.toMatch(/gold|#e5b21a/i);
    const muestra = bloque(".silice-barras-v__muestra--plan");
    expect(muestra).toMatch(/background-color:\s*transparent/);
    expect(hoja).not.toMatch(/#e5b21a/i);
  });

  test("el contorno del plan y el relleno del real llegan a 3:1 sobre la superficie y el fondo (WCAG 1.4.11)", () => {
    const tokenPlan = /border:\s*[0-9.]+rem solid var\((--silice-[a-z-]+)\)/.exec(bloque(".silice-barras-v__barra--plan"))![1]!;
    const tokenReal = /background-color:\s*var\((--silice-[a-z-]+)\)/.exec(bloque(".silice-barras-v__barra--real"))![1]!;
    for (const fondo of ["--silice-surface", "--silice-stone"]) {
      expect(contraste(hexDe(tokenPlan), hexDe(fondo))).toBeGreaterThanOrEqual(3);
      expect(contraste(hexDe(tokenReal), hexDe(fondo))).toBeGreaterThanOrEqual(3);
    }
  });

  test("las cifras van en las tintas de texto, no en el color de la serie", () => {
    expect(bloque(".silice-barras-v__cifra--sec")).not.toMatch(/gold/);
  });

  test("el foco del teclado en la leyenda del anillo se ve", () => {
    expect(bloque(".silice-donut__item:focus-visible")).toMatch(/outline:\s*2px solid var\(--cds-focus\)/);
  });
});

describe("RiskRangeMeter: base, P50 y P80 como los manda el servidor", () => {
  const PUNTOS = [
    { rotulo: "Presupuesto base vigente", valor: 1000, texto: "1.000,00 USD", tipo: "plan" as const },
    { rotulo: "Escenario probable (P50)", valor: 1248.7171, texto: "1.248,72 USD", tipo: "pronostico" as const },
    { rotulo: "Exposición recomendada (P80)", valor: 1302.4561, texto: "1.302,46 USD", tipo: "pronostico" as const },
  ];

  test("escribe cada monto tal cual y ninguna variación porcentual calculada aquí", () => {
    conMovimientoReducido(true);
    render(<RiskRangeMeter puntos={PUNTOS} />);
    const grupo = screen.getByRole("group", { name: "Rango de exposición de costos" });
    expect(within(grupo).getByText("1.000,00 USD")).toBeInTheDocument();
    expect(within(grupo).getByText("1.248,72 USD")).toBeInTheDocument();
    expect(within(grupo).getByText("1.302,46 USD")).toBeInTheDocument();
    expect(grupo.textContent).not.toMatch(/%/);
  });

  test("sin texto escribe «—» y «sin dato», nunca un monto en cero", () => {
    conMovimientoReducido(true);
    render(<RiskRangeMeter puntos={[PUNTOS[0]!, { ...PUNTOS[1]!, valor: null, texto: null }]} />);
    const grupo = screen.getByRole("group", { name: "Rango de exposición de costos" });
    expect(within(grupo).getByText("sin dato")).toBeInTheDocument();
    expect(grupo.textContent).not.toMatch(/0,00 USD\s*\(|\b0 USD/);
  });

  test("la base (lo previsto) va en contorno y P50 y P80 (pronóstico) achurados, sin colores en línea", () => {
    conMovimientoReducido(true);
    const { container } = render(<RiskRangeMeter puntos={PUNTOS} />);
    const barras = [...container.querySelectorAll<HTMLElement>(".silice-riesgo-medidor__barra")];
    expect(barras.map((b) => b.classList.contains("silice-riesgo-medidor__barra--plan"))).toEqual([true, false, false]);
    expect(barras.map((b) => b.classList.contains("silice-riesgo-medidor__barra--pronostico"))).toEqual([false, true, true]);
    for (const b of barras) expect(b.style.backgroundColor).toBe("");
    // El P80, el mayor, llena la pista; la base mide lo suyo.
    expect(barras[2]!.style.inlineSize).toBe("100%");
    expect(Number.parseFloat(barras[0]!.style.inlineSize)).toBeCloseTo((1000 / 1302.4561) * 100);
  });
});
