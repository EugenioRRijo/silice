import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { EtiquetaLibroMenor, TEXTO_LIBRO_MENOR_FIJO, textoLibroMenor } from "./EtiquetaLibroMenor";
import { FranjaIndicadores } from "./FranjaIndicadores";
import { IndicadorFiori } from "./IndicadorFiori";
import { esLibroMenor } from "./ibcs";
import type { IndicadorRespuesta } from "./tipos";

function indicador(extra: Partial<IndicadorRespuesta> = {}): IndicadorRespuesta {
  return {
    clave: "TOTALGEN",
    titulo: "Total general",
    actual: "4876.56",
    meta: "5055.52",
    delta: "-178.96",
    delta_pct: "-3.54",
    sentido: "exactitud",
    ...extra,
  };
}

describe("esLibroMenor (V-16)", () => {
  test("solo el libro contra Silice con delta negativo", () => {
    expect(esLibroMenor("-178.96", "exactitud")).toBe(true);
    expect(esLibroMenor("178.96", "exactitud")).toBe(false);
    expect(esLibroMenor("0.00", "exactitud")).toBe(false);
    expect(esLibroMenor("-0.00", "exactitud")).toBe(false);
    expect(esLibroMenor("-5", "costo")).toBe(false);
    expect(esLibroMenor("-5", "rendimiento")).toBe(false);
  });
});

describe("textoLibroMenor", () => {
  test("sin datos de omision: la frase fija, sin numeros inventados", () => {
    expect(textoLibroMenor(undefined)).toBe("Libro menor: puede deberse a partidas omitidas; revise antes de aceptar");
    expect(textoLibroMenor([])).toBe(TEXTO_LIBRO_MENOR_FIJO);
    expect(TEXTO_LIBRO_MENOR_FIJO).not.toMatch(/\d/);
  });

  test("con datos: el numero real de partidas y cuales son", () => {
    expect(textoLibroMenor([2])).toBe("Libro menor: revise si omite 1 partida (n.º\u00a02)");
    expect(textoLibroMenor([2, 5])).toBe("Libro menor: revise si omite 2 partidas (n.º\u00a02, 5)");
  });

  test("con muchas partidas lista las primeras cinco y cuenta el resto", () => {
    expect(textoLibroMenor([1, 2, 3, 4, 5, 6, 7])).toBe(
      "Libro menor: revise si omite 7 partidas (n.º\u00a01, 2, 3, 4, 5 y 2 más)",
    );
  });
});

describe("EtiquetaLibroMenor", () => {
  test("lleva icono y texto (nunca solo color) y es una nota, no un boton", () => {
    const { container } = render(<EtiquetaLibroMenor />);
    const nota = screen.getByRole("note");
    expect(nota).toHaveTextContent(TEXTO_LIBRO_MENOR_FIJO);
    expect(nota.querySelector("svg")).not.toBeNull();
    expect(nota.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    expect(container.querySelector("button, [role=button]")).toBeNull();
  });

  test("no se puede cerrar: ni boton, ni enlace, ni control alguno dentro", () => {
    render(<EtiquetaLibroMenor partidas={[2]} />);
    const nota = screen.getByRole("note");
    expect(within(nota).queryAllByRole("button")).toHaveLength(0);
    expect(nota.querySelector("button, a, input, [tabindex], [aria-label*='errar' i]")).toBeNull();
  });
});

describe("IndicadorFiori con libro menor (V-16)", () => {
  test("con delta negativo exactitud: la etiqueta va dentro del indicador, pegada a la cifra", () => {
    const { container } = render(<IndicadorFiori indicador={indicador()} />);
    const kpi = container.querySelector(".fiori-kpi") as HTMLElement;
    const etiqueta = within(kpi).getByRole("note");
    expect(etiqueta).toHaveTextContent(TEXTO_LIBRO_MENOR_FIJO);
    // Hermana de la cifra y de la variacion dentro de la misma tarjeta: ni tooltip ni portal.
    expect(etiqueta.parentElement).toBe(kpi);
    expect(etiqueta.closest("[role=tooltip]")).toBeNull();
  });

  test("forma parte del nombre accesible del indicador: la lectora la lee con la cifra", () => {
    render(<IndicadorFiori indicador={indicador()} partidasConOmision={[2]} />);
    const grupo = screen.getByRole("group", { name: /Total general/ });
    expect(grupo).toHaveAccessibleName("Total general. Libro menor: revise si omite 1 partida (n.º\u00a02)");
  });

  test("sin libro menor el nombre accesible es solo el titulo y no hay nota", () => {
    for (const delta of ["178.96", "0.00"]) {
      const { unmount } = render(<IndicadorFiori indicador={indicador({ delta })} partidasConOmision={[2]} />);
      expect(screen.getByRole("group")).toHaveAccessibleName("Total general");
      expect(screen.queryByRole("note")).toBeNull();
      unmount();
    }
  });

  test("el sentido costo con delta negativo es favorable pero NO es libro menor: sin etiqueta", () => {
    render(<IndicadorFiori indicador={indicador({ sentido: "costo" })} />);
    expect(screen.queryByRole("note")).toBeNull();
  });

  test("la etiqueta con datos de omision muestra el numero real", () => {
    render(<IndicadorFiori indicador={indicador()} partidasConOmision={[2, 7]} />);
    // El espacio tras «n.º» es duro (no se parte la linea ahi); toHaveTextContent lo normaliza a un espacio comun.
    expect(screen.getByRole("note").textContent).toBe("Libro menor: revise si omite 2 partidas (n.º\u00a02, 7)");
  });

  test("la etiqueta convive con el exacto en el tooltip y con el verde favorable", () => {
    const { container } = render(<IndicadorFiori indicador={indicador()} exactoLibro="4876.5625" exactoSilice="5055.5215" />);
    expect(screen.getByRole("note")).toBeInTheDocument();
    expect(container.querySelector(".ibcs-favorable")).not.toBeNull();
    expect(screen.getByRole("button", { name: /4\.876,56/ })).toBeInTheDocument();
  });
});

describe("FranjaIndicadores con libro menor (V-16)", () => {
  test("una etiqueta por cada indicador que sale menor y ninguna en los demas", () => {
    render(
      <FranjaIndicadores
        indicadores={[
          indicador({ clave: "SUBSINIVA", titulo: "Subtotal sin IVA" }),
          indicador({ clave: "IVATOT", titulo: "IVA", delta: "10.00", delta_pct: "1.00" }),
          indicador({ clave: "TOTALGEN" }),
        ]}
        partidasConOmision={[2]}
      />,
    );
    expect(screen.getAllByRole("note")).toHaveLength(2);
    expect(within(screen.getByRole("group", { name: /^IVA/ })).queryByRole("note")).toBeNull();
    expect(screen.getByRole("group", { name: /^Subtotal sin IVA/ })).toHaveAccessibleName(
      "Subtotal sin IVA. Libro menor: revise si omite 1 partida (n.º\u00a02)",
    );
  });

  test("una respuesta de la API anterior (sin el campo) da la etiqueta fija", () => {
    render(<FranjaIndicadores indicadores={[indicador()]} />);
    expect(screen.getByRole("note")).toHaveTextContent(TEXTO_LIBRO_MENOR_FIJO);
  });
});
