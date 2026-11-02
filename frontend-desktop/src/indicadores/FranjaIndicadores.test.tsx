import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { FranjaIndicadores } from "./FranjaIndicadores";
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

describe("FranjaIndicadores", () => {
  test("pinta un indicador por cada elemento de la lista", () => {
    render(<FranjaIndicadores indicadores={indicadores} />);
    expect(screen.getByRole("group", { name: "Total del libro" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Otro" })).toBeInTheDocument();
  });

  test("los conteos por severidad no estan en la franja: salen una sola vez, en los filtros de la lista (M3)", () => {
    const { container } = render(<FranjaIndicadores indicadores={indicadores} />);
    expect(screen.queryByRole("group", { name: "Hallazgos por severidad" })).toBeNull();
    expect(container.querySelector(".silice-sev")).toBeNull();
  });

  test("el exacto de cada total (clave del indicador) llega a su indicador, en es-VE y sin redondear", () => {
    render(
      <FranjaIndicadores
        indicadores={[{ ...indicadores[0], clave: "TOTALGEN" }]}
       
        totalesLibro={{ TOTALGEN: "1738.4070000000000000001" }}
        totalesSilice={{ TOTALGEN: "1500.0000000000000000002" }}
      />,
    );
    const valor = screen.getByRole("button", { name: /1\.738,407/ });
    expect(valor).toHaveAccessibleDescription(/En el libro: 1\.738,4070000000000000001/);
    expect(valor).toHaveAccessibleDescription(/Según Sílice: 1\.500,0000000000000000002/);
  });
});
