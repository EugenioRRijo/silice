import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { useGuardado } from "./useGuardado";

// Nota del árbitro de la rama (2026-11-18): si volver a leer el borrador falla tras el 422 «Ese desglose ya está
// guardado.», guardar no rechaza (nadie lo esperaría: el botón llama `void guardar()`) y el aviso sigue a la vista.
const fetchFalso = vi.fn<typeof fetch>();
beforeEach(() => {
  vi.stubGlobal("fetch", fetchFalso);
  fetchFalso.mockReset();
  fetchFalso.mockImplementation(async (ruta) =>
    String(ruta).endsWith("/guardar")
      ? new Response(JSON.stringify({ detalle: "Ese desglose ya está guardado." }), {
          status: 422,
          headers: { "Content-Type": "application/json" },
        })
      : new Response(JSON.stringify({ rev: 1, cambios: [] }), { headers: { "Content-Type": "application/json" } }),
  );
});
afterEach(() => vi.unstubAllGlobals());

test("si releer el borrador falla, guardar no rechaza y el aviso del desglose sigue", async () => {
  const alVaciarseLaCuenta = vi.fn(() => Promise.reject(new Error("sin red")));
  const { result } = renderHook(() =>
    useGuardado({ id: "b1", rev: 1, proyecto: "P", alExpirar: vi.fn(), alGuardada: vi.fn(), alVaciarseLaCuenta }),
  );
  await act(async () => {
    await result.current.guardar();
  });
  expect(alVaciarseLaCuenta).toHaveBeenCalledOnce();
  expect(result.current.error?.clase).toBe("desglose-ya-guardado");
  expect(result.current.enviando).toBe(false);
});
