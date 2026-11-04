import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ErrorDeApi, pedir } from "../api/cliente";
import { ContextoAplicacion } from "../shell/contexto";
import type { Aplicacion } from "../shell/contexto";
import { useFichaDeLaObra } from "./useFichaDeLaObra";

vi.mock("../api/cliente", async (importarOriginal) => ({
  ...(await importarOriginal<typeof import("../api/cliente")>()),
  pedir: vi.fn(),
}));
const pedirFalso = vi.mocked(pedir);

// Obras ficticias; los textos de la etapa están escritos a mano, como los daría el servidor.
const RESUMEN = {
  obras: [
    { codigo: "3", nombre: "Galpón Norte", etapa: "en_aprobacion", etapa_texto: "En aprobación" },
    { codigo: "4", nombre: "Puente Sur", etapa: "atrasada", etapa_texto: "Atrasada" },
  ],
};

const alExpirar = vi.fn();
const aplicacion = { alExpirar } as unknown as Aplicacion;
const envoltura = ({ children }: { children: ReactNode }) => (
  <ContextoAplicacion.Provider value={aplicacion}>{children}</ContextoAplicacion.Provider>
);

describe("useFichaDeLaObra", () => {
  afterEach(() => {
    pedirFalso.mockReset();
    alExpirar.mockReset();
  });

  it("arranca cargando y deja la fila de la obra pedida", async () => {
    pedirFalso.mockResolvedValue(RESUMEN);
    const { result } = renderHook(() => useFichaDeLaObra(4, null), { wrapper: envoltura });
    expect(result.current.estado).toBe("cargando");
    await waitFor(() => expect(result.current.estado).toBe("lista"));
    expect(result.current).toMatchObject({ estado: "lista", obra: { nombre: "Puente Sur", etapa_texto: "Atrasada" } });
    expect(pedirFalso).toHaveBeenCalledTimes(1);
    expect(pedirFalso.mock.calls[0]?.[0]).toBe("/v1/obras/resumen");
  });

  it("un 403, un error o una fila que falta dan sin_dato", async () => {
    pedirFalso.mockRejectedValueOnce(new ErrorDeApi(403, "No puede"));
    const a = renderHook(() => useFichaDeLaObra(3, null), { wrapper: envoltura });
    await waitFor(() => expect(a.result.current.estado).toBe("sin_dato"));

    pedirFalso.mockRejectedValueOnce(new ErrorDeApi(500, "Falló"));
    const b = renderHook(() => useFichaDeLaObra(3, null), { wrapper: envoltura });
    await waitFor(() => expect(b.result.current.estado).toBe("sin_dato"));

    pedirFalso.mockResolvedValueOnce(RESUMEN);
    const c = renderHook(() => useFichaDeLaObra(99, null), { wrapper: envoltura });
    await waitFor(() => expect(c.result.current.estado).toBe("sin_dato"));
    expect(alExpirar).not.toHaveBeenCalled();
  });

  it("una fila sin el texto de la etapa no sirve: sin_dato", async () => {
    pedirFalso.mockResolvedValue({ obras: [{ codigo: "3", nombre: "Galpón Norte" }] });
    const { result } = renderHook(() => useFichaDeLaObra(3, null), { wrapper: envoltura });
    await waitFor(() => expect(result.current.estado).toBe("sin_dato"));
  });

  it("un 401 llama a alExpirar", async () => {
    pedirFalso.mockRejectedValue(new ErrorDeApi(401, "Venció"));
    renderHook(() => useFichaDeLaObra(3, null), { wrapper: envoltura });
    await waitFor(() => expect(alExpirar).toHaveBeenCalledTimes(1));
  });

  it("no repite la lectura al volver a pintar; sí al cambiar de obra o de carpeta, y al recargar", async () => {
    pedirFalso.mockResolvedValue(RESUMEN);
    const { result, rerender } = renderHook(({ obra, carpeta }) => useFichaDeLaObra(obra, carpeta), {
      wrapper: envoltura,
      initialProps: { obra: 3, carpeta: null as string | null },
    });
    await waitFor(() => expect(result.current.estado).toBe("lista"));
    rerender({ obra: 3, carpeta: null });
    expect(pedirFalso).toHaveBeenCalledTimes(1);

    rerender({ obra: 4, carpeta: null });
    // Mientras llega la de la obra nueva no se enseña la ficha de la anterior.
    expect(result.current.estado).toBe("cargando");
    await waitFor(() => expect(result.current.estado).toBe("lista"));
    expect(pedirFalso).toHaveBeenCalledTimes(2);

    rerender({ obra: 4, carpeta: "Carpeta Norte.db" });
    await waitFor(() => expect(pedirFalso).toHaveBeenCalledTimes(3));
    await waitFor(() => expect(result.current.estado).toBe("lista"));

    act(() => result.current.recargar());
    await waitFor(() => expect(pedirFalso).toHaveBeenCalledTimes(4));
  });
});
