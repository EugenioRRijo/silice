import { describe, expect, test } from "vitest";
import { vistaEspacio } from "./datosDePrueba";
import {
  LIMITE_DE_FILAS,
  cuerpoDeEdicionDelEspacio,
  filaEnBlanco,
  mensajeDeRechazo,
  puedeAgregarFila,
  rutaDeEspacio,
  sembrarTablas,
  ubicarError,
} from "./logica";

// Rebanada 3c-1 (edición del espacio): lógica pura. Los literales salen del diseño (§4.4 E1, §4.1, §2.5.1, §2.12) y
// de la página clásica (ui/hoja.py: rótulos H:180 y plantillas de error H:452, H:518), no del código bajo prueba.

function contador() {
  let n = 0;
  return () => ++n;
}

describe("edición del espacio (3c-1): lógica", () => {
  test("E1 es PUT sobre /v1/hoja/borradores/{id}/espacio", () => {
    expect(rutaDeEspacio("abc_123-xyz")).toBe("/v1/hoja/borradores/abc_123-xyz/espacio");
  });

  test("sembrar: una fila por fila del servidor, con una clave propia y todas las columnas como texto", () => {
    const vista = vistaEspacio();
    const tablas = sembrarTablas(vista.tablas, vista.filas, contador());
    expect(Object.keys(tablas)).toEqual(["origenes", "ambientes", "fuentes", "puntos", "tramos"]);
    expect(tablas.ambientes!.map((f) => f.valores)).toEqual([
      { id: "BAN-01", nombre: "Baño", largo: "2" },
      { id: "COC-01", nombre: "Cocineta", largo: "2" },
    ]);
    // El generador entrega 1 a la fila de orígenes; las dos de ambientes son la 2 y la 3.
    expect(tablas.ambientes!.map((f) => f.clave)).toEqual([2, 3]);
    // Una columna que el servidor no mandó queda vacía, no ausente.
    expect(tablas.fuentes![0]!.valores).toEqual({ id: "F1", especialidad: "agua" });
    expect(tablas.tramos).toEqual([]);
  });

  test("una fila en blanco tiene todas las columnas vacías", () => {
    const vista = vistaEspacio();
    expect(filaEnBlanco(vista.tablas[1]!, 77)).toEqual({ clave: 77, valores: { id: "", nombre: "", largo: "" } });
  });

  test("el cuerpo de E1 lleva el rev y las cinco tablas completas, cada celda tal cual la escribió la persona", () => {
    const vista = vistaEspacio();
    const tablas = sembrarTablas(vista.tablas, vista.filas, contador());
    tablas.ambientes![0]!.valores.largo = "2.50";
    tablas.ambientes!.push({ clave: 99, valores: { id: "", nombre: "", largo: "" } });
    expect(cuerpoDeEdicionDelEspacio(4, vista.tablas, tablas)).toEqual({
      rev: 4,
      tablas: {
        origenes: [{ id: "O1", tipo: "supuesto", referencia: "motivo=ejemplo" }],
        ambientes: [
          { id: "BAN-01", nombre: "Baño", largo: "2.50" },
          { id: "COC-01", nombre: "Cocineta", largo: "2" },
          { id: "", nombre: "", largo: "" },
        ],
        fuentes: [{ id: "F1", especialidad: "agua" }],
        puntos: [{ id: "P1", superficie: "pared" }],
        tramos: [],
      },
    });
  });

  test("un decimal largo no pierde ni una cifra en el cuerpo", () => {
    const vista = vistaEspacio();
    const tablas = sembrarTablas(vista.tablas, vista.filas, contador());
    const largo = "0.1000000000000000055511151231257827";
    tablas.ambientes![1]!.valores.largo = largo;
    expect(cuerpoDeEdicionDelEspacio(0, vista.tablas, tablas).tablas.ambientes![1]!.largo).toBe(largo);
  });

  test("el rechazo agrega la frase de la clásica con tildes, sin duplicar el punto final", () => {
    expect(mensajeDeRechazo("ambientes, fila 1: largo: '2,5' no es un numero decimal valido")).toBe(
      "ambientes, fila 1: largo: '2,5' no es un numero decimal valido. La hoja sigue con el último borrador válido.",
    );
    expect(mensajeDeRechazo("Dato repetido.")).toBe("Dato repetido. La hoja sigue con el último borrador válido.");
  });

  test("ubicar el error: tabla por su rótulo sin tildes, fila (de 1) y columna por su clave", () => {
    const { tablas } = vistaEspacio();
    expect(ubicarError("ambientes, fila 2: largo: '2,5' no es un numero decimal valido", tablas)).toEqual({
      tabla: "ambientes",
      fila: 2,
      columna: "largo",
    });
    expect(ubicarError("origenes de medida, fila 1: tipo: 'x' no es un valor valido (plano, dxf)", tablas)).toEqual({
      tabla: "origenes",
      fila: 1,
      columna: "tipo",
    });
    expect(ubicarError("vertices de recorridos, fila 3: orden: 'a' no es un entero", tablas)).toEqual({
      tabla: "tramos",
      fila: 3,
      columna: null, // «orden» no es columna de esta vista de ejemplo
    });
  });

  test("ubicar el error: un mensaje sin tabla y fila no se ubica, ni una tabla desconocida", () => {
    const { tablas } = vistaEspacio();
    expect(ubicarError("ambientes: el id 'A1' esta repetido", tablas)).toBeNull();
    expect(ubicarError("pisos, fila 1: id: vacio", tablas)).toBeNull();
    expect(ubicarError("", tablas)).toBeNull();
  });

  test("los topes de filas son los del diseño (D-9) y «Agregar fila» se cierra en ellos", () => {
    expect(LIMITE_DE_FILAS).toEqual({ origenes: 5000, ambientes: 1000, fuentes: 1000, puntos: 5000, tramos: 20000 });
    expect(puedeAgregarFila("ambientes", 999)).toBe(true);
    expect(puedeAgregarFila("ambientes", 1000)).toBe(false);
    expect(puedeAgregarFila("tramos", 19999)).toBe(true);
    expect(puedeAgregarFila("tramos", 20000)).toBe(false);
    expect(puedeAgregarFila("desconocida", 0)).toBe(false);
  });
});
