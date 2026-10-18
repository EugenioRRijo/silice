import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { FranjaIndicadores } from "./FranjaIndicadores";
import { SEVERIDADES, estiloDeSeveridad } from "../severidad/severidad";
import type { IndicadorRespuesta } from "./tipos";

const indicadores: IndicadorRespuesta[] = [
  {
    clave: "total",
    titulo: "Total del libro",
    actual: "1738.407",
    meta: "1500.00",
    delta: "238.407",
    delta_pct: "15.89",
    sentido: "costo",
  },
  {
    clave: "otro",
    titulo: "Otro",
    actual: "10",
    meta: "12",
    delta: "-2",
    delta_pct: null,
    sentido: "costo",
  },
];

const conteos = { CRITICO: 2, ERROR: 0, ADVERTENCIA: 5, INFO: 1 } as const;

describe("FranjaIndicadores", () => {
  test("pinta un indicador por cada elemento de la lista", () => {
    render(<FranjaIndicadores indicadores={indicadores} porSeveridad={conteos} />);
    expect(screen.getByRole("group", { name: "Total del libro" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Otro" })).toBeInTheDocument();
  });

  test("los conteos por severidad llevan texto y numero", () => {
    render(<FranjaIndicadores indicadores={indicadores} porSeveridad={conteos} />);
    const zona = screen.getByRole("group", { name: "Hallazgos por severidad" });
    expect(within(zona).getByText("Crítico")).toBeInTheDocument();
    expect(within(zona).getByText("Error")).toBeInTheDocument();
    expect(within(zona).getByText("Advertencia")).toBeInTheDocument();
    expect(within(zona).getByText("Información")).toBeInTheDocument();
    expect(within(zona).getByText("2")).toBeInTheDocument();
    expect(within(zona).getByText("5")).toBeInTheDocument();
  });

  test("un conteo no usa las clases de variacion IBCS", () => {
    const { container } = render(<FranjaIndicadores indicadores={[]} porSeveridad={conteos} />);
    const zona = container.querySelector(".franja-indicadores__severidad");
    expect(zona).not.toBeNull();
    expect(zona?.querySelector(".ibcs-favorable, .ibcs-desfavorable, .ibcs-neutro")).toBeNull();
  });

  test("los conteos usan los mismos iconos y textos que la hoja y la lista (fuente unica)", () => {
    const { container } = render(<FranjaIndicadores indicadores={[]} porSeveridad={conteos} />);
    const etiquetas = [...container.querySelectorAll(".franja-indicadores__severidad .silice-sev")];
    expect(etiquetas).toHaveLength(SEVERIDADES.length);
    SEVERIDADES.forEach((sev, i) => {
      const estilo = estiloDeSeveridad(sev);
      expect(etiquetas[i].querySelector("svg")?.getAttribute("data-icono")).toBe(estilo.icono);
      expect(etiquetas[i].textContent).toContain(estilo.texto);
    });
  });

  test("el exacto de cada total (clave del indicador) llega a su indicador, en es-VE y sin redondear", () => {
    render(
      <FranjaIndicadores
        indicadores={[{ ...indicadores[0], clave: "TOTALGEN" }]}
        porSeveridad={conteos}
        totalesLibro={{ TOTALGEN: "1738.4070000000000000001" }}
        totalesSilice={{ TOTALGEN: "1500.0000000000000000002" }}
      />,
    );
    const valor = screen.getByRole("button", { name: /1\.738,407/ });
    expect(valor).toHaveAccessibleDescription(/En el libro: 1\.738,4070000000000000001/);
    expect(valor).toHaveAccessibleDescription(/Según Sílice: 1\.500,0000000000000000002/);
  });

  test("sin indicadores aun muestra los conteos", () => {
    render(<FranjaIndicadores indicadores={[]} porSeveridad={conteos} />);
    expect(screen.getByRole("group", { name: "Hallazgos por severidad" })).toBeInTheDocument();
  });
});
