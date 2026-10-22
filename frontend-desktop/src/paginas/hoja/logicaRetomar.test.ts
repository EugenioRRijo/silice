import { describe, expect, test } from "vitest";
import { ErrorDeApi } from "../../api/cliente";
import { borradorExistente, ofertasDeRetomar, rotuloDeOferta } from "./logicaRetomar";

// Retomar un borrador tras recargar o volver a la página (3c-3: E10 y E11 del diseño §4.4; 3c-F16). Los valores esperados
// están escritos a mano desde el contrato: E10 devuelve los borradores de MI ficha como `[{id, proyecto, version, cambios,
// tocado}]` y E11 contesta 409 `{detalle, borrador_id}` si ya hay uno con cambios de esa (proyecto, versión).
const fila = (extra: Record<string, unknown> = {}) => ({
  id: "id-borrador-aaaaaaaaaaaa",
  proyecto: "OF-001",
  version: "001",
  cambios: 2,
  tocado: "2026-10-20T10:00:00",
  ...extra,
});

describe("qué borradores se ofrecen para retomar", () => {
  test("solo los del proyecto abierto y con cambios sin guardar", () => {
    const lista = [
      fila(),
      fila({ id: "id-borrador-bbbbbbbbbbbb", proyecto: "TI-001" }),
      fila({ id: "id-borrador-cccccccccccc", cambios: 0 }),
    ];
    expect(ofertasDeRetomar(lista, "OF-001").map((o) => o.id)).toEqual(["id-borrador-aaaaaaaaaaaa"]);
  });

  // La API (E10) llama `proyecto` al NOMBRE del proyecto; la cabecera trae el CÓDIGO. Con datos reales (OF-001 se llama
  // «OF-001: oficina con baño…») la oferta nunca coincidía y la persona quedaba sin poder retomar (auditoría visual 3e-3).
  test("el servidor dice el nombre del proyecto y la cabecera el código: se ofrece por el nombre", () => {
    const nombre = "OF-001: oficina con baño, cocineta y puestos (caso de prueba)";
    const lista = [fila({ proyecto: nombre }), fila({ id: "id-borrador-bbbbbbbbbbbb", proyecto: "TI-001: telecom" })];
    expect(ofertasDeRetomar(lista, "OF-001", nombre).map((o) => o.id)).toEqual(["id-borrador-aaaaaaaaaaaa"]);
    expect(ofertasDeRetomar(lista, "OF-001", null)).toEqual([]);
    expect(ofertasDeRetomar([fila()], "OF-001", nombre)).toHaveLength(1); // y el código solo sigue valiendo
  });

  test("acepta la lista sola o envuelta en `borradores`", () => {
    expect(ofertasDeRetomar({ borradores: [fila()] }, "OF-001")).toHaveLength(1);
    expect(ofertasDeRetomar([fila()], "OF-001")).toHaveLength(1);
  });

  test.each([[null], [undefined], [204], ["texto"], [{}], [{ borradores: "no" }]])(
    "una respuesta que no es una lista (%s) no ofrece nada: abrir la hoja no depende de esto",
    (respuesta) => {
      expect(ofertasDeRetomar(respuesta, "OF-001")).toEqual([]);
    },
  );

  test("una fila mal formada se ignora; las buenas siguen", () => {
    const lista = [{ id: 3 }, null, fila({ cambios: "2" }), fila({ version: undefined }), fila()];
    expect(ofertasDeRetomar(lista, "OF-001")).toHaveLength(1);
  });

  test("un proyecto sin versiones llega con version null", () => {
    expect(ofertasDeRetomar([fila({ version: null })], "OF-001")[0]!.version).toBeNull();
  });
});

describe("el texto de la oferta", () => {
  test("«Retomar borrador de {proyecto} ({n} cambios)» y con un solo cambio, en singular", () => {
    expect(rotuloDeOferta({ ...fila(), version: "001" } as never, "OF-001", false)).toBe("Retomar borrador de OF-001 (2 cambios)");
    expect(rotuloDeOferta({ ...fila({ cambios: 1 }) } as never, "OF-001", false)).toBe("Retomar borrador de OF-001 (1 cambio)");
  });

  test("con varios borradores del proyecto se dice la versión de cada uno", () => {
    expect(rotuloDeOferta({ ...fila({ version: "002" }) } as never, "OF-001", true)).toBe(
      "Retomar borrador de OF-001, versión 002 (2 cambios)",
    );
    expect(rotuloDeOferta({ ...fila({ version: null }) } as never, "OF-001", true)).toBe(
      "Retomar borrador de OF-001, en blanco (2 cambios)",
    );
  });
});

describe("el 409 de abrir sobre un borrador con cambios (E11)", () => {
  test("da el id del borrador existente", () => {
    const e = new ErrorDeApi(409, "Ya hay un borrador de esa versión con cambios.", null, {
      detalle: "Ya hay un borrador de esa versión con cambios.",
      borrador_id: "id-borrador-aaaaaaaaaaaa",
    });
    expect(borradorExistente(e)).toBe("id-borrador-aaaaaaaaaaaa");
  });

  test.each([
    ["un 409 sin id", new ErrorDeApi(409, "x", null, { detalle: "x" })],
    ["un 409 con el id vacío", new ErrorDeApi(409, "x", null, { borrador_id: "" })],
    ["otro estado", new ErrorDeApi(422, "x", null, { borrador_id: "id-borrador-aaaaaaaaaaaa" })],
    ["no es un error de la API", new Error("x")],
    ["nada", null],
  ])("%s: no hay borrador existente", (_nombre, error) => {
    expect(borradorExistente(error)).toBeNull();
  });
});
