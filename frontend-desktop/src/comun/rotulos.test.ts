import { describe, expect, test } from "vitest";
import { rotuloDeCampo, rotuloDeObjeto, rotuloDeParametro, valorDeCambio } from "./rotulos";

describe("rótulos del registro de cambios", () => {
  test("un parámetro de control sale como «Control de obra: <parámetro>»", () => {
    expect(rotuloDeParametro("control|spi_error")).toBe("Control de obra: Umbral de SPI para error");
    expect(rotuloDeParametro("control|penalizacion_diaria")).toBe("Control de obra: Penalización diaria por retraso");
    expect(rotuloDeParametro("control|otro_nuevo")).toBe("Control de obra: Otro nuevo");
  });
  test("los parámetros de costo siguen como antes", () => {
    expect(rotuloDeParametro("bono_alimentacion")).toBe("Bono de alimentación");
    expect(rotuloDeObjeto("parametro")).toBe("Parámetro");
  });
  test("campos de control y de metraje con rótulo y tilde", () => {
    expect(rotuloDeCampo("penalizacion_diaria")).toBe("Penalización diaria por retraso");
    expect(rotuloDeCampo("spi_error")).toBe("Umbral de SPI para error");
    expect(rotuloDeCampo("ambiente_id")).toBe("Ambiente");
    expect(rotuloDeCampo("vertices")).toBe("Vértices");
    expect(rotuloDeCampo("x0")).toBe("Esquina X (m)");
    expect(rotuloDeCampo("campo_raro")).toBe("Campo raro");
  });
  test("valorDeCambio: cifra con coma, instantánea con tilde, el resto intacto", () => {
    expect(valorDeCambio("cantidad", "24.5")).toBe("24,5");
    expect(valorDeCambio("ambiente_id", "A1.2")).toBe("A1.2");
    expect(valorDeCambio("instantanea", "catalogo")).toBe("Catálogo");
    expect(valorDeCambio("instantanea", "instantanea")).toBe("Instantánea");
    expect(valorDeCambio("cantidad", "catalogo")).toBe("catalogo");
  });
});
