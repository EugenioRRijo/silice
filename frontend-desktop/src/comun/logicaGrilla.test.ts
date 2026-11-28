import { describe, expect, test } from "vitest";
import { estadoInicialDeGrilla, eventoDesdeTecla, siguiente } from "./logicaGrilla";
import type { EstadoDeGrilla, EventoDeGrilla, PosicionDeCelda } from "./logicaGrilla";

// Oráculos escritos a mano según la ficha de B1 (§1.10 punto 6, lote B1-2a) y la guía `spatial-navigation` de Google.

const ORIGEN: PosicionDeCelda = { fila: 0, columna: 0 };

describe("estadoInicialDeGrilla y contrato de tipos de la unión discriminada", () => {
  test("arranca en modo navegar en (0, 0) por omisión o en la celda indicada", () => {
    expect(estadoInicialDeGrilla()).toEqual({
      modo: "navegar",
      activa: { fila: 0, columna: 0 },
    });
    expect(estadoInicialDeGrilla({ fila: 2, columna: 3 })).toEqual({
      modo: "navegar",
      activa: { fila: 2, columna: 3 },
    });
  });

  test("un estado ilegal no compila en TypeScript", () => {
    const navegarConBorrador: EstadoDeGrilla = {
      modo: "navegar",
      activa: ORIGEN,
      // @ts-expect-error: el modo navegar no admite borrador ni valorOriginal
      borrador: "10",
    };
    // @ts-expect-error: el modo editar exige valorOriginal y borrador
    const editarIncompleto: EstadoDeGrilla = {
      modo: "editar",
      activa: ORIGEN,
    };
    const modoDesconocido: EstadoDeGrilla = {
      // @ts-expect-error: solo existen los modos navegar y editar
      modo: "seleccionar",
      activa: ORIGEN,
    };

    expect([navegarConBorrador, editarIncompleto, modoDesconocido]).toHaveLength(3);
  });
});

describe("flechas en navegación y preservación del desplazamiento nativo en los bordes (spatial-navigation)", () => {
  test("mueve la celda activa en las cuatro direcciones dentro de la grilla y consume el evento", () => {
    const centro = estadoInicialDeGrilla({ fila: 1, columna: 1 });

    const derecha = siguiente(centro, { tipo: "flecha", direccion: "derecha", filas: 3, columnas: 4 });
    expect(derecha).toEqual({
      estado: { modo: "navegar", activa: { fila: 1, columna: 2 } },
      activa: { fila: 1, columna: 2 },
      consumir: true,
      edicion: null,
    });

    const izquierda = siguiente(centro, { tipo: "flecha", direccion: "izquierda", filas: 3, columnas: 4 });
    expect(izquierda).toEqual({
      estado: { modo: "navegar", activa: { fila: 1, columna: 0 } },
      activa: { fila: 1, columna: 0 },
      consumir: true,
      edicion: null,
    });

    const abajo = siguiente(centro, { tipo: "flecha", direccion: "abajo", filas: 3, columnas: 4 });
    expect(abajo).toEqual({
      estado: { modo: "navegar", activa: { fila: 2, columna: 1 } },
      activa: { fila: 2, columna: 1 },
      consumir: true,
      edicion: null,
    });

    const arriba = siguiente(centro, { tipo: "flecha", direccion: "arriba", filas: 3, columnas: 4 });
    expect(arriba).toEqual({
      estado: { modo: "navegar", activa: { fila: 0, columna: 1 } },
      activa: { fila: 0, columna: 1 },
      consumir: true,
      edicion: null,
    });
  });

  test("en cada uno de los cuatro bordes no se mueve y dice «no consumir» (no llamar preventDefault)", () => {
    const bordeSuperior = estadoInicialDeGrilla({ fila: 0, columna: 1 });
    expect(siguiente(bordeSuperior, { tipo: "flecha", direccion: "arriba", filas: 3, columnas: 4 })).toEqual({
      estado: bordeSuperior,
      activa: { fila: 0, columna: 1 },
      consumir: false,
      edicion: null,
    });

    const bordeInferior = estadoInicialDeGrilla({ fila: 2, columna: 1 });
    expect(siguiente(bordeInferior, { tipo: "flecha", direccion: "abajo", filas: 3, columnas: 4 })).toEqual({
      estado: bordeInferior,
      activa: { fila: 2, columna: 1 },
      consumir: false,
      edicion: null,
    });

    const bordeIzquierdo = estadoInicialDeGrilla({ fila: 1, columna: 0 });
    expect(siguiente(bordeIzquierdo, { tipo: "flecha", direccion: "izquierda", filas: 3, columnas: 4 })).toEqual({
      estado: bordeIzquierdo,
      activa: { fila: 1, columna: 0 },
      consumir: false,
      edicion: null,
    });

    const bordeDerecho = estadoInicialDeGrilla({ fila: 1, columna: 3 });
    expect(siguiente(bordeDerecho, { tipo: "flecha", direccion: "derecha", filas: 3, columnas: 4 })).toEqual({
      estado: bordeDerecho,
      activa: { fila: 1, columna: 3 },
      consumir: false,
      edicion: null,
    });
  });

  test("en una grilla de 1×1 o sin celdas no se mueve ni consume ninguna flecha", () => {
    const unica = estadoInicialDeGrilla({ fila: 0, columna: 0 });
    for (const direccion of ["arriba", "abajo", "izquierda", "derecha"] as const) {
      expect(siguiente(unica, { tipo: "flecha", direccion, filas: 1, columnas: 1 })).toEqual({
        estado: unica,
        activa: { fila: 0, columna: 0 },
        consumir: false,
        edicion: null,
      });
      expect(siguiente(unica, { tipo: "flecha", direccion, filas: 0, columnas: 0 })).toEqual({
        estado: unica,
        activa: { fila: 0, columna: 0 },
        consumir: false,
        edicion: null,
      });
    }
  });
});

describe("Inicio y Fin en la fila", () => {
  test("Inicio lleva a la primera columna y Fin a la última cuando hay desplazamiento dentro de la fila", () => {
    const medio = estadoInicialDeGrilla({ fila: 2, columna: 2 });

    expect(siguiente(medio, { tipo: "inicio", columnas: 5 })).toEqual({
      estado: { modo: "navegar", activa: { fila: 2, columna: 0 } },
      activa: { fila: 2, columna: 0 },
      consumir: true,
      edicion: null,
    });

    expect(siguiente(medio, { tipo: "fin", columnas: 5 })).toEqual({
      estado: { modo: "navegar", activa: { fila: 2, columna: 4 } },
      activa: { fila: 2, columna: 4 },
      consumir: true,
      edicion: null,
    });
  });

  test("Inicio en la columna 0 y Fin en la última columna no se mueven ni consumen el evento", () => {
    const primera = estadoInicialDeGrilla({ fila: 2, columna: 0 });
    expect(siguiente(primera, { tipo: "inicio", columnas: 5 })).toEqual({
      estado: primera,
      activa: { fila: 2, columna: 0 },
      consumir: false,
      edicion: null,
    });

    const ultima = estadoInicialDeGrilla({ fila: 2, columna: 4 });
    expect(siguiente(ultima, { tipo: "fin", columnas: 5 })).toEqual({
      estado: ultima,
      activa: { fila: 2, columna: 4 },
      consumir: false,
      edicion: null,
    });

    expect(siguiente(primera, { tipo: "fin", columnas: 0 })).toEqual({
      estado: primera,
      activa: { fila: 2, columna: 0 },
      consumir: false,
      edicion: null,
    });
  });
});

describe("entrar a editar con F2, Enter o un carácter (como en Excel)", () => {
  test("F2 sobre una celda editable pasa a editar con el valor actual y consume el evento", () => {
    const inicial = estadoInicialDeGrilla({ fila: 1, columna: 3 });

    const paso = siguiente(inicial, { tipo: "f2", valorCelda: "12,5" });
    expect(paso).toEqual({
      estado: {
        modo: "editar",
        activa: { fila: 1, columna: 3 },
        valorOriginal: "12,5",
        borrador: "12,5",
      },
      activa: { fila: 1, columna: 3 },
      consumir: true,
      edicion: null,
    });
  });

  test("Enter en modo navegar sobre una celda editable también pasa a editar", () => {
    const inicial = estadoInicialDeGrilla({ fila: 0, columna: 3 });

    const paso = siguiente(inicial, { tipo: "enter", filas: 4, valorCelda: "10" });
    expect(paso).toEqual({
      estado: {
        modo: "editar",
        activa: { fila: 0, columna: 3 },
        valorOriginal: "10",
        borrador: "10",
      },
      activa: { fila: 0, columna: 3 },
      consumir: true,
      edicion: null,
    });
  });

  test("un carácter imprimible en modo navegar empieza a editar reemplazando el borrador y guardando el original", () => {
    const inicial = estadoInicialDeGrilla({ fila: 1, columna: 3 });

    const paso = siguiente(inicial, { tipo: "caracter", caracter: "5", valorCelda: "10" });
    expect(paso).toEqual({
      estado: {
        modo: "editar",
        activa: { fila: 1, columna: 3 },
        valorOriginal: "10",
        borrador: "5",
      },
      activa: { fila: 1, columna: 3 },
      consumir: true,
      edicion: null,
    });
  });

  test("sobre una celda de solo lectura (valorCelda null), F2, Enter y un carácter no editan ni consumen", () => {
    const soloLectura = estadoInicialDeGrilla({ fila: 1, columna: 0 });

    expect(siguiente(soloLectura, { tipo: "f2", valorCelda: null })).toEqual({
      estado: soloLectura,
      activa: { fila: 1, columna: 0 },
      consumir: false,
      edicion: null,
    });
    expect(siguiente(soloLectura, { tipo: "enter", filas: 4, valorCelda: null })).toEqual({
      estado: soloLectura,
      activa: { fila: 1, columna: 0 },
      consumir: false,
      edicion: null,
    });
    expect(siguiente(soloLectura, { tipo: "caracter", caracter: "j", valorCelda: null })).toEqual({
      estado: soloLectura,
      activa: { fila: 1, columna: 0 },
      consumir: false,
      edicion: null,
    });
  });

  test("un texto vacío, de control o de varios caracteres no inicia edición como carácter", () => {
    const inicial = estadoInicialDeGrilla({ fila: 0, columna: 3 });

    for (const caracter of ["", "F2", "\n", "\t"]) {
      expect(siguiente(inicial, { tipo: "caracter", caracter, valorCelda: "10" })).toEqual({
        estado: inicial,
        activa: { fila: 0, columna: 3 },
        consumir: false,
        edicion: null,
      });
    }
  });
});

describe("comportamiento durante la edición: flechas en el campo, Esc restaura y Enter confirma y baja", () => {
  test("mientras se edita, las flechas, Inicio, Fin y F2 no mueven de celda ni consumen el evento", () => {
    const editando: EstadoDeGrilla = {
      modo: "editar",
      activa: { fila: 1, columna: 3 },
      valorOriginal: "10",
      borrador: "12,5",
    };

    const eventos: EventoDeGrilla[] = [
      { tipo: "flecha", direccion: "izquierda", filas: 4, columnas: 7 },
      { tipo: "flecha", direccion: "derecha", filas: 4, columnas: 7 },
      { tipo: "flecha", direccion: "arriba", filas: 4, columnas: 7 },
      { tipo: "flecha", direccion: "abajo", filas: 4, columnas: 7 },
      { tipo: "inicio", columnas: 7 },
      { tipo: "fin", columnas: 7 },
      { tipo: "f2", valorCelda: "10" },
    ];

    for (const evento of eventos) {
      expect(siguiente(editando, evento)).toEqual({
        estado: editando,
        activa: { fila: 1, columna: 3 },
        consumir: false,
        edicion: null,
      });
    }
  });

  test("cambiar actualiza el borrador sin perder el valorOriginal ni abrir edición si ya se navegaba", () => {
    const inicial = estadoInicialDeGrilla({ fila: 1, columna: 3 });
    expect(siguiente(inicial, { tipo: "cambiar", valor: "99" })).toEqual({
      estado: inicial,
      activa: { fila: 1, columna: 3 },
      consumir: false,
      edicion: null,
    });

    const editando = siguiente(inicial, { tipo: "f2", valorCelda: "10" }).estado;
    const cambiado = siguiente(editando, { tipo: "cambiar", valor: "50,25" });
    expect(cambiado).toEqual({
      estado: {
        modo: "editar",
        activa: { fila: 1, columna: 3 },
        valorOriginal: "10",
        borrador: "50,25",
      },
      activa: { fila: 1, columna: 3 },
      consumir: false,
      edicion: null,
    });
  });

  test("un carácter en edición se agrega al borrador sin consumir el evento nativo del campo", () => {
    const inicial = estadoInicialDeGrilla({ fila: 0, columna: 3 });
    const conCinco = siguiente(inicial, { tipo: "caracter", caracter: "5", valorCelda: "10" }).estado;
    const conCincuenta = siguiente(conCinco, { tipo: "caracter", caracter: "0", valorCelda: "10" });

    expect(conCincuenta).toEqual({
      estado: {
        modo: "editar",
        activa: { fila: 0, columna: 3 },
        valorOriginal: "10",
        borrador: "50",
      },
      activa: { fila: 0, columna: 3 },
      consumir: false,
      edicion: null,
    });
  });

  test("Esc en edición devuelve el valor original, vuelve a navegar en la misma celda y consume el evento", () => {
    const inicial = estadoInicialDeGrilla({ fila: 1, columna: 3 });
    const enEdicion = siguiente(inicial, { tipo: "f2", valorCelda: "10,00" }).estado;
    const modificado = siguiente(enEdicion, { tipo: "cambiar", valor: "999,99" }).estado;

    const restaurado = siguiente(modificado, { tipo: "escape" });
    expect(restaurado).toEqual({
      estado: { modo: "navegar", activa: { fila: 1, columna: 3 } },
      activa: { fila: 1, columna: 3 },
      consumir: true,
      edicion: {
        tipo: "restaurar",
        celda: { fila: 1, columna: 3 },
        valor: "10,00",
      },
    });
  });

  test("Esc tras empezar a editar con un carácter devuelve el valor que tenía la celda antes de teclear", () => {
    const inicial = estadoInicialDeGrilla({ fila: 2, columna: 3 });
    const conCaracter = siguiente(inicial, { tipo: "caracter", caracter: "7", valorCelda: "24,5" }).estado;

    expect(siguiente(conCaracter, { tipo: "escape" })).toEqual({
      estado: { modo: "navegar", activa: { fila: 2, columna: 3 } },
      activa: { fila: 2, columna: 3 },
      consumir: true,
      edicion: {
        tipo: "restaurar",
        celda: { fila: 2, columna: 3 },
        valor: "24,5",
      },
    });
  });

  test("Esc en modo navegar no consume el evento para permitir cerrar un inspector o menú abierto", () => {
    const inicial = estadoInicialDeGrilla({ fila: 1, columna: 3 });
    expect(siguiente(inicial, { tipo: "escape" })).toEqual({
      estado: inicial,
      activa: { fila: 1, columna: 3 },
      consumir: false,
      edicion: null,
    });
  });

  test("Enter en edición confirma el borrador, pasa a navegar, baja una fila y consume el evento", () => {
    const inicial = estadoInicialDeGrilla({ fila: 1, columna: 3 });
    const conCinco = siguiente(inicial, { tipo: "caracter", caracter: "5", valorCelda: "10" }).estado;
    const conCincuenta = siguiente(conCinco, { tipo: "caracter", caracter: "0", valorCelda: "10" }).estado;

    const confirmado = siguiente(conCincuenta, { tipo: "enter", filas: 4 });
    expect(confirmado).toEqual({
      estado: { modo: "navegar", activa: { fila: 2, columna: 3 } },
      activa: { fila: 2, columna: 3 },
      consumir: true,
      edicion: {
        tipo: "confirmar",
        celda: { fila: 1, columna: 3 },
        valor: "50",
      },
    });
  });

  test("Enter en edición sobre la última fila confirma el borrador sin salirse del borde inferior", () => {
    const ultimaFila: EstadoDeGrilla = {
      modo: "editar",
      activa: { fila: 3, columna: 3 },
      valorOriginal: "10",
      borrador: "18,5",
    };

    expect(siguiente(ultimaFila, { tipo: "enter", filas: 4 })).toEqual({
      estado: { modo: "navegar", activa: { fila: 3, columna: 3 } },
      activa: { fila: 3, columna: 3 },
      consumir: true,
      edicion: {
        tipo: "confirmar",
        celda: { fila: 3, columna: 3 },
        valor: "18,5",
      },
    });
  });

  test("mientras el método de entrada (IME) compone texto, Enter y Esc no cierran la edición", () => {
    const editando: EstadoDeGrilla = {
      modo: "editar",
      activa: { fila: 1, columna: 3 },
      valorOriginal: "10",
      borrador: "12",
    };

    expect(siguiente(editando, { tipo: "enter", filas: 4, componiendo: true })).toEqual({
      estado: editando,
      activa: { fila: 1, columna: 3 },
      consumir: false,
      edicion: null,
    });
    expect(siguiente(editando, { tipo: "escape", componiendo: true })).toEqual({
      estado: editando,
      activa: { fila: 1, columna: 3 },
      consumir: false,
      edicion: null,
    });
  });
});

describe("Tab y una sola parada de tabulación (spatial-navigation)", () => {
  test("en modo navegar, Tab y Shift+Tab mantienen la celda activa y no consumen el evento", () => {
    const inicial = estadoInicialDeGrilla({ fila: 1, columna: 3 });

    expect(siguiente(inicial, { tipo: "tab" })).toEqual({
      estado: inicial,
      activa: { fila: 1, columna: 3 },
      consumir: false,
      edicion: null,
    });
    expect(siguiente(inicial, { tipo: "tab", conShift: true })).toEqual({
      estado: inicial,
      activa: { fila: 1, columna: 3 },
      consumir: false,
      edicion: null,
    });
  });

  test("en modo editar, Tab y Shift+Tab confirman el borrador y salen sin consumir Tab para pasar al siguiente control", () => {
    const editando: EstadoDeGrilla = {
      modo: "editar",
      activa: { fila: 1, columna: 3 },
      valorOriginal: "10",
      borrador: "42,5",
    };

    expect(siguiente(editando, { tipo: "tab" })).toEqual({
      estado: { modo: "navegar", activa: { fila: 1, columna: 3 } },
      activa: { fila: 1, columna: 3 },
      consumir: false,
      edicion: {
        tipo: "confirmar",
        celda: { fila: 1, columna: 3 },
        valor: "42,5",
      },
    });

    expect(siguiente(editando, { tipo: "tab", conShift: true })).toEqual({
      estado: { modo: "navegar", activa: { fila: 1, columna: 3 } },
      activa: { fila: 1, columna: 3 },
      consumir: false,
      edicion: {
        tipo: "confirmar",
        celda: { fila: 1, columna: 3 },
        valor: "42,5",
      },
    });
  });
});

describe("activar celda por clic o salto externo", () => {
  test("mueve la celda activa en navegación y confirma la edición previa si se activa otra celda", () => {
    const inicial = estadoInicialDeGrilla({ fila: 0, columna: 0 });
    expect(siguiente(inicial, { tipo: "activar", celda: { fila: 2, columna: 3 }, filas: 4, columnas: 7 })).toEqual({
      estado: { modo: "navegar", activa: { fila: 2, columna: 3 } },
      activa: { fila: 2, columna: 3 },
      consumir: false,
      edicion: null,
    });

    const editando: EstadoDeGrilla = {
      modo: "editar",
      activa: { fila: 1, columna: 3 },
      valorOriginal: "10",
      borrador: "33",
    };

    // Hacer clic en la misma celda que ya se edita conserva la edición abierta.
    expect(siguiente(editando, { tipo: "activar", celda: { fila: 1, columna: 3 }, filas: 4, columnas: 7 })).toEqual({
      estado: editando,
      activa: { fila: 1, columna: 3 },
      consumir: false,
      edicion: null,
    });

    // Activar otra celda confirma el borrador de la anterior y enfoca la nueva.
    expect(siguiente(editando, { tipo: "activar", celda: { fila: 0, columna: 1 }, filas: 4, columnas: 7 })).toEqual({
      estado: { modo: "navegar", activa: { fila: 0, columna: 1 } },
      activa: { fila: 0, columna: 1 },
      consumir: false,
      edicion: {
        tipo: "confirmar",
        celda: { fila: 1, columna: 3 },
        valor: "33",
      },
    });

    // Una coordenada fuera de rango no altera el estado.
    expect(siguiente(inicial, { tipo: "activar", celda: { fila: 9, columna: 0 }, filas: 4, columnas: 7 })).toEqual({
      estado: inicial,
      activa: { fila: 0, columna: 0 },
      consumir: false,
      edicion: null,
    });
  });
});

describe("modificadores, defaultPrevented y traducción pura desde teclado (spatial-navigation)", () => {
  test("no intercepta eventos con modificador ni ya prevenidos", () => {
    const centro = estadoInicialDeGrilla({ fila: 1, columna: 1 });
    expect(siguiente(centro, { tipo: "flecha", direccion: "abajo", filas: 3, columnas: 4, conModificador: true })).toEqual({
      estado: centro,
      activa: { fila: 1, columna: 1 },
      consumir: false,
      edicion: null,
    });
    expect(siguiente(centro, { tipo: "f2", valorCelda: "10", yaPrevenido: true })).toEqual({
      estado: centro,
      activa: { fila: 1, columna: 1 },
      consumir: false,
      edicion: null,
    });
  });

  test("eventoDesdeTecla traduce las teclas de la grilla y descarta Ctrl, Alt, Meta y defaultPrevented", () => {
    const contexto = { filas: 4, columnas: 7, valorCelda: "10" };

    expect(eventoDesdeTecla({ key: "ArrowUp" }, contexto)).toEqual({
      tipo: "flecha",
      direccion: "arriba",
      filas: 4,
      columnas: 7,
    });
    expect(eventoDesdeTecla({ key: "ArrowDown" }, contexto)).toEqual({
      tipo: "flecha",
      direccion: "abajo",
      filas: 4,
      columnas: 7,
    });
    expect(eventoDesdeTecla({ key: "ArrowLeft" }, contexto)).toEqual({
      tipo: "flecha",
      direccion: "izquierda",
      filas: 4,
      columnas: 7,
    });
    expect(eventoDesdeTecla({ key: "ArrowRight" }, contexto)).toEqual({
      tipo: "flecha",
      direccion: "derecha",
      filas: 4,
      columnas: 7,
    });
    expect(eventoDesdeTecla({ key: "Home" }, contexto)).toEqual({ tipo: "inicio", columnas: 7 });
    expect(eventoDesdeTecla({ key: "End" }, contexto)).toEqual({ tipo: "fin", columnas: 7 });
    expect(eventoDesdeTecla({ key: "F2" }, contexto)).toEqual({ tipo: "f2", valorCelda: "10" });
    expect(eventoDesdeTecla({ key: "Enter", isComposing: false }, contexto)).toEqual({
      tipo: "enter",
      filas: 4,
      valorCelda: "10",
      componiendo: false,
    });
    expect(eventoDesdeTecla({ key: "Escape", isComposing: true }, contexto)).toEqual({
      tipo: "escape",
      componiendo: true,
    });
    expect(eventoDesdeTecla({ key: "Tab", shiftKey: true }, contexto)).toEqual({
      tipo: "tab",
      conShift: true,
    });
    // Carácter con Shift (por ejemplo una letra mayúscula) sí es escritura normal, sin Ctrl/Alt/Meta.
    expect(eventoDesdeTecla({ key: "A", shiftKey: true }, contexto)).toEqual({
      tipo: "caracter",
      caracter: "A",
      valorCelda: "10",
      componiendo: false,
    });

    // Con Ctrl, Alt, Meta, Shift en navegación espacial o defaultPrevented no se intercepta nada.
    expect(eventoDesdeTecla({ key: "z", ctrlKey: true }, contexto)).toBeNull();
    expect(eventoDesdeTecla({ key: "ArrowLeft", altKey: true }, contexto)).toBeNull();
    expect(eventoDesdeTecla({ key: "Home", metaKey: true }, contexto)).toBeNull();
    expect(eventoDesdeTecla({ key: "ArrowDown", shiftKey: true }, contexto)).toBeNull();
    expect(eventoDesdeTecla({ key: "Home", shiftKey: true }, contexto)).toBeNull();
    expect(eventoDesdeTecla({ key: "End", shiftKey: true }, contexto)).toBeNull();
    expect(eventoDesdeTecla({ key: "F2", shiftKey: true }, contexto)).toBeNull();
    expect(eventoDesdeTecla({ key: "Enter", shiftKey: true }, contexto)).toBeNull();
    expect(eventoDesdeTecla({ key: "ArrowDown", defaultPrevented: true }, contexto)).toBeNull();
    expect(eventoDesdeTecla({ key: "Backspace" }, contexto)).toBeNull();
  });
});
