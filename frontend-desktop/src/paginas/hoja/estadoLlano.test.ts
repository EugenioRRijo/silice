import { describe, expect, test } from "vitest";
import { estadoLlano } from "./estadoLlano";

// Eugenio (2026-11-23), sobre una captura del Presupuesto: la celda decía «⚠ Advertencia» y debajo «ADVERTENCIA: la
// cantidad de S1-R01 (1000 m3) es manual y no declara la regla que la produjo: no es derivable ni reproducible». El
// ícono ya dice la severidad: el texto no la repite en mayúsculas, y el aviso del núcleo (que no se toca) se lee en
// español llano.

describe("el Estado de una fila en español llano", () => {
  test("el aviso de cantidad manual del núcleo se traduce, con la cifra y la unidad en es-VE", () => {
    expect(
      estadoLlano(
        "ADVERTENCIA: la cantidad de S1-R01 (1000 m3) es manual y no declara la regla que la produjo: no es derivable ni reproducible",
        "ADVERTENCIA",
      ),
    ).toBe("La cantidad de S1-R01 (1.000 m³) se escribió a mano, sin el cálculo que la produce: Sílice no puede comprobar de dónde sale.");
  });

  test("el prefijo de la severidad que ya muestra el ícono se quita y el texto empieza con mayúscula", () => {
    expect(estadoLlano("ERROR: la partida no cuadra con su regla", "ERROR")).toBe("La partida no cuadra con su regla");
  });

  test("los avisos siguientes conservan su severidad, sin mayúsculas sostenidas, separados por un punto medio", () => {
    expect(estadoLlano("ERROR: no cuadra | ADVERTENCIA: revise la unidad", "ERROR")).toBe("No cuadra · Advertencia: revise la unidad");
  });

  test("«PENDIENTE» no es una severidad: se escribe «Pendiente:» y no se borra", () => {
    expect(estadoLlano("PENDIENTE: sin precio con la lista de esta versión (AF-SALIDA)", "ERROR")).toBe(
      "Pendiente: sin precio con la lista de esta versión (AF-SALIDA)",
    );
  });

  test("el rótulo congelado «sin APU en el catálogo» se lee como lo que suele faltar: el precio en la lista", () => {
    // `aplicacion/hoja.py` está congelado por el experimento del asistente (RS-9): el servidor sigue escribiendo
    // «sin APU en el catálogo», y a menudo lo que falta es el precio en la lista de la versión (juez F2, 2026-11-23).
    expect(estadoLlano("PENDIENTE: sin APU en el catálogo (AF-SALIDA; AF-LLAVE)", "ERROR")).toBe(
      "Pendiente: sin precio con la lista de esta versión (AF-SALIDA; AF-LLAVE)",
    );
  });

  test("un texto sin prefijo queda igual", () => {
    expect(estadoLlano("OK", null)).toBe("OK");
    expect(estadoLlano("Cuadra con su regla (7.5 m2)", null)).toBe("Cuadra con su regla (7.5 m2)");
  });
});
