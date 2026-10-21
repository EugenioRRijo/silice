import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import {
  CLAVE_TAMANO_LETRA,
  TAMANOS_DE_LETRA,
  aplicarTamanoLetra,
  guardarTamanoLetra,
  leerTamanoLetra,
} from "./preferenciaDeLetra";

// Presbicia en la oficina (Eugenio, 2026-10-21): tres tamaños de letra que se recuerdan en el navegador. El almacenamiento
// puede faltar o fallar (ventana privada, datos bloqueados): la interfaz funciona igual, con el tamaño normal.
describe("tamaño de letra", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("style");
    document.documentElement.removeAttribute("data-silice-letra");
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("hay tres tamaños: Normal 100 %, Grande 125 % y Muy grande 150 %", () => {
    expect(TAMANOS_DE_LETRA.map((t) => [t.valor, t.rotulo, t.escala])).toEqual([
      ["normal", "Normal", 1],
      ["grande", "Grande", 1.25],
      ["muy-grande", "Muy grande", 1.5],
    ]);
  });

  test("sin nada guardado el tamaño es normal", () => {
    expect(leerTamanoLetra()).toBe("normal");
  });

  test("lee lo guardado", () => {
    localStorage.setItem(CLAVE_TAMANO_LETRA, "muy-grande");
    expect(leerTamanoLetra()).toBe("muy-grande");
  });

  test.each(["enorme", "", "1.5", "NORMAL", "grande "])("un valor guardado que no es un tamaño (%j) se ignora", (malo) => {
    localStorage.setItem(CLAVE_TAMANO_LETRA, malo);
    expect(leerTamanoLetra()).toBe("normal");
  });

  test("si leer el almacenamiento lanza, el tamaño es normal y no se propaga el error", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    expect(leerTamanoLetra()).toBe("normal");
  });

  test("guardar escribe la clave y, si el almacenamiento lanza, no propaga el error", () => {
    guardarTamanoLetra("grande");
    expect(localStorage.getItem(CLAVE_TAMANO_LETRA)).toBe("grande");
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("lleno", "QuotaExceededError");
    });
    expect(() => guardarTamanoLetra("muy-grande")).not.toThrow();
  });

  test("aplicar fija la variable CSS de la raíz y el atributo de la escala", () => {
    aplicarTamanoLetra("grande");
    expect(document.documentElement.style.getPropertyValue("--silice-escala-letra")).toBe("1.25");
    expect(document.documentElement.dataset.siliceLetra).toBe("grande");
    aplicarTamanoLetra("normal");
    expect(document.documentElement.style.getPropertyValue("--silice-escala-letra")).toBe("1");
    expect(document.documentElement.dataset.siliceLetra).toBe("normal");
  });

  test("arrancar aplica lo guardado y no escribe nada si la persona no ha elegido", () => {
    localStorage.setItem(CLAVE_TAMANO_LETRA, "muy-grande");
    aplicarTamanoLetra(leerTamanoLetra());
    expect(document.documentElement.style.getPropertyValue("--silice-escala-letra")).toBe("1.5");
    localStorage.clear();
    aplicarTamanoLetra(leerTamanoLetra());
    expect(localStorage.length).toBe(0);
  });
});
