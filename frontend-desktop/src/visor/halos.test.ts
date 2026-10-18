import { describe, expect, test } from "vitest";
import type { HallazgoLibroRespuesta, HojaVisualRespuesta } from "../api/tipos";
import { construirHalos, estiloDeHallazgo } from "./halos";

function hallazgo(parcial: Partial<HallazgoLibroRespuesta>): HallazgoLibroRespuesta {
  return {
    codigo: "L1",
    severidad: "ERROR",
    descripcion: "Descripcion",
    celda: "PRESUPUESTO!F12",
    impacto: null,
    accion: "Revisar",
    ...parcial,
  };
}

function hojaVisible(nombre: string): HojaVisualRespuesta {
  return {
    nombre,
    visible: true,
    filas: 30,
    columnas: 10,
    anchos: {},
    altos: {},
    ocultas_filas: [],
    ocultas_columnas: [],
    combinadas: [],
    fijas: null,
    celdas: [],
  };
}

describe("estiloDeHallazgo", () => {
  test("CRITICO usa el rojo, el icono de error y el texto Critico", () => {
    expect(estiloDeHallazgo(hallazgo({ severidad: "CRITICO" }))).toEqual({
      token: "--silice-sev-critico",
      icono: "ErrorFilled",
      texto: "Crítico",
    });
  });

  test("ERROR, ADVERTENCIA e INFO tienen cada uno el suyo", () => {
    expect(estiloDeHallazgo(hallazgo({ severidad: "ERROR" }))).toEqual({
      token: "--silice-sev-error",
      icono: "WarningFilled",
      texto: "Error",
    });
    expect(estiloDeHallazgo(hallazgo({ severidad: "ADVERTENCIA" }))).toEqual({
      token: "--silice-sev-advertencia",
      icono: "WarningAltFilled",
      texto: "Advertencia",
    });
    expect(estiloDeHallazgo(hallazgo({ severidad: "INFO" }))).toEqual({
      token: "--silice-sev-info",
      icono: "InformationFilled",
      texto: "Información",
    });
  });

  test("el codigo ATIPICO es morado cualquiera sea su severidad", () => {
    for (const severidad of ["CRITICO", "ERROR", "ADVERTENCIA", "INFO"]) {
      const estilo = estiloDeHallazgo(hallazgo({ codigo: "ATIPICO", severidad }));
      expect(estilo.token).toBe("--silice-atipico");
      expect(estilo.texto).toBe("Atípico");
    }
  });

  test("una severidad desconocida se muestra como Informacion, nunca se esconde", () => {
    expect(estiloDeHallazgo(hallazgo({ severidad: "RARA" })).texto).toBe("Información");
  });
});

describe("construirHalos", () => {
  test("un hallazgo con celda A1 produce un halo en la misma fila y columna", () => {
    const { halos, sinCelda } = construirHalos([hallazgo({ celda: "PRESUPUESTO!F12" })]);
    expect(sinCelda).toEqual([]);
    expect(halos).toHaveLength(1);
    expect(halos[0]).toMatchObject({ hoja: "PRESUPUESTO", fila0: 11, columna0: 5, indices: [0] });
  });

  test("un hallazgo sin celda ubicable queda fuera de los halos y dentro de sinCelda", () => {
    const hallazgos = [
      hallazgo({ celda: "" }),
      hallazgo({ celda: "APU-01!Rendimiento" }),
      hallazgo({ celda: "PRESUPUESTO!F12" }),
    ];
    const { halos, sinCelda } = construirHalos(hallazgos);
    expect(halos).toHaveLength(1);
    expect(sinCelda).toEqual([0, 1]);
  });

  test("una hoja que el libro no tiene tambien es sin celda", () => {
    const { halos, sinCelda } = construirHalos([hallazgo({ celda: "FANTASMA!A1" })], [hojaVisible("PRESUPUESTO")]);
    expect(halos).toEqual([]);
    expect(sinCelda).toEqual([0]);
  });

  test("un hallazgo en una hoja oculta va a ocultos, con el motivo, y no es sin celda ni halo", () => {
    const { halos, sinCelda, ocultos } = construirHalos(
      [hallazgo({ celda: "AUX!A1" })],
      [hojaVisible("PRESUPUESTO"), { ...hojaVisible("AUX"), visible: false }],
    );
    expect(halos).toEqual([]);
    expect(sinCelda).toEqual([]);
    expect(ocultos).toEqual([{ indice: 0, motivo: "hoja AUX oculta" }]);
  });

  test("una fila oculta dice cual: fila 19 oculta (base 1, como en Excel)", () => {
    const hoja = { ...hojaVisible("PRESUPUESTO"), ocultas_filas: [19] };
    const { halos, ocultos } = construirHalos([hallazgo({ celda: "PRESUPUESTO!F19" })], [hoja]);
    expect(halos).toEqual([]);
    expect(ocultos).toEqual([{ indice: 0, motivo: "fila 19 oculta" }]);
  });

  test("una columna oculta dice la letra, y fila y columna ocultas a la vez, las dos", () => {
    const hoja = { ...hojaVisible("PRESUPUESTO"), ocultas_columnas: [3], ocultas_filas: [5] };
    const columna = construirHalos([hallazgo({ celda: "PRESUPUESTO!C9" })], [hoja]);
    expect(columna.ocultos[0].motivo).toBe("columna C oculta");
    const ambas = construirHalos([hallazgo({ celda: "PRESUPUESTO!C5" })], [hoja]);
    expect(ambas.ocultos[0].motivo).toBe("fila 5 oculta y columna C oculta");
  });

  test("una celda visible de una hoja con filas ocultas sigue teniendo halo", () => {
    const hoja = { ...hojaVisible("PRESUPUESTO"), ocultas_filas: [19] };
    expect(construirHalos([hallazgo({ celda: "PRESUPUESTO!F12" })], [hoja]).halos).toHaveLength(1);
  });

  test("dos hallazgos en la misma celda comparten halo y gana la mayor severidad", () => {
    const { halos } = construirHalos([
      hallazgo({ severidad: "INFO", celda: "H!B2" }),
      hallazgo({ severidad: "CRITICO", celda: "H!B2" }),
    ]);
    expect(halos).toHaveLength(1);
    expect(halos[0].indices).toEqual([0, 1]);
    expect(halos[0].estilo.texto).toBe("Crítico");
  });

  test("un atipico de la misma severidad que otro hallazgo de la celda se queda con el halo morado", () => {
    const { halos } = construirHalos([
      hallazgo({ severidad: "ADVERTENCIA", celda: "H!B2" }),
      hallazgo({ codigo: "ATIPICO", severidad: "ADVERTENCIA", celda: "H!B2" }),
    ]);
    expect(halos[0].estilo.token).toBe("--silice-atipico");
  });
});
