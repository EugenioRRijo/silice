import { describe, expect, test } from "vitest";
import {
  COLUMNAS_CAMBIOS,
  SIN_ARCHIVO,
  filasDeCambios,
  formularioDictamen,
  formularioExcel,
  formularioPaquete,
  presentador,
  tipoDeBanner,
  tituloDeLote,
} from "./logica";

// Oraculos: los colores del banner de paquete.verificar.banner y su pintura en ui/paginas/revisar.py (COLORES: verde
// st.success, ambar st.warning, rojo y cualquier otro st.error), los titulos de la hoja «Cambios» del Excel de la
// revision (aplicacion/revision.py, tablas_de_revision) y el formato es-VE, escritos a mano.

describe("logica de Revisar un paquete", () => {
  test("el color del banner es el aviso de Carbon de la clasica; uno desconocido es error", () => {
    expect(tipoDeBanner("verde")).toBe("success");
    expect(tipoDeBanner("ambar")).toBe("warning");
    expect(tipoDeBanner("rojo")).toBe("error");
    expect(tipoDeBanner("morado")).toBe("error");
  });

  test("cada lote de hallazgos lleva su cuenta, como el subtitulo de la clasica", () => {
    expect(tituloDeLote("El emisor no los declaró", 3)).toBe("El emisor no los declaró (3)");
    expect(tituloDeLote("En común", 0)).toBe("En común (0)");
  });

  test("el presentador muestra el texto de la API en es-VE y deja el exacto como clave", () => {
    const ver = presentador([
      ["-209.199375", "-209.20"],
      ["1045.996875", "1046.00"],
    ]);
    expect(ver("-209.199375")).toBe("-209,20");
    expect(ver("1045.996875")).toBe("1.046,00");
    expect(ver("12.5")).toBe("12,5"); // sin par conocido: el mismo texto, solo con formato
  });

  test("el texto vacio de la pestaña es el de la clasica sin Markdown", () => {
    expect(SIN_ARCHIVO).toBe("Elija el archivo .silice que recibió.");
  });

  test("los formularios llevan el archivo y los campos que pide la API", () => {
    const archivo = new File(["x"], "recibido.silice");
    const solo = formularioPaquete(archivo);
    expect((solo.get("paquete") as File).name).toBe("recibido.silice");
    expect(solo.has("lista")).toBe(false);
    expect(formularioPaquete(archivo, 7).get("lista")).toBe("7");
    const dictamen = formularioDictamen(archivo, "con observaciones", "Falta R4");
    expect([dictamen.get("resultado"), dictamen.get("notas")]).toEqual(["con observaciones", "Falta R4"]);
    expect(formularioExcel(archivo, "revision").get("tipo")).toBe("revision");
  });

  test("las columnas de quien cambio que son las de la hoja Cambios del Excel", () => {
    expect(COLUMNAS_CAMBIOS.map((c) => c.titulo)).toEqual([
      "Versión",
      "Objeto",
      "Clave",
      "Campo",
      "Antes",
      "Después",
      "Fuente",
      "Responsable",
      "Fecha",
      "Marca",
    ]);
    const [fila] = filasDeCambios([{ version: "005", objeto: "apu" }]);
    expect(fila).toMatchObject({ id: "0", version: "005", objeto: "apu", marca: "" });
  });
});
