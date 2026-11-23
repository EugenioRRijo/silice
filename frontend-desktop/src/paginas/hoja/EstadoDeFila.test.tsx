import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { EstadoDeFila } from "./EstadoDeFila";

// Prueba en vivo del 18/11/2026: el texto del Estado sale de las reglas del núcleo con punto decimal («(1.89 m3)»); se lee
// con coma decimal, sin tocar los códigos de partida con puntos («C-000.000.012»). Textos ficticios, escritos a mano.
describe("Estado de una fila del presupuesto", () => {
  test("las cifras del hallazgo se leen con coma decimal, también en el título", () => {
    const texto =
      "la cantidad de C-000.000.012 (1.89 m3) es manual y no declara la regla que la produjo: no es derivable ni reproducible";
    render(<EstadoDeFila estado={{ severidad: "ADVERTENCIA", texto }} />);
    const leido =
      "la cantidad de C-000.000.012 (1,89 m3) es manual y no declara la regla que la produjo: no es derivable ni reproducible";
    expect(screen.getByText(leido)).toBeInTheDocument();
    expect(screen.getByTitle(leido)).toBeInTheDocument();
  });

  test("sin hallazgo, el texto también va con coma decimal", () => {
    render(<EstadoDeFila estado={{ severidad: null, texto: "Cuadra con su regla (7.5 m2)" }} />);
    expect(screen.getByText("Cuadra con su regla (7,5 m2)")).toBeInTheDocument();
  });

  test("la severidad la dice el ícono: el texto no la repite en mayúsculas y el aviso del núcleo se lee llano", () => {
    render(
      <EstadoDeFila
        estado={{
          severidad: "ADVERTENCIA",
          texto: "ADVERTENCIA: la cantidad de S1-R01 (1000 m3) es manual y no declara la regla que la produjo: no es derivable ni reproducible",
        }}
      />,
    );
    expect(screen.getByText("Advertencia")).toBeInTheDocument();
    expect(screen.getByText(/^La cantidad de S1-R01 \(1\.000 m³\) se escribió a mano/)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/ADVERTENCIA|derivable|reproducible/);
  });
});
