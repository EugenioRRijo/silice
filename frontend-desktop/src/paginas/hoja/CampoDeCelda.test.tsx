import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { CampoDeCelda } from "./CampoDeCelda";

const nada = () => undefined;

function lectura(valor: string, etiquetaVisible = false) {
  return render(
    <CampoDeCelda
      soloLectura
      id="cantidad-3"
      etiqueta="Cantidad, Presupuesto fila 3"
      etiquetaVisible={etiquetaVisible}
      valor={valor}
      alCambiar={nada}
      alRestaurar={nada}
    />,
  );
}

describe("CampoDeCelda en solo lectura", () => {
  test("en una tabla conserva su etiqueta para el lector de pantalla, oculta a la vista", () => {
    const { container } = lectura("1.234,5");
    const oculta = container.querySelector(".cds--visually-hidden");
    expect(oculta).toHaveTextContent("Cantidad, Presupuesto fila 3");
    expect(screen.getByText("1.234,5")).toBeInTheDocument();
    expect(container).toHaveTextContent("Cantidad, Presupuesto fila 3: 1.234,5");
  });

  test("no deja ningún campo de texto", () => {
    lectura("1.234,5");
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  test("en un formulario la etiqueta se ve y no se repite oculta", () => {
    const { container } = lectura("12", true);
    expect(container.querySelector(".cds--visually-hidden")).toBeNull();
    expect(screen.getByText("Cantidad, Presupuesto fila 3")).toHaveClass("cds--label");
  });
});
