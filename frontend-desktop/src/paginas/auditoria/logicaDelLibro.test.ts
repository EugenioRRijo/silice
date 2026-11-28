import { describe, expect, it } from "vitest";
import { alertasDePrueba, auditoriaDePrueba, auditoriaSinHallazgos, catalogoDePrueba } from "./datosDePrueba";
import {
  anuncioDeResultado,
  avisosDePrecio,
  causasMultiples,
  celdasResumidas,
  cuentaDeHallazgos,
  cuerpoDeLibro,
  desgloseDeSeveridad,
  fechaDeHoy,
  fraseDeLaCausa,
  fraseDeRespuesta,
  hallazgosSueltos,
  noAplicables,
  pasoSiguiente,
  textoDeCasos,
  veredictoDelLibro,
} from "./logicaDelLibro";
import type { AuditoriaDelLibro, CuentaDeHallazgos } from "./logicaDelLibro";

const cuenta = (parcial: Partial<CuentaDeHallazgos> = {}): CuentaDeHallazgos => ({
  critico: 0,
  error: 0,
  advertencia: 0,
  info: 0,
  total: 0,
  ...parcial,
});

describe("cuentaDeHallazgos", () => {
  it("cuenta por severidad y deja fuera los avisos de regla no aplicable", () => {
    expect(cuentaDeHallazgos(auditoriaDePrueba())).toEqual({ critico: 0, error: 8, advertencia: 0, info: 0, total: 8 });
  });

  it("sin hallazgos, todo en cero", () => {
    expect(cuentaDeHallazgos(auditoriaSinHallazgos())).toEqual(cuenta());
  });

  it("una severidad que no se conoce cuenta como información", () => {
    const base = auditoriaDePrueba();
    const a: AuditoriaDelLibro = { ...base, no_aplicables: [], hallazgos: [{ ...base.hallazgos[0], severidad: "RARA" }] };
    expect(cuentaDeHallazgos(a)).toEqual(cuenta({ info: 1, total: 1 }));
  });

  it("ignora una posición de no aplicable que no existe", () => {
    expect(cuentaDeHallazgos(auditoriaDePrueba({ no_aplicables: [99, -1] })).total).toBe(9);
  });

  it("una API anterior sin no_aplicables cuenta todos", () => {
    const sinCampo = { ...auditoriaDePrueba() } as Partial<AuditoriaDelLibro>;
    delete sinCampo.no_aplicables;
    expect(cuentaDeHallazgos(sinCampo as AuditoriaDelLibro).total).toBe(9);
  });
});

describe("fraseDeRespuesta", () => {
  it("cero, uno y varios", () => {
    expect(fraseDeRespuesta(cuenta())).toBe("El libro no tiene hallazgos");
    expect(fraseDeRespuesta(cuenta({ error: 1, total: 1 }))).toBe("1 hallazgo en el libro");
    expect(fraseDeRespuesta(cuenta({ error: 8, total: 8 }))).toBe("8 hallazgos en el libro");
  });

  it("los miles llevan punto", () => {
    expect(fraseDeRespuesta(cuenta({ error: 1200, total: 1200 }))).toBe("1.200 hallazgos en el libro");
  });
});

describe("desgloseDeSeveridad", () => {
  it("dice cada severidad con su palabra, de la más a la menos grave, y omite las que no hay", () => {
    expect(desgloseDeSeveridad(cuenta({ critico: 1, error: 3, advertencia: 3, info: 2, total: 9 }))).toEqual([
      "1 crítico",
      "3 errores",
      "3 advertencias",
      "2 informativos",
    ]);
    expect(desgloseDeSeveridad(cuenta({ error: 1, advertencia: 1, total: 2 }))).toEqual(["1 error", "1 advertencia"]);
    expect(desgloseDeSeveridad(cuenta())).toEqual([]);
  });
});

describe("anuncioDeResultado", () => {
  it("dice el resultado en una frase", () => {
    expect(anuncioDeResultado(cuenta({ error: 3, advertencia: 3, total: 6 }))).toBe(
      "Auditoría lista: 3 errores y 3 advertencias.",
    );
    expect(anuncioDeResultado(cuenta({ error: 1, total: 1 }))).toBe("Auditoría lista: 1 error.");
    expect(anuncioDeResultado(cuenta({ critico: 1, error: 2, advertencia: 4, total: 7 }))).toBe(
      "Auditoría lista: 1 crítico, 2 errores y 4 advertencias.",
    );
    expect(anuncioDeResultado(cuenta())).toBe("Auditoría lista: el libro no tiene hallazgos.");
  });
});

describe("veredictoDelLibro", () => {
  it("cumple sin nada que corregir", () => {
    expect(veredictoDelLibro(true, cuenta())).toEqual({
      cumple: true,
      titulo: "El libro cumple",
      detalle: "Sílice no halló nada que corregir.",
    });
  });

  it("cumple, pero con avisos que confirmar", () => {
    expect(veredictoDelLibro(true, cuenta({ advertencia: 2, total: 2 }))).toEqual({
      cumple: true,
      titulo: "El libro cumple",
      detalle: "Sílice no halló errores; quedan 2 advertencias por confirmar.",
    });
  });

  it("no cumple: dice qué tiene y qué hacer después", () => {
    expect(veredictoDelLibro(false, cuenta({ error: 3, advertencia: 3, total: 6 }))).toEqual({
      cumple: false,
      titulo: "El libro no cumple",
      detalle: "Tiene 3 errores y 3 advertencias. Corríjalos en su Excel y suba el libro de nuevo para comprobarlo.",
    });
  });

  it("la palabra del servidor manda: no cumple aunque la cuenta diga cero", () => {
    expect(veredictoDelLibro(false, cuenta()).cumple).toBe(false);
  });
});

describe("pasoSiguiente", () => {
  it("con algo que entregar, el informe; sin nada, auditar otro libro", () => {
    expect(pasoSiguiente(cuenta({ error: 1, total: 1 }))).toBe("informe");
    expect(pasoSiguiente(cuenta({ info: 1, total: 1 }))).toBe("informe");
    expect(pasoSiguiente(cuenta())).toBe("otro");
  });
});

describe("causasMultiples y hallazgosSueltos", () => {
  it("una causa con varios casos va agrupada y sus casos no se repiten sueltos", () => {
    const a = auditoriaDePrueba();
    expect(causasMultiples(a).map((c) => [c.codigo, c.ocurrencias])).toEqual([["L1", 6]]);
    expect(hallazgosSueltos(a).map((s) => s.hallazgo.codigo)).toEqual(["L4", "L5"]);
  });

  it("los sueltos van de lo más a lo menos grave y, a igual gravedad, en el orden del servidor", () => {
    const base = auditoriaDePrueba();
    const a: AuditoriaDelLibro = {
      ...base,
      causas: [],
      no_aplicables: [],
      hallazgos: [
        { ...base.hallazgos[0], codigo: "X1", severidad: "ADVERTENCIA" },
        { ...base.hallazgos[0], codigo: "X2", severidad: "ERROR" },
        { ...base.hallazgos[0], codigo: "X3", severidad: "CRITICO" },
        { ...base.hallazgos[0], codigo: "X4", severidad: "ERROR" },
      ],
    };
    expect(hallazgosSueltos(a).map((s) => s.hallazgo.codigo)).toEqual(["X3", "X2", "X4", "X1"]);
    expect(hallazgosSueltos(a).map((s) => s.indice)).toEqual([2, 1, 3, 0]);
  });

  it("una API anterior sin causas deja todos los hallazgos sueltos", () => {
    const sinCampo = { ...auditoriaDePrueba() } as Partial<AuditoriaDelLibro>;
    delete sinCampo.causas;
    expect(hallazgosSueltos(sinCampo as AuditoriaDelLibro)).toHaveLength(8);
    expect(causasMultiples(sinCampo as AuditoriaDelLibro)).toEqual([]);
  });

  it("los avisos de regla no aplicable salen aparte y no entre los sueltos", () => {
    const a = auditoriaDePrueba();
    expect(noAplicables(a).map((h) => h.codigo)).toEqual(["R2"]);
    expect(hallazgosSueltos(a).some((s) => s.hallazgo.codigo === "R2")).toBe(false);
  });
});

describe("avisosDePrecio", () => {
  const catalogo = catalogoDePrueba();

  it("los datos de prueba tienen la forma exacta de los mensajes del servidor (fusion/alertas.py): es-VE, tasa sin ceros finales", () => {
    const usdBs = alertasDePrueba().filter((a) => a.tipo === "USD-Bs");
    for (const a of usdBs) {
      expect(a.mensaje).toMatch(
        /^\d{1,3}(\.\d{3})*,\d{2} Bs al \d{4}-\d{2}-\d{2} \(tasa \d{1,3}(\.\d{3})*(,\d*[1-9])?\) y \d{1,3}(\.\d{3})*,\d{2} Bs al \d{4}-\d{2}-\d{2} \(tasa \d{1,3}(\.\d{3})*(,\d*[1-9])?\): [+-]\d+,\d{2} %, (pasa|dentro) del umbral de \d+,\d{2} %$/,
      );
    }
  });

  it("deja las tres alertas de la prueba y calla la que está dentro del umbral", () => {
    const avisos = avisosDePrecio(alertasDePrueba(), catalogo);
    expect(avisos.map((a) => [a.tipo, a.codigos])).toEqual([
      ["sin fuente", ["MT-04"]],
      ["base de la empresa", ["MT-08"]],
      ["USD-Bs", ["MT-08"]],
    ]);
  });

  it("agrupa las que dicen lo mismo y cuenta cuántos precios son", () => {
    const igual = "no contrastable: la instalación no tiene la tasa del BCV de 2026-11-24";
    const base = alertasDePrueba()[0];
    const alertas = ["MT-01", "MT-02", "MT-03"].map((codigo) => ({ ...base, tipo: "USD-Bs", codigo, mensaje: igual }));
    expect(avisosDePrecio(alertas, catalogo)).toEqual([
      { tipo: "USD-Bs", codigos: ["MT-01", "MT-02", "MT-03"], mensaje: igual, cantidad: 3 },
    ]);
  });

  it("no mezcla el mismo mensaje de tipos distintos", () => {
    const base = alertasDePrueba()[0];
    const alertas = [
      { ...base, tipo: "sin fuente", mensaje: "x" },
      { ...base, tipo: "otra versión", mensaje: "x" },
    ];
    expect(avisosDePrecio(alertas, catalogo)).toHaveLength(2);
  });

  it("sin catálogo no calla nada", () => {
    expect(avisosDePrecio(alertasDePrueba(), null)).toHaveLength(4);
  });

  it("sin alertas, nada", () => {
    expect(avisosDePrecio([], catalogo)).toEqual([]);
    expect(avisosDePrecio(undefined, catalogo)).toEqual([]);
  });
});

describe("celdasResumidas", () => {
  it("lista hasta cuatro y dice cuántas más", () => {
    expect(celdasResumidas(["A1", "A2"])).toBe("A1 y A2");
    expect(celdasResumidas(["A1"])).toBe("A1");
    expect(celdasResumidas(["A1", "A2", "A3", "A4"])).toBe("A1, A2, A3 y A4");
    expect(celdasResumidas(["A1", "A2", "A3", "A4", "A5", "A6"])).toBe("A1, A2, A3, A4 y 2 más");
    expect(celdasResumidas([])).toBe("");
  });
});

describe("fechaDeHoy", () => {
  it("es la fecha local, no la de UTC", () => {
    expect(fechaDeHoy(new Date(2026, 10, 27, 23, 59))).toBe("2026-11-27");
    expect(fechaDeHoy(new Date(2026, 0, 5, 0, 1))).toBe("2026-01-05");
  });
});

describe("fraseDeLaCausa y textoDeCasos", () => {
  it("la causa se lee hasta su primer «;»: lo que sigue es detalle del caso", () => {
    expect(fraseDeLaCausa("PRESUPUESTO!F10 lee APU-01!E14 como rendimiento; encontrado 0, esperado 120")).toBe(
      "PRESUPUESTO!F10 lee APU-01!E14 como rendimiento",
    );
    expect(fraseDeLaCausa("  sin punto y coma  ")).toBe("sin punto y coma");
  });

  it("uno y varios casos", () => {
    expect(textoDeCasos(1)).toBe("1 caso");
    expect(textoDeCasos(6)).toBe("6 casos");
    expect(textoDeCasos(1500)).toBe("1.500 casos");
  });
});

describe("cuerpoDeLibro", () => {
  it("lleva el libro y, si hay, la fecha de la revisión", () => {
    const archivo = new File(["x"], "obra.xlsx");
    const con = cuerpoDeLibro(archivo, "2026-11-24");
    expect((con.get("libro") as File).name).toBe("obra.xlsx");
    expect(con.get("fecha_devolucion")).toBe("2026-11-24");
    const sin = cuerpoDeLibro(archivo);
    expect(sin.has("fecha_devolucion")).toBe(false);
    expect(sin.has("libro")).toBe(true);
  });
});
