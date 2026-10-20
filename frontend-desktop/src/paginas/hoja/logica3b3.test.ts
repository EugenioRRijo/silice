import { describe, expect, test } from "vitest";
import {
  clavesDeAuditoria,
  periodoSinCodigos,
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

  test("una clave con varios orígenes unidos por «;» nombra cada uno en palabras (clave real de R14)", () => {
    expect(rotuloDeOrigen("AF-LLAVE|esp_fuentes:F1;esp_fuentes:FC1;esp_puntos:P1;esp_puntos:P2;esp_puntos:PC1")).toBe(
      "AF-LLAVE, Fuente F1, Fuente FC1, Punto P1, Punto P2, Punto PC1",
    );
    expect(rotuloDeOrigen("esp_fuentes:F1;esp_puntos:P1")).toBe("Fuente F1, Punto P1");
    // Segmentos: llevan «|» con coordenadas y «;+n» con los que no caben.
    expect(rotuloDeOrigen("AF-TUB|esp_segmentos:F1|0.000,0.000,0.000|0.000,0.000,2.500;+4")).toBe("AF-TUB, Segmento F1 y 4 más");
    expect(rotuloDeOrigen("AF-TUB|esp_segmentos:F1|0.000,0.000,0.000|0.000,0.000,2.500")).toBe("AF-TUB, Segmento F1");
  });

  test("el período se lee sin los códigos entre corchetes", () => {
    expect(periodoSinCodigos("Dia 23 [EL-CAJA]")).toBe("Dia 23");
    expect(periodoSinCodigos("Dia 6 [TI-PTO, TI-UTP, TI-LAP]")).toBe("Dia 6");
    expect(periodoSinCodigos("Dia 7")).toBe("Dia 7");
  });

  test("las claves con que un renglón del presupuesto se busca en la auditoría", () => {
    expect(clavesDeAuditoria("AF-LLAVE|esp_puntos:P1")).toEqual(["AF-LLAVE|esp_puntos:P1", "esp_puntos:P1", "AF-LLAVE"]);
    expect(clavesDeAuditoria("AF-LLAVE|esp_puntos:P1#2")).toEqual([
      "AF-LLAVE|esp_puntos:P1#2",
      "AF-LLAVE|esp_puntos:P1",
      "esp_puntos:P1",
      "AF-LLAVE",
    ]);
    // Una fila con varios orígenes se busca por cada uno de ellos y por su partida.
    expect(clavesDeAuditoria("AF-LLAVE|esp_fuentes:F1;esp_fuentes:FC1;esp_puntos:P1;esp_puntos:P2;esp_puntos:PC1")).toEqual([
      "AF-LLAVE|esp_fuentes:F1;esp_fuentes:FC1;esp_puntos:P1;esp_puntos:P2;esp_puntos:PC1",
      "esp_fuentes:F1",
      "esp_fuentes:FC1",
      "esp_puntos:P1",
      "esp_puntos:P2",
      "esp_puntos:PC1",
      "AF-LLAVE",
    ]);
    expect(clavesDeAuditoria("esp_fuentes:F1")).toEqual(["esp_fuentes:F1"]);
  });

  test("3b-F6b: los hallazgos de una fila son los que la nombran en su origen", () => {
    const { hallazgos } = informeAuditoria();
    expect(hallazgosDeOrigen(hallazgos, ["esp_fuentes:F1"]).map((h) => h.numero)).toEqual([1]);
    expect(hallazgosDeOrigen(hallazgos, ["AF-LLAVE|esp_puntos:P1", "esp_puntos:P1"]).map((h) => h.numero)).toEqual([2]);
    expect(hallazgosDeOrigen(hallazgos, ["esp_puntos:P9"])).toEqual([]);
    // Como la clásica, también se atribuyen por la partida del renglón.
    expect(hallazgosDeOrigen(hallazgos, ["esp_puntos:P9", "AF-LLAVE"]).map((h) => h.numero)).toEqual([2]);
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
