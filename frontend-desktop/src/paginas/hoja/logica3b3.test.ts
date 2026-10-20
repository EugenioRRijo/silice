import { describe, expect, test } from "vitest";
import {
  clavesDeAuditoria,
  fechaCorta,
  hallazgosDeOrigen,
  partirColumnasDePrecios,
  rotuloDeOrigen,
  rutaDeAtipicos,
  rutaDePrecios,
  rutaDeTrazabilidad,
  rutaDeVista,
} from "./logica";
import { informeAuditoria, preciosRespuesta } from "./datosDePrueba";

// Lógica pura de la rebanada 3b-3: Punto de equilibrio, Parámetros, Auditoría, Precios y Trazabilidad.
describe("lógica de la hoja, 3b-3", () => {
  test("las rutas de las vistas nuevas y las de lectura de versión guardada", () => {
    expect(rutaDeVista("abc", "equilibrio")).toBe("/v1/hoja/borradores/abc/vistas/equilibrio");
    expect(rutaDeVista("abc", "parametros")).toBe("/v1/hoja/borradores/abc/vistas/parametros");
    expect(rutaDeVista("abc", "auditoria")).toBe("/v1/hoja/borradores/abc/vistas/auditoria");
    expect(rutaDePrecios("OF 001", "002")).toBe("/v1/hoja/precios?proyecto=OF+001&version=002");
    expect(rutaDeAtipicos("OF-001", "002")).toBe("/v1/hoja/precios/atipicos?proyecto=OF-001&version=002");
    expect(rutaDeTrazabilidad("OF-001", "002")).toBe("/v1/hoja/trazabilidad?proyecto=OF-001&version=002");
  });

  test("la clave de fila del servidor se lee como la persona la nombra, sin códigos crudos", () => {
    expect(rotuloDeOrigen("esp_puntos:P1")).toBe("Punto P1");
    expect(rotuloDeOrigen("esp_ambientes:BAN-01")).toBe("Ambiente BAN-01");
    expect(rotuloDeOrigen("esp_fuentes:F1")).toBe("Fuente F1");
    expect(rotuloDeOrigen("AF-LLAVE|esp_puntos:P1")).toBe("AF-LLAVE, Punto P1");
    expect(rotuloDeOrigen("AF-LLAVE|esp_puntos:P1#2")).toBe("AF-LLAVE, Punto P1 (2)");
    expect(rotuloDeOrigen("AF-LLAVE")).toBe("AF-LLAVE");
  });

  test("las claves con que un renglón del presupuesto se busca en la auditoría", () => {
    expect(clavesDeAuditoria("AF-LLAVE|esp_puntos:P1")).toEqual(["AF-LLAVE|esp_puntos:P1", "esp_puntos:P1"]);
    expect(clavesDeAuditoria("AF-LLAVE|esp_puntos:P1#2")).toEqual([
      "AF-LLAVE|esp_puntos:P1#2",
      "AF-LLAVE|esp_puntos:P1",
      "esp_puntos:P1",
    ]);
    expect(clavesDeAuditoria("esp_fuentes:F1")).toEqual(["esp_fuentes:F1"]);
  });

  test("3b-F6b: los hallazgos de una fila son los que la nombran en su origen", () => {
    const { hallazgos } = informeAuditoria();
    expect(hallazgosDeOrigen(hallazgos, ["esp_fuentes:F1"]).map((h) => h.numero)).toEqual([1]);
    expect(hallazgosDeOrigen(hallazgos, ["AF-LLAVE|esp_puntos:P1", "esp_puntos:P1"]).map((h) => h.numero)).toEqual([2]);
    expect(hallazgosDeOrigen(hallazgos, ["esp_puntos:P9"])).toEqual([]);
  });

  test("3b-F10: la tabla de precios muestra las columnas principales y el resto va al detalle del insumo", () => {
    const { columnas } = preciosRespuesta();
    expect(columnas).toHaveLength(21);
    const { principales, detalle } = partirColumnasDePrecios(columnas, false);
    expect(principales.map((c) => c.rotulo)).toEqual([
      "Insumo",
      "Código",
      "Precio",
      "Lista",
      "Moneda",
      "Fecha del precio",
      "Referencia",
      "Cotización",
      "Estado",
    ]);
    // «Erosión por índice» no se ofrece si ningún valor viene (nunca se llenaba en la clásica, DV-11).
    expect(detalle.map((c) => c.rotulo)).toEqual([
      "Tipo",
      "Tasa",
      "Fecha de la tasa",
      "Moneda original",
      "Precio original",
      "Fuente de la tasa",
      "Fuente",
      "Propio/heredado",
      "Erosión USD",
      "Erosión Bs",
      "Erosión %",
    ]);
    expect(partirColumnasDePrecios(columnas, true).detalle.map((c) => c.rotulo)).toContain("Erosión por índice");
  });

  test("las fechas ISO se leen día/mes/año; lo que no es una fecha queda igual", () => {
    expect(fechaCorta("2026-07-01")).toBe("01/07/2026");
    expect(fechaCorta("2026-10-06 09:30:00")).toBe("06/10/2026 09:30:00");
    expect(fechaCorta("2026-10-06T09:30:00")).toBe("06/10/2026 09:30:00"); // la hora ISO del servidor
    expect(fechaCorta("")).toBe("");
    expect(fechaCorta("hoy")).toBe("hoy");
  });
});
