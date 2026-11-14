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

  // Ronda 1 del árbitro de la ola 2 (hallazgo 6): las especificaciones de un renglón (`_cambios_de_especificaciones`,
  // aplicacion/hoja.py, congelado) son «clave=valor; clave=valor» ordenadas; la directiva «_frente» es una clave interna.
  test("las especificaciones de un renglón dicen «Frente: …» y no muestran las directivas internas sin rótulo", () => {
    expect(presentarValor("especificaciones", "_frente=FRENTE A")).toBe("Frente: FRENTE A");
    expect(presentarValor("especificaciones", "")).toBe("");
    expect(presentarValor("especificaciones", "_frente=Tramo 2; espesor=0.05")).toBe("Frente: Tramo 2; espesor=0,05");
    expect(presentarValor("especificaciones", "Clase=B; _frente=Norte")).toBe("Clase=B; Frente: Norte");
    expect(presentarValor("especificaciones", "_interna=1; espesor=0.05")).toBe("espesor=0,05");
    expect(presentarValor("especificaciones", "_frente=Estación; 2")).toBe("Frente: Estación; 2");
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

  // Resto N1 del árbitro de la tanda (F8, C5): un nombre libre puede llevar «; <columna>=». Antes ganaba la primera
  // coincidencia de cada columna y el nombre se cortaba; ahora gana la lectura que reconoce más columnas y, si dos
  // reconocen las mismas, la que deja el texto libre entero (la coincidencia de la columna que va más tarde).
  test("N1 (F8): un nombre «Toma; z=3» no se come la posición: gana la lectura con más columnas", () => {
    const resumen = "id=P1; nombre=Toma; z=3; x=1.5; y=0; z=0.3";
    expect(presentarValor("fila", resumen, "esp_puntos:P1")).toBe(
      "Código=P1; Nombre=Toma; z=3; Posición X (m)=1,5; Posición Y (m)=0; Altura (m)=0,3",
    );
  });

  test("N1 (F8): un nombre «Toma; x=3» con la misma cantidad de columnas queda entero", () => {
    const resumen = "id=P1; nombre=Toma; x=3; x=1.5; y=0; z=0.3";
    expect(presentarValor("fila", resumen, "esp_puntos:P1")).toBe(
      "Código=P1; Nombre=Toma; x=3; Posición X (m)=1,5; Posición Y (m)=0; Altura (m)=0,3",
    );
    const ambiente = "id=A1; nombre=Sala; x0=3; x0=1; y0=2; largo=4.5";
    expect(presentarValor("fila", ambiente, "esp_ambientes:A1")).toBe(
      "Código=A1; Nombre=Sala; x0=3; Esquina X (m)=1; Esquina Y (m)=2; Largo (m)=4,5",
    );
  });

  test("N2: el campo suelto «vertices» (un cambio de un vértice) sale con coma decimal y entre paréntesis", () => {
    expect(presentarValor("vertices", "1.5,0,2.5; 1.5,0,0.6")).toBe("(1,5; 0; 2,5), (1,5; 0; 0,6)");
  });

  test("N1: un campo «fila» que no es un resumen de su tabla queda como cualquier valor", () => {
    expect(presentarValor("fila", "", "esp_ambientes:A1")).toBe("");
    expect(presentarValor("fila", "12.5", "esp_ambientes:A1")).toBe("12,5");
    expect(presentarValor("fila", "Eje B2.5", "esp_ambientes:A1")).toBe("Eje B2.5");
    expect(presentarValor("fila", "largo=4.5; ancho=3.2")).toBe("largo=4.5; ancho=3.2");
    expect(presentarValor("fila", "largo=4.5", "esp_zzz:Q9")).toBe("largo=4.5");
  });
});
