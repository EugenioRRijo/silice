import { describe, expect, test } from "vitest";
import { coincide, normalizar } from "./filtro";

describe("normalizar", () => {
  test("quita tildes, mayusculas y espacios de los bordes", () => {
    expect(normalizar("  Excavación MANUAL ")).toBe("excavacion manual");
  });
});

describe("coincide", () => {
  const campos = ["CIV-001", "Excavación manual en tierra", "m3"];

  test("una busqueda vacia deja pasar todo", () => {
    expect(coincide(campos, "")).toBe(true);
    expect(coincide(campos, "   ")).toBe(true);
  });

  test("ignora tildes y mayusculas y busca en cualquier campo", () => {
    expect(coincide(campos, "EXCAVACION")).toBe(true);
    expect(coincide(campos, "civ-001")).toBe(true);
    expect(coincide(campos, "M3")).toBe(true);
  });

  test("todas las palabras deben aparecer, en cualquier orden", () => {
    expect(coincide(campos, "tierra excavacion")).toBe(true);
    expect(coincide(campos, "tierra relleno")).toBe(false);
  });

  test("un campo nulo no rompe la busqueda", () => {
    expect(coincide(["INS-1", null, "Cemento"], "cemento")).toBe(true);
    expect(coincide(["INS-1", null, "Cemento"], "arena")).toBe(false);
  });
});
