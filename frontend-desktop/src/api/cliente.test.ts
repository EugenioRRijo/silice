import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ErrorDeApi, alPerderSesion, fijarCsrf, nombreDeDescarga, pedir, pedirBinario } from "./cliente";

function respuesta(estado: number, cuerpo?: unknown, cabeceras: Record<string, string> = {}): Response {
  return new Response(cuerpo === undefined ? null : JSON.stringify(cuerpo), {
    status: estado,
    headers: { "Content-Type": "application/json", ...cabeceras },
  });
}

describe("cliente de la API", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const bajas: Array<() => void> = [];

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf(null);
  });
  afterEach(() => {
    while (bajas.length > 0) bajas.pop()?.();
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

  test("un PUT manda su cuerpo JSON con el token CSRF y el metodo PUT", async () => {
    fijarCsrf("abc123");
    fetchFalso.mockImplementation(async () => respuesta(200, { rev: 1 }));
    await expect(pedir("/v1/hoja/borradores/x/espacio", { metodo: "PUT", cuerpo: { rev: 0 } })).resolves.toEqual({ rev: 1 });
    const init = fetchFalso.mock.calls[0][1];
    expect(init?.method).toBe("PUT");
    expect(new Headers(init?.headers).get("X-Silice-CSRF")).toBe("abc123");
    expect(new Headers(init?.headers).get("Content-Type")).toBe("application/json");
    expect(init?.body).toBe('{"rev":0}');
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

  // Diseño de autocompletado §12-8 (H-13): un buscador aborta la petición vieja; ese aborto no es un servidor caído.
  test("la señal de aborto llega a fetch y un aborto se relanza tal cual, sin envolverlo en ErrorDeApi", async () => {
    const controlador = new AbortController();
    fetchFalso.mockImplementation(async (_ruta, init) => {
      expect(init?.signal).toBe(controlador.signal);
      throw new DOMException("The operation was aborted.", "AbortError");
    });
    const error = await pedir("/v1/buscar/partidas?q=tub", { senal: controlador.signal }).catch((e: unknown) => e);
    expect(error).not.toBeInstanceOf(ErrorDeApi);
    expect((error as DOMException).name).toBe("AbortError");
  });

  test("pedirBinario devuelve el contenido y el nombre del Content-Disposition", async () => {
    fetchFalso.mockImplementation(
      async () =>
        new Response("hola", {
          status: 200,
          headers: {
            "Content-Type": "application/pdf",
            "Content-Disposition": 'attachment; filename="ficha.pdf"',
            "X-Silice-SHA256": "abc123",
          },
        }),
    );
    const { blob, nombre, cabeceras } = await pedirBinario("/v1/algo", { respaldo: "descarga.bin" });
    expect(nombre).toBe("ficha.pdf");
    expect(cabeceras.get("X-Silice-SHA256")).toBe("abc123");
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

  test("un 401 avisa a las funciones registradas y lanza ErrorDeApi con codigo no_autenticado", async () => {
    fijarCsrf("tok");
    let avisosAlAtrapar = 0;
    const aviso = vi.fn();
    const otroAviso = vi.fn();
    bajas.push(alPerderSesion(aviso), alPerderSesion(otroAviso));
    fetchFalso.mockImplementation(async () => respuesta(401, { detalle: "Sesión vencida." }));

    const error = await pedir("/v1/obras").catch((e: unknown) => {
      avisosAlAtrapar = aviso.mock.calls.length;
      return e;
    });

    expect(avisosAlAtrapar).toBe(1);
    expect(aviso).toHaveBeenCalledTimes(1);
    expect(otroAviso).toHaveBeenCalledTimes(1);
    expect(error).toBeInstanceOf(ErrorDeApi);
    expect(error).toMatchObject({
      estado: 401,
      codigo: "no_autenticado",
      detalle: "Sesión vencida.",
      message: "Sesión vencida.",
    });
  });

  test("un 401 en pedirBinario tambien avisa a quien escucha la sesion y lanza ErrorDeApi", async () => {
    fijarCsrf("tok");
    const aviso = vi.fn();
    bajas.push(alPerderSesion(aviso));
    fetchFalso.mockImplementation(async () => respuesta(401, { detalle: "Sesión vencida." }));

    await expect(pedirBinario("/v1/entrega")).rejects.toMatchObject({
      estado: 401,
      codigo: "no_autenticado",
      detalle: "Sesión vencida.",
    });
    expect(aviso).toHaveBeenCalledTimes(1);
  });

  test("darse de baja deja de recibir avisos de sesion perdida", async () => {
    fijarCsrf("tok");
    const aviso = vi.fn();
    const darDeBaja = alPerderSesion(aviso);
    bajas.push(darDeBaja);

    fetchFalso.mockImplementationOnce(async () => respuesta(401, { detalle: "Sesión vencida." }));
    await pedir("/v1/obras").catch(() => null);
    expect(aviso).toHaveBeenCalledTimes(1);

    fetchFalso.mockImplementationOnce(async () => respuesta(200, { ok: true }));
    await pedir("/v1/sesion");

    darDeBaja();
    fijarCsrf("tok2");
    fetchFalso.mockImplementationOnce(async () => respuesta(401, { detalle: "Sesión vencida." }));
    await pedir("/v1/obras").catch(() => null);
    expect(aviso).toHaveBeenCalledTimes(1);
  });

  test("dos 401 seguidos dan un solo aviso y tras volver a entrar (nuevo CSRF) vuelve a avisar", async () => {
    fijarCsrf("tok");
    const aviso = vi.fn();
    bajas.push(alPerderSesion(aviso));
    fetchFalso.mockImplementation(async () => respuesta(401, { detalle: "Sesión vencida." }));

    await Promise.allSettled([pedir("/v1/obras"), pedir("/v1/carpeta")]);
    await expect(pedir("/v1/pendientes")).rejects.toMatchObject({ estado: 401, codigo: "no_autenticado" });
    expect(aviso).toHaveBeenCalledTimes(1);

    fetchFalso.mockImplementationOnce(async () => respuesta(200, { ok: true }));
    await pedir("/v1/sesion");
    expect(aviso).toHaveBeenCalledTimes(1);

    fijarCsrf("tok-nuevo");
    fetchFalso.mockImplementationOnce(async () => respuesta(401, { detalle: "Sesión vencida otra vez." }));
    await expect(pedir("/v1/obras")).rejects.toMatchObject({ estado: 401, codigo: "no_autenticado" });
    expect(aviso).toHaveBeenCalledTimes(2);
  });

  // Hallazgo 1: un 401 sin sesion (contrasena errada, codigo de instalacion errado, GET /v1/sesion al arrancar) no es una
  // sesion perdida. `csrf` solo es no nulo entre abrir sesion (useSesion lo fija con el token del servidor) y cerrarla.
  test("un 401 sin sesion abierta (POST /v1/sesion con clave errada) no avisa de sesion perdida", async () => {
    const aviso = vi.fn();
    bajas.push(alPerderSesion(aviso));
    fetchFalso.mockImplementation(async () => respuesta(401, { detalle: "Usuario o contraseña incorrectos." }));
    await expect(pedir("/v1/sesion", { metodo: "POST", cuerpo: { login: "a", contrasena: "x" } })).rejects.toMatchObject({
      estado: 401,
      codigo: "no_autenticado",
    });
    await expect(pedir("/v1/sesion")).rejects.toMatchObject({ estado: 401 });
    expect(aviso).not.toHaveBeenCalled();
  });

  test("401, un 200 de una ruta publica y otro 401 de la misma caida dan un solo aviso", async () => {
    fijarCsrf("tok");
    const aviso = vi.fn();
    bajas.push(alPerderSesion(aviso));
    fetchFalso.mockImplementationOnce(async () => respuesta(401, { detalle: "Sesión vencida." }));
    await pedir("/v1/obras").catch(() => null);
    fetchFalso.mockImplementationOnce(async () => respuesta(200, { ok: true }));
    await pedir("/v1/publica");
    fetchFalso.mockImplementationOnce(async () => respuesta(401, { detalle: "Sesión vencida." }));
    await pedir("/v1/carpeta").catch(() => null);
    expect(aviso).toHaveBeenCalledTimes(1);
  });

  test("un 403 y un 500 no avisan de sesion perdida", async () => {
    fijarCsrf("tok");
    const aviso = vi.fn();
    bajas.push(alPerderSesion(aviso));
    for (const estado of [403, 500]) {
      fetchFalso.mockImplementationOnce(async () => respuesta(estado, { detalle: `Fallo ${estado}.` }));
      await pedir("/v1/obras").catch(() => null);
    }
    expect(aviso).not.toHaveBeenCalled();
  });

  test("un 401 sin oyentes no se guarda: el oyente que se registra despues avisa en el siguiente 401", async () => {
    fijarCsrf("tok");
    fetchFalso.mockImplementationOnce(async () => respuesta(401, { detalle: "Sesión vencida." }));
    await pedir("/v1/obras").catch(() => null);

    const aviso = vi.fn();
    bajas.push(alPerderSesion(aviso));
    fetchFalso.mockImplementationOnce(async () => respuesta(401, { detalle: "Sesión vencida." }));
    await pedir("/v1/obras").catch(() => null);
    expect(aviso).toHaveBeenCalledTimes(1);
  });

  test("el oyente se llama antes de que pedir rechace, no diferido", async () => {
    fijarCsrf("tok");
    const diferido = vi.spyOn(globalThis, "queueMicrotask");
    const orden: string[] = [];
    bajas.push(alPerderSesion(() => orden.push("aviso")));
    fetchFalso.mockImplementationOnce(async () => respuesta(401, { detalle: "Sesión vencida." }));
    await pedir("/v1/obras").catch(() => orden.push("rechazo"));
    expect(orden).toEqual(["aviso", "rechazo"]);
    // Otras piezas (Response, el motor de pruebas) usan queueMicrotask: solo importa que no se difiera el oyente.
    expect(diferido.mock.calls.filter(([fn]) => String(fn).includes("oyente"))).toEqual([]);
    diferido.mockRestore();
  });

  // Hallazgo 10
  test("un oyente que lanza no impide avisar al siguiente ni tapa el ErrorDeApi del 401", async () => {
    fijarCsrf("tok");
    const roto = new Error("oyente roto");
    const relanzados: unknown[] = [];
    const diferido = vi.spyOn(globalThis, "queueMicrotask").mockImplementation((fn) => {
      try {
        fn();
      } catch (e) {
        relanzados.push(e);
      }
    });
    const segundo = vi.fn();
    bajas.push(
      alPerderSesion(() => {
        throw roto;
      }),
      alPerderSesion(segundo),
    );
    fetchFalso.mockImplementationOnce(async () => respuesta(401, { detalle: "Sesión vencida." }));
    await expect(pedir("/v1/obras")).rejects.toMatchObject({ estado: 401, codigo: "no_autenticado" });
    expect(segundo).toHaveBeenCalledTimes(1);
    expect(relanzados).toEqual([roto]);
    diferido.mockRestore();
  });

  // Hallazgo 2
  test("con leer, un aborto durante la lectura del cuerpo se relanza como AbortError, no como respuesta_invalida", async () => {
    const abortada = new DOMException("The operation was aborted.", "AbortError");
    fetchFalso.mockImplementationOnce(async () => {
      const r = respuesta(200, {});
      vi.spyOn(r, "json").mockRejectedValue(abortada);
      return r;
    });
    const leer = vi.fn((d: unknown) => d);
    const error = await pedir("/v1/obras/1", { leer }).catch((e: unknown) => e);
    expect(error).not.toBeInstanceOf(ErrorDeApi);
    expect((error as DOMException).name).toBe("AbortError");
    expect(leer).not.toHaveBeenCalled();
  });

  test("con leer, un cuerpo que no es JSON o un analizador que falla es respuesta_invalida y conserva la causa", async () => {
    fetchFalso.mockImplementationOnce(async () => new Response("<html>", { status: 200 }));
    const sinJson = (await pedir("/v1/obras/1", { leer: (d) => d }).catch((e: unknown) => e)) as ErrorDeApi;
    expect(sinJson).toBeInstanceOf(ErrorDeApi);
    expect(sinJson.codigo).toBe("respuesta_invalida");
    expect(sinJson.cause).toBeInstanceOf(SyntaxError);

    const causa = new Error("contrato roto");
    fetchFalso.mockImplementationOnce(async () => respuesta(200, { a: 1 }));
    const roto = (await pedir("/v1/obras/1", {
      leer: () => {
        throw causa;
      },
    }).catch((e: unknown) => e)) as ErrorDeApi;
    expect(roto.codigo).toBe("respuesta_invalida");
    expect(roto.cause).toBe(causa);
    expect(roto.cuerpo).toEqual({ a: 1 });
  });

  test("el codigo de ErrorDeApi viene del cuerpo cuando existe y del estado HTTP o de red cuando no", async () => {
    fetchFalso.mockImplementationOnce(async () =>
      respuesta(409, { detalle: "El borrador cambió.", codigo: "borrador_desactualizado" }),
    );
    const conCodigo = (await pedir("/v1/hoja").catch((e: unknown) => e)) as ErrorDeApi;
    expect(conCodigo.codigo).toBe("borrador_desactualizado");
    expect(conCodigo.message).toBe("El borrador cambió.");

    const casos: Array<[number, string]> = [
      [401, "no_autenticado"],
      [403, "sin_permiso"],
      [404, "no_encontrado"],
      [409, "conflicto"],
      [422, "datos_invalidos"],
      [500, "error_del_servidor"],
      [503, "error_del_servidor"],
      [429, "error_http"],
    ];
    for (const [estado, esperado] of casos) {
      fetchFalso.mockImplementationOnce(async () => respuesta(estado, { detalle: `Fallo ${estado}.` }));
      const error = (await pedir("/v1/recurso").catch((e: unknown) => e)) as ErrorDeApi;
      expect(error.codigo).toBe(esperado);
      expect(error.message).toBe(`Fallo ${estado}.`);
    }

    fetchFalso.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    const sinRed = (await pedir("/v1/recurso").catch((e: unknown) => e)) as ErrorDeApi;
    expect(sinRed.estado).toBe(0);
    expect(sinRed.codigo).toBe("sin_conexion");
  });

  test("ErrorDeApi lee campo del cuerpo cuando viene y lo deja undefined cuando no", async () => {
    fetchFalso.mockImplementationOnce(async () =>
      respuesta(422, { detalle: "Escriba una cantidad positiva.", codigo: "cifra_invalida", campo: "cantidad" }),
    );
    const conCampo = (await pedir("/v1/partidas", { metodo: "POST", cuerpo: {} }).catch((e: unknown) => e)) as ErrorDeApi;
    expect(conCampo.codigo).toBe("cifra_invalida");
    expect(conCampo.campo).toBe("cantidad");
    expect(conCampo.message).toBe("Escriba una cantidad positiva.");

    fetchFalso.mockImplementationOnce(async () => respuesta(422, { detalle: "Faltan datos." }));
    const sinCampo = (await pedir("/v1/partidas", { metodo: "POST", cuerpo: {} }).catch((e: unknown) => e)) as ErrorDeApi;
    expect(sinCampo.campo).toBeUndefined();
  });

  test("pedir aplica leer cuando se pasa y convierte un fallo del analizador en respuesta_invalida", async () => {
    fetchFalso.mockImplementationOnce(async () => respuesta(200, { nombre: "Puente Chama", renglones: 4 }));
    const obra = await pedir("/v1/obras/1", {
      leer: (datos) => {
        if (!datos || typeof datos !== "object") throw new Error("no es objeto");
        const { nombre, renglones } = datos as { nombre?: unknown; renglones?: unknown };
        if (typeof nombre !== "string" || typeof renglones !== "number") throw new Error("forma inesperada");
        return { titulo: `${nombre} (${renglones})` };
      },
    });
    expect(obra).toEqual({ titulo: "Puente Chama (4)" });

    fetchFalso.mockImplementationOnce(async () => respuesta(200, { nombre: 123 }));
    const error = await pedir("/v1/obras/1", {
      leer: () => {
        throw new Error("contrato roto");
      },
    }).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ErrorDeApi);
    expect(error).toMatchObject({
      estado: 200,
      codigo: "respuesta_invalida",
      detalle:
        "El servidor respondió algo que esta pantalla no esperaba. Vuelva a intentarlo; si se repite, avise al equipo de Sílice.",
      message:
        "El servidor respondió algo que esta pantalla no esperaba. Vuelva a intentarlo; si se repite, avise al equipo de Sílice.",
    });
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
