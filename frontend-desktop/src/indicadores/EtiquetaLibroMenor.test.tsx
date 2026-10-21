import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { EtiquetaLibroMenor, TEXTO_LIBRO_MENOR_BREVE, TEXTO_LIBRO_MENOR_FIJO, textoLibroMenor } from "./EtiquetaLibroMenor";
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

  test("con datos: dice lo que se cuenta (partidas con costo directo incompleto), no partidas ausentes (B1)", () => {
    expect(textoLibroMenor([2])).toBe(
      "Libro menor: 1 partida con costo directo incompleto (n.º 2). Puede faltar además alguna partida; revise antes de aceptar",
    );
    expect(textoLibroMenor([2, 5])).toBe(
      "Libro menor: 2 partidas con costo directo incompleto (n.º 2, 5). Puede faltar además alguna partida; revise antes de aceptar",
    );
    expect(textoLibroMenor([2, 5])).not.toMatch(/omite/);
  });

  test("con muchas partidas lista las primeras cinco y cuenta el resto", () => {
    expect(textoLibroMenor([1, 2, 3, 4, 5, 6, 7])).toBe(
      "Libro menor: 7 partidas con costo directo incompleto (n.º 1, 2, 3, 4, 5 y 2 más). Puede faltar además alguna partida; revise antes de aceptar",
    );
  });

  test("el marcador breve es solo «Libro menor»", () => {
    expect(TEXTO_LIBRO_MENOR_BREVE).toBe("Libro menor");
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

  test("el marcador breve lleva el mismo icono, el texto «Libro menor» y la misma clase de nota", () => {
    render(<EtiquetaLibroMenor breve />);
    const nota = screen.getByRole("note");
    expect(nota.textContent).toBe("Libro menor");
    expect(nota.querySelector("svg")).not.toBeNull();
    expect(nota).toHaveClass("fiori-kpi__aviso");
  });

  test.each([false, true])("no se puede cerrar (breve=%s): ni boton, ni enlace, ni control alguno dentro", (breve) => {
    render(<EtiquetaLibroMenor partidas={[2]} breve={breve} />);
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

  test("la lectora lo oye UNA vez: el nombre del grupo es el titulo y la nota es su descripcion (B3)", () => {
    render(<IndicadorFiori indicador={indicador()} partidasConOmision={[2]} />);
    const grupo = screen.getByRole("group", { name: "Total general" });
    expect(grupo).toHaveAccessibleName("Total general");
    expect(grupo).toHaveAccessibleDescription(/^Libro menor: 1 partida con costo directo incompleto/);
    expect(grupo.getAttribute("aria-label")).not.toMatch(/Libro menor/);
  });

  test("sin libro menor no hay nota ni descripcion", () => {
    for (const delta of ["178.96", "0.00"]) {
      const { unmount } = render(<IndicadorFiori indicador={indicador({ delta })} partidasConOmision={[2]} />);
      expect(screen.getByRole("group")).toHaveAccessibleName("Total general");
      expect(screen.getByRole("group")).not.toHaveAttribute("aria-describedby");
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
    // El espacio tras «n.º» es duro (no se parte la linea ahi).
    expect(screen.getByRole("note").textContent).toBe(textoLibroMenor([2, 7]));
    expect(screen.getByRole("note").textContent).toContain("2 partidas con costo directo incompleto (n.º 2, 7)");
  });

  test("con etiquetaBreve: solo «Libro menor», y esa es su descripcion accesible", () => {
    render(<IndicadorFiori indicador={indicador({ titulo: "IVA", clave: "IVATOT" })} partidasConOmision={[2]} etiquetaBreve />);
    expect(screen.getByRole("note").textContent).toBe("Libro menor");
    expect(screen.getByRole("group", { name: "IVA" })).toHaveAccessibleDescription("Libro menor");
  });

  test("la etiqueta convive con el exacto en el tooltip y con el verde favorable", () => {
    const { container } = render(<IndicadorFiori indicador={indicador()} exactoLibro="4876.5625" exactoSilice="5055.5215" />);
    expect(screen.getByRole("note")).toBeInTheDocument();
    expect(container.querySelector(".ibcs-favorable")).not.toBeNull();
    expect(screen.getByRole("button", { name: /4\.876,56/ })).toBeInTheDocument();
  });
});

describe("FranjaIndicadores con libro menor (V-16)", () => {
  const tres = [
    indicador({ clave: "SUBSINIVA", titulo: "Subtotal sin IVA" }),
    indicador({ clave: "IVATOT", titulo: "IVA" }),
    indicador({ clave: "TOTALGEN" }),
  ];

  test("etiqueta completa solo en «Total general»; subtotal e IVA llevan el marcador breve", () => {
    render(<FranjaIndicadores indicadores={tres} partidasConOmision={[2]} />);
    expect(screen.getAllByRole("note")).toHaveLength(3);
    const total = within(screen.getByRole("group", { name: "Total general" })).getByRole("note");
    expect(total.textContent).toBe(textoLibroMenor([2]));
    for (const nombre of ["Subtotal sin IVA", "IVA"]) {
      expect(within(screen.getByRole("group", { name: nombre })).getByRole("note").textContent).toBe("Libro menor");
    }
  });

  test("solo los indicadores que salen menores llevan nota", () => {
    render(
      <FranjaIndicadores
        indicadores={[tres[0], indicador({ clave: "IVATOT", titulo: "IVA", delta: "10.00", delta_pct: "1.00" }), tres[2]]}
      />,
    );
    expect(screen.getAllByRole("note")).toHaveLength(2);
    expect(within(screen.getByRole("group", { name: "IVA" })).queryByRole("note")).toBeNull();
  });

  test("sin «Total general» menor, la completa va en el primer indicador menor", () => {
    render(<FranjaIndicadores indicadores={[tres[0], tres[1]]} partidasConOmision={[2]} />);
    const notas = screen.getAllByRole("note").map((n) => n.textContent);
    expect(notas).toEqual([textoLibroMenor([2]), "Libro menor"]);
  });

  test("una respuesta de la API anterior (sin el campo) da la etiqueta fija en el total", () => {
    render(<FranjaIndicadores indicadores={[indicador()]} />);
    expect(screen.getByRole("note")).toHaveTextContent(TEXTO_LIBRO_MENOR_FIJO);
  });
});
