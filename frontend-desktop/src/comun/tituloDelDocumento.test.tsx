import { renderHook } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { useTituloDelDocumento } from "./tituloDelDocumento";

describe("useTituloDelDocumento", () => {
  test("«Página · Sílice»", () => {
    renderHook(() => useTituloDelDocumento("Control de obra"));
    expect(document.title).toBe("Control de obra · Sílice");
  });

  test("sin página, solo «Sílice»", () => {
    renderHook(() => useTituloDelDocumento(null));
    expect(document.title).toBe("Sílice");
  });

  test("si la página ya nombra a Sílice no se repite", () => {
    renderHook(() => useTituloDelDocumento("Acerca de Sílice"));
    expect(document.title).toBe("Acerca de Sílice");
  });
});
