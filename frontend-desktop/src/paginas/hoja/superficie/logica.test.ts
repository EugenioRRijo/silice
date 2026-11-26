import { describe, expect, it } from "vitest";
import type { HallazgoInformeRespuesta, InformeAuditoriaRespuesta } from "../../../api/tipos";
import type { FilaPresupuesto, VistaPresupuesto } from "../logica";
import {
  cuentaDeProblemas,
  filaDelHallazgo,
  filasDeLaGrilla,
  fraseDeRespuesta,
  gruposDeProblemas,
} from "./logica";

function crearFila(parcial: Partial<FilaPresupuesto> & Pick<FilaPresupuesto, "clave" | "partida">): FilaPresupuesto {
  return {
    clave: parcial.clave,
    partida: parcial.partida,
    descripcion: parcial.descripcion ?? `Descripción de ${parcial.partida}`,
    unidad: parcial.unidad ?? "m2",
    cantidad: parcial.cantidad ?? "10,00",
    cantidad_calculada: parcial.cantidad_calculada ?? "10,00",
    escrita: parcial.escrita ?? false,
    pu: parcial.pu === undefined ? { texto: "25,50", exacto: "25.5" } : parcial.pu,
    total: parcial.total === undefined ? { texto: "255,00", exacto: "255" } : parcial.total,
    estado: parcial.estado ?? { severidad: null, texto: "" },
    quitable: parcial.quitable ?? true,
    nota: parcial.nota ?? null,
    calculo: parcial.calculo ?? null,
    ...(parcial.de_tramo !== undefined ? { de_tramo: parcial.de_tramo } : {}),
  };
}

function crearVista(parcial: Partial<VistaPresupuesto> = {}): VistaPresupuesto {
  return {
    filas: parcial.filas ?? [
      crearFila({ clave: "CIM-01|manual", partida: "CIM-01", descripcion: "Excavación a mano" }),
      crearFila({ clave: "MUR-02|manual", partida: "MUR-02", descripcion: "Muro de bloques" }),
    ],
    total: parcial.total ?? { texto: "1234567.89", exacto: "1234567.89" },
    moneda: parcial.moneda ?? "Bs",
    vacio_mensaje: parcial.vacio_mensaje ?? null,
    impuestos: parcial.impuestos ?? {
      subtotal: "1234567.89",
      iva: "197530.86",
      total: "1432098.75",
      alicuota: "0.16",
      fuente_alicuota: "Referencia 16 %",
    },
  };
}

function crearHallazgo(
  parcial: Partial<HallazgoInformeRespuesta> & Pick<HallazgoInformeRespuesta, "numero" | "regla" | "severidad">,
): HallazgoInformeRespuesta {
  return {
    numero: parcial.numero,
    regla: parcial.regla,
    severidad: parcial.severidad,
    partida: parcial.partida ?? null,
    descripcion: parcial.descripcion ?? `Detalle del hallazgo ${parcial.numero}`,
    impacto: parcial.impacto ?? null,
    observado: parcial.observado ?? null,
    esperado: parcial.esperado ?? null,
    origen: parcial.origen ?? [],
  };
}

function crearInforme(parcial: Partial<InformeAuditoriaRespuesta> = {}): InformeAuditoriaRespuesta {
  const hallazgos = parcial.hallazgos ?? [];
  return {
    codigo_presupuesto: parcial.codigo_presupuesto ?? "OBRA-FICTICIA",
    cumple: parcial.cumple ?? hallazgos.length === 0,
    veredicto: parcial.veredicto ?? "REVISADO",
    total_hallazgos: parcial.total_hallazgos ?? hallazgos.length,
    por_severidad: parcial.por_severidad ?? [],
    reglas_evaluadas: parcial.reglas_evaluadas ?? [
      { regla: "R01", nombre: "Rendimiento fuera de rango", hallazgos: 0 },
      { regla: "R02", nombre: "Insumos sin respaldo reciente", hallazgos: 0 },
    ],
    hallazgos,
    sin_hallazgos:
      parcial.sin_hallazgos !== undefined
        ? parcial.sin_hallazgos
        : hallazgos.length === 0
          ? "Sílice revisó 18 reglas y no halló problemas."
          : null,
  };
}

describe("cuentaDeProblemas", () => {
  it("cuenta críticos, errores y advertencias, y descarta INFO", () => {
    const filas = [
      crearFila({ clave: "CIM-01|a", partida: "CIM-01" }),
      crearFila({ clave: "MUR-02|b", partida: "MUR-02" }),
      crearFila({ clave: "FRI-01|c", partida: "FRI-01" }),
    ];
    const informe = crearInforme({
      total_hallazgos: 5,
      hallazgos: [
        crearHallazgo({ numero: 1, regla: "R01", severidad: "CRITICO", partida: "CIM-01" }),
        crearHallazgo({ numero: 2, regla: "R02", severidad: "ERROR", partida: "CIM-01" }),
        crearHallazgo({ numero: 3, regla: "R02", severidad: "ADVERTENCIA", origen: ["b"] }),
        crearHallazgo({ numero: 4, regla: "R03", severidad: "INFO", partida: "FRI-01" }),
        crearHallazgo({ numero: 5, regla: "R04", severidad: "INFO", partida: null }),
      ],
    });

    expect(cuentaDeProblemas(informe, filas)).toEqual({
      total: 3,
      criticos: 1,
      errores: 1,
      advertencias: 1,
      partidasConProblemas: 2,
    });
  });

  it("devuelve todo en cero cuando el informe aún no está disponible", () => {
    expect(cuentaDeProblemas(null)).toEqual({
      total: 0,
      criticos: 0,
      errores: 0,
      advertencias: 0,
      partidasConProblemas: 0,
    });
  });
});

describe("filaDelHallazgo", () => {
  it("asocia por clave de auditoría y distingue el origen exacto en PENDIENTE", () => {
    const primera = crearFila({ clave: "MUR-02|tramo_norte#1", partida: "MUR-02" });
    const segunda = crearFila({ clave: "MUR-02|tramo_sur#2", partida: "MUR-02" });
    const tercera = crearFila({ clave: "CIM-01|zapata_1", partida: "CIM-01" });
    const filas = [primera, segunda, tercera];

    const pendienteSur = crearHallazgo({
      numero: 1,
      regla: "PENDIENTE",
      severidad: "ADVERTENCIA",
      partida: "MUR-02",
      origen: ["MUR-02", "tramo_sur"],
    });
    const porOrigen = crearHallazgo({
      numero: 2,
      regla: "R01",
      severidad: "ERROR",
      partida: null,
      origen: ["zapata_1"],
    });
    const sinFila = crearHallazgo({
      numero: 3,
      regla: "R09",
      severidad: "ADVERTENCIA",
      partida: null,
      origen: [],
    });

    expect(filaDelHallazgo(pendienteSur, filas)).toBe(segunda);
    expect(filaDelHallazgo(porOrigen, filas)).toBe(tercera);
    expect(filaDelHallazgo(sinFila, filas)).toBeNull();
  });
});

describe("gruposDeProblemas y hallazgos sin fila", () => {
  it("deja un hallazgo sin fila solo en la lista agrupada y fuera de las filas de la grilla", () => {
    const vista = crearVista({
      filas: [
        crearFila({ clave: "CIM-01|manual", partida: "CIM-01", descripcion: "Excavación a mano" }),
        crearFila({ clave: "MUR-02|manual", partida: "MUR-02", descripcion: "Muro de bloques" }),
      ],
    });
    const informe = crearInforme({
      reglas_evaluadas: [
        { regla: "R01", nombre: "Rendimiento fuera de rango", hallazgos: 1 },
        { regla: "R08", nombre: "Parámetros generales de la obra", hallazgos: 1 },
        { regla: "R10", nombre: "Observaciones informativas", hallazgos: 1 },
      ],
      hallazgos: [
        crearHallazgo({
          numero: 1,
          regla: "R01",
          severidad: "ERROR",
          partida: "CIM-01",
          descripcion: "El rendimiento supera el tope esperado.",
        }),
        crearHallazgo({
          numero: 2,
          regla: "R08",
          severidad: "ADVERTENCIA",
          partida: null,
          origen: [],
          descripcion: "No se declaró la fecha de referencia del contrato.",
        }),
        crearHallazgo({
          numero: 3,
          regla: "R10",
          severidad: "INFO",
          partida: "MUR-02",
          descripcion: "Nota informativa que no es problema.",
        }),
      ],
    });

    const grupos = gruposDeProblemas(informe, vista.filas);
    expect(grupos.map((g) => ({ regla: g.regla, nombre: g.nombre }))).toEqual([
      { regla: "R01", nombre: "Rendimiento fuera de rango" },
      { regla: "R08", nombre: "Parámetros generales de la obra" },
    ]);
    expect(grupos[0]?.problemas[0]).toMatchObject({
      numero: 1,
      palabra: "Error",
      partida: "CIM-01",
      descripcionPartida: "Excavación a mano",
      claveFila: "CIM-01|manual",
      descripcion: "El rendimiento supera el tope esperado.",
    });
    expect(grupos[1]?.problemas[0]).toMatchObject({
      numero: 2,
      palabra: "Advertencia",
      partida: null,
      descripcionPartida: null,
      claveFila: null,
      descripcion: "No se declaró la fecha de referencia del contrato.",
    });

    const filas = filasDeLaGrilla(vista, informe);
    expect(filas[0]?.problemas.map((h) => h.numero)).toEqual([1]);
    expect(filas[1]?.problemas).toEqual([]);
    expect(filas[1]?.problema).toBeNull();
  });
});

describe("filasDeLaGrilla y cifras del servidor", () => {
  it("copia las cifras del servidor sin recalcularlas, marca Pendiente sin precio y resume la peor severidad", () => {
    const vista = crearVista({
      // Deliberadamente distinto de la suma de las filas: jamás debe recalcularse en el cliente.
      total: { texto: "9.876.543,21", exacto: "9876543.21" },
      filas: [
        crearFila({
          clave: "CIM-01|manual",
          partida: "CIM-01",
          cantidad: "3,50",
          pu: { texto: "100,00", exacto: "100" },
          // Deliberadamente distinto de 3,50 × 100,00 para verificar que se copia tal cual del servidor.
          total: { texto: "999.111,22", exacto: "999111.22" },
        }),
        crearFila({
          clave: "FRI-01|manual",
          partida: "FRI-01",
          cantidad: "50",
          pu: null,
          total: null,
        }),
      ],
    });
    const informe = crearInforme({
      hallazgos: [
        crearHallazgo({
          numero: 1,
          regla: "R02",
          severidad: "ADVERTENCIA",
          partida: "CIM-01",
          descripcion: "Insumo con cotización antigua.",
        }),
        crearHallazgo({
          numero: 2,
          regla: "R01",
          severidad: "CRITICO",
          partida: "CIM-01",
          descripcion: "Falta el rendimiento de la cuadrilla.",
        }),
        crearHallazgo({
          numero: 3,
          regla: "PENDIENTE",
          severidad: "ADVERTENCIA",
          partida: "FRI-01",
          origen: ["FRI-01", "manual"],
          descripcion: "Partida pendiente de precio.",
        }),
      ],
    });

    const filas = filasDeLaGrilla(vista, informe);
    expect(filas[0]).toMatchObject({
      clave: "CIM-01|manual",
      cantidad: "3,50",
      puTexto: "100,00",
      totalTexto: "999.111,22",
      sinPrecio: false,
      problema: {
        severidad: "CRITICO",
        palabra: "Crítico",
        texto: "Falta el rendimiento de la cuadrilla.",
        total: 2,
      },
    });
    expect(filas[1]).toMatchObject({
      clave: "FRI-01|manual",
      cantidad: "50",
      puTexto: "Pendiente",
      totalTexto: "Pendiente",
      sinPrecio: true,
      problema: {
        severidad: "ADVERTENCIA",
        palabra: "Advertencia",
        texto: "Partida pendiente de precio.",
        total: 1,
      },
    });
  });
});

describe("fraseDeRespuesta", () => {
  const doceFilas = Array.from({ length: 12 }, (_, indice) => {
    const codigo = `P-${String(indice + 1).padStart(2, "0")}`;
    return crearFila({ clave: `${codigo}|manual`, partida: codigo });
  });

  it("escribe la frase con 0 problemas copiando total y sin_hallazgos del servidor", () => {
    const vista = crearVista({
      filas: doceFilas,
      total: { texto: "1234567.89", exacto: "1234567.89" },
      moneda: "Bs",
    });
    const informe = crearInforme({
      hallazgos: [],
      sin_hallazgos: "Sílice revisó 18 reglas y no halló problemas.",
    });

    expect(fraseDeRespuesta(vista, informe)).toBe(
      "El presupuesto suma 1.234.567,89 Bs sin IVA en 12 partidas. Sílice revisó 18 reglas y no halló problemas.",
    );
  });

  it("no cuenta los hallazgos INFO como problemas en la frase de respuesta", () => {
    const vista = crearVista({
      filas: doceFilas,
      total: { texto: "1234567.89", exacto: "1234567.89" },
      moneda: "Bs",
    });
    const informe = crearInforme({
      sin_hallazgos: null,
      reglas_evaluadas: Array.from({ length: 18 }, (_, i) => ({
        regla: `R${String(i + 1)}`,
        nombre: `Regla ${String(i + 1)}`,
        hallazgos: i === 0 ? 1 : 0,
      })),
      hallazgos: [
        crearHallazgo({ numero: 1, regla: "R1", severidad: "INFO", partida: "P-01" }),
      ],
    });

    expect(fraseDeRespuesta(vista, informe)).toBe(
      "El presupuesto suma 1.234.567,89 Bs sin IVA en 12 partidas. Sílice revisó 18 reglas y no halló problemas.",
    );
  });

  it("escribe la frase en singular cuando hay 1 problema en 1 partida o 1 problema sin fila", () => {
    const vistaUna = crearVista({
      filas: [crearFila({ clave: "CIM-01|manual", partida: "CIM-01" })],
      total: { texto: "500.25", exacto: "500.25" },
      moneda: "Bs",
    });
    const unErrorEnFila = crearInforme({
      hallazgos: [crearHallazgo({ numero: 1, regla: "R01", severidad: "ERROR", partida: "CIM-01" })],
    });
    const unProblemaGlobal = crearInforme({
      hallazgos: [crearHallazgo({ numero: 1, regla: "R08", severidad: "ADVERTENCIA", partida: null })],
    });

    expect(fraseDeRespuesta(vistaUna, unErrorEnFila)).toBe(
      "El presupuesto suma 500,25 Bs sin IVA en 1 partida. 1 partida tiene 1 problema: 1 error.",
    );
    expect(fraseDeRespuesta(vistaUna, unProblemaGlobal)).toBe(
      "El presupuesto suma 500,25 Bs sin IVA en 1 partida. El presupuesto tiene 1 problema: 1 advertencia.",
    );
  });

  it("escribe la frase con N problemas desglosando por severidad y formateando conteos en es-VE", () => {
    const vista = crearVista({
      filas: doceFilas,
      total: { texto: "1234567.89", exacto: "1234567.89" },
      moneda: "Bs",
    });
    const informe = crearInforme({
      hallazgos: [
        crearHallazgo({ numero: 1, regla: "R01", severidad: "ERROR", partida: "P-01" }),
        crearHallazgo({ numero: 2, regla: "R02", severidad: "ADVERTENCIA", partida: "P-02" }),
        crearHallazgo({ numero: 3, regla: "R02", severidad: "ADVERTENCIA", partida: "P-03" }),
      ],
    });

    expect(fraseDeRespuesta(vista, informe)).toBe(
      "El presupuesto suma 1.234.567,89 Bs sin IVA en 12 partidas. 3 partidas tienen problemas: 1 error y 2 advertencias.",
    );

    const milDoscientas = Array.from({ length: 1200 }, (_, indice) => {
      const codigo = `P-${String(indice + 1)}`;
      return crearFila({ clave: `${codigo}|manual`, partida: codigo });
    });
    const vistaGrande = crearVista({
      filas: milDoscientas,
      total: { texto: "80.000.000,00", exacto: "80000000" },
      moneda: "Bs",
    });
    const tresSeveridades = crearInforme({
      hallazgos: [
        crearHallazgo({ numero: 1, regla: "R01", severidad: "CRITICO", partida: "P-1" }),
        crearHallazgo({ numero: 2, regla: "R02", severidad: "ERROR", partida: "P-1" }),
        crearHallazgo({ numero: 3, regla: "R02", severidad: "ERROR", partida: "P-2" }),
        crearHallazgo({ numero: 4, regla: "R03", severidad: "ADVERTENCIA", partida: "P-2" }),
      ],
    });

    expect(fraseDeRespuesta(vistaGrande, tresSeveridades)).toBe(
      "El presupuesto suma 80.000.000,00 Bs sin IVA en 1.200 partidas. 2 partidas tienen problemas: 1 crítico, 2 errores y 1 advertencia.",
    );
  });

  it("cubre los estados vacío, cargando revisión y fallo de la revisión", () => {
    const vacia = crearVista({ filas: [], vacio_mensaje: null });
    expect(fraseDeRespuesta(vacia, null)).toBe("Esta obra aún no tiene partidas");

    const vista = crearVista({
      filas: doceFilas,
      total: { texto: "1234567.89", exacto: "1234567.89" },
      moneda: "Bs",
    });
    expect(fraseDeRespuesta(vista, { estado: "cargando" })).toBe(
      "El presupuesto suma 1.234.567,89 Bs sin IVA en 12 partidas.",
    );
    expect(fraseDeRespuesta(vista, { estado: "error" })).toBe(
      "El presupuesto suma 1.234.567,89 Bs sin IVA en 12 partidas. No se pudo revisar el presupuesto.",
    );
  });
});
