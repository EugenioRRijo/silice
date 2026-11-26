import { fileURLToPath } from "node:url";
import { render, screen, within } from "@testing-library/react";
import * as sass from "sass";
import { describe, expect, test } from "vitest";
import { Grilla } from "../../../comun/Grilla";
import type { ColumnaDeGrilla } from "../../../comun/Grilla";
import { CeldaDeProblemas, textoDeCeldaDeProblemas } from "./CeldaDeProblemas";
import type { ResumenDeProblemaEnFila } from "./logica";

// Lote B1-7 (ficha-b1 §1.6, §1.10 prueba 8 y §3.2): celda de la columna Problemas.
// Muestra ícono, severidad en palabra y texto corto (e indica cuando hay más de un problema), sin atributo title ni
// controles emergentes no pedidos.

interface FilaPrueba {
  id: string;
  partida: string;
  problema: ResumenDeProblemaEnFila | null;
}

describe("CeldaDeProblemas (lote B1-7)", () => {
  test("sin problemas muestra «Sin problemas» y no agrega atributo title", () => {
    const { container } = render(<CeldaDeProblemas problema={null} />);
    expect(screen.getByText("Sin problemas")).toBeInTheDocument();
    expect(textoDeCeldaDeProblemas(null)).toBe("Sin problemas");
    expect(container.querySelectorAll("[title]")).toHaveLength(0);
  });

  test("muestra la severidad en palabra, traduce el texto del servidor a español llano y sin title", () => {
    const problema: ResumenDeProblemaEnFila = {
      severidad: "ERROR",
      palabra: "Error",
      texto: "PENDIENTE: sin APU en el catálogo (AF-SALIDA)",
      total: 1,
    };
    const { container } = render(<CeldaDeProblemas problema={problema} />);

    expect(screen.getByText("Error")).toBeInTheDocument();
    expect(screen.getByText("Pendiente: sin precio con la lista de esta versión (AF-SALIDA)")).toBeInTheDocument();
    expect(textoDeCeldaDeProblemas(problema)).toBe(
      "Error: Pendiente: sin precio con la lista de esta versión (AF-SALIDA)",
    );
    expect(container.querySelectorAll("[title]")).toHaveLength(0);
  });

  test("convierte decimales del servidor a coma decimal y punto de miles", () => {
    const problema: ResumenDeProblemaEnFila = {
      severidad: "ADVERTENCIA",
      palabra: "Advertencia",
      texto:
        // Como lo manda el servidor: la gravedad delante («ADVERTENCIA: …»); estadoLlano la quita porque la dice el ícono.
        "ADVERTENCIA: la cantidad de AF-LLAVE (1234.50 m2) es manual y no declara la regla que la produjo: no es derivable ni reproducible",
      total: 1,
    };
    render(<CeldaDeProblemas problema={problema} />);

    expect(screen.getByText("Advertencia")).toBeInTheDocument();
    expect(
      screen.getByText(
        "La cantidad de AF-LLAVE (1.234,50 m²) se escribió a mano, sin el cálculo que la produce: Sílice no puede comprobar de dónde sale.",
      ),
    ).toBeInTheDocument();
  });

  test("cuando la fila tiene más de un problema, indica el conteo total además de la severidad más grave", () => {
    const problema: ResumenDeProblemaEnFila = {
      severidad: "CRITICO",
      palabra: "Crítico",
      texto: "Falta el rendimiento de la cuadrilla.",
      total: 2,
    };
    render(<CeldaDeProblemas problema={problema} />);

    expect(screen.getByText("Crítico")).toBeInTheDocument();
    expect(screen.getByText("Falta el rendimiento de la cuadrilla.")).toBeInTheDocument();
    expect(screen.getByText("(2 problemas)")).toBeInTheDocument();
    expect(textoDeCeldaDeProblemas(problema)).toBe("Crítico: Falta el rendimiento de la cuadrilla. (2 problemas)");
  });

  test("no repite la palabra de severidad cuando el detalle coincide con ella", () => {
    const problema: ResumenDeProblemaEnFila = {
      severidad: "ERROR",
      palabra: "Error",
      texto: "ERROR: error",
      total: 1,
    };
    render(<CeldaDeProblemas problema={problema} />);

    expect(screen.getAllByText("Error")).toHaveLength(1);
    expect(textoDeCeldaDeProblemas(problema)).toBe("Error");
  });

  test("dentro de Grilla conserva la única parada de Tab (sin botones propios) y no abre nada no pedido", () => {
    const filas: FilaPrueba[] = [
      {
        id: "CIM-01|manual",
        partida: "CIM-01",
        problema: {
          severidad: "CRITICO",
          palabra: "Crítico",
          texto: "Falta el rendimiento de la cuadrilla.",
          total: 2,
        },
      },
      {
        id: "FRI-01|manual",
        partida: "FRI-01",
        problema: null,
      },
    ];
    const columnas: ColumnaDeGrilla<FilaPrueba>[] = [
      { clave: "partida", titulo: "Partida", valor: (f) => f.partida },
      {
        clave: "problemas",
        titulo: "Problemas",
        valor: (f) => textoDeCeldaDeProblemas(f.problema),
        render: (f) => <CeldaDeProblemas problema={f.problema} />,
      },
    ];

    const { container } = render(
      <Grilla<FilaPrueba> etiqueta="Presupuesto" columnas={columnas} filas={filas} idDeFila={(f) => f.id} />,
    );

    const grilla = screen.getByRole("grid", { name: "Presupuesto" });
    expect(within(grilla).getByRole("gridcell", { name: /Crítico.*Falta el rendimiento de la cuadrilla\..*\(2 problemas\)/ })).toBeInTheDocument();
    expect(within(grilla).getByRole("gridcell", { name: "Sin problemas" })).toBeInTheDocument();
    expect(screen.queryAllByRole("button")).toHaveLength(0);
    expect(container.querySelectorAll("[popover], [role='dialog'], [title]")).toHaveLength(0);
  });
});

describe("estilos de problemas.scss", () => {
  const nodo = (
    globalThis as unknown as {
      process: {
        getBuiltinModule(nombre: "node:fs"): { readFileSync(ruta: string, codificacion: string): string };
      };
    }
  ).process;
  // En una variable: con el texto literal, Vite reescribe new URL(...) como un recurso y deja de ser file:.
  const relativa = "./problemas.scss";
  const rutaScss = fileURLToPath(new URL(relativa, import.meta.url));
  const fuenteScss = nodo.getBuiltinModule("node:fs").readFileSync(rutaScss, "utf-8");
  const cssCompilado = sass.compile(rutaScss).css;

  test("usa solo tokens --silice-*, sin colores literales ni font-size en px", () => {
    expect(fuenteScss).toMatch(/var\(--silice-/);
    expect(cssCompilado).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(cssCompilado).not.toMatch(/rgba?\(/);
    expect(cssCompilado).not.toMatch(/font-size:\s*[^;]*px\b/);
  });

  test("el texto de la celda recorta con overflow: hidden y puntos suspensivos, nunca clip", () => {
    const regla = /\.silice-problemas-celda__texto\s*\{([^}]*)\}/.exec(cssCompilado)?.[1] ?? "";
    expect(regla).toMatch(/overflow:\s*hidden/);
    expect(regla).toMatch(/text-overflow:\s*ellipsis/);
    expect(regla).toMatch(/white-space:\s*nowrap/);
    expect(cssCompilado).not.toMatch(/overflow:\s*clip/);
  });
});
