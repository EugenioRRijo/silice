import { describe, expect, test } from "vitest";
import {
  AVISO_SIN_ARCHIVO,
  COLUMNAS_DEL_INFORME,
  EXTENSIONES_DE_PLANO,
  ROTULO_CARGAR_ALTURAS,
  ROTULO_CONTINUAR_UNIDAD,
  ROTULO_DECLARAR_CIRCUITOS,
  ROTULO_DESCARTAR_PLANO,
  ROTULO_FUSIONAR,
  ROTULO_IMPORTAR,
  ROTULO_LEER_PLANO,
  cuerpoDeAlturas,
  cuerpoDeCircuitos,
  cuerpoDeUnidad,
  esImportacionPerdida,
  etiquetaDeAltura,
  etiquetaDeCampoDeCircuito,
  filasDelInforme,
  formularioDeLectura,
  lineaDeFilasPorTabla,
  lineaDeOrigenes,
  rutaDeAlturas,
  rutaDeCircuitos,
  rutaDeFusion,
  rutaDePlano,
  rutaDeUnidad,
  textoDeAlturasCargadas,
  textoDeCircuitosDeclarados,
  textoDeLector,
  valoresDeCircuitos,
} from "./logicaPlano";

// Rebanada 3e-2, lógica pura del flujo «Importar plano». Los literales salen de la clásica (ui/paginas/hoja.py:1238-1385) y
// del contrato (docs/bitacora/2026-10-20-hoja-3e-contrato-rutas.md), escritos a mano.
const ID = "id-borrador-aaaaaaaaaaaa";

describe("rutas del plano (P1 a P6)", () => {
  test("cuelgan del borrador, sin armarse con texto de la persona", () => {
    expect(rutaDePlano(ID)).toBe("/v1/hoja/borradores/id-borrador-aaaaaaaaaaaa/plano");
    expect(rutaDeUnidad(ID)).toBe("/v1/hoja/borradores/id-borrador-aaaaaaaaaaaa/plano/unidad");
    expect(rutaDeAlturas(ID)).toBe("/v1/hoja/borradores/id-borrador-aaaaaaaaaaaa/plano/alturas");
    expect(rutaDeCircuitos(ID)).toBe("/v1/hoja/borradores/id-borrador-aaaaaaaaaaaa/plano/circuitos");
    expect(rutaDeFusion(ID)).toBe("/v1/hoja/borradores/id-borrador-aaaaaaaaaaaa/plano/fusionar");
  });
});

describe("rótulos y textos de la clásica, con tildes", () => {
  test("los siete rótulos de los botones", () => {
    expect(ROTULO_IMPORTAR).toBe("Importar plano (DXF o IFC)");
    expect(ROTULO_LEER_PLANO).toBe("Leer plano");
    expect(ROTULO_CARGAR_ALTURAS).toBe("Cargar alturas");
    expect(ROTULO_DECLARAR_CIRCUITOS).toBe("Declarar circuitos");
    expect(ROTULO_CONTINUAR_UNIDAD).toBe("Continuar con esta unidad");
    expect(ROTULO_FUSIONAR).toBe("Fusionar con el espacio del borrador");
    expect(ROTULO_DESCARTAR_PLANO).toBe("Descartar la importación");
  });

  test("sin archivo elegido, el texto de la clásica (P:1284)", () => {
    expect(AVISO_SIN_ARCHIVO).toBe("Elija primero un archivo de plano (DXF o IFC) y pulse Leer plano.");
  });

  test("solo .dxf e .ifc, con punto y en minúscula", () => {
    expect(EXTENSIONES_DE_PLANO).toEqual([".dxf", ".ifc"]);
  });

  test("las cuatro columnas del informe (COLUMNAS_DEL_INFORME de la clásica)", () => {
    expect(COLUMNAS_DEL_INFORME.map((c) => c.titulo)).toEqual(["Tipo", "En el plano", "Fila de la hoja", "Qué pasó"]);
    expect(COLUMNAS_DEL_INFORME.map((c) => c.clave)).toEqual(["tipo", "referencia", "fila", "mensaje"]);
  });
});

describe("lo que se manda", () => {
  test("P1: el archivo y el rev viajan como campos del formulario, el rev como texto", () => {
    const archivo = new File(["x"], "of001.dxf");
    const f = formularioDeLectura(7, archivo);
    expect([...f.keys()].sort()).toEqual(["archivo", "rev"]);
    expect(f.get("rev")).toBe("7");
    expect((f.get("archivo") as File).name).toBe("of001.dxf");
  });

  test("P2: la unidad tal como la eligió la persona", () => {
    expect(cuerpoDeUnidad(3, "cm")).toEqual({ rev: 3, unidades: "cm" });
  });

  test("P3: cada ambiente pendiente con el TEXTO escrito (coma incluida), en blanco si no escribió", () => {
    const pendientes = [
      { id: "A1", nombre: "Oficina 1" },
      { id: "A2", nombre: "Oficina 2" },
    ];
    expect(cuerpoDeAlturas(4, pendientes, { A1: "2,50" })).toEqual({ rev: 4, alturas: { A1: "2,50", A2: "" } });
    // lo escrito para un ambiente que ya no está pendiente no viaja
    expect(cuerpoDeAlturas(4, pendientes, { A1: "2,5", Z9: "3" })).toEqual({ rev: 4, alturas: { A1: "2,5", A2: "" } });
  });

  test("P4: los cuatro textos de cada circuito, en el orden fase, neutro, tierra, puntos", () => {
    const supuestos = [
      { id: "C1", fase: "1", neutro: "1", tierra: "1", puntos: "6" },
      { id: "C2", fase: "1", neutro: "1", tierra: "1", puntos: "6" },
    ];
    expect(valoresDeCircuitos(supuestos)).toEqual({ C1: ["1", "1", "1", "6"], C2: ["1", "1", "1", "6"] });
    const escritos = { ...valoresDeCircuitos(supuestos), C1: ["2", "1", "1", "08"] as [string, string, string, string] };
    expect(cuerpoDeCircuitos(5, supuestos, escritos)).toEqual({
      rev: 5,
      circuitos: { C1: ["2", "1", "1", "08"], C2: ["1", "1", "1", "6"] },
    });
  });
});

describe("etiquetas accesibles de los campos", () => {
  test("altura: como la clásica, con el id y, si difiere, el nombre", () => {
    expect(etiquetaDeAltura({ id: "A1", nombre: "Oficina 1" })).toBe("Altura de A1 (Oficina 1), en metros");
    expect(etiquetaDeAltura({ id: "A1", nombre: "A1" })).toBe("Altura de A1, en metros");
  });

  test("circuito: el rótulo del campo y el circuito", () => {
    expect(etiquetaDeCampoDeCircuito("Puntos máximos", "C2")).toBe("Puntos máximos del circuito C2");
  });
});

describe("el informe como filas de tabla", () => {
  test("un id propio por fila y los cuatro textos tal cual", () => {
    const filas = filasDelInforme([
      { tipo: "Importado", referencia: "Capa AMB", fila: "A1", mensaje: "Ambiente A1" },
      { tipo: "Pendiente", referencia: "Capa AMB", fila: "A2", mensaje: "Sin altura" },
    ]);
    expect(filas).toEqual([
      { id: "informe-0", tipo: "Importado", referencia: "Capa AMB", fila: "A1", mensaje: "Ambiente A1" },
      { id: "informe-1", tipo: "Pendiente", referencia: "Capa AMB", fila: "A2", mensaje: "Sin altura" },
    ]);
  });
});

describe("textos de resultado", () => {
  test("las alturas cargadas: cuántas se escribieron y cuántos ambientes siguen pendientes", () => {
    expect(textoDeAlturasCargadas(["2,50", "2,50", "", " "], 0)).toBe("Se cargaron 2 alturas. No quedan ambientes pendientes.");
    expect(textoDeAlturasCargadas(["2,50", ""], 1)).toBe("Se cargó 1 altura. Queda 1 ambiente pendiente.");
    expect(textoDeAlturasCargadas(["", ""], 2)).toBe("No escribió ninguna altura. Quedan 2 ambientes pendientes.");
  });

  test("los circuitos declarados", () => {
    expect(textoDeCircuitosDeclarados(2)).toBe("Se declararon 2 circuitos.");
    expect(textoDeCircuitosDeclarados(1)).toBe("Se declaró 1 circuito.");
  });

  test("las filas de la fusión por tabla y los orígenes, como la clásica", () => {
    expect(
      lineaDeFilasPorTabla([
        { rotulo: "Ambientes", cantidad: 6 },
        { rotulo: "Fuentes", cantidad: 6 },
        { rotulo: "Puntos", cantidad: 21 },
      ]),
    ).toBe("Filas que entraron al borrador: Ambientes 6 · Fuentes 6 · Puntos 21.");
    expect(lineaDeFilasPorTabla([])).toBe("Filas que entraron al borrador: ninguna.");
    expect(lineaDeOrigenes(1)).toBe("1 orígenes de medida del plano, aparte de las filas: cada fila importada cita el suyo.");
  });
});

describe("textos del servidor", () => {
  const DXF =
    "Falta instalar el componente para leer planos DXF. Instale el extra «planos» con el comando «uv sync --extra planos» y vuelva a intentarlo.";
  const IFC =
    "Falta instalar el componente para leer planos IFC. Instale el extra «civil» con el comando «uv sync --extra civil» y vuelva a intentarlo.";

  test("el lector que falta se dice sin el comando, solo en la vista", () => {
    expect(textoDeLector(DXF)).toBe("Falta instalar el componente para leer planos DXF. Pídalo a quien instaló Sílice y vuelva a intentarlo.");
    expect(textoDeLector(IFC)).toBe("Falta instalar el componente para leer planos IFC. Pídalo a quien instaló Sílice y vuelva a intentarlo.");
  });

  test("cualquier otro texto del servidor queda tal cual", () => {
    const otros = [
      "El archivo «x.exe» no es un plano que se pueda importar. Suba un plano en formato DXF o IFC.",
      "Altura de «A1»: «abc» no es una altura valida. Escriba un numero de metros mayor que 0 y hasta 250, por ejemplo 2,50. No se cargó ninguna altura.",
      DXF.replace("planos DXF", "planos DWG"),
      `${DXF} Más.`,
      "",
    ];
    for (const t of otros) expect(textoDeLector(t)).toBe(t);
  });

  test("adversarial: 100 000 caracteres, parecidos o no a la plantilla, en menos de un segundo", () => {
    const largos = [
      "a".repeat(100_000),
      "Falta instalar el componente para leer planos ".repeat(2_500),
      `Falta instalar el componente para leer planos DXF. ${"«".repeat(100_000)}`,
      `${DXF}${" ".repeat(100_000)}`,
    ];
    const inicio = performance.now();
    for (const t of largos) expect(textoDeLector(t)).toBe(t);
    expect(performance.now() - inicio).toBeLessThan(1000);
  });

  test("la importación perdida: el 409 «Vuelva a subir el plano» (y solo ese)", () => {
    expect(esImportacionPerdida("Vuelva a subir el plano: ya no está disponible.")).toBe(true);
    expect(esImportacionPerdida("No se puede fusionar «roto.dxf»: el archivo no se pudo leer")).toBe(false);
    expect(esImportacionPerdida("El borrador cambió en otra ventana: vuelva a cargarlo.")).toBe(false);
  });
});
