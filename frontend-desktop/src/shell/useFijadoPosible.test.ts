import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import { useFijadoPosible } from "./useFijadoPosible";

const VARIABLE = "--silice-fijado-posible";
const html = document.documentElement;

afterEach(() => {
  html.style.removeProperty(VARIABLE);
  delete html.dataset.siliceLetra;
});

// El umbral vive solo en _umbrales.scss, que pone la variable en <html>; aqui se simula con el estilo en linea.
describe("useFijadoPosible", () => {
  test("sin la variable (o con 0) el fijado no es posible; con 1 si", () => {
    expect(renderHook(() => useFijadoPosible()).result.current).toBe(false);
    html.style.setProperty(VARIABLE, "0");
    expect(renderHook(() => useFijadoPosible()).result.current).toBe(false);
    html.style.setProperty(VARIABLE, "1");
    expect(renderHook(() => useFijadoPosible()).result.current).toBe(true);
  });

  test("se recalcula al redimensionar la ventana", () => {
    const { result } = renderHook(() => useFijadoPosible());
    expect(result.current).toBe(false);
    html.style.setProperty(VARIABLE, "1");
    act(() => {
      window.dispatchEvent(new Event("resize"));
    });
    expect(result.current).toBe(true);
  });

  test("se recalcula al cambiar el tamaño de letra (data-silice-letra)", async () => {
    html.style.setProperty(VARIABLE, "1");
    html.dataset.siliceLetra = "normal";
    const { result } = renderHook(() => useFijadoPosible());
    expect(result.current).toBe(true);
    act(() => {
      html.style.setProperty(VARIABLE, "0");
      html.dataset.siliceLetra = "muy-grande";
    });
    await waitFor(() => expect(result.current).toBe(false));
  });
});
