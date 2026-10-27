import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ErrorDeApi, pedir } from "../api/cliente";
import { aplicarTema, leerTema, type TemaRespuesta } from "./tema";
import { useTema } from "./useTema";

vi.mock("../api/cliente", async (importarOriginal) => ({
  ...(await importarOriginal<typeof import("../api/cliente")>()),
  pedir: vi.fn(),
}));

// Colores inventados: ningun valor de una empresa real vive en el repositorio.
const NEUTRO: TemaRespuesta = { acento: null, marco: null, lateral: null, tiene_logo: false, avisos: [] };

describe("aplicarTema", () => {
  let raiz: HTMLElement;
  beforeEach(() => {
    raiz = document.createElement("div");
  });

  it("fija solo la variable del color valido", () => {
    aplicarTema({ ...NEUTRO, acento: "#123abc" }, raiz);
    expect(raiz.style.getPropertyValue("--silice-acento")).toBe("#123abc");
    expect(raiz.style.getPropertyValue("--silice-marco")).toBe("");
    expect(raiz.style.getPropertyValue("--silice-lateral")).toBe("");
  });

  it("no fija nada con un color que no es #rrggbb", () => {
    aplicarTema({ ...NEUTRO, acento: "rojo", marco: "#12345", lateral: "url(x)" }, raiz);
    expect(raiz.getAttribute("style") ?? "").toBe("");
  });

  it("fija los tres cuando los tres son validos", () => {
    aplicarTema({ ...NEUTRO, acento: "#111111", marco: "#222222", lateral: "#AbCdEf" }, raiz);
    expect(raiz.style.getPropertyValue("--silice-acento")).toBe("#111111");
    expect(raiz.style.getPropertyValue("--silice-marco")).toBe("#222222");
    expect(raiz.style.getPropertyValue("--silice-lateral")).toBe("#AbCdEf");
  });
});

describe("leerTema: avisos", () => {
  it("conserva los textos de aviso y descarta lo que no es texto", () => {
    expect(leerTema({ avisos: ["a", 3, null, "b"] }).avisos).toEqual(["a", "b"]);
  });

  it("sin avisos, o con otra forma, quedan en una lista vacia", () => {
    expect(leerTema({}).avisos).toEqual([]);
    expect(leerTema({ avisos: "texto" }).avisos).toEqual([]);
    expect(leerTema(null).avisos).toEqual([]);
  });
});

describe("useTema", () => {
  const pedirFalso = vi.mocked(pedir);
  afterEach(() => {
    pedirFalso.mockReset();
    document.documentElement.removeAttribute("style");
  });

  it("devuelve la ruta del logo cuando hay logo", async () => {
    pedirFalso.mockResolvedValue({ ...NEUTRO, tiene_logo: true });
    const { result } = renderHook(() => useTema());
    await waitFor(() => expect(result.current.logo).toBe("/v1/tema/logo"));
  });

  it("devuelve null sin logo y no falla", async () => {
    pedirFalso.mockResolvedValue(NEUTRO);
    const { result } = renderHook(() => useTema());
    await act(async () => {});
    expect(result.current.logo).toBeNull();
  });

  it("si el servidor no contesta queda el tema neutro", async () => {
    pedirFalso.mockRejectedValue(new ErrorDeApi(500, "x"));
    const { result } = renderHook(() => useTema());
    await act(async () => {});
    expect(result.current.logo).toBeNull();
    expect(document.documentElement.getAttribute("style") ?? "").toBe("");
  });

  it("una respuesta con otra forma se trata como neutra", async () => {
    pedirFalso.mockResolvedValue({ acento: 5, tiene_logo: "si" });
    const { result } = renderHook(() => useTema());
    await act(async () => {});
    expect(result.current.logo).toBeNull();
  });

  it("aplica los colores a la raiz del documento", async () => {
    pedirFalso.mockResolvedValue({ ...NEUTRO, acento: "#123abc" });
    renderHook(() => useTema());
    await waitFor(() =>
      expect(document.documentElement.style.getPropertyValue("--silice-acento")).toBe("#123abc"),
    );
  });
});
