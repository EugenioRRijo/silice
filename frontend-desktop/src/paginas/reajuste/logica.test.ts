import { describe, expect, test } from "vitest";
import {
  armarCuerpo,
  columnasDeResultado,
  filasDeResultado,
  filasVacias,
  formularioInicial,
  hayFilaConDatos,
  quitarFilaVacia,
} from "./logica";

describe("filas editables", () => {
  test("una fila con algun texto tiene datos; en blanco o solo espacios, no", () => {
    expect(hayFilaConDatos({ desde: "", hasta: "  " })).toBe(false);
    expect(hayFilaConDatos({ desde: "2027-02-01", hasta: "" })).toBe(true);
  });

  test("filasVacias arma n filas con las claves dadas", () => {
    expect(filasVacias(["a", "b"], 2)).toEqual([
      { a: "", b: "" },
      { a: "", b: "" },
    ]);
  });

  test("quitarFilaVacia deja siempre al menos una fila", () => {
    expect(quitarFilaVacia([{ a: "x" }], 0)).toEqual([{ a: "" }]);
    expect(quitarFilaVacia([{ a: "x" }, { a: "y" }], 0)).toEqual([{ a: "y" }]);
  });
});

describe("armarCuerpo", () => {
  const base = formularioInicial();

  test("el formulario inicial trae los tres componentes y una fila de periodos y de ejecutado", () => {
    expect(base.componentes.map((c) => c.componente)).toEqual(["materiales", "equipos", "mano_obra"]);
    expect(base.periodos).toHaveLength(1);
    expect(base.ejecutado).toHaveLength(1);
    expect(base.clausula.r_en_comprobacion).toBe("no");
  });

  test("manda el proyecto, la version y los textos tal cual, sin filas en blanco", () => {
    const f = {
      ...base,
      version: "001",
      clausula: { ...base.clausula, fecha_inicio: "2026-01-15", r: "0.10" },
      periodos: [
        { desde: "2027-02-01", hasta: "2027-02-28", version_comprobacion: "002", excepcion: "" },
        { desde: "", hasta: "", version_comprobacion: "", excepcion: "" },
      ],
      ejecutado: [{ periodo: "1", partida: "S1-R01", cantidad: "1000", fuente: "AV-01" }],
    };
    const cuerpo = armarCuerpo("Contrato S1", f);
    expect(cuerpo.proyecto).toBe("Contrato S1");
    expect(cuerpo.version).toBe("001");
    expect(cuerpo.clausula.fecha_inicio).toBe("2026-01-15");
    expect(cuerpo.clausula.r).toBe("0.10");
    expect(cuerpo.periodos).toHaveLength(1);
    expect(cuerpo.ejecutado).toEqual([{ periodo: "1", partida: "S1-R01", cantidad: "1000", fuente: "AV-01" }]);
    expect(cuerpo.con_valuaciones).toBe(false);
  });

  test("la fila de ejecutado que solo trae el numero de periodo es una fila en blanco", () => {
    expect(armarCuerpo("P", { ...base, version: "001" }).ejecutado).toEqual([]);
  });

  test("con valuaciones no manda lo ejecutado a mano", () => {
    const f = { ...base, version: "001", con_valuaciones: true, ejecutado: [{ periodo: "1", partida: "X", cantidad: "1", fuente: "f" }] };
    const cuerpo = armarCuerpo("P", f);
    expect(cuerpo.con_valuaciones).toBe(true);
    expect(cuerpo.ejecutado).toEqual([]);
  });

  test("los tres componentes se mandan siempre, aun sin serie (la API dice cual falta)", () => {
    const cuerpo = armarCuerpo("P", { ...base, version: "001" });
    expect(cuerpo.componentes).toEqual([
      { componente: "materiales", serie: "", peso: "" },
      { componente: "equipos", serie: "", peso: "" },
      { componente: "mano_obra", serie: "", peso: "" },
    ]);
  });
});

describe("resultado", () => {
  const filas = [
    { Período: "01/02/2027 a 28/02/2027", Escalatoria: "15300.00", Comprobación: "16000.00" },
    { Período: "Total", Escalatoria: "15300.00", Comprobación: "16000.00" },
  ];

  test("las columnas numericas son todas salvo Periodo, Mecanismo, Moneda y Marcas", () => {
    const columnas = columnasDeResultado(["Período", "Escalatoria", "Mecanismo", "Moneda", "Tasa", "Marcas"]);
    expect(columnas.map((c) => [c.clave, c.numerica === true])).toEqual([
      ["Período", false],
      ["Escalatoria", true],
      ["Mecanismo", false],
      ["Moneda", false],
      ["Tasa", true],
      ["Marcas", false],
    ]);
  });

  test("filasDeResultado les pone un id y conserva el texto de la API", () => {
    const resultado = filasDeResultado(filas);
    expect(resultado.map((f) => f.id)).toEqual(["0", "1"]);
    expect(resultado[0].Escalatoria).toBe("15300.00");
  });
});
