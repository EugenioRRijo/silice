import { describe, expect, test } from "vitest";
import { FRASES_DE_RECHAZO } from "../logicaSecciones";
import { accionEnCampo, aperturaPorTecla, rechazoDeLaCelda, textoDeRechazoDeCelda } from "./logicaDeCantidad";

// Lógica pura de la celda de cantidad (lote B1-5, ficha-b1 §1.10 pruebas 5 y 6). Oráculos escritos a mano.

describe("aperturaPorTecla: qué tecla abre la edición de una celda en reposo", () => {
  test("F2 y Enter abren sin cambiar el texto", () => {
    expect(aperturaPorTecla({ key: "F2" })).toEqual({ texto: null });
    expect(aperturaPorTecla({ key: "Enter" })).toEqual({ texto: null });
  });

  test("un carácter imprimible abre y reemplaza el texto por ese carácter, como en Excel", () => {
    expect(aperturaPorTecla({ key: "7" })).toEqual({ texto: "7" });
    expect(aperturaPorTecla({ key: "," })).toEqual({ texto: "," });
    expect(aperturaPorTecla({ key: "-" })).toEqual({ texto: "-" });
    expect(aperturaPorTecla({ key: "A", shiftKey: true })).toEqual({ texto: "A" });
  });

  test("con Ctrl, Alt o Meta no abre nada", () => {
    expect(aperturaPorTecla({ key: "7", ctrlKey: true })).toBeNull();
    expect(aperturaPorTecla({ key: "F2", altKey: true })).toBeNull();
    expect(aperturaPorTecla({ key: "Enter", metaKey: true })).toBeNull();
  });

  test("un evento ya prevenido o una composición de teclas en curso no abren", () => {
    expect(aperturaPorTecla({ key: "7", defaultPrevented: true })).toBeNull();
    expect(aperturaPorTecla({ key: "Enter", isComposing: true })).toBeNull();
    expect(aperturaPorTecla({ key: "ñ", isComposing: true })).toBeNull();
  });

  test("las flechas, Tab, Esc, Inicio y Fin son de la grilla: no abren", () => {
    for (const key of ["ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight", "Tab", "Escape", "Home", "End", "Shift"]) {
      expect(aperturaPorTecla({ key })).toBeNull();
    }
  });
});

describe("accionEnCampo: lo que hacen Enter, Esc y Tab dentro del campo abierto", () => {
  test("Enter confirma y baja; Esc restaura; Tab confirma y sigue", () => {
    expect(accionEnCampo({ key: "Enter" })).toBe("confirmar-y-bajar");
    expect(accionEnCampo({ key: "Escape" })).toBe("restaurar");
    expect(accionEnCampo({ key: "Tab" })).toBe("confirmar-y-seguir");
    expect(accionEnCampo({ key: "Tab", shiftKey: true })).toBe("confirmar-y-seguir");
  });

  test("las flechas, Inicio, Fin y las letras son del campo: no son una acción", () => {
    for (const key of ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End", "1", ",", "x"]) {
      expect(accionEnCampo({ key })).toBeNull();
    }
  });

  test("con modificador, ya prevenido o componiendo no hay acción", () => {
    expect(accionEnCampo({ key: "Enter", ctrlKey: true })).toBeNull();
    expect(accionEnCampo({ key: "Escape", altKey: true })).toBeNull();
    expect(accionEnCampo({ key: "Tab", metaKey: true })).toBeNull();
    expect(accionEnCampo({ key: "Enter", defaultPrevented: true })).toBeNull();
    expect(accionEnCampo({ key: "Enter", isComposing: true })).toBeNull();
    expect(accionEnCampo({ key: "Escape", isComposing: true })).toBeNull();
  });
});

describe("rechazoDeLaCelda: de quién es el error del servidor", () => {
  const rechazo = { tipo: "rechazo" as const, mensaje: "m", ubicacion: 2 };

  test("un rechazo con la fila de esta celda es de esta celda, y se devuelve el mismo objeto", () => {
    expect(rechazoDeLaCelda(rechazo, 2)).toBe(rechazo);
  });

  test("la fila de otra celda, un rechazo sin fila o ningún error no son de esta celda", () => {
    expect(rechazoDeLaCelda(rechazo, 1)).toBeNull();
    expect(rechazoDeLaCelda({ ...rechazo, ubicacion: null }, 2)).toBeNull();
    expect(rechazoDeLaCelda(null, 2)).toBeNull();
  });

  test("un conflicto (409) o cualquier otro fallo no marcan una celda: los dice el aviso de la sección", () => {
    expect(rechazoDeLaCelda({ tipo: "conflicto", mensaje: "El borrador cambió", ubicacion: 2 }, 2)).toBeNull();
    expect(rechazoDeLaCelda({ tipo: "perdido", mensaje: "x", ubicacion: 2 }, 2)).toBeNull();
    expect(rechazoDeLaCelda({ tipo: "otro", mensaje: "x", ubicacion: 2 }, 2)).toBeNull();
  });
});

describe("textoDeRechazoDeCelda: el mensaje del servidor, corto para la celda", () => {
  const FRASE = FRASES_DE_RECHAZO.cantidades;

  test("quita la ubicación («presupuesto, fila N (CÓDIGO): ») y la frase de la clásica", () => {
    const detalle =
      "presupuesto, fila 1 (AF-LLAVE): la cantidad no puede ser negativa; escriba cero o una cantidad positiva";
    expect(textoDeRechazoDeCelda(`${detalle}. ${FRASE}`)).toBe(
      "La cantidad no puede ser negativa; escriba cero o una cantidad positiva.",
    );
  });

  test("quita también el nombre del campo que antepone la regla de las cifras", () => {
    const detalle =
      "presupuesto, fila 2 (AF-SALIDA): cantidad: «2.5» no se entiende como número. Use la coma para los decimales: por ejemplo 2,5. El punto separa los miles: 1.234,56.";
    expect(textoDeRechazoDeCelda(`${detalle} ${FRASE}`)).toBe(
      "«2.5» no se entiende como número. Use la coma para los decimales: por ejemplo 2,5. El punto separa los miles: 1.234,56.",
    );
  });

  test("un mensaje que no trae ubicación ni frase queda tal cual", () => {
    expect(textoDeRechazoDeCelda("El servidor no pudo aplicar el cambio.")).toBe("El servidor no pudo aplicar el cambio.");
  });

  test("si quitar lo anterior no dejara nada, se conserva el mensaje entero", () => {
    expect(textoDeRechazoDeCelda("presupuesto, fila 3 (X-1): ")).toBe("presupuesto, fila 3 (X-1): ");
  });
});
