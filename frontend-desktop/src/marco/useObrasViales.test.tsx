import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ErrorDeApi, pedir } from "../api/cliente";
import { ContextoAplicacion } from "../shell/contexto";
import { sesionDe } from "../shell/obras/datosDePrueba";
import { useObrasViales } from "./useObrasViales";

vi.mock("../api/cliente", async (importarOriginal) => ({
  ...(await importarOriginal<typeof import("../api/cliente")>()),
  pedir: vi.fn(),
}));
const pedirFalso = vi.mocked(pedir);

function envolver(rol: "ana" | "rita") {
  return ({ children }: { children: ReactNode }) => (
    <ContextoAplicacion.Provider value={{ sesion: sesionDe(rol), proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() }}>
      {children}
    </ContextoAplicacion.Provider>
  );
}

describe("useObrasViales", () => {
  beforeEach(() => pedirFalso.mockReset());

  it("da las claves (carpeta|obra) de las obras con tramos de la carpeta abierta", async () => {
    pedirFalso.mockResolvedValue({ obras: [3, 7] });
    const { result } = renderHook(() => useObrasViales("Carpeta Norte.db", "x"), { wrapper: envolver("ana") });
    await waitFor(() => expect([...result.current].sort()).toEqual(["Carpeta Norte.db|3", "Carpeta Norte.db|7"]));
    expect(pedirFalso).toHaveBeenCalledWith("/v1/vial/obras");
  });

  it("la carpeta de la empresa se escribe vacía, como en el resto del marco", async () => {
    pedirFalso.mockResolvedValue({ obras: [1] });
    const { result } = renderHook(() => useObrasViales(null, "x"), { wrapper: envolver("ana") });
    await waitFor(() => expect([...result.current]).toEqual(["|1"]));
  });

  it("vuelve a pedir cuando cambia la clave de refresco (otra sección u otra obra)", async () => {
    pedirFalso.mockResolvedValue({ obras: [] });
    const { rerender } = renderHook(({ k }) => useObrasViales("c.db", k), { wrapper: envolver("ana"), initialProps: { k: "a" } });
    await waitFor(() => expect(pedirFalso).toHaveBeenCalledTimes(1));
    rerender({ k: "b" });
    await waitFor(() => expect(pedirFalso).toHaveBeenCalledTimes(2));
  });

  it("un error no avisa ni rompe: el conjunto queda vacío", async () => {
    pedirFalso.mockRejectedValue(new ErrorDeApi(500, "falló"));
    const { result } = renderHook(() => useObrasViales("c.db", "x"), { wrapper: envolver("ana") });
    await waitFor(() => expect(pedirFalso).toHaveBeenCalled());
    expect(result.current.size).toBe(0);
  });

  it("sin editar_hoja no pide nada", () => {
    const { result } = renderHook(() => useObrasViales("c.db", "x"), { wrapper: envolver("rita") });
    expect(pedirFalso).not.toHaveBeenCalled();
    expect(result.current.size).toBe(0);
  });
});
