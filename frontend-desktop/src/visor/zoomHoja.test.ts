import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import {
  CLAVE_ZOOM_HOJA,
  ZOOM_INICIAL,
  ZOOM_MAXIMO,
  ZOOM_MINIMO,
  ajustarZoom,
  factorDeLetra,
  guardarZoomHoja,
  leerZoomHoja,
  MAX_REINTENTOS_ZOOM,
  debeReaplicarZoom,
  pasoDeRueda,
  puedeSubirZoom,
  razonEfectiva,
} from "./zoomHoja";

describe("zoomHoja (logica pura)", () => {
  beforeEach(() => {
    localStorage.clear();
    delete document.documentElement.dataset.siliceLetra;
  });
  afterEach(() => vi.restoreAllMocks());

  test("el rango es 50 a 300 por 10 y empieza en 100", () => {
    expect([ZOOM_MINIMO, ZOOM_MAXIMO, ZOOM_INICIAL]).toEqual([50, 300, 100]);
  });

  test("ajustarZoom redondea al paso de 10 y respeta los topes", () => {
    expect(ajustarZoom(100)).toBe(100);
    expect(ajustarZoom(104)).toBe(100);
    expect(ajustarZoom(105)).toBe(110);
    expect(ajustarZoom(10)).toBe(50);
    expect(ajustarZoom(999)).toBe(300);
    expect(ajustarZoom(Number.NaN)).toBe(100);
  });

  test("el factor sale del tamano de letra que dejo la raiz: 1, 1,25 y 1,5", () => {
    expect(factorDeLetra()).toBe(1);
    document.documentElement.dataset.siliceLetra = "grande";
    expect(factorDeLetra()).toBe(1.25);
    document.documentElement.dataset.siliceLetra = "muy-grande";
    expect(factorDeLetra()).toBe(1.5);
    document.documentElement.dataset.siliceLetra = "raro";
    expect(factorDeLetra()).toBe(1);
  });

  test("razonEfectiva multiplica el zoom propio por el factor y no pasa de 4 (tope de Univer)", () => {
    expect(razonEfectiva(100, 1)).toBe(1);
    expect(razonEfectiva(100, 1.25)).toBe(1.25);
    expect(razonEfectiva(200, 1.5)).toBe(3);
    expect(razonEfectiva(50, 1.5)).toBe(0.75);
    expect(razonEfectiva(300, 1.25)).toBe(3.75);
    expect(razonEfectiva(300, 1.5)).toBe(4);
  });

  test("sin nada guardado lee 100; un valor valido se lee; uno invalido se ignora", () => {
    expect(leerZoomHoja()).toBe(100);
    localStorage.setItem(CLAVE_ZOOM_HOJA, "150");
    expect(leerZoomHoja()).toBe(150);
    localStorage.setItem(CLAVE_ZOOM_HOJA, "7000");
    expect(leerZoomHoja()).toBe(100);
    localStorage.setItem(CLAVE_ZOOM_HOJA, "abc");
    expect(leerZoomHoja()).toBe(100);
  });

  test("guarda con su propia clave, distinta de la del tamano de letra", () => {
    guardarZoomHoja(120);
    expect(localStorage.getItem(CLAVE_ZOOM_HOJA)).toBe("120");
    expect(CLAVE_ZOOM_HOJA).not.toBe("silice.tamano-letra");
  });

  test("sin almacenamiento (lanza) ni leer ni guardar rompen la hoja", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("bloqueado");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("bloqueado");
    });
    expect(leerZoomHoja()).toBe(100);
    expect(() => guardarZoomHoja(130)).not.toThrow();
  });

  test("pasoDeRueda acumula los gestos pequenos y da un paso por muesca", () => {
    expect(pasoDeRueda(0, -100)).toEqual({ paso: 1, resto: 0 });
    expect(pasoDeRueda(0, 100)).toEqual({ paso: -1, resto: 0 });
    // Pellizco de trackpad: muchos deltas chicos suman un paso.
    let acumulado = 0;
    let pasos = 0;
    for (let i = 0; i < 10; i++) {
      const r = pasoDeRueda(acumulado, -5);
      pasos += r.paso;
      acumulado = r.resto;
    }
    expect(pasos).toBe(1);
    expect(pasoDeRueda(0, 0)).toEqual({ paso: 0, resto: 0 });
  });

  test("pasoDeRueda normaliza por deltaMode: una linea (modo 1) y una pagina (modo 2) ya son un paso", () => {
    // Firefox da deltaY = ±3 lineas por muesca: sin normalizar, 3 no llegaria al umbral.
    expect(pasoDeRueda(0, -3, 1)).toEqual({ paso: 1, resto: 0 });
    expect(pasoDeRueda(0, 1, 1)).toEqual({ paso: -1, resto: 0 });
    expect(pasoDeRueda(0, -1, 2)).toEqual({ paso: 1, resto: 0 });
    // En pixeles (modo 0) no cambia.
    expect(pasoDeRueda(0, -3, 0)).toEqual({ paso: 0, resto: -3 });
  });

  test("puedeSubirZoom: no en el tope propio y no cuando subir no cambiaria lo dibujado (tope de Univer)", () => {
    expect(puedeSubirZoom(100, 1)).toBe(true);
    expect(puedeSubirZoom(300, 1)).toBe(false);
    expect(puedeSubirZoom(250, 1.5)).toBe(true); // 3,75 -> 3,9
    expect(puedeSubirZoom(260, 1.5)).toBe(true); // 3,9 -> 4 (cambia)
    expect(puedeSubirZoom(270, 1.5)).toBe(false); // 4 -> 4: no se veria nada
    expect(puedeSubirZoom(290, 1.5)).toBe(false);
  });
});

describe("debeReaplicarZoom (decision pura del adaptador)", () => {
  test("escala igual a la vigente (con la tolerancia): no reaplica", () => {
    expect(debeReaplicarZoom({ escalaDibujada: 1.25, razonVigente: 1.25, intentos: 0 })).toBe(false);
    expect(debeReaplicarZoom({ escalaDibujada: 1.2504, razonVigente: 1.25, intentos: 0 })).toBe(false);
  });

  test("escala distinta: reaplica mientras queden reintentos", () => {
    expect(debeReaplicarZoom({ escalaDibujada: 1, razonVigente: 2, intentos: 0 })).toBe(true);
    expect(debeReaplicarZoom({ escalaDibujada: 1, razonVigente: 2, intentos: MAX_REINTENTOS_ZOOM - 1 })).toBe(true);
  });

  test("con el tope de reintentos alcanzado no reaplica (no hay bucle a 60 Hz)", () => {
    expect(MAX_REINTENTOS_ZOOM).toBe(3);
    expect(debeReaplicarZoom({ escalaDibujada: 1, razonVigente: 2, intentos: MAX_REINTENTOS_ZOOM })).toBe(false);
  });

  test("sin render (escala indefinida, NaN o infinita) no reaplica", () => {
    expect(debeReaplicarZoom({ escalaDibujada: undefined, razonVigente: 2, intentos: 0 })).toBe(false);
    expect(debeReaplicarZoom({ escalaDibujada: Number.NaN, razonVigente: 2, intentos: 0 })).toBe(false);
    expect(debeReaplicarZoom({ escalaDibujada: Number.POSITIVE_INFINITY, razonVigente: 2, intentos: 0 })).toBe(false);
  });
});
