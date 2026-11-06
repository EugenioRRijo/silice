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

  test("N1: el alta de un punto con especificaciones lleva rótulos del servidor y no confunde un dato interno con un campo", () => {
    // Formato exacto de `_resumen_de_fila` (aplicacion/hoja.py): las columnas en orden, sin las vacías; las
    // especificaciones van como «clave=valor; clave=valor» dentro de la columna.
    const resumen =
      "id=P1; nombre=Toma cocina; especialidad=electricidad; tipo=tomacorriente; ambiente_id=A1; superficie=pared; x=1.5; y=0; z=0.3; especificaciones=amperaje=15; tipo_de_caja=plastica; origen_id=O1";
    expect(presentarValor("fila", resumen, "esp_puntos:P1")).toBe(
      "Código=P1; Nombre=Toma cocina; Especialidad=electricidad; Tipo de punto=tomacorriente; Ambiente=A1; Superficie=pared; Posición X (m)=1,5; Posición Y (m)=0; Altura (m)=0,3; Especificaciones=amperaje=15; tipo_de_caja=plastica; Origen de la medida=O1",
    );
  });

  test("N1: el alta de un tramo no corta los vértices por su «; » y los muestra legibles", () => {
    const resumen =
      "recorrido_id=R1; punto_id=P1; orden=1; superficie=pared; empotrado=si; pendiente=0.02; vertices=1.5,0,2.5; 1.5,0,0.6";
    expect(presentarValor("fila", resumen, "esp_tramos:R1#1")).toBe(
      "Recorrido=R1; Punto=P1; Orden del vértice=1; Superficie=pared; Empotrado=si; Pendiente=0,02; Vértices=(1,5; 0; 2,5), (1,5; 0; 0,6)",
    );
    expect(presentarValor("fila", resumen, "esp_tramos:R1#1")).not.toContain("1.5");
  });

  test("N1: la baja de una fila (el resumen va en «antes») y un nombre libre con «; » siguen enteros", () => {
    const resumen = "id=A1; nombre=Sala; comedor; largo=4.5; ancho=3.2";
    expect(presentarValor("fila", resumen, "esp_ambientes:A1")).toBe(
      "Código=A1; Nombre=Sala; comedor; Largo (m)=4,5; Ancho (m)=3,2",
    );
  });

  test("N1: un campo «fila» que no es un resumen de su tabla queda como cualquier valor", () => {
    expect(presentarValor("fila", "", "esp_ambientes:A1")).toBe("");
    expect(presentarValor("fila", "12.5", "esp_ambientes:A1")).toBe("12,5");
    expect(presentarValor("fila", "Eje B2.5", "esp_ambientes:A1")).toBe("Eje B2.5");
    expect(presentarValor("fila", "largo=4.5; ancho=3.2")).toBe("largo=4.5; ancho=3.2");
    expect(presentarValor("fila", "largo=4.5", "esp_zzz:Q9")).toBe("largo=4.5");
  });
});
