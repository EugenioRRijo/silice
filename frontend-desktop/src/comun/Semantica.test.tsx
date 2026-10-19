import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { Severidad } from "./Severidad";
import { TablaDensa } from "./TablaDensa";
import { Variacion } from "./Variacion";

describe("Severidad", () => {
  test.each([
    ["CRITICO", "Crítico", "critico"],
    ["ERROR", "Error", "error"],
    ["ADVERTENCIA", "Advertencia", "advertencia"],
    ["INFO", "Información", "info"],
  ])("%s lleva su nombre en texto y la clase de su token", (valor, texto, clase) => {
    const { container } = render(<Severidad valor={valor} />);

    expect(screen.getByText(texto)).toBeInTheDocument();
    expect(container.querySelector(`.silice-sev--${clase}`)).not.toBeNull();
    expect(container.querySelector("svg")).not.toBeNull(); // el color nunca va solo
  });

  test("una severidad desconocida se muestra con su texto y sin inventar un color", () => {
    const { container } = render(<Severidad valor="RARA" />);

    expect(screen.getByText("RARA")).toBeInTheDocument();
    expect(container.querySelector(".silice-sev--critico, .silice-sev--error")).toBeNull();
  });
});

describe("Variacion (IBCS de costo)", () => {
  test("subir un costo es desfavorable, con flecha y texto accesible", () => {
    const { container } = render(<Variacion valor="12.43" />);

    expect(container.querySelector(".ibcs-desfavorable")).not.toBeNull();
    expect(screen.getByText("12.43")).toBeInTheDocument();
    expect(screen.getByText("(desfavorable)")).toBeInTheDocument();
    expect(container.querySelector("svg")).not.toBeNull();
  });

  test("bajar un costo es favorable", () => {
    const { container } = render(<Variacion valor="-72.12" />);

    expect(container.querySelector(".ibcs-favorable")).not.toBeNull();
    expect(screen.getByText("(favorable)")).toBeInTheDocument();
  });

  test.each(["0", "0.00", "-0.00"])("%s es neutro, nunca verde por signo", (valor) => {
    const { container } = render(<Variacion valor={valor} />);

    expect(container.querySelector(".ibcs-neutro")).not.toBeNull();
    expect(container.querySelector(".ibcs-favorable, .ibcs-desfavorable")).toBeNull();
  });
});

describe("TablaDensa con celdas de semantica", () => {
  test("dibuja la severidad y la variación según la columna y deja el resto como texto", () => {
    render(
      <TablaDensa
        etiqueta="Prueba"
        columnas={[
          { clave: "regla", titulo: "Regla" },
          { clave: "sev", titulo: "Severidad", celda: "severidad" },
          { clave: "var", titulo: "Variación", numerica: true, celda: "variacion" },
        ]}
        filas={[{ id: "1", regla: "R3", sev: "ERROR", var: "9.09" }]}
      />,
    );

    const tabla = screen.getByRole("table", { name: "Prueba" });
    expect(within(tabla).getByText("R3")).toBeInTheDocument();
    expect(within(tabla).getByText("Error")).toBeInTheDocument();
    expect(within(tabla).getByText("(desfavorable)")).toBeInTheDocument();
  });
});
