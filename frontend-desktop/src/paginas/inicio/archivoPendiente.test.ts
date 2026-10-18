import { afterEach, describe, expect, test } from "vitest";
import { fijarArchivoPendiente, hayArchivoPendiente, tomarArchivoPendiente } from "./archivoPendiente";

describe("archivoPendiente", () => {
  afterEach(() => {
    tomarArchivoPendiente();
  });

  test("sin nada fijado no hay archivo", () => {
    expect(hayArchivoPendiente()).toBe(false);
    expect(tomarArchivoPendiente()).toBeNull();
  });

  test("lo fijado se entrega una sola vez, con su modo", () => {
    const archivo = new File(["x"], "presupuesto.xlsx");
    fijarArchivoPendiente(archivo, "guiado");
    expect(hayArchivoPendiente()).toBe(true);
    expect(tomarArchivoPendiente()).toEqual({ archivo, modo: "guiado" });
    expect(hayArchivoPendiente()).toBe(false);
    expect(tomarArchivoPendiente()).toBeNull();
  });

  test("fijar otro reemplaza al anterior", () => {
    const uno = new File(["1"], "uno.xlsx");
    const dos = new File(["2"], "dos.xlsx");
    fijarArchivoPendiente(uno, "propio");
    fijarArchivoPendiente(dos, "propio");
    expect(tomarArchivoPendiente()?.archivo).toBe(dos);
  });
});
