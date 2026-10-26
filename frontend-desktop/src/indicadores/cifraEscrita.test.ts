import { describe, expect, test } from "vitest";
import { AYUDA_CIFRAS, BLANCOS, MENSAJE_CIFRA, MENSAJE_CIFRA_VACIA, leerCifra, textoParaEscribir } from "./cifraEscrita";

// Regla de Eugenio (2026-10-25): coma para los decimales, punto para los miles. El oraculo es el MISMO archivo, escrito
// a mano, que usa la prueba de `aplicacion/cifras.py` (tests/fixtures/cifras_escritas.json): si la regla del navegador
// y la del servidor se separan, una de las dos pruebas falla.
interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
interface Oraculo {
  mensajes: { vacio: string; formato: string };
  ayuda: string;
  aceptados: { texto: string; valor: string }[];
  rechazados: { texto: string; error: "vacio" | "formato" }[];
  escritura: { valor: string; texto: string }[];
  escritura_no_canonica: { valor: string; texto: string }[];
  blancos: string;
}
const nodo = (globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }).process;
const oraculo = JSON.parse(
  nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/../tests/fixtures/cifras_escritas.json`, "utf-8"),
) as Oraculo;

describe("leerCifra: lo que teclea la persona", () => {
  test("los blancos que se recortan son exactamente los del oraculo (los mismos que en el servidor)", () => {
    expect(BLANCOS).toBe(oraculo.blancos);
  });

  test("los mensajes y la ayuda son los del oraculo compartido", () => {
    expect({ vacio: MENSAJE_CIFRA_VACIA, formato: MENSAJE_CIFRA }).toEqual(oraculo.mensajes);
    expect(AYUDA_CIFRAS).toBe(oraculo.ayuda);
  });

  test.each(oraculo.aceptados)("«$texto» se lee $valor (con punto, para la API)", ({ texto, valor }) => {
    expect(leerCifra(texto)).toEqual({ valor });
  });

  test.each(oraculo.rechazados)("«$texto» se rechaza ($error)", ({ texto, error }) => {
    expect(leerCifra(texto)).toEqual({ error: oraculo.mensajes[error] });
  });

  test("el mil con punto no se lee como uno (el defecto que motivo la regla)", () => {
    expect(leerCifra("1.000")).toEqual({ valor: "1000" });
  });

  test("una cifra de 40 cifras no pierde ninguna (nunca pasa por Number)", () => {
    expect(leerCifra("1.234.567.890.123.456.789.012.345.678.901.234.567.890,123456789")).toEqual({
      valor: "1234567890123456789012345678901234567890.123456789",
    });
  });
});

describe("textoParaEscribir: el decimal de la API en un campo editable", () => {
  test.each(oraculo.escritura)("$valor se escribe «$texto»", ({ valor, texto }) => {
    expect(textoParaEscribir(valor)).toBe(texto);
  });

  test.each(oraculo.escritura_no_canonica)("$valor (no canonico) se escribe «$texto», como en el servidor", ({ valor, texto }) => {
    expect(textoParaEscribir(valor)).toBe(texto);
  });

  test("un exponente no es un texto de la API: se deja como llego (solo el servidor lo escribe)", () => {
    expect(textoParaEscribir("1E+3")).toBe("1E+3");
  });

  // «3.000» (tres, con tres decimales) se escribe «3,000» y vuelve como 3.000, nunca como 3000.
  test.each(oraculo.escritura)("$valor vuelve igual tras escribirse (ida y vuelta)", ({ valor }) => {
    expect(leerCifra(textoParaEscribir(valor))).toEqual({ valor });
  });
});
