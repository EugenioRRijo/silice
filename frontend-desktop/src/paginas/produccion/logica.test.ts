import { describe, expect, test } from "vitest";
import { ErrorDeApi } from "../../api/cliente";
import { leerMonto, mensajeDeCostos, mostrarMonto, totalesPorCentro } from "./logica";

describe("leerMonto", () => {
  test.each([
    ["1.250,50", "1250.50"],
    ["300", "300"],
    ["0,5", "0.5"],
    ["0", "0"],
  ])("«%s» sale como «%s»", (escrito, esperado) => {
    expect(leerMonto(escrito)).toEqual({ valor: esperado });
  });

  test.each(["diez", "1,2,3", "1.2", "-5", "  ", "1e3"])("«%s» se rechaza con un motivo", (escrito) => {
    expect(leerMonto(escrito)).toHaveProperty("error");
  });
});

describe("mostrarMonto", () => {
  test.each([
    ["1250.50", "1.250,50"],
    ["300", "300,00"],
    ["800.000", "800,000"],
    ["0.5", "0,50"],
  ])("«%s» se muestra «%s»", (api, texto) => expect(mostrarMonto(api)).toBe(texto));
});

describe("totalesPorCentro", () => {
  const f = (centro: string, monto: string, moneda: string, parcial = {}) => ({
    centro,
    monto,
    moneda,
    anulado: false,
    anula_id: null,
    ...parcial,
  });

  test("suma exacta por centro y moneda, sin números de coma flotante", () => {
    const t = totalesPorCentro([
      f("cantera", "0.10", "USD"),
      f("cantera", "0.20", "USD"),
      f("cantera", "5", "Bs"),
      f("planta", "1", "USD"),
    ]);
    expect(t).toEqual([
      { centro: "cantera", moneda: "Bs", total: "5.00" },
      { centro: "cantera", moneda: "USD", total: "0.30" },
      { centro: "planta", moneda: "USD", total: "1.00" },
    ]);
  });

  test("los anulados y sus anulaciones no suman", () => {
    const t = totalesPorCentro([
      f("cantera", "10", "USD"),
      f("cantera", "7", "USD", { anulado: true }),
      f("cantera", "7", "USD", { anulado: true, anula_id: 2 }),
    ]);
    expect(t).toEqual([{ centro: "cantera", moneda: "USD", total: "10.00" }]);
  });
});

describe("mensajeDeCostos", () => {
  test("traduce los estados sin tecnicismos", () => {
    expect(mensajeDeCostos(new ErrorDeApi(403, "Forbidden"))).toBe("Su cuenta no tiene permiso para registrar costos.");
    expect(mensajeDeCostos(new ErrorDeApi(409, "Ese costo ya fue anulado."))).toBe("Ese costo ya fue anulado.");
    expect(mensajeDeCostos(new ErrorDeApi(404, "x"))).toBe("Ese costo ya no existe.");
    expect(mensajeDeCostos(new ErrorDeApi(422, "El programa de Sílice respondió con el estado 422."))).toBe(
      "Revise los datos: alguno no es válido.",
    );
    expect(mensajeDeCostos(new ErrorDeApi(0, "No se pudo hablar con el programa de Sílice. Compruebe que esté encendido."))).toBe(
      "No se pudo hablar con el programa de Sílice. Compruebe que esté encendido.",
    );
  });
});
