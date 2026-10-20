import { describe, expect, test } from "vitest";
import { vistaParametros, vistaPlan, vistaPresupuesto } from "./datosDePrueba";
import {
  CAMPOS_DE_PARAMETROS,
  cambiarCantidad,
  cambiarFraccion,
  FRASES_DE_RECHAZO,
  claseDeConflicto,
  cuerpoDeCantidades,
  cuerpoDeParametros,
  cuerpoDelPlan,
  rutaDeCantidades,
  rutaDeParametros,
  rutaDePlan,
  rutaDePlanSecuencial,
  sembrarCantidades,
  sembrarParametros,
  sembrarPlan,
  ubicarErrorDeCantidad,
  ubicarErrorDeParametro,
  ubicarErrorDePlan,
} from "./logicaSecciones";
import { mensajeDeRechazo } from "./logica";

// Rebanada 3c-2 (cantidades, parámetros y plan): lógica pura. Los literales salen del diseño (§4.4 E2 a E5, §2.5.3,
// §2.5.4, §2.5.7, §6.2 3c-B2, B5, B12) y de la página clásica (ui/hoja.py: H:855-863 cantidades, H:1124 parámetros,
// H:1202-1212 plan), no del código bajo prueba.

describe("edición por sección (3c-2): rutas", () => {
  test("E2 a E5 cuelgan del borrador", () => {
    expect(rutaDeCantidades("abc_123-xyz")).toBe("/v1/hoja/borradores/abc_123-xyz/cantidades");
    expect(rutaDeParametros("abc_123-xyz")).toBe("/v1/hoja/borradores/abc_123-xyz/parametros");
    expect(rutaDePlan("abc_123-xyz")).toBe("/v1/hoja/borradores/abc_123-xyz/plan");
    expect(rutaDePlanSecuencial("abc_123-xyz")).toBe("/v1/hoja/borradores/abc_123-xyz/plan/secuencial");
  });
});

describe("edición por sección (3c-2): cantidades (E2)", () => {
  const filas = vistaPresupuesto().filas;

  test("sembrar: el texto de cada renglón es su cantidad tal como llegó y ninguno está tocado", () => {
    expect(sembrarCantidades(filas)).toEqual({
      orden: ["AF-LLAVE|esp_puntos:P1", "AF-SALIDA|esp_puntos:P2"],
      textos: { "AF-LLAVE|esp_puntos:P1": "3", "AF-SALIDA|esp_puntos:P2": "5" },
      tocadas: [],
    });
  });

  test("cambiar marca el renglón como tocado, una sola vez, y no muta lo anterior", () => {
    const inicial = sembrarCantidades(filas);
    const uno = cambiarCantidad(inicial, "AF-LLAVE|esp_puntos:P1", "5");
    expect(uno.textos["AF-LLAVE|esp_puntos:P1"]).toBe("5");
    expect(uno.tocadas).toEqual(["AF-LLAVE|esp_puntos:P1"]);
    const dos = cambiarCantidad(uno, "AF-LLAVE|esp_puntos:P1", "51");
    expect(dos.tocadas).toEqual(["AF-LLAVE|esp_puntos:P1"]);
    expect(inicial.tocadas).toEqual([]);
    expect(inicial.textos["AF-LLAVE|esp_puntos:P1"]).toBe("3");
  });

  test("el cuerpo lleva el rev y solo las filas tocadas, en el orden de la tabla, con el texto tal cual", () => {
    let e = sembrarCantidades(filas);
    expect(cuerpoDeCantidades(0, e)).toEqual({ rev: 0, filas: [] });
    e = cambiarCantidad(e, "AF-SALIDA|esp_puntos:P2", "7,5");
    e = cambiarCantidad(e, "AF-LLAVE|esp_puntos:P1", "0007e3");
    expect(cuerpoDeCantidades(4, e)).toEqual({
      rev: 4,
      filas: [
        { clave: "AF-LLAVE|esp_puntos:P1", cantidad: "0007e3" },
        { clave: "AF-SALIDA|esp_puntos:P2", cantidad: "7,5" },
      ],
    });
  });

  test("ubicar: «presupuesto, fila n (…)» da la fila desde 1; otro mensaje no da ninguna", () => {
    expect(
      ubicarErrorDeCantidad(
        "presupuesto, fila 12 (AF-LLAVE): la cantidad no puede ser negativa; escriba cero o una cantidad positiva",
      ),
    ).toBe(12);
    expect(ubicarErrorDeCantidad("presupuesto, fila 2 (AF-SALIDA): '2,5' no es un numero decimal valido")).toBe(2);
    expect(ubicarErrorDeCantidad("El borrador cambió en otra ventana: vuelva a cargarlo.")).toBeNull();
  });
});

describe("edición por sección (3c-2): parámetros (E3)", () => {
  test("los cuatro campos, en el orden de la clásica", () => {
    expect([...CAMPOS_DE_PARAMETROS]).toEqual(["fcas", "bono_alimentacion", "administracion", "utilidad"]);
  });

  test("sembrar guarda el valor de cada campo como texto", () => {
    expect(sembrarParametros(vistaParametros().campos)).toEqual({
      fcas: "6.00",
      bono_alimentacion: "5.8100",
      administracion: "0.15",
      utilidad: "0.10",
    });
  });

  test("el cuerpo lleva el rev y los cuatro textos; el que falte va vacío, y nada se convierte", () => {
    expect(cuerpoDeParametros(2, { fcas: "6.00", bono_alimentacion: "5.8100", administracion: "0,20", utilidad: "0.10" })).toEqual({
      rev: 2,
      fcas: "6.00",
      bono_alimentacion: "5.8100",
      administracion: "0,20",
      utilidad: "0.10",
    });
    expect(cuerpoDeParametros(0, { fcas: "1" })).toEqual({ rev: 0, fcas: "1", bono_alimentacion: "", administracion: "", utilidad: "" });
  });

  test("ubicar: «parametros: {campo}: …» da el campo y su texto propio; sin campo conocido, nada", () => {
    expect(ubicarErrorDeParametro("parametros: utilidad: 'mucho' no es un numero decimal valido")).toEqual({
      campo: "utilidad",
      texto: "'mucho' no es un numero decimal valido",
    });
    expect(ubicarErrorDeParametro("parametros: bono_alimentacion: 'x' no es un numero decimal valido")?.campo).toBe(
      "bono_alimentacion",
    );
    expect(ubicarErrorDeParametro("parametros: otra cosa")).toBeNull();
    expect(ubicarErrorDeParametro("parametros: zeta: 'x' no es un numero decimal valido")).toBeNull();
    expect(ubicarErrorDeParametro("El borrador cambió en otra ventana: vuelva a cargarlo.")).toBeNull();
  });
});

describe("edición por sección (3c-2): plan (E4)", () => {
  test("sembrar copia las etiquetas y las fracciones como texto", () => {
    expect(sembrarPlan(vistaPlan())).toEqual({
      etiquetas: ["Dia 1", "Dia 2"],
      filas: [
        { partida: "AF-CODO-1/2", valores: { "Dia 1": "1", "Dia 2": "0" } },
        { partida: "AF-LLAVE", valores: { "Dia 1": "0", "Dia 2": "1" } },
      ],
    });
  });

  test("cambiar una fracción no muta lo anterior y solo toca esa celda", () => {
    const inicial = sembrarPlan(vistaPlan());
    const nuevo = cambiarFraccion(inicial, "AF-LLAVE", "Dia 1", "0.5");
    expect(nuevo.filas[1]!.valores).toEqual({ "Dia 1": "0.5", "Dia 2": "1" });
    expect(nuevo.filas[0]).toEqual(inicial.filas[0]);
    expect(inicial.filas[1]!.valores["Dia 1"]).toBe("0");
  });

  test("el cuerpo es la matriz completa con una fracción por etiqueta (vacía si falta) y los textos sin convertir", () => {
    const e = cambiarFraccion(sembrarPlan(vistaPlan()), "AF-CODO-1/2", "Dia 2", "0.333333333333333333333333333333");
    expect(cuerpoDelPlan(3, e)).toEqual({
      rev: 3,
      etiquetas: ["Dia 1", "Dia 2"],
      filas: [
        { partida: "AF-CODO-1/2", valores: { "Dia 1": "1", "Dia 2": "0.333333333333333333333333333333" } },
        { partida: "AF-LLAVE", valores: { "Dia 1": "0", "Dia 2": "1" } },
      ],
    });
    expect(cuerpoDelPlan(0, { etiquetas: ["Dia 1"], filas: [{ partida: "X", valores: {} }] }).filas[0]!.valores).toEqual({ "Dia 1": "" });
  });

  test("ubicar: «plan, partida {c}: …» da la partida; el mensaje sin partida no da ninguna", () => {
    expect(
      ubicarErrorDePlan(
        "plan, partida AF-LLAVE: las fracciones suman 1.5 y deben sumar exactamente 1; repartala entre los periodos hasta completar 1",
      ),
    ).toBe("AF-LLAVE");
    expect(ubicarErrorDePlan("plan, partida AF-TUB-PVC-1/2: la fraccion de Dia 2 no puede ser negativa")).toBe("AF-TUB-PVC-1/2");
    expect(ubicarErrorDePlan("plan: algo general")).toBeNull();
  });
});

describe("edición por sección (3c-2): clases de conflicto (409)", () => {
  test("solo el rev viejo se arregla recargando; caso cambiado y ya guardado piden abrir de nuevo; lo demás es otro", () => {
    expect(claseDeConflicto("El borrador cambió en otra ventana: vuelva a cargarlo.")).toBe("rev");
    expect(claseDeConflicto("El caso cambió desde que abrió este borrador: ábralo de nuevo en el caso actual.")).toBe("perdido");
    expect(claseDeConflicto("Este borrador ya se guardó como la versión 002; abra esa versión para seguir.")).toBe("perdido");
    expect(claseDeConflicto("Cualquier otra cosa")).toBe("otro");
  });
});

describe("edición por sección (3c-2): frase tras el rechazo", () => {
  test("cada sección dice con qué sigue la hoja (la clásica, ui/paginas/hoja.py:1674, 1773, 1827, 2053)", () => {
    expect(FRASES_DE_RECHAZO).toEqual({
      cantidades: "La hoja sigue con las últimas cantidades válidas.",
      parametros: "La hoja sigue con los últimos parámetros válidos.",
      plan: "La hoja sigue con el último plan válido.",
    });
  });

  test("el mensaje es el detalle del servidor sin su punto final, una frase y nada más; sin frase, la del borrador", () => {
    expect(mensajeDeRechazo("parametros: utilidad: 'mucho' no es un numero decimal valido", FRASES_DE_RECHAZO.parametros)).toBe(
      "parametros: utilidad: 'mucho' no es un numero decimal valido. La hoja sigue con los últimos parámetros válidos.",
    );
    expect(mensajeDeRechazo("Algo pasó.", FRASES_DE_RECHAZO.plan)).toBe("Algo pasó. La hoja sigue con el último plan válido.");
    expect(mensajeDeRechazo("Algo pasó")).toBe("Algo pasó. La hoja sigue con el último borrador válido.");
  });
});
