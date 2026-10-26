import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../api/cliente";
import { guardarPreferencias } from "./preferencias";

function respuesta(estado: number, cuerpo?: unknown): Response {
  return cuerpo === undefined
    ? new Response(null, { status: estado })
    : new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

describe("guardarPreferencias", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
  });
  afterEach(() => vi.unstubAllGlobals());

  test("hace PUT /v1/sesion/preferencias con el cambio y el token", async () => {
    fetchFalso.mockResolvedValue(respuesta(204));
    const alExpirar = vi.fn();
    await guardarPreferencias({ sidebar_fijado: true }, alExpirar);
    expect(fetchFalso).toHaveBeenCalledTimes(1);
    const [ruta, init] = fetchFalso.mock.calls[0];
    expect(String(ruta)).toBe("/v1/sesion/preferencias");
    expect(init?.method).toBe("PUT");
    expect(init?.body).toBe('{"sidebar_fijado":true}');
    expect(new Headers(init?.headers).get("X-Silice-CSRF")).toBe("tok");
    expect(alExpirar).not.toHaveBeenCalled();
  });

  test("un 401 da la sesion por vencida", async () => {
    fetchFalso.mockResolvedValue(respuesta(401, { detalle: "Sin sesión." }));
    const alExpirar = vi.fn();
    await guardarPreferencias({ modulo: "obras" }, alExpirar);
    expect(alExpirar).toHaveBeenCalledTimes(1);
  });

  test("otro error se calla: no rechaza ni da la sesion por vencida", async () => {
    fetchFalso.mockResolvedValue(respuesta(500, { detalle: "La base de la instalación no responde." }));
    const alExpirar = vi.fn();
    await expect(guardarPreferencias({ modulo: "obras" }, alExpirar)).resolves.toBeUndefined();
    fetchFalso.mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(guardarPreferencias({ sidebar_fijado: false }, alExpirar)).resolves.toBeUndefined();
    expect(alExpirar).not.toHaveBeenCalled();
  });
});
