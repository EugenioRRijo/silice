import { describe, expect, test } from "vitest";
import { presentarClave, presentarValor } from "./presentarCambio";

describe("presentador común de las filas del registro de cambios", () => {
  test("la clave de un parámetro de costo o de control sale con su rótulo", () => {
    expect(presentarClave("parametro", "administracion")).toBe("Administración");
    expect(presentarClave("parametro", "control|spi_error")).toBe("Control de obra: Umbral de SPI para error");
  });

  test("la clave de una fila del metraje o de un renglón sale como la nombra la persona", () => {
    expect(presentarClave("metraje", "esp_puntos:P1")).toBe("Punto P1");
    expect(presentarClave("apu", "MIN-001|Arena")).toBe("MIN-001, Arena");
  });

  test("el antes y el después: cifra con coma, instantánea con tilde, texto intacto", () => {
    expect(presentarValor("cantidad", "24.5")).toBe("24,5");
    expect(presentarValor("ambiente_id", "A1.2")).toBe("A1.2");
    expect(presentarValor("instantanea", "catalogo")).toBe("Catálogo");
    expect(presentarValor("instantanea", "instantanea")).toBe("Instantánea");
  });

  test("N1: el resumen del alta o baja de una fila lleva rótulos y cifras con coma", () => {
    // El formato exacto de `_resumen_de_fila` (aplicacion/hoja.py): «clave=valor; clave=valor», sin los valores vacíos.
    expect(presentarValor("fila", "largo=4.5; ancho=3.2; ambiente_id=A1.2")).toBe(
      "Largo (m)=4,5; Ancho (m)=3,2; Ambiente=A1.2",
    );
    expect(presentarValor("fila", "")).toBe("");
  });

  test("N1: un campo «fila» que no es un resumen compuesto queda como cualquier valor", () => {
    expect(presentarValor("fila", "12.5")).toBe("12,5");
    expect(presentarValor("fila", "Eje B2.5")).toBe("Eje B2.5");
  });
});
