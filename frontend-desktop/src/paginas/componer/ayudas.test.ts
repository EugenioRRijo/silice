import { describe, expect, test } from "vitest";
import { AYUDA_CONDICIONES, AYUDA_DESCRIPCION, ayudaDelConsumo, ayudaDelRendimiento } from "./ayudas";
import type { Similar } from "./cliente";

// Ficha de Componer, lote 2 (supuesto S1 aprobado por Eugenio el 2026-11-23): «no sabía qué datos colocar porque no
// domino el lenguaje de este tema». Cada campo con palabras del oficio dice qué es en una línea, y el ejemplo con cifra
// sale de una partida real del catálogo (las similares), nunca de un valor inventado.

const similar = (parcial: Partial<Similar>): Similar => ({
  codigo: "FIC-009",
  descripcion: "Muro ficticio",
  puntaje: 0.91,
  rendimiento: "8.00",
  unidad: "m2",
  tablas: null,
  aviso: null,
  ...parcial,
});

describe("ayudas de Componer para quien no domina el oficio", () => {
  test("el rendimiento, sin partidas parecidas, se explica sin inventar una cifra", () => {
    expect(ayudaDelRendimiento([], "")).toBe("Cuánto de esta partida hace la cuadrilla en un día de trabajo.");
    expect(ayudaDelRendimiento([], "m3")).toBe("Cuánto de esta partida hace la cuadrilla en un día de trabajo, en m³ por día.");
  });

  test("con una partida parecida del catálogo, el ejemplo es su rendimiento real, con coma decimal y su unidad", () => {
    expect(ayudaDelRendimiento([similar({})], "m2")).toBe(
      "Cuánto de esta partida hace la cuadrilla en un día de trabajo, en m² por día. Por ejemplo, la partida parecida FIC-009 (Muro ficticio) rinde 8,00 m² por día.",
    );
  });

  test("toma la primera parecida que tiene rendimiento y omite las que no lo traen", () => {
    const sinDato = similar({ codigo: "FIC-001", rendimiento: null });
    expect(ayudaDelRendimiento([sinDato, similar({ codigo: "FIC-002", rendimiento: "12.5" })], "")).toContain(
      "la partida parecida FIC-002 (Muro ficticio) rinde 12,5 m² por día.",
    );
    expect(ayudaDelRendimiento([sinDato], "")).not.toContain("Por ejemplo");
  });

  test("las condiciones dicen qué escribir con un ejemplo de texto, no de cifra", () => {
    expect(AYUDA_CONDICIONES).toMatch(/^Obligatorio\./);
    expect(AYUDA_CONDICIONES).toContain("por ejemplo");
    expect(AYUDA_CONDICIONES).not.toMatch(/\d/);
  });

  test("la descripción avisa que trae partidas parecidas", () => {
    expect(AYUDA_DESCRIPCION).toContain("partidas parecidas");
  });

  test("el consumo por unidad se explica en la unidad de la partida", () => {
    expect(ayudaDelConsumo("m3")).toBe(
      "En «Consumo por unidad» escriba cuánto de cada insumo entra en un m³ de la partida; por ejemplo, cuántos sacos de cemento lleva un m³.",
    );
    expect(ayudaDelConsumo("")).toBe(
      "En «Consumo por unidad» escriba cuánto de cada insumo entra en una unidad de la partida; por ejemplo, cuántos sacos de cemento lleva una unidad.",
    );
  });
});
