import { describe, expect, test } from "vitest";
import type { AuditoriaGuardadaRespuesta } from "../inicio/UltimasAuditorias";
import { FILTROS_VACIOS, clasificar, fechaEsVe, filtrar, filtrosInvalidos } from "./logica";

function a(id: number, parcial: Partial<AuditoriaGuardadaRespuesta> = {}): AuditoriaGuardadaRespuesta {
  return {
    id,
    archivo: `libro-${id}.xlsx`,
    fecha: "2026-10-18T10:00:00",
    tipo: "libro",
    errores: 0,
    advertencias: 0,
    ...parcial,
  };
}

describe("clasificar", () => {
  test("con un error o mas es «con errores», aunque haya advertencias", () => {
    expect(clasificar(1, 0)).toBe("con_errores");
    expect(clasificar(3, 7)).toBe("con_errores");
  });
  test("sin errores y con advertencias es «solo advertencias»", () => {
    expect(clasificar(0, 1)).toBe("solo_advertencias");
  });
  test("sin errores ni advertencias es «limpia»", () => {
    expect(clasificar(0, 0)).toBe("limpia");
  });
});

describe("fechaEsVe", () => {
  test("pasa «2026-10-18T14:32:05» a «18/10/2026 14:32»", () => {
    expect(fechaEsVe("2026-10-18T14:32:05")).toBe("18/10/2026 14:32");
  });
  test("un dia solo (la fecha del libro) pasa a «31/07/2026»", () => {
    expect(fechaEsVe("2026-07-31")).toBe("31/07/2026");
  });
  test("lo que no es una fecha ISO se devuelve tal cual", () => {
    expect(fechaEsVe("ayer")).toBe("ayer");
  });
});

describe("filtrar", () => {
  const lista = [
    a(5, { fecha: "2026-10-20T08:00:00", errores: 2, advertencias: 1 }),
    a(4, { fecha: "2026-10-19T23:59:59", tipo: "pdf", advertencias: 3 }),
    a(3, { fecha: "2026-10-19T00:00:00" }),
    a(2, { fecha: "2026-10-18T12:00:00", tipo: "pdf", errores: 1 }),
    a(1, { fecha: "2026-10-17T09:00:00", advertencias: 1 }),
  ];
  const ids = (f: Partial<typeof FILTROS_VACIOS>) => filtrar(lista, { ...FILTROS_VACIOS, ...f }).map((x) => x.id);

  test("sin filtros devuelve todo, en el orden recibido", () => {
    expect(ids({})).toEqual([5, 4, 3, 2, 1]);
  });
  test("«desde» y «hasta» incluyen el dia entero de sus extremos", () => {
    expect(ids({ desde: "2026-10-19", hasta: "2026-10-19" })).toEqual([4, 3]);
    expect(ids({ desde: "2026-10-19" })).toEqual([5, 4, 3]);
    expect(ids({ hasta: "2026-10-18" })).toEqual([2, 1]);
  });
  test("una fecha mal escrita no filtra (la pagina avisa aparte)", () => {
    expect(ids({ desde: "19/10/2026" })).toEqual([5, 4, 3, 2, 1]);
  });
  test("un rango invertido no filtra por fecha (la pagina avisa aparte), pero si por lo demas", () => {
    expect(ids({ desde: "2026-10-20", hasta: "2026-10-18" })).toEqual([5, 4, 3, 2, 1]);
    expect(ids({ desde: "2026-10-20", hasta: "2026-10-18", tipo: "pdf" })).toEqual([4, 2]);
  });
  test("tipo", () => {
    expect(ids({ tipo: "pdf" })).toEqual([4, 2]);
    expect(ids({ tipo: "libro" })).toEqual([5, 3, 1]);
  });
  test("resultado", () => {
    expect(ids({ resultado: "con_errores" })).toEqual([5, 2]);
    expect(ids({ resultado: "solo_advertencias" })).toEqual([4, 1]);
    expect(ids({ resultado: "limpia" })).toEqual([3]);
  });
  test("los filtros se combinan con «y»", () => {
    expect(ids({ tipo: "pdf", resultado: "con_errores" })).toEqual([2]);
    expect(ids({ desde: "2026-10-19", resultado: "solo_advertencias" })).toEqual([4]);
  });
  test("un rango sin coincidencias da lista vacia", () => {
    expect(ids({ desde: "2027-01-01" })).toEqual([]);
  });
});

describe("filtrosInvalidos", () => {
  test("fecha mal escrita o inexistente", () => {
    expect(filtrosInvalidos({ ...FILTROS_VACIOS, desde: "2026-02-30" })).toBe("La fecha «Desde» no es válida: use AAAA-MM-DD.");
    expect(filtrosInvalidos({ ...FILTROS_VACIOS, hasta: "hoy" })).toBe("La fecha «Hasta» no es válida: use AAAA-MM-DD.");
  });
  test("rango invertido", () => {
    expect(filtrosInvalidos({ ...FILTROS_VACIOS, desde: "2026-10-20", hasta: "2026-10-19" })).toBe(
      "La fecha «Desde» es posterior a «Hasta».",
    );
  });
  test("vacios o correctos no avisan", () => {
    expect(filtrosInvalidos(FILTROS_VACIOS)).toBeNull();
    expect(filtrosInvalidos({ ...FILTROS_VACIOS, desde: "2026-10-19", hasta: "2026-10-19" })).toBeNull();
  });
});
