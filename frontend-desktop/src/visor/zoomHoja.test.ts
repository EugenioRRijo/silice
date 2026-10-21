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
  pasoDeRueda,
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
});
