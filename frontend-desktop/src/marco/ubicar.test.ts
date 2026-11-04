import { describe, expect, test } from "vitest";
import { PAGINAS } from "../shell/rutas";
import { carpetaDelDestino, ubicar } from "./ubicar";
import type { ObraDeCarpeta } from "./useObras";

// F6, T5: la ruta de una subvista (`/obra/<c>/<o>/<seccion>/<subvista>`) se ubica como la de su sección, con un nivel más.
// Oráculos escritos a mano; las obras son ficticias.
const OBRAS: ObraDeCarpeta[] = [
  { carpeta: "Carpeta Sur.db", carpeta_titulo: "Carpeta Sur", obra_id: 3, obra: "Galpón Sur", version_codigo: "002" },
  { carpeta: null, carpeta_titulo: "Carpeta de la empresa", obra_id: 7, obra: "Casa Demo", version_codigo: null },
];

describe("ubicar: la sección de una obra (como antes)", () => {
  test("título y migas de una sección", () => {
    const u = ubicar("/obra/Carpeta%20Sur.db/3/presupuesto", OBRAS, PAGINAS);
    expect(u.titulo).toBe("Presupuesto · Galpón Sur");
    expect(u.migas).toEqual([
      { texto: "Mis obras", ruta: "/pendientes" },
      { texto: "Galpón Sur", ruta: "/obra/Carpeta%20Sur.db/3/resumen" },
      { texto: "Presupuesto" },
    ]);
  });
});

describe("ubicar: la subvista de una sección (F6, T5)", () => {
  test("el título dice la subvista, la sección y la obra", () => {
    expect(ubicar("/obra/empresa/7/control/reajuste", OBRAS, PAGINAS).titulo).toBe("Reajuste · Control de obra · Casa Demo");
    expect(ubicar("/obra/Carpeta%20Sur.db/3/presupuesto/componer", OBRAS, PAGINAS).titulo).toBe("Componer · Presupuesto · Galpón Sur");
    expect(ubicar("/obra/empresa/7/aprobaciones/revisar", OBRAS, PAGINAS).titulo).toBe("Revisar un paquete · Aprobaciones · Casa Demo");
    expect(ubicar("/obra/empresa/7/mercado/actualizar", OBRAS, PAGINAS).titulo).toBe("Actualizar precios · Mercado · Casa Demo");
  });

  test("las migas suman la subvista; la sección pasa a ser un enlace a su pantalla principal", () => {
    expect(ubicar("/obra/Carpeta%20Sur.db/3/control/escenarios", OBRAS, PAGINAS).migas).toEqual([
      { texto: "Mis obras", ruta: "/pendientes" },
      { texto: "Galpón Sur", ruta: "/obra/Carpeta%20Sur.db/3/resumen" },
      { texto: "Control de obra", ruta: "/obra/Carpeta%20Sur.db/3/control" },
      { texto: "Escenarios" },
    ]);
  });

  test("una subvista que no existe se ubica como su sección", () => {
    const u = ubicar("/obra/empresa/7/control/xyz", OBRAS, PAGINAS);
    expect(u.titulo).toBe("Control de obra · Casa Demo");
    expect(u.migas.map((m) => m.texto)).toEqual(["Mis obras", "Casa Demo", "Control de obra"]);
    expect(ubicar("/obra/empresa/7/versiones/xyz", OBRAS, PAGINAS).titulo).toBe("Versiones · Casa Demo");
  });

  test("una sección que no existe, con subvista, solo da el nombre de la obra", () => {
    expect(ubicar("/obra/empresa/7/nada/reajuste", OBRAS, PAGINAS).titulo).toBe("Casa Demo");
  });

  test("una obra que aún no llegó se llama «Obra»", () => {
    expect(ubicar("/obra/empresa/99/control/reajuste", OBRAS, PAGINAS).titulo).toBe("Reajuste · Control de obra · Obra");
  });

  test("más de cuatro segmentos no es una ruta de obra", () => {
    expect(ubicar("/obra/empresa/7/control/reajuste/mas", OBRAS, PAGINAS).migas).toEqual([]);
  });
});

describe("carpetaDelDestino con subvista", () => {
  test("la carpeta se lee igual con y sin subvista, y con consulta", () => {
    expect(carpetaDelDestino("/obra/Carpeta%20Sur.db/3/presupuesto/componer")).toBe("Carpeta Sur.db");
    expect(carpetaDelDestino("/obra/empresa/7/control/reajuste?x=1")).toBeNull();
    expect(carpetaDelDestino("/obra/empresa/7/control")).toBeNull();
  });

  test("lo que no es una obra da undefined", () => {
    expect(carpetaDelDestino("/precios/catalogo")).toBeUndefined();
    expect(carpetaDelDestino("/obra/empresa/0/control/reajuste")).toBeUndefined();
    expect(carpetaDelDestino("/obra/empresa/7/control/reajuste/mas")).toBeUndefined();
  });
});
