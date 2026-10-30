import { describe, expect, test } from "vitest";
import { ErrorDeApi } from "../../api/cliente";
import {
  TOLERANCIA_MASA,
  armarComponentes,
  desgloseDeTasas,
  fuenteDelPrecio,
  mensajeDePlanta,
  nombreDeLista,
  resumenDeCalculo,
  sumaDeMasa,
} from "./logicaPlanta";

// Lee el valor de Python con Node: con `css: false` ni el .py es un módulo del front.
interface Nodo {
  cwd(): string;
  getBuiltinModule(nombre: "node:fs"): { readFileSync(ruta: string, codificacion: string): string };
}
const nodo = (globalThis as unknown as { process: Nodo }).process;

describe("la tolerancia de masa", () => {
  test("es la misma que TOLERANCIA_MASA de produccion/fuentes.py", () => {
    const fuente = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/../produccion/fuentes.py`, "utf-8");
    const valor = /^TOLERANCIA_MASA = Decimal\("([0-9.]+)"\)/m.exec(fuente)?.[1];
    expect(valor).toBeDefined();
    expect(TOLERANCIA_MASA).toBe(valor);
  });
});

describe("suma de masa", () => {
  const t = (cantidad: string) => ({ cantidad, unidad: "t" });

  test("suma exacta con coma decimal", () => {
    expect(sumaDeMasa([t("0,94"), t("0,05")])).toMatchObject({ texto: "0,99", dentro: true, completa: true });
  });

  test("0,1 + 0,2 es 0,3 exacto, sin error de coma flotante", () => {
    expect(sumaDeMasa([t("0,1"), t("0,2")]).texto).toBe("0,3");
  });

  test("los límites 0,98 y 1,02 entran; 0,979 y 1,021 no", () => {
    expect(sumaDeMasa([t("0,98")]).dentro).toBe(true);
    expect(sumaDeMasa([t("1,02")]).dentro).toBe(true);
    expect(sumaDeMasa([t("0,979")]).dentro).toBe(false);
    expect(sumaDeMasa([t("1,021")]).dentro).toBe(false);
  });

  test("con 30 decimales no pierde ninguno", () => {
    const s = sumaDeMasa([t("0,999999999999999999999999999999"), t("0,000000000000000000000000000001")]);
    expect(s.texto).toBe("1");
    expect(s.dentro).toBe(true);
  });

  test("los litros no cuentan en la masa", () => {
    expect(sumaDeMasa([t("0,94"), t("0,06"), { cantidad: "8", unidad: "l" }]).texto).toBe("1");
  });

  test("una cantidad vacía o mal escrita deja la suma incompleta y fuera", () => {
    expect(sumaDeMasa([t("0,94"), t("")])).toMatchObject({ completa: false, dentro: false });
    expect(sumaDeMasa([t("0,94"), t("0.06")])).toMatchObject({ completa: false, dentro: false });
  });

  test("sin filas no hay suma que aceptar", () => {
    expect(sumaDeMasa([])).toMatchObject({ texto: "0", dentro: false });
  });
});

describe("armar los componentes", () => {
  const fila = (parcial: Record<string, string> = {}) => ({ codigo: "AGR-12", cantidad: "0,94", unidad: "t", tipo: "propio", ...parcial });

  test("devuelve el decimal con punto y el código recortado", () => {
    expect(armarComponentes([fila({ codigo: " AGR-12 " })])).toEqual({
      componentes: [{ codigo: "AGR-12", cantidad_por_t: "0.94", unidad: "t", tipo: "propio" }],
    });
  });

  test("dice qué fila falla y por qué", () => {
    expect(armarComponentes([fila({ codigo: "" })])).toEqual({ error: "Componente 1: escriba el código." });
    expect(armarComponentes([fila(), fila({ codigo: "CA-30", cantidad: "0" })])).toEqual({
      error: "Componente 2: la cantidad debe ser mayor que cero.",
    });
    expect(armarComponentes([fila({ cantidad: "0.94" })])).toMatchObject({ error: expect.stringMatching(/^Componente 1: la cantidad está mal escrita/) });
    expect(armarComponentes([fila({ unidad: "l" })])).toEqual({ error: "Componente 1: un componente propio sale del inventario y va en t." });
    expect(armarComponentes([fila(), fila()])).toEqual({ error: "El código AGR-12 está repetido." });
  });

  test("sin elegir tipo o unidad no se adivina", () => {
    expect(armarComponentes([fila({ tipo: "" })])).toEqual({ error: "Componente 1: elija si es propio o comprado." });
    expect(armarComponentes([fila({ unidad: "" })])).toEqual({ error: "Componente 1: elija la unidad." });
  });
});

describe("textos de la fuente y la lista", () => {
  test("la fuente y el nombre son los del servidor", () => {
    expect(fuenteDelPrecio("2026-11", 7)).toBe("Producción, período 2026-11, cálculo n.º 7");
    expect(nombreDeLista("2026-11", 7)).toBe("Costo propio 2026-11, cálculo n.º 7");
  });
});

describe("tasas faltantes", () => {
  const mensaje =
    "No hay tasa del BCV del mismo día para convertir a USD: costo n.º 7 del 07/11/2026; costo n.º 9 del 08/11/2026. " +
    "Cárguela en Índices y vuelva a calcular; no se calculó nada.";

  test("lista cada costo con su fecha", () => {
    expect(desgloseDeTasas(mensaje)).toEqual({
      encabezado: "No hay tasa del BCV del mismo día para convertir a USD:",
      faltan: ["costo n.º 7 del 07/11/2026", "costo n.º 9 del 08/11/2026"],
      cierre: "Cárguela en Índices y vuelva a calcular; no se calculó nada.",
    });
  });

  test("otro mensaje no se desglosa", () => {
    expect(desgloseDeTasas("No hubo producción en 2026-11.")).toBeNull();
  });
});

describe("mensajes de error", () => {
  test("el detalle del servidor va tal cual", () => {
    expect(mensajeDePlanta(new ErrorDeApi(422, "No hubo producción en 2026-11."))).toBe("No hubo producción en 2026-11.");
  });
  test("nunca el estado ni el cuerpo de una validación", () => {
    expect(mensajeDePlanta(new ErrorDeApi(422, "El programa de Sílice respondió con el estado 422."))).toBe(
      "Revise los datos: alguno no es válido.",
    );
    expect(mensajeDePlanta(new ErrorDeApi(500, "El programa de Sílice respondió con el estado 500."))).not.toMatch(/estado 500/);
  });
  test("403", () => {
    expect(mensajeDePlanta(new ErrorDeApi(403, "Prohibido"))).toBe("Su cuenta no tiene permiso para esta acción.");
  });
});

describe("resumen del cálculo", () => {
  test("lee de la instantánea lo que el servidor guardó", () => {
    const r = resumenDeCalculo({
      entradas: { agregados: ["AGR-12"], producido: { "AGR-12": "150", "MZP-01": "100" } },
      resultado: { total_cantera: "1000", total_planta: "1200", planta_por_t: "12", por_tonelada: {} },
    });
    expect(r).toEqual({
      agregados: ["AGR-12"],
      producido: [
        ["AGR-12", "150"],
        ["MZP-01", "100"],
      ],
      totalCantera: "1000",
      totalPlanta: "1200",
    });
  });
  test("una instantánea rara no rompe la pantalla", () => {
    expect(resumenDeCalculo({})).toEqual({ agregados: [], producido: [], totalCantera: null, totalPlanta: null });
  });
});
