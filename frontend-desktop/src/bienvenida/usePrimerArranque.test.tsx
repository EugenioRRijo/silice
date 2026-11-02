import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { usePrimerArranque } from "./usePrimerArranque";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const fetchFalso = vi.fn<typeof fetch>();
const estado = { sin_cuentas: true, archivo_presente: true, modo: "producto", politica: { minimo: 10, maximo: 128 } };

beforeEach(() => {
  vi.stubGlobal("fetch", fetchFalso);
  fetchFalso.mockReset();
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe("usePrimerArranque (F1)", () => {
  test("pide GET /v1/primer-arranque y dice sin_cuentas con lo que contesta la API", async () => {
    fetchFalso.mockResolvedValue(json(estado));
    const { result } = renderHook(() => usePrimerArranque(true));
    expect(result.current.tipo).toBe("cargando");
    await waitFor(() => expect(result.current.tipo).toBe("sin_cuentas"));
    expect(fetchFalso).toHaveBeenCalledTimes(1);
    expect(String(fetchFalso.mock.calls[0][0])).toBe("/v1/primer-arranque");
    expect(fetchFalso.mock.calls[0][1]?.method).toBe("GET");
    if (result.current.tipo === "sin_cuentas") expect(result.current.info).toEqual(estado);
  });

  test("con cuentas, deja el estado para el texto de recuperación", async () => {
    fetchFalso.mockResolvedValue(json({ ...estado, sin_cuentas: false }));
    const { result } = renderHook(() => usePrimerArranque(true));
    await waitFor(() => expect(result.current.tipo).toBe("con_cuentas"));
    if (result.current.tipo === "con_cuentas") expect(result.current.info?.modo).toBe("producto");
  });

  test.each([
    ["403 por equipo remoto", () => json({ detalle: "Solo desde el propio equipo." }, 403)],
    ["500", () => json({ detalle: "x" }, 500)],
    ["cuerpo que no es un objeto", () => json("hola")],
    ["sin_cuentas que no es booleano", () => json({ ...estado, sin_cuentas: "true" })],
    ["sin_cuentas ausente", () => json({ archivo_presente: true })],
  ])("%s: se trata como «con cuentas» y no inventa un estado", async (_nombre, respuesta) => {
    fetchFalso.mockImplementation(async () => respuesta());
    const { result } = renderHook(() => usePrimerArranque(true));
    await waitFor(() => expect(result.current.tipo).toBe("con_cuentas"));
    if (result.current.tipo === "con_cuentas") expect(result.current.info).toBeNull();
  });

  test("un fallo de red también es «con cuentas»", async () => {
    fetchFalso.mockRejectedValue(new TypeError("Failed to fetch"));
    const { result } = renderHook(() => usePrimerArranque(true));
    await waitFor(() => expect(result.current.tipo).toBe("con_cuentas"));
  });

  test("si la política viene rota usa 10 y 128 y no confía en lo que no es número", async () => {
    fetchFalso.mockResolvedValue(json({ ...estado, politica: { minimo: "diez", maximo: null } }));
    const { result } = renderHook(() => usePrimerArranque(true));
    await waitFor(() => expect(result.current.tipo).toBe("sin_cuentas"));
    if (result.current.tipo === "sin_cuentas") expect(result.current.info.politica).toEqual({ minimo: 10, maximo: 128 });
  });

  test("inactivo no pide nada", () => {
    renderHook(() => usePrimerArranque(false));
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("al volver a activarse vuelve a preguntar (por ejemplo tras salir)", async () => {
    fetchFalso.mockResolvedValue(json({ ...estado, sin_cuentas: false }));
    const { result, rerender } = renderHook(({ activo }) => usePrimerArranque(activo), {
      initialProps: { activo: true },
    });
    await waitFor(() => expect(result.current.tipo).toBe("con_cuentas"));
    rerender({ activo: false });
    rerender({ activo: true });
    await waitFor(() => expect(fetchFalso).toHaveBeenCalledTimes(2));
  });

  test("una respuesta tardía de una consulta anterior no pisa a la nueva", async () => {
    let soltar: (r: Response) => void = () => {};
    fetchFalso.mockImplementationOnce(() => new Promise<Response>((r) => (soltar = r)));
    fetchFalso.mockResolvedValueOnce(json({ ...estado, sin_cuentas: false }));
    const { result, rerender } = renderHook(({ activo }) => usePrimerArranque(activo), {
      initialProps: { activo: true },
    });
    rerender({ activo: false });
    rerender({ activo: true });
    await waitFor(() => expect(result.current.tipo).toBe("con_cuentas"));
    soltar(json(estado)); // la primera, ya vieja, dice «sin cuentas»
    await new Promise((r) => setTimeout(r, 20));
    expect(result.current.tipo).toBe("con_cuentas");
  });
});
