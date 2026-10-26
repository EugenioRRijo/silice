import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ErrorDeApi } from "../api/cliente";
import {
  buscadorDePartidas,
  entradasDeLaLista,
  esAborto,
  gruposDePartidas,
  mensajeDeError,
  moverActiva,
  recortarParaAnuncio,
  rutaDePartidas,
  textoDelMinimo,
  textoDelResultado,
  tramosResaltados,
} from "./logicaBusqueda";
import type { GrupoDeResultados, PartidasHalladas } from "./logicaBusqueda";

// Oráculos escritos a mano desde el diseño de autocompletado (2026-10-21) §3.3, §3.5, §3.6 y §5.4.

function grupo(rotulo: string, n: number, hayMas = false): GrupoDeResultados<string> {
  return {
    rotulo,
    opciones: Array.from({ length: n }, (_, i) => ({ clave: `${rotulo}:${i}`, principal: `${rotulo} ${i}`, secundaria: [], valor: `${i}` })),
    hayMas,
  };
}

describe("moverActiva: flechas, saltos de 5 y vuelta al campo (§3.6)", () => {
  test("↓ desde el campo va a la primera y desde la última vuelve al campo", () => {
    expect(moverActiva(null, "ArrowDown", 3)).toBe(0);
    expect(moverActiva(0, "ArrowDown", 3)).toBe(1);
    expect(moverActiva(2, "ArrowDown", 3)).toBeNull();
  });

  test("↑ desde el campo va a la última y desde la primera vuelve al campo", () => {
    expect(moverActiva(null, "ArrowUp", 3)).toBe(2);
    expect(moverActiva(2, "ArrowUp", 3)).toBe(1);
    expect(moverActiva(0, "ArrowUp", 3)).toBeNull();
  });

  test("RePág y AvPág saltan de 5 en 5 sin salirse de la lista", () => {
    expect(moverActiva(null, "PageDown", 12)).toBe(4);
    expect(moverActiva(4, "PageDown", 12)).toBe(9);
    expect(moverActiva(9, "PageDown", 12)).toBe(11);
    expect(moverActiva(11, "PageUp", 12)).toBe(6);
    expect(moverActiva(3, "PageUp", 12)).toBe(0);
    expect(moverActiva(null, "PageUp", 12)).toBe(0);
  });

  test("sin entradas no hay opción activa", () => {
    expect(moverActiva(null, "ArrowDown", 0)).toBeNull();
    expect(moverActiva(null, "ArrowUp", 0)).toBeNull();
    expect(moverActiva(null, "PageDown", 0)).toBeNull();
  });
});

describe("entradasDeLaLista: opciones, «Ver más resultados» por grupo y el valor propio al final (§3.3-5)", () => {
  test("un grupo con más resultados termina en «Ver más» y el valor propio va al final de todo", () => {
    const entradas = entradasDeLaLista([grupo("A", 2, true), grupo("B", 1)], new Set(), 8, true);
    expect(entradas.map((e) => (e.tipo === "opcion" ? e.opcion.clave : `${e.tipo}${e.tipo === "ver_mas" ? e.grupo : ""}`))).toEqual([
      "A:0",
      "A:1",
      "ver_mas0",
      "B:0",
      "propio",
    ]);
  });

  test("se muestran a lo sumo `limite` opciones por grupo; ampliado, hasta 20 y sin «Ver más»", () => {
    const largo = grupo("A", 25, true);
    expect(entradasDeLaLista([largo], new Set(), 8, false).filter((e) => e.tipo === "opcion")).toHaveLength(8);
    const ampliadas = entradasDeLaLista([largo], new Set([0]), 8, false);
    expect(ampliadas.filter((e) => e.tipo === "opcion")).toHaveLength(20);
    expect(ampliadas.some((e) => e.tipo === "ver_mas")).toBe(false);
  });

  test("sin valor propio no hay última opción propia", () => {
    expect(entradasDeLaLista([grupo("A", 1)], new Set(), 8, false).map((e) => e.tipo)).toEqual(["opcion"]);
  });
});

describe("textos de la región de estado (§3.6)", () => {
  test("cuenta de resultados", () => {
    expect(textoDelResultado(12, "tubo")).toBe("12 resultados. Use las flechas para recorrerlos.");
    expect(textoDelResultado(1, "tubo")).toBe("1 resultado.");
    expect(textoDelResultado(0, "tuberia")).toBe("Sin resultados para «tuberia».");
  });

  test("lo escrito se recorta a 60 caracteres", () => {
    const largo = "a".repeat(70);
    expect(recortarParaAnuncio(largo)).toBe(`${"a".repeat(60)}…`);
    expect(recortarParaAnuncio("corto")).toBe("corto");
    expect(textoDelResultado(0, largo)).toBe(`Sin resultados para «${"a".repeat(60)}…».`);
  });

  test("el mínimo de letras", () => {
    expect(textoDelMinimo(2)).toBe("Escriba al menos 2 letras o un código");
    expect(textoDelMinimo(1)).toBe("Escriba al menos 1 letra o un código");
  });
});

describe("errores de la búsqueda (§3.3-10)", () => {
  test("401 no es un mensaje: la página cierra la sesión", () => {
    expect(mensajeDeError(new ErrorDeApi(401, "La sesión venció."))).toBeNull();
  });

  test("403 dice que la cuenta no puede usar la búsqueda, con el detalle de la API", () => {
    expect(mensajeDeError(new ErrorDeApi(403, "Su cuenta no tiene permiso para esta acción."))).toBe(
      "Su cuenta no puede usar esta búsqueda. Su cuenta no tiene permiso para esta acción.",
    );
  });

  test("422 es un mensaje fijo que no repite lo escrito", () => {
    expect(mensajeDeError(new ErrorDeApi(422, "q demasiado largo: XXXXX"))).toBe("La búsqueda no es válida: escriba otra cosa.");
  });

  test("503 y la red caída muestran el detalle de la API", () => {
    expect(mensajeDeError(new ErrorDeApi(503, "No se pudo leer el catálogo de la carpeta de trabajo."))).toBe(
      "No se pudo leer el catálogo de la carpeta de trabajo.",
    );
    expect(mensajeDeError(new ErrorDeApi(0, "No se pudo hablar con el programa de Sílice."))).toBe(
      "No se pudo hablar con el programa de Sílice.",
    );
  });

  test("cualquier otro fallo tiene un texto llano", () => {
    expect(mensajeDeError(new TypeError("x is undefined"))).toBe("No se pudo buscar. Inténtelo de nuevo.");
  });

  test("un aborto deliberado se reconoce y no es un error que mostrar", () => {
    expect(esAborto(new DOMException("aborted", "AbortError"))).toBe(true);
    expect(esAborto(new ErrorDeApi(0, "No se pudo hablar con el programa de Sílice."))).toBe(false);
    expect(esAborto(null)).toBe(false);
  });
});

describe("tramosResaltados: la parte que coincide, sin HTML (§3.4)", () => {
  test("resalta cada palabra buscada, sin tildes ni mayúsculas, conservando el texto original", () => {
    expect(tramosResaltados("Tubería PVC de 4 pulgadas", "tuberia pvc")).toEqual([
      { texto: "Tubería", resaltado: true },
      { texto: " ", resaltado: false },
      { texto: "PVC", resaltado: true },
      { texto: " de 4 pulgadas", resaltado: false },
    ]);
  });

  test("sin coincidencia es un solo tramo sin resaltar", () => {
    expect(tramosResaltados("Friso liso", "bloque")).toEqual([{ texto: "Friso liso", resaltado: false }]);
  });

  test("el texto con marcas se devuelve tal cual, como texto", () => {
    expect(tramosResaltados("<img src=x onerror=alert(1)>", "img")).toEqual([
      { texto: "<", resaltado: false },
      { texto: "img", resaltado: true },
      { texto: " src=x onerror=alert(1)>", resaltado: false },
    ]);
  });
});

describe("partidas del catálogo (§5.4)", () => {
  const respuesta: PartidasHalladas = {
    rotulo: "Partidas del catálogo",
    resultados: [
      {
        clave: "partida:LB-02-TUB",
        codigo: "LB-02-TUB",
        descripcion: "Suministro e instalación de tubería PVC de 4 pulgadas",
        unidad: "pieza",
        dominio: "civil",
        tiene_composicion: true,
      },
      {
        clave: "partida:PRU-03",
        codigo: "PRU-03",
        descripcion: "Partida ficticia de prueba 03",
        unidad: "m2",
        dominio: "telecom",
        tiene_composicion: false,
      },
    ],
    hay_mas: true,
  };

  test("la ruta lleva el texto codificado, el límite y, si se da, el dominio", () => {
    expect(rutaDePartidas("tubo pvc", 8)).toBe("/v1/buscar/partidas?q=tubo+pvc&limite=8");
    expect(rutaDePartidas("a&b", 20, "civil")).toBe("/v1/buscar/partidas?q=a%26b&limite=20&dominio=civil");
  });

  test("cada partida es una opción: descripción arriba; código, unidad, tipo de obra y composición abajo", () => {
    const [unico] = gruposDePartidas(respuesta);
    expect(unico.rotulo).toBe("Partidas del catálogo");
    expect(unico.hayMas).toBe(true);
    expect(unico.opciones.map((o) => [o.clave, o.principal, o.secundaria])).toEqual([
      [
        "partida:LB-02-TUB",
        "Suministro e instalación de tubería PVC de 4 pulgadas",
        ["LB-02-TUB", "pieza", "obra civil", "con composición"],
      ],
      ["partida:PRU-03", "Partida ficticia de prueba 03", ["PRU-03", "m2", "telecomunicaciones", "sin composición todavía"]],
    ]);
    expect(unico.opciones[0].valor).toBe(respuesta.resultados[0]);
  });

  describe("buscadorDePartidas pide la ruta con la señal de aborto", () => {
    const fetchFalso = vi.fn<typeof fetch>();
    beforeEach(() => {
      vi.stubGlobal("fetch", fetchFalso);
      fetchFalso.mockReset();
    });
    afterEach(() => {
      vi.unstubAllGlobals();
    });

    test("GET a /v1/buscar/partidas con la señal y entrega los grupos", async () => {
      fetchFalso.mockImplementation(async () => new Response(JSON.stringify(respuesta), { status: 200 }));
      const controlador = new AbortController();
      const grupos = await buscadorDePartidas("civil")("tub", controlador.signal, 8);
      expect(fetchFalso.mock.calls[0][0]).toBe("/v1/buscar/partidas?q=tub&limite=8&dominio=civil");
      expect(fetchFalso.mock.calls[0][1]?.signal).toBe(controlador.signal);
      expect(grupos[0].opciones).toHaveLength(2);
    });
  });
});
