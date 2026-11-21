import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { leerModulos } from "../api/modulos";
import type { ModulosRespuesta } from "../api/modulos";
import { useModulos } from "./useModulos";

vi.mock("../api/modulos", () => ({ leerModulos: vi.fn() }));
const leerFalso = vi.mocked(leerModulos);

function modulo(clave: string, activo: boolean) {
  return { clave, nombre: clave, activo, cambiado_por: null, cambiado_el: null };
}

afterEach(() => leerFalso.mockReset());

// Una pantalla que solo se monta con el módulo encendido (Series del riesgo vial) necesita distinguir «todavía no se sabe»
// de «ninguno está apagado»: con la lectura en vuelo, `apagados` vacío no debe leerse como «todo encendido».
describe("useModulos", () => {
  test("mientras la lectura no ha vuelto dice que todavía no se leyó", async () => {
    let contestar: (r: ModulosRespuesta) => void = () => undefined;
    leerFalso.mockReturnValue(new Promise<ModulosRespuesta>((resolver) => (contestar = resolver)));
    const { result } = renderHook(() => useModulos());
    expect(result.current.leidos).toBe(false);
    expect(result.current.apagados).toEqual([]);
    await act(async () => contestar({ modulos: [modulo("riesgo", false), modulo("vial", true)] }));
    expect(result.current.leidos).toBe(true);
    expect(result.current.apagados).toEqual(["riesgo"]);
  });

  test("si la lectura falla no se esconde nada y se da por leída", async () => {
    leerFalso.mockRejectedValue(new Error("sin red"));
    const { result } = renderHook(() => useModulos());
    await waitFor(() => expect(result.current.leidos).toBe(true));
    expect(result.current.apagados).toEqual([]);
  });

  test("al recargar conserva lo leído hasta que llegue la respuesta nueva", async () => {
    leerFalso.mockResolvedValueOnce({ modulos: [modulo("riesgo", false)] });
    const { result } = renderHook(() => useModulos());
    await waitFor(() => expect(result.current.apagados).toEqual(["riesgo"]));
    let contestar: (r: ModulosRespuesta) => void = () => undefined;
    leerFalso.mockReturnValueOnce(new Promise<ModulosRespuesta>((resolver) => (contestar = resolver)));
    act(() => result.current.recargar());
    expect(result.current.leidos).toBe(true);
    expect(result.current.apagados).toEqual(["riesgo"]);
    await act(async () => contestar({ modulos: [] }));
    expect(result.current.apagados).toEqual([]);
  });
});
