import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ErrorDeApi } from "../../api/cliente";
import {
  aceptarPropuesta,
  calcular,
  filasIguales,
  lineaPendiente,
  lineaPropuesta,
  mapeoCodigos,
  periodoAlServidor,
  periodoAVista,
  textoDispersion,
  textoPropuestaRendimiento,
  veredictoLegible,
} from "./logica";
import type { CuerpoCalculo, ItemComputo, RendimientoPorDeclarar } from "./tipos";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const ITEM = (origen: string, codigo: string): ItemComputo => ({
  codigo_partida: codigo,
  descripcion: "Item ficticio",
  unidad: "m3",
  cantidad: "12.5000",
  origen_id: origen,
  origen_tipo: "tabla",
  dominio: "civil",
  regla: null,
  parametros: {},
  especificaciones: {},
});

describe("logica de Elaborar", () => {
  test("el mapeo de codigos civil lleva relleno solo si se pide", () => {
    const base = { concreto: "A", encofrado: "B", excavacion: "C", tuberia: "D" };
    expect(mapeoCodigos({ ...base, relleno: null })).toEqual(base);
    expect(mapeoCodigos({ ...base, relleno: "E" })).toEqual({ ...base, relleno: "E" });
  });

  test("aceptar una propuesta cambia solo el item con ese origen y ese codigo", () => {
    const items = [ITEM("o1", "X"), ITEM("o2", "X"), ITEM("o1", "Y")];
    const nuevos = aceptarPropuesta(items, { origen_id: "o2", codigo_partida: "X" }, "Z");
    expect(nuevos?.map((i) => i.codigo_partida)).toEqual(["X", "Z", "Y"]);
    expect(items[1].codigo_partida).toBe("X"); // no muta
  });

  test("aceptar una propuesta de un item que ya no esta devuelve null", () => {
    expect(aceptarPropuesta([ITEM("o1", "X")], { origen_id: "o9", codigo_partida: "X" }, "Z")).toBeNull();
  });

  test("filasIguales compara periodo, partida y fraccion en orden", () => {
    const a = [{ periodo: "1", codigo_partida: "P", fraccion: "1" }];
    expect(filasIguales(a, [{ ...a[0] }])).toBe(true);
    expect(filasIguales(a, [{ ...a[0], fraccion: "0.5" }])).toBe(false);
    expect(filasIguales(a, [])).toBe(false);
  });

  test("las lineas de pendientes y propuestas siguen el texto de Streamlit", () => {
    expect(lineaPendiente({ origen_id: "o1", codigo_partida: "X", descripcion: "Zanja" })).toBe("o1 · X · Zanja");
    expect(lineaPropuesta({ codigo: "Z", descripcion: "Zanja tipo", puntaje: 0.9137 })).toBe("Z · Zanja tipo (0,91)");
    expect(lineaPropuesta({ codigo: "Z", descripcion: "d", puntaje: 1 })).toBe("Z · d (1,00)");
  });

  // VB-6: las cifras se leen en es-VE (coma decimal, todos sus decimales) y la fecha dd/mm/aaaa; el rango se separa
  // con punto y coma para no confundirlo con la coma decimal.
  test("las lineas de rendimiento muestran las cifras de la API en es-VE, sin redondearlas", () => {
    const entrada: RendimientoPorDeclarar = {
      codigo_partida: "FIC-01",
      propuesta: {
        rendimiento: { valor: "8.123456", tipo: "estimado", fecha: "2026-01-02", condiciones: "", referencia_ejecucion: null },
        dispersion: { observaciones: 3, medidos: 1, estimados: 2, media: "8.10", minimo: "7.50", maximo: "9.00" },
      },
    };
    expect(textoPropuestaRendimiento(entrada)).toBe(
      "rendimiento propuesto 8,123456 unidades por día (estimado del 02/01/2026)",
    );
    expect(textoDispersion(entrada)).toBe(
      "Dispersión del histórico: 3 observaciones (1 medidas, 2 estimadas), media 8,10, rango [7,50; 9,00].",
    );
  });
});

describe("periodos del plan y veredicto (VB-6)", () => {
  test("«Dia N» del nucleo se lee «Día N» y vuelve al servidor como «Dia N»", () => {
    expect(periodoAVista("Dia 1")).toBe("Día 1");
    expect(periodoAVista("Dia 12 [LB-01-EXC]")).toBe("Día 12 [LB-01-EXC]");
    expect(periodoAlServidor("Día 1")).toBe("Dia 1");
    expect(periodoAlServidor("Día 12 [LB-01-EXC]")).toBe("Dia 12 [LB-01-EXC]");
  });
  test("un periodo escrito a mano que no es «Dia N» no se toca", () => {
    for (const p of ["Semana 2", "1", "", "Diario 3", "Día de pago"]) {
      expect(periodoAVista(p)).toBe(p);
      expect(periodoAlServidor(p)).toBe(p);
    }
  });
  test("el veredicto se lee con mayuscula inicial", () => {
    expect(veredictoLegible(true)).toBe("Cumple");
    expect(veredictoLegible(false)).toBe("No cumple");
  });
});

describe("calcular", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
  });
  afterEach(() => vi.unstubAllGlobals());

  const CUERPO: CuerpoCalculo = { codigo: "P-001", fecha: "2026-10-18", moneda: "USD", items: [ITEM("o1", "X")] };

  test("manda el cuerpo por POST con el token y devuelve la respuesta", async () => {
    fetchFalso.mockResolvedValue(json({ total: "10.00" }));
    const r = await calcular(CUERPO, "tok");
    expect(r).toEqual({ tipo: "ok", respuesta: { total: "10.00" } });
    const [ruta, init] = fetchFalso.mock.calls[0];
    expect(ruta).toBe("/presupuestos/calcular");
    expect(init?.method).toBe("POST");
    expect(new Headers(init?.headers).get("X-Silice-CSRF")).toBe("tok");
    expect(JSON.parse(String(init?.body))).toEqual(CUERPO);
  });

  test("un 409 con rendimientos por declarar devuelve la lista", async () => {
    const lista = [{ codigo_partida: "FIC-01", propuesta: null }];
    fetchFalso.mockResolvedValue(json({ detalle: "falta", rendimientos_por_declarar: lista }, 409));
    expect(await calcular(CUERPO, "tok")).toEqual({ tipo: "rendimientos", detalle: "falta", lista });
  });

  test("un 409 sin lista es un error con su detalle", async () => {
    fetchFalso.mockResolvedValue(json({ detalle: "No hay lista de precios vigente.", rendimientos_por_declarar: [] }, 409));
    const error = await calcular(CUERPO, "tok").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ErrorDeApi);
    expect((error as ErrorDeApi).estado).toBe(409);
    expect((error as ErrorDeApi).detalle).toBe("No hay lista de precios vigente.");
  });

  test("otros errores lanzan ErrorDeApi con el detalle", async () => {
    fetchFalso.mockResolvedValue(json({ detail: "plan invalido" }, 422));
    const error = await calcular(CUERPO, "tok").catch((e: unknown) => e);
    expect((error as ErrorDeApi).estado).toBe(422);
    expect((error as ErrorDeApi).detalle).toBe("plan invalido");
  });

  test("sin red lanza ErrorDeApi de estado 0", async () => {
    fetchFalso.mockRejectedValue(new TypeError("red"));
    const error = await calcular(CUERPO, "tok").catch((e: unknown) => e);
    expect((error as ErrorDeApi).estado).toBe(0);
  });
});
