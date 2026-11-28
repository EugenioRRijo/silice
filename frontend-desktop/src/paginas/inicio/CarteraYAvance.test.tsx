import { fileURLToPath } from "node:url";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import * as sass from "sass";
import { describe, expect, test } from "vitest";
import type { ResumenTodasRespuesta } from "../../api/tipos";
import { CarteraYAvance, escalaHorizontal, segmentosPorEtapa } from "./CarteraYAvance";

// Pruebas de CarteraYAvance en la cara «Papel y resaltador» (00-inicio-resumen.html): gráfico principal de barras
// horizontales por moneda (sin mezclar Bs con USD ni inventar montos) y bloque secundario compacto «Avance de la cartera»,
// ambos con su párrafo «Qué muestra / Qué leer» y su desplegable «Ver como tabla». Obras y cifras ficticias.
const CARTERA: ResumenTodasRespuesta = {
  hoy: "2026-11-05",
  por_moneda: [
    { moneda: "Bs", obras: 3, total: "334570.5", en_ejecucion: 2 },
    { moneda: "USD", obras: 1, total: "95066.6", en_ejecucion: 1 },
  ],
  obras: [
    obra(8, "Torre B", "Bs", null, "en_elaboracion", "En elaboración", null, null),
    obra(7, "Casa Demo", "Bs", "250000.5", "en_ejecucion", "En ejecución", "62.5", "70.0"),
    obra(9, "Puente Norte", "Bs", "84570.00", "aprobada", "Aprobada", "100.0", "100.0"),
    obra(3, "Galpón Sur", "USD", "95066.6", "atrasada", "Atrasada", "10.0", "25.5"),
  ],
  carpetas_omitidas: 0,
};

function obra(
  id: number,
  nombre: string,
  moneda: string,
  total: string | null,
  etapa: string,
  etapa_texto: string,
  real: string | null,
  plan: string | null,
) {
  return {
    carpeta: null,
    carpeta_titulo: "Carpeta de la empresa",
    obra_id: id,
    nombre,
    moneda,
    etapa,
    etapa_texto,
    total,
    avance_real: real,
    avance_plan: plan,
  };
}

function montar(
  datos: ResumenTodasRespuesta = CARTERA,
  problemas = new Map<string, { bloquea: number; aviso: number }>([["|7", { bloquea: 2, aviso: 1 }]]),
) {
  return render(
    <MemoryRouter>
      <CarteraYAvance carga={{ estado: "listo", datos }} carpetas={new Map()} problemasPorObra={problemas} puedeCrear={false} />
    </MemoryRouter>,
  );
}

const seccionCartera = () => screen.getByRole("region", { name: "La cartera de obras" });
const seccionAvance = () => screen.getByRole("region", { name: "Avance de la cartera" });

describe("Inicio › Resumen: el gráfico principal «La cartera de obras»", () => {
  test("separa cada moneda en su propio bloque, ordena de mayor a menor presupuesto y muestra las cifras al extremo en es-VE", () => {
    montar();
    const cartera = seccionCartera();
    const enBs = within(cartera).getByRole("region", { name: "Cartera en Bs" });
    const enUsd = within(cartera).getByRole("region", { name: "Cartera en USD" });

    // En Bs las obras salen ordenadas por presupuesto descendente, y la sin versión al final.
    const nombresEnBs = Array.from(enBs.querySelectorAll(".silice-cartera-grafico__obra-nombre")).map((n) => n.textContent);
    expect(nombresEnBs).toEqual(["Casa Demo", "Puente Norte", "Torre B"]);

    // Las cifras del extremo usan coma decimal y punto de miles; nunca punto decimal crudo.
    expect(within(enBs).getAllByText("250.000,50 Bs").length).toBeGreaterThan(0);
    expect(within(enBs).getAllByText("84.570,00 Bs").length).toBeGreaterThan(0);
    expect(within(enBs).getAllByText("62,5 %").length).toBeGreaterThan(0);
    expect(within(enBs).getAllByText("Sin versión").length).toBeGreaterThan(0);
    expect(within(enBs).getAllByText("Sin avance").length).toBeGreaterThan(0);
    expect(enBs.textContent).not.toMatch(/250000\.5|62\.5/);

    // USD va aparte y jamás se suma con Bs (334.570,50 + 95.066,60 = 429.637,10).
    expect(within(enUsd).getAllByText("95.066,60 USD").length).toBeGreaterThan(0);
    expect(within(enUsd).getAllByText("10,0 %").length).toBeGreaterThan(0);
    expect(cartera.textContent).not.toContain("429.637");
  });

  test("dibuja barras de presupuesto y de ejecutado, leyenda de dos series, «Qué muestra / Qué leer» y «Ver como tabla»", async () => {
    const u = userEvent.setup();
    montar();
    const cartera = seccionCartera();
    const enBs = within(cartera).getByRole("region", { name: "Cartera en Bs" });

    expect(enBs.querySelectorAll(".silice-cartera-grafico__barra--presupuesto")).toHaveLength(3);
    expect(enBs.querySelectorAll(".silice-cartera-grafico__barra--ejecutado")).toHaveLength(3);
    expect(within(enBs).getByText("Presupuesto de la obra")).toBeInTheDocument();
    expect(within(enBs).getByText("Ejecutado (avance físico)")).toBeInTheDocument();

    expect(within(cartera).getByText(/Qué muestra:.*Qué leer:/)).toBeInTheDocument();

    // «Ver como tabla» despliega el detalle y muestra la tabla completa con el pie de la cartera y los problemas con su palabra.
    const detalle = enBs.querySelector("details")!;
    expect(detalle).not.toHaveAttribute("open");
    await u.click(within(enBs).getByText("Ver como tabla"));
    expect(detalle).toHaveAttribute("open");
    const tabla = within(enBs).getByRole("table", { name: "Presupuesto, avance y problemas abiertos de las obras en Bs" });
    expect(within(tabla).getByText("334.570,50 Bs")).toBeInTheDocument();
    expect(within(tabla).getAllByText("2 bloquean").length).toBeGreaterThan(0);
    expect(within(tabla).getAllByText("1 aviso").length).toBeGreaterThan(0);
  });

  test("una cifra que no es un decimal de la API no se dibuja como barra (valorParaDibujar, no Number)", () => {
    montar({
      ...CARTERA,
      por_moneda: [{ moneda: "Bs", obras: 2, total: "3000.00", en_ejecucion: 0 }],
      obras: [
        obra(1, "Obra clara", "Bs", "2000.00", "aprobada", "Aprobada", null, null),
        obra(2, "Obra rara", "Bs", "1e3", "aprobada", "Aprobada", null, null),
      ],
    });
    const enBs = within(seccionCartera()).getByRole("region", { name: "Cartera en Bs" });
    const ancho = (nombre: string) => {
      const fila = Array.from(enBs.querySelectorAll(".silice-cartera-grafico__fila")).find((f) => f.textContent?.includes(nombre))!;
      return (fila.querySelector(".silice-cartera-grafico__barra--presupuesto") as HTMLElement).style.inlineSize;
    };
    expect(ancho("Obra clara")).toBe("100%");
    expect(ancho("Obra rara")).toBe("0%");
  });

  test("escalaHorizontal produce marcas limpias y maneja cero sin NaN", () => {
    expect(escalaHorizontal(2915780)).toEqual({ tope: 3000000, marcas: [0, 1000000, 2000000, 3000000] });
    expect(escalaHorizontal(0)).toEqual({ tope: 0, marcas: [0] });
  });
});

describe("Inicio › Resumen: el bloque secundario «Avance de la cartera»", () => {
  test("ordena las etapas en el orden de la obra, escribe el avance real frente al plan en es-VE y ofrece «Ver como tabla» y «Qué muestra / Qué leer»", () => {
    montar();
    const avance = seccionAvance();

    const ordenEtapas = segmentosPorEtapa(CARTERA.obras).map((s) => `${s.label}: ${s.valorTexto}`);
    expect(ordenEtapas).toEqual(["En elaboración: 1", "Aprobada: 1", "En ejecución: 1", "Atrasada: 1"]);
    for (const texto of ordenEtapas) expect(within(avance).getByText(texto)).toBeInTheDocument();

    // Medidores compactos solo para obras con avance real y planificado.
    const medidores = within(avance).getByRole("list", { name: "Avance real frente al planificado" });
    expect(within(medidores).getByText("Casa Demo")).toBeInTheDocument();
    expect(within(medidores).getByText("Real 62,5 % · Plan 70,0 %")).toBeInTheDocument();
    expect(within(medidores).getByText("Real 10,0 % · Plan 25,5 %")).toBeInTheDocument();
    expect(within(medidores).queryByText("Torre B")).toBeNull();

    expect(avance.querySelector("details > summary")?.textContent).toBe("Ver como tabla");
    expect(within(avance).getByRole("table", { name: "Obras de la cartera y su avance contra el plan" })).toBeInTheDocument();
    expect(within(avance).getByText(/Qué muestra:.*Qué leer:/)).toBeInTheDocument();
  });

  test("los colores de etapa usan exclusivamente tokens --silice-* sin hexadecimales sueltos", () => {
    const otraEtapa = {
      ...CARTERA,
      obras: [...CARTERA.obras, obra(11, "Obra rara", "Bs", "1000.00", "suspendida", "Suspendida", null, null)],
    };
    const { container } = montar(otraEtapa);
    const color = (id: string) =>
      container.querySelector<HTMLElement>(`.silice-avance-segmentos__parte[data-etapa="${id}"]`)!.style.backgroundColor;

    expect(color("en_elaboracion")).toBe("var(--silice-grafico-etapa-en-elaboracion)");
    expect(color("en_ejecucion")).toBe("var(--silice-grafico-etapa-en-ejecucion)");
    expect(color("suspendida")).toBe("var(--silice-grafico-etapa-otra)");
    expect(color("atrasada")).toBe("var(--silice-gravedad-error)");

    // Ni el componente ni inicio.scss fijan hexadecimales crudos ni font-size en px.
    const componente = "./CarteraYAvance.tsx";
    const estilos = "./inicio.scss";
    const fs = (
      globalThis as unknown as { process: { getBuiltinModule(n: string): { readFileSync(r: string, c: string): string } } }
    ).process.getBuiltinModule("node:fs");
    expect(fs.readFileSync(fileURLToPath(new URL(componente, import.meta.url)), "utf-8")).not.toMatch(/#[0-9a-f]{3,8}\b/i);
    const scssFuente = fs.readFileSync(fileURLToPath(new URL(estilos, import.meta.url)), "utf-8");
    expect(scssFuente).not.toMatch(/#[0-9a-f]{3,8}\b/i);
    const css = sass.compile(fileURLToPath(new URL(estilos, import.meta.url))).css;
    for (const etapa of ["en-elaboracion", "en-aprobacion", "aprobada", "en-ejecucion", "otra"]) {
      expect(css).toMatch(new RegExp(`--silice-grafico-etapa-${etapa}:\\s*var\\(--silice-`));
    }
  });
});

describe("Inicio › Resumen: cartera aún no disponible en el servidor", () => {
  test("un 404 dice a quién pedirle que actualice el programa", () => {
    render(
      <MemoryRouter>
        <CarteraYAvance carga={{ estado: "no_disponible", error: null }} carpetas={new Map()} puedeCrear={false} />
      </MemoryRouter>,
    );
    expect(screen.getByText("La cartera aún no está disponible en esta instalación")).toBeInTheDocument();
    expect(
      screen.getByText("Pídale a quien administra Sílice que actualice el programa; mientras tanto, esta parte no se puede mostrar."),
    ).toBeInTheDocument();
  });
});
