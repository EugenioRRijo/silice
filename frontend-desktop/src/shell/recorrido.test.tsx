import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import {
  RECORRIDO_AUDITAR,
  iniciarRecorrido,
  pasoDeRuta,
  recorridoEnCurso,
  suscribirRecorrido,
  terminarRecorrido,
  useRecorrido,
} from "./recorrido";

// Spec 2026-10-18 del Inicio, §2.5: tres pasos, uno por pantalla (Inicio, Libro de la empresa, Historial), cada uno
// con «que hacer» y «sabra que termino cuando».
describe("recorrido «Auditar un libro de la empresa»", () => {
  afterEach(() => terminarRecorrido());

  test("tiene tres pasos, uno por pantalla y sin repetir", () => {
    expect(RECORRIDO_AUDITAR.titulo).toBe("Auditar un libro de la empresa");
    expect(RECORRIDO_AUDITAR.pasos.map((p) => p.pagina)).toEqual(["inicio", "libros", "historial"]);
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

  test("el paso se deduce de la ruta: cada pantalla del recorrido es su paso y las demas ninguno", () => {
    expect(pasoDeRuta(RECORRIDO_AUDITAR, "/inicio")).toBe(0);
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
