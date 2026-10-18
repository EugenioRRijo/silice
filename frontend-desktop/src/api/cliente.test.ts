import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ErrorDeApi, fijarCsrf, nombreDeDescarga, pedir, pedirBinario } from "./cliente";

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

  test("el ErrorDeApi conserva el cuerpo de la respuesta para los campos extra (por ejemplo `faltan`)", async () => {
    fetchFalso.mockImplementation(async () => respuesta(422, { detalle: "Faltan columnas.", faltan: ["ticket", "fecha"] }));
    const error = await pedir("/v1/produccion/bascula/importar", { metodo: "POST", cuerpo: new FormData() }).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ErrorDeApi);
    expect((error as ErrorDeApi).cuerpo).toEqual({ detalle: "Faltan columnas.", faltan: ["ticket", "fecha"] });
  });

  test("sin cuerpo JSON el ErrorDeApi trae cuerpo null", async () => {
    fetchFalso.mockImplementation(async () => new Response("<html>", { status: 502 }));
    const error = await pedir("/v1/sesion").catch((e: unknown) => e);
    expect((error as ErrorDeApi).cuerpo).toBeNull();
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

  test("un 204 devuelve undefined", async () => {
    fetchFalso.mockImplementation(async () => respuesta(204));
    await expect(pedir("/v1/sesion", { metodo: "DELETE" })).resolves.toBeUndefined();
  });

  test("si el servidor no responde, el error lo dice en espanol", async () => {
    fetchFalso.mockRejectedValue(new TypeError("Failed to fetch"));
    const error = await pedir("/v1/sesion").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ErrorDeApi);
    expect(error).toMatchObject({ estado: 0 });
    expect((error as ErrorDeApi).detalle).toMatch(/servidor/i);
  });

  test("pedirBinario devuelve el contenido y el nombre del Content-Disposition", async () => {
    fetchFalso.mockImplementation(
      async () =>
        new Response("hola", {
          status: 200,
          headers: { "Content-Type": "application/pdf", "Content-Disposition": 'attachment; filename="ficha.pdf"' },
        }),
    );
    const { blob, nombre } = await pedirBinario("/v1/algo", { respaldo: "descarga.bin" });
    expect(nombre).toBe("ficha.pdf");
    expect(await blob.text()).toBe("hola");
    expect(blob.type).toBe("application/pdf");
  });

  test("pedirBinario manda el token en un POST y falla con el detalle de la API", async () => {
    fijarCsrf("tok");
    fetchFalso.mockImplementation(async () => respuesta(409, { detalle: "No hay nada que entregar." }));
    await expect(pedirBinario("/v1/entrega", { metodo: "POST", cuerpo: {} })).rejects.toMatchObject({
      estado: 409,
      detalle: "No hay nada que entregar.",
    });
    expect(new Headers(fetchFalso.mock.calls[0][1]?.headers).get("X-Silice-CSRF")).toBe("tok");
  });

  test("pedirBinario sin red lanza ErrorDeApi con estado 0", async () => {
    fetchFalso.mockRejectedValue(new TypeError("fallo"));
    await expect(pedirBinario("/v1/algo")).rejects.toMatchObject({ estado: 0 });
  });
});

describe("nombreDeDescarga", () => {
  test("lee filename entre comillas y sin ellas", () => {
    expect(nombreDeDescarga('attachment; filename="a b.xlsx"', "x")).toBe("a b.xlsx");
    expect(nombreDeDescarga("attachment; filename=a.csv", "x")).toBe("a.csv");
  });

  test("prefiere filename* con UTF-8 codificado", () => {
    expect(
      nombreDeDescarga("attachment; filename=\"presupuesto.xlsx\"; filename*=UTF-8''presupuesto%20%C3%B1and%C3%BA.xlsx", "x"),
    ).toBe("presupuesto ñandú.xlsx");
  });

  test("sin cabecera usa el nombre de respaldo", () => {
    expect(nombreDeDescarga(null, "descarga.bin")).toBe("descarga.bin");
    expect(nombreDeDescarga("inline", "descarga.bin")).toBe("descarga.bin");
  });

  test("quita las rutas del nombre para que no escape de la carpeta de descargas", () => {
    expect(nombreDeDescarga('attachment; filename="../../etc/passwd"', "x")).toBe("passwd");
    expect(nombreDeDescarga('attachment; filename="C:\\malo\\a.pdf"', "x")).toBe("a.pdf");
  });
});
