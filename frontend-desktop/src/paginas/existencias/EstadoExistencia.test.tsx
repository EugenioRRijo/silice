import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { EstadoExistencia, estadoDe, ROTULOS_DE_ESTADO } from "./EstadoExistencia";

const base = {
  codigo: "ARE-01",
  nombre: "Arena lavada",
  unidad_venta: "m3",
  existencia: "10",
  minima: "5",
  queda_poco: false,
  negativa: false,
};

describe("estadoDe", () => {
  test("normal, queda poco y negativa", () => {
    expect(estadoDe(base)).toBe("normal");
    expect(estadoDe({ ...base, queda_poco: true })).toBe("queda_poco");
    expect(estadoDe({ ...base, negativa: true })).toBe("negativa");
  });

  test("la existencia negativa manda sobre queda poco (una negativa siempre queda por debajo de la minima)", () => {
    expect(estadoDe({ ...base, queda_poco: true, negativa: true })).toBe("negativa");
  });
});

describe("EstadoExistencia", () => {
  test("los rotulos son los de la pantalla clasica", () => {
    expect(ROTULOS_DE_ESTADO).toEqual({
      normal: "Normal",
      queda_poco: "Queda poco",
      negativa: "Existencia negativa: falta registrar producción o conteo",
    });
  });

  test.each([
    ["normal", "Normal"],
    ["queda_poco", "Queda poco"],
    ["negativa", "Existencia negativa: falta registrar producción o conteo"],
  ] as const)("%s lleva un icono y su texto, nunca solo color", (estado, texto) => {
    const { container } = render(<EstadoExistencia estado={estado} />);
    expect(screen.getByText(texto)).toBeInTheDocument();
    const icono = container.querySelector("svg");
    expect(icono).not.toBeNull();
    expect(icono).toHaveAttribute("aria-hidden", "true");
    expect(container.firstElementChild).toHaveAttribute("data-estado", estado);
  });

  test("cada estado usa un icono distinto", () => {
    const formas = (["normal", "queda_poco", "negativa"] as const).map((estado) => {
      const { container, unmount } = render(<EstadoExistencia estado={estado} />);
      const forma = container.querySelector("svg")?.innerHTML ?? "";
      unmount();
      return forma;
    });
    expect(new Set(formas).size).toBe(3);
  });
});
