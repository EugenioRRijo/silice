import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { useTamanoDeLetra } from "./useTamanoDeLetra";

// Oráculo: el atributo que `aplicarTamanoLetra` deja en la raíz, escrito a mano (no se llama al código bajo prueba).
afterEach(() => {
  document.documentElement.removeAttribute("data-silice-letra");
  window.localStorage.clear();
});

describe("useTamanoDeLetra", () => {
  test("devuelve el tamaño puesto en la raíz", () => {
    document.documentElement.setAttribute("data-silice-letra", "grande");
    const { result } = renderHook(() => useTamanoDeLetra());
    expect(result.current).toBe("grande");
  });

  test("sin atributo ni preferencia guardada devuelve normal", () => {
    const { result } = renderHook(() => useTamanoDeLetra());
    expect(result.current).toBe("normal");
  });

  test("cambia cuando cambia el atributo", async () => {
    const { result } = renderHook(() => useTamanoDeLetra());
    expect(result.current).toBe("normal");
    act(() => document.documentElement.setAttribute("data-silice-letra", "muy-grande"));
    await waitFor(() => expect(result.current).toBe("muy-grande"));
  });

  test("al desmontarse desconecta su observador", () => {
    const { unmount } = renderHook(() => useTamanoDeLetra());
    const antes = vi.spyOn(MutationObserver.prototype, "disconnect");
    unmount();
    expect(antes).toHaveBeenCalled();
    antes.mockRestore();
  });
});
