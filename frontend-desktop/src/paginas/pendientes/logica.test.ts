import { describe, expect, test } from "vitest";
import type { PendienteDeObra } from "../../api/tipos";
import { claveDeObra, contarPorObra, destinoDelPendiente, indiceTrasTecla, paginaQueAbre } from "./logica";

// Rediseño F3, Tarea 2 (D-F3-2): la acción de un pendiente abre la sección de su obra que monta la pantalla que la
// fuente nombra (`accion.pagina`, el id de `shell/rutas.ts`). Oráculo escrito a mano desde la tabla de D-F3-2 y las
// rutas de la especificación (§8 ter): `#/obra/<carpeta con .db>/<obra>/<sección>`, `empresa` para la de la empresa, y
// `#/empresa/<entrada>`. Obras y carpetas ficticias.

function pendiente(pagina: string, carpeta: string | null = "Carpeta Norte.db", obraId = 2): PendienteDeObra {
  return {
    carpeta,
    obra_id: obraId,
    obra: "Galpón",
    grupo: "precios",
    urgencia: "aviso",
    texto: "Galpón: precios viejos",
    accion: { texto: "Abrir", pagina },
  };
}

describe("destinoDelPendiente (D-F3-2)", () => {
  test.each([
    ["hoja", "/obra/Carpeta%20Norte.db/2/presupuesto"],
    ["aprobar", "/obra/Carpeta%20Norte.db/2/aprobaciones"],
    ["mercado", "/obra/Carpeta%20Norte.db/2/mercado"],
    ["control", "/obra/Carpeta%20Norte.db/2/control"],
    ["obras", "/obra/Carpeta%20Norte.db/2/resumen"],
  ])("«%s» abre su sección de la obra", (pagina, ruta) => {
    expect(destinoDelPendiente(pendiente(pagina))).toBe(ruta);
  });

  test("«catalogo» abre Empresa › Precios y catálogo", () => {
    expect(destinoDelPendiente(pendiente("catalogo"))).toBe("/empresa/precios");
  });

  test("«actualizacion», que aún no tiene sección, va a Mercado", () => {
    expect(destinoDelPendiente(pendiente("actualizacion"))).toBe("/obra/Carpeta%20Norte.db/2/mercado");
  });

  test("«entregar», que aún no tiene sección, va a Aprobaciones", () => {
    expect(destinoDelPendiente(pendiente("entregar"))).toBe("/obra/Carpeta%20Norte.db/2/aprobaciones");
  });

  test.each(["tablero", "", "toString", "constructor"])("una pantalla desconocida («%s») va al Resumen de la obra", (pagina) => {
    expect(destinoDelPendiente(pendiente(pagina))).toBe("/obra/Carpeta%20Norte.db/2/resumen");
  });

  test("la obra de la carpeta de la empresa (carpeta null) va por `empresa`", () => {
    expect(destinoDelPendiente(pendiente("hoja", null, 7))).toBe("/obra/empresa/7/presupuesto");
  });
});

// Lo que se monta al llegar: con esto la bandeja sabe si la cuenta puede usarlo (foco 1: no ofrecer lo que daría 403).
describe("paginaQueAbre", () => {
  test.each([
    ["hoja", "hoja"],
    ["aprobar", "aprobar"],
    ["catalogo", "catalogo"],
    ["actualizacion", "mercado"],
    ["entregar", "aprobar"],
    ["tablero", "obras"],
  ])("«%s» monta «%s»", (pagina, montada) => {
    expect(paginaQueAbre(pendiente(pagina))).toBe(montada);
  });
});

describe("contarPorObra", () => {
  test("cuenta por carpeta y obra: el mismo id en dos carpetas son dos obras", () => {
    const lista = [
      pendiente("hoja", "Carpeta Norte.db", 2),
      pendiente("aprobar", null, 2),
      pendiente("mercado", "Carpeta Norte.db", 2),
      pendiente("control", "Carpeta Sur.db", 5),
    ];
    expect(contarPorObra(lista)).toEqual(
      new Map([
        ["Carpeta Norte.db|2", 2],
        ["|2", 1],
        ["Carpeta Sur.db|5", 1],
      ]),
    );
  });

  test("sin pendientes, ninguna obra", () => {
    expect(contarPorObra([]).size).toBe(0);
  });

  test("la clave es la carpeta (vacía la de la empresa) y el número de la obra", () => {
    expect(claveDeObra("Carpeta Sur.db", 5)).toBe("Carpeta Sur.db|5");
    expect(claveDeObra(null, 7)).toBe("|7");
  });
});

// Flechas en la lista (patrón listbox de WAI-ARIA): no da la vuelta; Inicio y Fin van a los extremos.
describe("indiceTrasTecla", () => {
  test.each([
    ["ArrowDown", 0, 1],
    ["ArrowDown", 3, 3],
    ["ArrowUp", 2, 1],
    ["ArrowUp", 0, 0],
    ["Home", 2, 0],
    ["End", 0, 3],
  ])("%s desde %i con 4 → %i", (tecla, desde, hasta) => {
    expect(indiceTrasTecla(tecla, desde, 4)).toBe(hasta);
  });

  test("otra tecla no mueve", () => {
    expect(indiceTrasTecla("Enter", 1, 4)).toBeNull();
    expect(indiceTrasTecla("a", 1, 4)).toBeNull();
  });
});
