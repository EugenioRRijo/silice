import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { tablasVacias } from "./tablas";
import { evaluar, guardar, opciones, partida, referencia, similares } from "./cliente";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

describe("cliente de composición", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fetchFalso.mockImplementation(async () => json({}));
  });
  afterEach(() => vi.unstubAllGlobals());

  function ultima() {
    const [ruta, init] = fetchFalso.mock.calls.at(-1)!;
    return { ruta: String(ruta), init: init as RequestInit };
  }

  test("opciones y partida son GET; el código se codifica", async () => {
    await opciones();
    expect(ultima().ruta).toBe("/v1/composicion/opciones");
    await partida("A B/1");
    expect(ultima().ruta).toBe("/v1/composicion/partidas/A%20B%2F1");
    expect(ultima().init.method).toBe("GET");
  });

  test("referencia y similares llevan sus parámetros codificados", async () => {
    await referencia("mano_obra", "obrero ñ");
    expect(ultima().ruta).toBe("/v1/composicion/referencia?tipo=mano_obra&q=obrero%20%C3%B1");
    await similares("civil", "muro de bloque");
    expect(ultima().ruta).toBe("/v1/composicion/similares?dominio=civil&descripcion=muro%20de%20bloque");
  });

  test("evaluar y guardar son POST con cuerpo JSON", async () => {
    const cabecera = { codigo: "X-1", descripcion: "d", unidad: "m2", dominio: "civil", rendimiento: "10" };
    await evaluar(cabecera, tablasVacias());
    const e = ultima();
    expect(e.ruta).toBe("/v1/composicion/evaluar");
    expect(e.init.method).toBe("POST");
    expect(JSON.parse(String(e.init.body))).toEqual({ ...cabecera, ...tablasVacias() });

    await guardar(cabecera, tablasVacias(), { fecha: "2026-10-18", condiciones: "ficticias", justificacion: null });
    const g = ultima();
    expect(g.ruta).toBe("/v1/composicion/guardar");
    expect(JSON.parse(String(g.init.body))).toMatchObject({
      codigo: "X-1",
      fecha: "2026-10-18",
      condiciones: "ficticias",
      justificacion: null,
    });
  });

  test("un error de la API llega como ErrorDeApi con su detalle", async () => {
    fetchFalso.mockImplementation(async () => json({ detail: "Condiciones vacías." }, 422));
    await expect(
      guardar({ codigo: "", descripcion: "", unidad: "", dominio: "civil", rendimiento: "" }, tablasVacias(), {
        fecha: "2026-10-18",
        condiciones: "",
        justificacion: null,
      }),
    ).rejects.toMatchObject({ estado: 422, detalle: "Condiciones vacías." });
  });
});
