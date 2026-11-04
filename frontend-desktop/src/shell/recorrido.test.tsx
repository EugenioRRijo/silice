import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import {
  RECORRIDO_AUDITAR,
  iniciarRecorrido,
  mostrarColumna,
  ocultarColumna,
  pasoDeRuta,
  recorridoEnCurso,
  suscribirRecorrido,
  terminarRecorrido,
  useColumnaOculta,
  useRecorrido,
} from "./recorrido";

// Spec 2026-10-18 del Inicio, §2.5: tres pasos, uno por pantalla (Inicio, Libro de la empresa, Historial), cada uno
// con «que hacer» y «sabra que termino cuando».
describe("recorrido «Auditar un libro de la empresa»", () => {
  afterEach(() => terminarRecorrido());

  test("tiene tres pasos, uno por pantalla y sin repetir", () => {
    expect(RECORRIDO_AUDITAR.titulo).toBe("Auditar un libro de la empresa");
    // Plan de modulos (MOD-1): el paso 1 vive en el inicio de Auditoria.
    expect(RECORRIDO_AUDITAR.pasos.map((p) => p.pagina)).toEqual(["auditoria", "libros", "historial"]);
    expect(RECORRIDO_AUDITAR.pasos.map((p) => p.titulo)).toEqual([
      "Suba el libro",
      "Lea el resumen y los hallazgos",
      "Compruebe que quedó guardada",
    ]);
  });

  test("cada paso dice que hacer y cuando se sabe que termino, sin jerga interna", () => {
    for (const paso of RECORRIDO_AUDITAR.pasos) {
      expect(paso.queHacer.length).toBeGreaterThan(20);
      expect(paso.sabraQueTermino).toMatch(/^Sabrá que terminó cuando /);
      expect(`${paso.titulo} ${paso.queHacer} ${paso.sabraQueTermino}`).not.toMatch(/UC-|RF-|RNF-|—/);
    }
  });

  // Tanda 2 del pulido F5 (Tarea 8): el visor de «Libro de la empresa» no tiene descarga; el paso dice lo que la pantalla
  // hace: elegir un hallazgo de la lista lleva a su celda marcada.
  test("el paso 2 no pide descargar el libro y dice cómo se ve la celda de un hallazgo", () => {
    const paso = RECORRIDO_AUDITAR.pasos[1];
    expect(paso.pagina).toBe("libros");
    expect(paso.queHacer).not.toMatch(/descarg/i);
    expect(paso.queHacer).toBe(
      "Compare el total del libro con el que recalculó Sílice y revise los hallazgos por severidad, de errores a avisos. Elija un hallazgo de la lista para ver su celda marcada en el libro.",
    );
  });

  test("el paso se deduce de la ruta: cada pantalla del recorrido es su paso y las demas ninguno", () => {
    expect(pasoDeRuta(RECORRIDO_AUDITAR, "/empresa/auditoria")).toBe(0);
    expect(pasoDeRuta(RECORRIDO_AUDITAR, "/inicio")).toBeNull();
    expect(pasoDeRuta(RECORRIDO_AUDITAR, "/libros")).toBe(1);
    expect(pasoDeRuta(RECORRIDO_AUDITAR, "/historial")).toBe(2);
    expect(pasoDeRuta(RECORRIDO_AUDITAR, "/tablero")).toBeNull();
    expect(pasoDeRuta(RECORRIDO_AUDITAR, "/")).toBeNull();
  });
});

describe("recorrido en curso", () => {
  afterEach(() => terminarRecorrido());

  test("empieza sin ninguno, se inicia y se termina", () => {
    expect(recorridoEnCurso()).toBeNull();
    iniciarRecorrido(RECORRIDO_AUDITAR);
    expect(recorridoEnCurso()).toBe(RECORRIDO_AUDITAR);
    terminarRecorrido();
    expect(recorridoEnCurso()).toBeNull();
  });

  test("avisa a quien escucha y deja de avisar al darse de baja", () => {
    const oyente = vi.fn();
    const baja = suscribirRecorrido(oyente);
    iniciarRecorrido(RECORRIDO_AUDITAR);
    expect(oyente).toHaveBeenCalledTimes(1);
    baja();
    terminarRecorrido();
    expect(oyente).toHaveBeenCalledTimes(1);
  });

  test("nada se guarda en el navegador", () => {
    const espia = vi.spyOn(Storage.prototype, "setItem");
    iniciarRecorrido(RECORRIDO_AUDITAR);
    expect(espia).not.toHaveBeenCalled();
    espia.mockRestore();
  });

  test("useRecorrido sigue los cambios", () => {
    const { result } = renderHook(() => useRecorrido());
    expect(result.current).toBeNull();
    act(() => iniciarRecorrido(RECORRIDO_AUDITAR));
    expect(result.current).toBe(RECORRIDO_AUDITAR);
    act(() => terminarRecorrido());
    expect(result.current).toBeNull();
  });
});

describe("columna del recorrido oculta o a la vista", () => {
  afterEach(() => terminarRecorrido());

  test("empieza a la vista, se oculta, se muestra y useColumnaOculta lo sigue", () => {
    const { result } = renderHook(() => useColumnaOculta());
    expect(result.current).toBe(false);
    act(() => ocultarColumna());
    expect(result.current).toBe(true);
    act(() => mostrarColumna());
    expect(result.current).toBe(false);
  });

  test("avisa a quien escucha al cambiar", () => {
    const oyente = vi.fn();
    const baja = suscribirRecorrido(oyente);
    ocultarColumna();
    expect(oyente).toHaveBeenCalledTimes(1);
    baja();
    mostrarColumna();
  });

  test("terminar el recorrido vuelve a mostrar la columna para el siguiente", () => {
    const { result } = renderHook(() => useColumnaOculta());
    iniciarRecorrido(RECORRIDO_AUDITAR);
    act(() => ocultarColumna());
    expect(result.current).toBe(true);
    act(() => terminarRecorrido());
    expect(result.current).toBe(false);
  });

  test("nada se guarda en el navegador", () => {
    const espia = vi.spyOn(Storage.prototype, "setItem");
    ocultarColumna();
    mostrarColumna();
    expect(espia).not.toHaveBeenCalled();
    espia.mockRestore();
  });
});
