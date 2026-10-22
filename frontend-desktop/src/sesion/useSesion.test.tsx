import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ErrorDeApi, fijarCsrf, pedir } from "../api/cliente";
import { useSesion } from "./useSesion";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const nueva = { login: "admin", nombre: "Ana Pérez", roles: ["administrador"], csrf: "tok-nuevo" };
const cuerpo = { codigo: "ABCD-EFGH-JKLM-NPQR-STUV", usuario: "admin", nombre: "Ana Pérez", contrasena: "x".repeat(12), tambien_arma: false };

const fetchFalso = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchFalso);
  fetchFalso.mockReset();
  fijarCsrf(null);
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useSesion.reclamar (BCP-4)", () => {
  test("hace POST /v1/primer-arranque/reclamo con el cuerpo tal cual y deja la sesión activa normalizada", async () => {
    fetchFalso.mockImplementation(async (entrada, init) => {
      if (String(entrada) === "/v1/sesion") return json({ detalle: "Sin sesión." }, 401);
      expect(String(entrada)).toBe("/v1/primer-arranque/reclamo");
      expect(init?.method).toBe("POST");
      expect(init?.body).toBe(JSON.stringify(cuerpo));
      return json(nueva, 201);
    });
    const { result } = renderHook(() => useSesion());
    await waitFor(() => expect(result.current.estado.tipo).toBe("sin_sesion"));
    await act(async () => {
      await result.current.reclamar(cuerpo);
    });
    expect(result.current.estado.tipo).toBe("activa");
    if (result.current.estado.tipo === "activa") {
      // Una respuesta sin los campos de la ola 0a se normaliza igual que la de /v1/sesion.
      expect(result.current.estado.sesion).toMatchObject({ login: "admin", debe_cambiar_clave: false, acciones: [], modo_entrega: false });
    }
  });

  test("fija el token anti-CSRF de la respuesta para las peticiones siguientes", async () => {
    fetchFalso.mockImplementation(async (entrada) => {
      if (String(entrada) === "/v1/sesion") return json({ detalle: "Sin sesión." }, 401);
      if (String(entrada) === "/v1/primer-arranque/reclamo") return json(nueva, 201);
      return json({}, 200);
    });
    const { result } = renderHook(() => useSesion());
    await waitFor(() => expect(result.current.estado.tipo).toBe("sin_sesion"));
    await act(async () => {
      await result.current.reclamar(cuerpo);
    });
    await pedir("/v1/algo", { metodo: "POST", cuerpo: {} });
    const ultima = fetchFalso.mock.calls.at(-1)!;
    expect(new Headers(ultima[1]?.headers).get("X-Silice-CSRF")).toBe("tok-nuevo");
  });

  test("un error de la API se propaga con su detalle y la sesión sigue sin abrir", async () => {
    fetchFalso.mockImplementation(async (entrada) => {
      if (String(entrada) === "/v1/sesion") return json({ detalle: "Sin sesión." }, 401);
      return json({ detalle: "El código no es válido o ya se usó." }, 401);
    });
    const { result } = renderHook(() => useSesion());
    await waitFor(() => expect(result.current.estado.tipo).toBe("sin_sesion"));
    let error: unknown;
    await act(async () => {
      await result.current.reclamar(cuerpo).catch((e: unknown) => {
        error = e;
      });
    });
    expect(error).toBeInstanceOf(ErrorDeApi);
    expect((error as ErrorDeApi).detalle).toBe("El código no es válido o ya se usó.");
    expect(result.current.estado.tipo).toBe("sin_sesion");
  });
});
