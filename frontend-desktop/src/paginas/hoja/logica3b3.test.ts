import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
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

  test("una clave con circuitos (OF-001 real) los nombra en palabras", () => {
    expect(rotuloDeOrigen("EL-PROT|esp_fuentes:T1;esp_circuitos:C1;esp_circuitos:C2")).toBe(
      "EL-PROT, Fuente T1, Circuito C1, Circuito C2",
    );
    expect(rotuloDeOrigen("EL-COND-12-AWG|esp_fuentes:T1;esp_circuitos:C1")).toBe("EL-COND-12-AWG, Fuente T1, Circuito C1");
  });

  test("ningún prefijo esp_* de los adaptadores y de la hoja se cuela como código: todos tienen nombre", () => {
    // Barrido de lo que emiten el servidor (`esp_xxx:`) en adapters/espacio y aplicacion/hoja*.py.
    const raiz = resolve(process.cwd(), "..");
    const archivos: string[] = [];
    const recorrer = (dir: string) => {
      for (const e of readdirSync(dir, { withFileTypes: true })) {
        const ruta = resolve(dir, e.name);
        if (e.isDirectory()) recorrer(ruta);
        else if (e.name.endsWith(".py")) archivos.push(ruta);
      }
    };
    recorrer(resolve(raiz, "adapters", "espacio"));
    for (const e of readdirSync(resolve(raiz, "aplicacion"))) {
      if (/^hoja.*\.py$/.test(e)) archivos.push(resolve(raiz, "aplicacion", e));
    }
    const barridos = new Set<string>();
    for (const a of archivos) for (const m of readFileSync(a, "utf-8").matchAll(/(esp_[a-z_]+):/g)) barridos.add(m[1]!);
    // Lista escrita a mano (los nombres de las tablas esp_* del espacio) contrastada con el barrido.
    const conocidos = [
      "esp_ambientes",
      "esp_circuitos",
      "esp_fuentes",
      "esp_origenes",
      "esp_puntos",
      "esp_recorridos",
      "esp_segmentos",
      "esp_sobrescrituras",
      "esp_tramos",
    ];
    expect(barridos.size).toBeGreaterThan(3);
    for (const p of barridos) expect(conocidos, p).toContain(p);
    for (const p of conocidos) {
      expect(rotuloDeOrigen(`${p}:X1`), p).not.toMatch(/esp_/);
      expect(rotuloDeOrigen(`AF-X|${p}:X1`), p).not.toMatch(/esp_/);
    }
  });

  test("un prefijo esp_* desconocido nunca llega como código: cae a «Origen X»", () => {
    expect(rotuloDeOrigen("esp_zzz:Q9")).toBe("Origen Q9");
    expect(rotuloDeOrigen("AF-X|esp_zzz:Q9;esp_puntos:P1")).toBe("AF-X, Origen Q9, Punto P1");
  });

  test("una clave sin partida con un segmento no toma el «|» del segmento por la partida", () => {
    expect(rotuloDeOrigen("esp_segmentos:F1|0.000,0.000,0.000|0.000,0.000,2.500;+4")).toBe("Segmento F1 y 4 más");
  });

  test("como la clásica, un hallazgo PENDIENTE no se atribuye a toda la partida, solo al renglón que lo cita", () => {
    const base = informeAuditoria().hallazgos[1]!;
    const pendiente = { ...base, numero: 9, regla: "PENDIENTE", partida: "AF-SALIDA", origen: ["esp_puntos:P2"] };
    expect(hallazgosDeOrigen([pendiente], ["AF-SALIDA|esp_puntos:P3", "esp_puntos:P3", "AF-SALIDA"])).toEqual([]);
    expect(hallazgosDeOrigen([pendiente], ["AF-SALIDA|esp_puntos:P2", "esp_puntos:P2", "AF-SALIDA"])).toHaveLength(1);
  });
});
