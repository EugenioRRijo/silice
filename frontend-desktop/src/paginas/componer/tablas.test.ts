import { describe, expect, test } from "vitest";
import {
  agregarFila,
  borrarFila,
  COLUMNAS,
  editarCelda,
  filaVacia,
  hayFilas,
  normalizarFila,
  tablasVacias,
} from "./tablas";

describe("tablas de insumos", () => {
  test("empiezan sin filas", () => {
    const t = tablasVacias();
    expect(t).toEqual({ materiales: [], equipos: [], mano_obra: [] });
    expect(hayFilas(t)).toBe(false);
  });

  test("la fila vacía trae todas las columnas de su tabla, en texto", () => {
    expect(filaVacia("materiales")).toEqual({ descripcion: "", unidad: "", cantidad: "", precio: "" });
    expect(filaVacia("equipos")).toEqual({ descripcion: "", cantidad: "", precio: "", depreciacion: "" });
    expect(filaVacia("mano_obra")).toEqual({ descripcion: "", cantidad: "", sueldo: "", modalidad: "" });
  });

  test("la columna de cantidad de materiales se llama «Consumo por unidad»", () => {
    const cantidad = COLUMNAS.materiales.find((c) => c.clave === "cantidad");
    expect(cantidad?.titulo).toBe("Consumo por unidad");
  });

  test("agregar, editar y borrar no mutan la tabla anterior", () => {
    const base = tablasVacias();
    const con = agregarFila(base, "equipos");
    expect(base.equipos).toHaveLength(0);
    expect(con.equipos).toHaveLength(1);
    const editada = editarCelda(con, "equipos", 0, "descripcion", "Mezcladora ficticia");
    expect(con.equipos[0].descripcion).toBe("");
    expect(editada.equipos[0].descripcion).toBe("Mezcladora ficticia");
    expect(hayFilas(editada)).toBe(true);
    const sin = borrarFila(editada, "equipos", 0);
    expect(sin.equipos).toHaveLength(0);
  });

  test("agregar con una fila dada la completa con las columnas que falten", () => {
    const t = agregarFila(tablasVacias(), "mano_obra", { descripcion: "Ayudante ficticio", sueldo: "12.5" });
    expect(t.mano_obra[0]).toEqual({ descripcion: "Ayudante ficticio", cantidad: "", sueldo: "12.5", modalidad: "" });
  });

  test("normalizar convierte todo a texto y descarta claves ajenas", () => {
    expect(
      normalizarFila("materiales", { descripcion: "Arena", unidad: "m3", cantidad: 2, precio: null, otra: "x" }),
    ).toEqual({ descripcion: "Arena", unidad: "m3", cantidad: "2", precio: "" });
  });
});
