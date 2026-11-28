import { render, screen, within } from "@testing-library/react";
import { createRef } from "react";
import { describe, expect, test, vi } from "vitest";
import type { CalculoDeCosto } from "../../api/produccionPlanta";
import { ResultadoDelCalculo } from "./ResultadoDelCalculo";

interface OpcionesResultado {
  title?: string;
  axes?: { left?: { title?: string; ticks?: { formatter?: (v: number) => string } }; right?: unknown };
  color?: { scale: Record<string, string> };
  tooltip?: { customHTML?: (data: unknown, html: string, datum: unknown) => string };
}

vi.mock("../../comun/GraficoCarbon", () => ({
  default: ({ tipo, datos, opciones }: { tipo: string; datos: { group?: string; key?: string; value?: number }[]; opciones: OpcionesResultado }) => {
    const primero = datos[0];
    return (
      <div
        role="img"
        aria-label={opciones.title ?? "Gráfico"}
        data-tipo={tipo}
        data-valores={datos.map((d) => `${d.group}:${d.key}:${d.value}`).join("|")}
        data-doble-eje={String(Boolean(opciones.axes?.right))}
        data-eje-formato={opciones.axes?.left?.ticks?.formatter?.(258.4) ?? ""}
        data-colores={JSON.stringify(opciones.color?.scale ?? null)}
        data-globo={primero ? opciones.tooltip?.customHTML?.([primero], "", primero) ?? "" : ""}
      />
    );
  },
}));

// Datos ficticios. Las constancias de la 4b salen de la instantánea que guardó el servidor; la pantalla no calcula nada.
function calculo(entradas: Record<string, unknown>, resultado: Record<string, unknown>): CalculoDeCosto {
  return {
    id: 11,
    periodo: "2026-11",
    moneda: "Bs",
    huella: "d".repeat(64),
    usuario: "ana",
    registrado: "2026-11-30T10:00:00",
    productos: [{ codigo: "MZP-01", por_tonelada: "50.7", presentado: "50.70" }],
    instantanea: { entradas: { agregados: [], producido: {}, ...entradas }, resultado: { total_cantera: "1500", total_planta: "120", ...resultado } },
    publicado: null,
  };
}
function ver(c: CalculoDeCosto) {
  render(<ResultadoDelCalculo calculo={c} region={createRef<HTMLElement>()} />);
  return screen.getByRole("region", { name: "Resultado del cálculo" });
}

describe("gráfico del costo por tonelada en el resultado", () => {
  test("dibuja barras con título y unidad, color fijo por tipo de producto, extremos, lectura y Ver como tabla", async () => {
    const c = calculo({ agregados: [] }, {});
    const region = ver(c);
    const grafico = await within(region).findByRole("img", { name: "Costo por tonelada por producto (Bs/t)" });
    expect(grafico).toHaveAttribute("data-tipo", "barras");
    expect(grafico).toHaveAttribute("data-doble-eje", "false");
    expect(grafico).toHaveAttribute("data-eje-formato", "258,4");
    // Mezcla conserva su color de entidad (serie 2, aguamarina) aunque no haya ningún agregado en este cálculo.
    expect(JSON.parse(grafico.getAttribute("data-colores")!)).toEqual({ Mezcla: "#1BAF7A" });
    expect(grafico.getAttribute("data-globo")).toContain("50,70 Bs/t");
    expect(grafico.getAttribute("data-globo")).toContain("50,7 Bs/t");

    const extremos = within(region).getByRole("list", { name: "Costo en el extremo de cada barra" });
    expect(within(extremos).getByRole("listitem")).toHaveTextContent("MZP-01 (Mezcla): 50,70 Bs/t");
    expect(within(region).getByText(/Qué muestra:.*noviembre de 2026.*Qué leer:.*MZP-01/)).toBeInTheDocument();
    expect(within(region).getByText("Ver como tabla")).toBeInTheDocument();
    expect(within(region).getByRole("table", { name: "Costo por tonelada de noviembre de 2026" })).toBeInTheDocument();
  });
});

// T4 (mutantes RC1 a RC3): lo que se dibuja y lo que dice la lectura salen de las cifras que mandó el servidor.
describe("lectura y altura de las barras del costo por tonelada", () => {
  test("la altura de cada barra es el costo presentado, no el exacto", async () => {
    const c = calculo({ agregados: [] }, {});
    c.productos = [{ codigo: "MZP-01", por_tonelada: "50.700123", presentado: "50.70" }];
    const region = ver(c);
    const grafico = await within(region).findByRole("img", { name: "Costo por tonelada por producto (Bs/t)" });
    expect(grafico).toHaveAttribute("data-valores", "Mezcla:MZP-01:50.7");
  });

  test("un solo producto se lee con su costo y el exacto sin redondear", async () => {
    const region = ver(calculo({ agregados: [] }, {}));
    await within(region).findByRole("img", { name: "Costo por tonelada por producto (Bs/t)" });
    expect(within(region).getByText(/Qué leer: MZP-01 queda en 50,70 Bs\/t \(sin redondear: 50,7 Bs\/t\)\./)).toBeInTheDocument();
  });

  test("con varios productos la lectura nombra el de mayor costo por tonelada", async () => {
    const c = calculo({ agregados: ["AGR-12"] }, {});
    c.productos = [
      { codigo: "AGR-12", por_tonelada: "5", presentado: "5.00" },
      { codigo: "MZP-01", por_tonelada: "80.4", presentado: "80.40" },
      { codigo: "MZP-02", por_tonelada: "60", presentado: "60.00" },
    ];
    const region = ver(c);
    await within(region).findByRole("img", { name: "Costo por tonelada por producto (Bs/t)" });
    expect(within(region).getByText(/Qué leer: el mayor costo unitario corresponde a MZP-01 con 80,40 Bs\/t;/)).toBeInTheDocument();
  });
});

describe("Constancias de la Tarea 4b en el resultado", () => {
  test("el cálculo muestra lo que viene del mes anterior y lo que pasa al siguiente", () => {
    const region = ver(
      calculo(
        { viene_del_mes_anterior: { cantera: { total: "1000", calculo: 5, periodo: "2026-10", costos: [1, 2], tasa: null } } },
        { pasa_al_mes_siguiente: { planta: { total: "2500.5", costos: [9] } } },
      ),
    );
    const anterior = within(region).getByRole("region", { name: "Viene del mes anterior" });
    expect(anterior).toHaveTextContent("Cantera: 1.000,00 Bs");
    expect(anterior).toHaveTextContent("cálculo n.º 5 de octubre de 2026");
    const siguiente = within(region).getByRole("region", { name: "Pasa al mes siguiente" });
    expect(siguiente).toHaveTextContent("Planta: 2.500,50 Bs");
  });

  test("lo que viene en otra moneda dice la tasa del cierre con que se convirtió", () => {
    const region = ver(
      calculo(
        { viene_del_mes_anterior: { cantera: { total: "8000", calculo: 5, periodo: "2026-10", costos: [1], tasa: { valor: "40", fecha: "2026-10-30", fuente: "BCV" } } } },
        {},
      ),
    );
    expect(within(region).getByRole("region", { name: "Viene del mes anterior" })).toHaveTextContent("tasa del cierre de octubre de 2026: 40,00 del 30/10/2026");
  });

  test("un agregado con costo de otro cálculo lo dice con su período", () => {
    const region = ver(calculo({ de_otro_calculo: { "AGR-12": { costo: "5", calculo: 4, periodo: "2026-10" } } }, {}));
    const bloque = within(region).getByRole("region", { name: "Costos tomados de otro cálculo" });
    expect(bloque).toHaveTextContent("AGR-12: 5,00 Bs por tonelada, del cálculo n.º 4 de octubre de 2026");
  });

  test("un cálculo de la versión 1 (sin esas claves) no muestra ninguna de las tres secciones", () => {
    const region = ver(calculo({}, {}));
    for (const nombre of ["Viene del mes anterior", "Pasa al mes siguiente", "Costos tomados de otro cálculo"]) {
      expect(within(region).queryByRole("region", { name: nombre })).not.toBeInTheDocument();
    }
  });

  test("un cálculo sin costos por tonelada dice que no se puede publicar", () => {
    const c = { ...calculo({}, { pasa_al_mes_siguiente: { cantera: { total: "300", costos: [1] } } }), productos: [] };
    const region = ver(c);
    expect(within(region).getByText("Este cálculo no tiene costos por tonelada: todo pasa al mes siguiente.")).toBeInTheDocument();
  });

  test("muestra carpeta en lugar de caso y código de verificación del cálculo", () => {
    const c = {
      ...calculo({}, {}),
      publicado: { lista_id: 12, caso: "obra_sur", registrado: "2026-11-30T10:05:00" },
    };
    const region = ver(c);
    expect(within(region).getByText(/carpeta «obra_sur»/)).toBeInTheDocument();
    expect(within(region).getByText(/Código de verificación del cálculo \(SHA-256, comprueba que no cambió\):/)).toBeInTheDocument();
  });
});
