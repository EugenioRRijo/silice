import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { InformeAuditoria } from "./InformeAuditoria";
import type { InformeAuditoriaRespuesta } from "../api/tipos";

const CON_HALLAZGOS: InformeAuditoriaRespuesta = {
  codigo_presupuesto: "P-001",
  cumple: false,
  veredicto: "NO CUMPLE",
  total_hallazgos: 2,
  por_severidad: [
    { severidad: "ALTA", total: 1 },
    { severidad: "BAJA", total: 1 },
  ],
  reglas_evaluadas: [
    { regla: "R1", nombre: "Cantidades positivas", hallazgos: 0 },
    { regla: "R4", nombre: "Subcadena", hallazgos: 2 },
  ],
  hallazgos: [
    {
      numero: 1,
      regla: "R4",
      severidad: "ALTA",
      partida: "LB-01-EXC",
      descripcion: "![x](http://ejemplo.invalido/p.png) insumo raro",
      impacto: "12.50",
      observado: "3.00",
      esperado: null,
      origen: ["T-01", "T-02"],
    },
    {
      numero: 2,
      regla: "R4",
      severidad: "BAJA",
      partida: null,
      descripcion: "Otro hallazgo",
      impacto: null,
      observado: null,
      esperado: null,
      origen: [],
    },
  ],
  sin_hallazgos: null,
};

const LIMPIO: InformeAuditoriaRespuesta = {
  codigo_presupuesto: "P-002",
  cumple: true,
  veredicto: "CUMPLE",
  total_hallazgos: 0,
  por_severidad: [],
  reglas_evaluadas: [{ regla: "R1", nombre: "Cantidades positivas", hallazgos: 0 }],
  hallazgos: [],
  sin_hallazgos: "Sin hallazgos: se verificaron las reglas listadas.",
};

describe("InformeAuditoria", () => {
  test("encabeza con el presupuesto, los hallazgos y el veredicto", () => {
    render(<InformeAuditoria informe={CON_HALLAZGOS} />);

    expect(screen.getByText(/Presupuesto P-001/)).toBeInTheDocument();
    expect(screen.getByText(/Hallazgos: 2/)).toBeInTheDocument();
    expect(screen.getByText(/Resultado: NO CUMPLE/)).toBeInTheDocument();
  });

  test("declara las reglas evaluadas con su cuenta, aunque sea cero", () => {
    render(<InformeAuditoria informe={CON_HALLAZGOS} />);

    const tabla = screen.getByRole("table", { name: "Reglas evaluadas" });
    expect(within(tabla).getByText("Cantidades positivas")).toBeInTheDocument();
    expect(within(tabla).getByText("Subcadena")).toBeInTheDocument();
  });

  test("lista los hallazgos como texto plano: un enlace o imagen en Markdown no se interpreta", () => {
    const { container } = render(<InformeAuditoria informe={CON_HALLAZGOS} />);

    const tabla = screen.getByRole("table", { name: "Hallazgos" });
    expect(within(tabla).getByText("![x](http://ejemplo.invalido/p.png) insumo raro")).toBeInTheDocument();
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("a")).toBeNull();
    expect(within(tabla).getByText("LB-01-EXC")).toBeInTheDocument();
    expect(within(tabla).getByText("T-01; T-02")).toBeInTheDocument();
  });

  test("una partida, un monto o un origen ausentes se ven vacíos, no como 'null'", () => {
    render(<InformeAuditoria informe={CON_HALLAZGOS} />);

    expect(screen.queryByText(/null/)).toBeNull();
    expect(screen.queryByText(/undefined/)).toBeNull();
  });

  test("sin hallazgos declara que se verificó y no muestra la tabla de hallazgos", () => {
    render(<InformeAuditoria informe={LIMPIO} />);

    expect(screen.getByText("Sin hallazgos: se verificaron las reglas listadas.")).toBeInTheDocument();
    expect(screen.queryByRole("table", { name: "Hallazgos" })).toBeNull();
    expect(screen.getByText(/Resultado: CUMPLE/)).toBeInTheDocument();
  });
});
