import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ErrorDeApi, fijarCsrf, pedir } from "./cliente";

function respuesta(estado: number, cuerpo?: unknown, cabeceras: Record<string, string> = {}): Response {
  return new Response(cuerpo === undefined ? null : JSON.stringify(cuerpo), {
    status: estado,
    headers: { "Content-Type": "application/json", ...cabeceras },
  });
}

describe("cliente de la API", () => {
  const fetchFalso = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf(null);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("todas las peticiones llevan credentials same-origin", async () => {
    fetchFalso.mockImplementation(async () => respuesta(200, { ok: true }));
    await pedir("/v1/sesion");
    expect(fetchFalso.mock.calls[0][1]?.credentials).toBe("same-origin");
  });

  test("un POST con el token CSRF lo manda en X-Silice-CSRF", async () => {
    fijarCsrf("abc123");
    fetchFalso.mockImplementation(async () => respuesta(200, {}));
    await pedir("/v1/libros/auditoria", { metodo: "POST", cuerpo: new FormData() });
    const cabeceras = new Headers(fetchFalso.mock.calls[0][1]?.headers);
    expect(cabeceras.get("X-Silice-CSRF")).toBe("abc123");
  });

  test("un DELETE tambien lleva el token y un GET no", async () => {
    fijarCsrf("abc123");
    fetchFalso.mockImplementation(async () => respuesta(204));
    await pedir("/v1/sesion", { metodo: "DELETE" });
    await pedir("/v1/sesion");
    expect(new Headers(fetchFalso.mock.calls[0][1]?.headers).get("X-Silice-CSRF")).toBe("abc123");
    expect(new Headers(fetchFalso.mock.calls[1][1]?.headers).get("X-Silice-CSRF")).toBeNull();
  });

  test("un cuerpo JSON viaja con su Content-Type y un FormData se lo deja al navegador", async () => {
    fetchFalso.mockImplementation(async () => respuesta(200, {}));
    await pedir("/v1/sesion", { metodo: "POST", cuerpo: { login: "a", contrasena: "b" } });
    await pedir("/v1/libros/replica", { metodo: "POST", cuerpo: new FormData() });
    const json = fetchFalso.mock.calls[0][1];
    expect(new Headers(json?.headers).get("Content-Type")).toBe("application/json");
    expect(json?.body).toBe(JSON.stringify({ login: "a", contrasena: "b" }));
    expect(new Headers(fetchFalso.mock.calls[1][1]?.headers).get("Content-Type")).toBeNull();
  });

  test("un 401 es un ErrorDeApi con estado 401 y el detalle de la API", async () => {
    fetchFalso.mockImplementation(async () => respuesta(401, { detalle: "Usuario o contraseña incorrectos." }));
    const error = await pedir("/v1/sesion").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ErrorDeApi);
    expect(error).toMatchObject({ estado: 401, detalle: "Usuario o contraseña incorrectos." });
  });

  test("un 429 trae los segundos de espera de Retry-After", async () => {
    fetchFalso.mockImplementation(async () => respuesta(429, { detalle: "Demasiados intentos." }, { "Retry-After": "30" }));
    const error = await pedir("/v1/sesion").catch((e: unknown) => e);
    expect(error).toMatchObject({ estado: 429, detalle: "Demasiados intentos.", reintentarEnSegundos: 30 });
  });

  test("sin detalle JSON, el mensaje dice el estado", async () => {
    fetchFalso.mockImplementation(async () => new Response("<html>", { status: 502 }));
    const error = await pedir("/v1/sesion").catch((e: unknown) => e);
    expect(error).toMatchObject({ estado: 502 });
    expect((error as ErrorDeApi).detalle).toContain("502");
  });

  test("los mensajes al usuario dicen \"el programa de Sílice\", no \"la API\" (m6)", async () => {
    fetchFalso.mockImplementation(async () => new Response("<html>", { status: 502 }));
    const sinDetalle = await pedir("/v1/sesion").catch((e: unknown) => e);
    fetchFalso.mockRejectedValue(new TypeError("Failed to fetch"));
    const sinServidor = await pedir("/v1/sesion").catch((e: unknown) => e);
    for (const error of [sinDetalle, sinServidor]) {
      expect((error as ErrorDeApi).detalle).toMatch(/programa de Sílice/);
      expect((error as ErrorDeApi).detalle).not.toMatch(/\bAPI\b/);
    }
  });

  test("un 204 devuelve undefined", async () => {
    fetchFalso.mockImplementation(async () => respuesta(204));
    await expect(pedir("/v1/sesion", { metodo: "DELETE" })).resolves.toBeUndefined();
  });

  test("si el servidor no responde, el error lo dice en espanol", async () => {
    fetchFalso.mockRejectedValue(new TypeError("Failed to fetch"));
    const error = await pedir("/v1/sesion").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ErrorDeApi);
    expect(error).toMatchObject({ estado: 0 });
    expect((error as ErrorDeApi).detalle).toMatch(/no se pudo hablar/i);
  });
});
