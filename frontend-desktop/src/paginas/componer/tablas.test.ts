import { describe, expect, test } from "vitest";
import {
  agregarFila,
  borrarFila,
  completarFila,
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

describe("completarFila (al elegir un insumo del catálogo)", () => {
  const base = {
    materiales: [
      { descripcion: "cem", unidad: "", cantidad: "2", precio: "" },
      { descripcion: "otra", unidad: "kg", cantidad: "", precio: "5" },
    ],
    equipos: [],
    mano_obra: [],
  };

  test("llena solo las columnas dadas de esa fila y deja el resto y las otras filas", () => {
    const t = completarFila(base, "materiales", 0, { descripcion: "Cemento gris ficticio", unidad: "saco", precio: "18,00" });
    expect(t.materiales[0]).toEqual({ descripcion: "Cemento gris ficticio", unidad: "saco", cantidad: "2", precio: "18,00" });
    expect(t.materiales[1]).toEqual(base.materiales[1]);
    expect(base.materiales[0].precio).toBe(""); // no muta
  });

  test("ignora una clave que la tabla no tiene (no inventa columnas)", () => {
    const t = completarFila(base, "materiales", 0, { descripcion: "X", sueldo: "9" });
    expect(t.materiales[0]).toEqual({ descripcion: "X", unidad: "", cantidad: "2", precio: "" });
  });

  test("una fila que no existe no cambia nada", () => {
    expect(completarFila(base, "materiales", 7, { descripcion: "X" })).toEqual(base);
  });
});
