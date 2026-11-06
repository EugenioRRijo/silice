import { describe, expect, test } from "vitest";
import { filtrarPorPalabras, plano } from "./normalizar";

// Dictamen de la ronda 2 del autocompletado (MENOR 5): el refactor b20c41da cambio la normalizacion sin una prueba que dijera
// que hace. Oraculos a mano.

describe("plano: sin tildes ni mayusculas", () => {
  test("quita la tilde, la dieresis y la virgulilla, y pasa a minusculas", () => {
    expect(plano("Tubería")).toBe("tuberia");
    expect(plano("PINGÜINO")).toBe("pinguino");
    expect(plano("Cañería")).toBe("caneria");
  });

  // Decision: la ñ pierde su virgulilla («año» y «ano» se buscan igual). Una busqueda debe encontrar de mas antes que callar:
  // quien escribe «caneria» en un teclado sin ñ busca «Cañería», y lo que sobra lo descarta la persona al leer la lista. Es
  // la misma regla de los otros normalizadores de la interfaz (marco/busqueda, hoja, consulta) y de aplicacion/casos.py.
  test("la ñ se busca como n (decision: una busqueda no calla lo que la persona no pudo teclear)", () => {
    expect(plano("año")).toBe("ano");
    expect(plano("Ñandú")).toBe("nandu");
  });

  test("conserva los signos sueltos que no son marcas combinadas: ^ ` ´ ¨ · (no son tildes de ninguna letra)", () => {
    expect(plano("x^2")).toBe("x^2");
    expect(plano("a`b")).toBe("a`b");
    expect(plano("a´b")).toBe("a´b");
    expect(plano("a¨b")).toBe("a¨b");
    expect(plano("10·20")).toBe("10·20");
  });

  test("una letra ya compuesta y la misma descompuesta dan lo mismo", () => {
    expect(plano("é")).toBe(plano("é"));
  });
});

describe("filtrarPorPalabras", () => {
  const lista = ["Cañería de cobre", "Canal de drenaje", "Viga x^2"];

  test("todas las palabras, sin tildes ni mayusculas, en cualquier orden", () => {
    expect(filtrarPorPalabras(lista, "COBRE caneria", (t) => t)).toEqual(["Cañería de cobre"]);
  });

  test("un signo escrito solo busca ese signo, no todo", () => {
    expect(filtrarPorPalabras(lista, "^", (t) => t)).toEqual(["Viga x^2"]);
  });
});
