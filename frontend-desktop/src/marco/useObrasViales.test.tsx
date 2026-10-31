import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ContextoAplicacion } from "../shell/contexto";
import { sesionDe } from "../shell/obras/datosDePrueba";
import { useObrasViales } from "./useObrasViales";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

function envolver(rol: "ana" | "rita") {
  return ({ children }: { children: ReactNode }) => (
    <ContextoAplicacion.Provider value={{ sesion: sesionDe(rol), proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() }}>
      {children}
    </ContextoAplicacion.Provider>
  );
}

describe("useObrasViales", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  beforeEach(() => {
    fetchFalso.mockReset();
    vi.stubGlobal("fetch", fetchFalso);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("da las claves (carpeta|obra) de las obras con tramos de la carpeta abierta", async () => {
    fetchFalso.mockImplementation(async () => json({ obras: [3, 7] }));
    const { result } = renderHook(() => useObrasViales("Carpeta Norte.db", "x"), { wrapper: envolver("ana") });
    await waitFor(() => expect([...result.current].sort()).toEqual(["Carpeta Norte.db|3", "Carpeta Norte.db|7"]));
    expect(fetchFalso.mock.calls.map((c) => String(c[0]))).toEqual(["/v1/vial/obras"]);
  });

  it("la carpeta de la empresa se escribe vacía, como en el resto del marco", async () => {
    fetchFalso.mockImplementation(async () => json({ obras: [1] }));
    const { result } = renderHook(() => useObrasViales(null, "x"), { wrapper: envolver("ana") });
    await waitFor(() => expect([...result.current]).toEqual(["|1"]));
  });

  it("vuelve a pedir cuando cambia la clave de refresco (otra sección u otra obra)", async () => {
    fetchFalso.mockImplementation(async () => json({ obras: [] }));
    const { rerender } = renderHook(({ k }) => useObrasViales("c.db", k), { wrapper: envolver("ana"), initialProps: { k: "a" } });
    await waitFor(() => expect(fetchFalso).toHaveBeenCalledTimes(1));
    rerender({ k: "b" });
    await waitFor(() => expect(fetchFalso).toHaveBeenCalledTimes(2));
  });

  it("un error del servidor no avisa ni rompe: el conjunto queda vacío", async () => {
    fetchFalso.mockImplementation(async () => json({ detalle: "falló" }, 500));
    const { result } = renderHook(() => useObrasViales("c.db", "x"), { wrapper: envolver("ana") });
    await waitFor(() => expect(fetchFalso).toHaveBeenCalled());
    await new Promise((resolver) => setTimeout(resolver, 10));
    expect(result.current.size).toBe(0);
  });

  it("sin editar_hoja no pide nada", () => {
    const { result } = renderHook(() => useObrasViales("c.db", "x"), { wrapper: envolver("rita") });
    expect(fetchFalso).not.toHaveBeenCalled();
    expect(result.current.size).toBe(0);
  });
});
