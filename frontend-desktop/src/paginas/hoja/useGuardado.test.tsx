import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import type { ReactNode } from "react";
import { ProveedorDeNotificaciones, useNotificaciones } from "../../comun/notificaciones/ProveedorDeNotificaciones";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import type { ObraFilaRespuesta } from "../../api/tipos";
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

// T4 (mutantes UG2 y UG3): la confirmación de «versión guardada» dice la obra por su nombre cuando la ficha ya llegó, no por el
// código con que se guarda, y solo con una versión nueva.
test("al guardar con la obra abierta, la notificación lleva el nombre de la obra y la versión nueva", async () => {
  fetchFalso.mockImplementation(async () =>
    new Response(JSON.stringify({ codigo: "003", proyecto: "P", cambios: 2, total: { texto: "1.00", exacto: "1" }, primera: false, mensaje: "x" }), {
      headers: { "Content-Type": "application/json" },
    }),
  );
  const obra = { codigo: "3", nombre: "Vialidad Tramo 3", etapa: "en_elaboracion", etapa_texto: "En elaboración" } as ObraFilaRespuesta;
  const envoltorio = ({ children }: { children: ReactNode }) => (
    <ProveedorDeNotificaciones>
      <ContextoDeLaObra.Provider value={{ carpeta: null, obraId: 3, ficha: { estado: "lista", obra }, recargarFicha: vi.fn() }}>
        {children}
      </ContextoDeLaObra.Provider>
    </ProveedorDeNotificaciones>
  );
  const { result } = renderHook(
    () => ({
      guardado: useGuardado({ id: "b1", rev: 1, proyecto: "P", alExpirar: vi.fn(), alGuardada: vi.fn() }),
      avisos: useNotificaciones(),
    }),
    { wrapper: envoltorio },
  );
  await act(async () => {
    await result.current.guardado.guardar();
  });
  expect(result.current.avisos.notificaciones).toHaveLength(1);
  expect(result.current.avisos.notificaciones[0]).toMatchObject({
    gravedad: "listo",
    titulo: "Versión 003 guardada",
    detalle: "Vialidad Tramo 3",
  });
});
