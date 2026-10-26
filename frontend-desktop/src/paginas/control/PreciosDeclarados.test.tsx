import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { BarraDeCorte } from "./PestanasDeResultados";
import { FILTROS_INICIALES, consultaDeCalculo } from "./logica";

// Tarea 25 (plan de montar un presupuesto; diseno §11, meta 4): los precios del corte pueden salir de los precios
// declarados de los materiales (desde el estudio de mercado o al recibir una compra), sin cargar un archivo. La barra
// del corte ofrece el metodo nuevo con su nombre llano y dice de donde salen esos precios; la consulta lleva
// `metodo=declarados` y nada mas (no hay Km, R ni version que mandar).

describe("Precios declarados en la barra del corte", () => {
  test("el método nuevo se elige por su nombre, dice de dónde salen los precios y se aplica sin Km ni R", async () => {
    const alAplicar = vi.fn();
    const u = userEvent.setup();
    render(<BarraDeCorte filtros={FILTROS_INICIALES} versiones={[]} alAplicar={alAplicar} />);
    const metodo = screen.getByLabelText("Precios del corte");
    expect(screen.getByRole("option", { name: "Precios declarados de insumos" })).toBeInTheDocument();
    expect(screen.queryByText(/último precio declarado/)).not.toBeInTheDocument();

    await u.selectOptions(metodo, "declarados");
    expect(
      screen.getByText(
        "Usa el último precio declarado de cada material hasta la fecha de corte. Se declaran en Estudio de mercado o al recibir una compra en Procura.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Km declarado")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Versión revalorada")).not.toBeInTheDocument();

    await u.click(screen.getByRole("button", { name: "Calcular al corte" }));
    expect(alAplicar).toHaveBeenCalledTimes(1);
    expect(alAplicar.mock.calls[0][0].precios.metodo).toBe("declarados");
  });

  test("la consulta del cálculo con los declarados solo lleva el método", () => {
    const filtros = { corte: "", precios: { ...FILTROS_INICIALES.precios, metodo: "declarados" as const, km: "1,1" } };
    expect(consultaDeCalculo("OB-S2", filtros)).toBe("/v1/control/calculo?proyecto=OB-S2&metodo=declarados");
  });
});
