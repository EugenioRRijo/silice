import { describe, expect, test } from "vitest";
import { ErrorDeApi } from "../../api/cliente";
import { MENSAJE_INESPERADO } from "../../comun/errores";
import { fechaEsVe, leerMonto, mensajeDeCostos, mostrarMonto } from "./logica";

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

describe("fechaEsVe", () => {
  test("«2026-11-03» se lee «03/11/2026»", () => expect(fechaEsVe("2026-11-03")).toBe("03/11/2026"));
});

describe("mensajeDeCostos", () => {
  test("traduce los estados sin tecnicismos", () => {
    expect(mensajeDeCostos(new ErrorDeApi(403, "Forbidden"))).toBe("Su cuenta no tiene permiso para registrar costos.");
    expect(mensajeDeCostos(new ErrorDeApi(409, "Ese costo ya fue anulado."))).toBe("Ese costo ya fue anulado.");
    expect(mensajeDeCostos(new ErrorDeApi(404, "x"))).toBe("Ese costo ya no existe.");
    expect(mensajeDeCostos(new ErrorDeApi(422, "El programa de Sílice respondió con el estado 422."))).toBe(
      "Revise los datos: alguno no es válido.",
    );
    expect(mensajeDeCostos(new Error("detalle interno"))).toBe(MENSAJE_INESPERADO);
    expect(mensajeDeCostos(new ErrorDeApi(0, "No se pudo hablar con el programa de Sílice. Compruebe que esté encendido."))).toBe(
      "No se pudo hablar con el programa de Sílice. Compruebe que esté encendido.",
    );
  });
});
