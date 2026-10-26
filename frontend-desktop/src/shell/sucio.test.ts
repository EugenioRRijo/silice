import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import { formulariosSucios, olvidarFormularios, useFormularioSucio } from "./sucio";

afterEach(() => olvidarFormularios());

describe("formularios con cambios sin guardar", () => {
  test("al empezar no hay ninguno", () => {
    expect(formulariosSucios()).toEqual([]);
  });

  test("un formulario limpio no se registra; al ensuciarse si, y al limpiarse sale", () => {
    const { rerender } = renderHook(({ sucio }) => useFormularioSucio("componer", sucio), { initialProps: { sucio: false } });
    expect(formulariosSucios()).toEqual([]);
    rerender({ sucio: true });
    expect(formulariosSucios()).toEqual(["componer"]);
    rerender({ sucio: false });
    expect(formulariosSucios()).toEqual([]);
  });

  test("se desregistra al desmontar la pantalla", () => {
    const { unmount } = renderHook(() => useFormularioSucio("componer", true));
    expect(formulariosSucios()).toEqual(["componer"]);
    unmount();
    expect(formulariosSucios()).toEqual([]);
  });

  test("conserva el orden de registro y no repite una pantalla con dos formularios sucios", () => {
    renderHook(() => useFormularioSucio("hoja", true));
    renderHook(() => useFormularioSucio("componer", true));
    const segundo = renderHook(() => useFormularioSucio("hoja", true));
    expect(formulariosSucios()).toEqual(["hoja", "componer"]);
    segundo.unmount();
    // El primer formulario de la Hoja sigue sucio.
    expect(formulariosSucios()).toEqual(["hoja", "componer"]);
  });

  test("olvidar los quita todos (Salir y descartar)", () => {
    const { unmount } = renderHook(() => useFormularioSucio("componer", true));
    olvidarFormularios();
    expect(formulariosSucios()).toEqual([]);
    // Desmontar despues de olvidar no falla ni deja rastro.
    unmount();
    expect(formulariosSucios()).toEqual([]);
  });
});
