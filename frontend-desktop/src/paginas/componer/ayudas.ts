import { unidadEscrita } from "../../comun/unidades";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import type { Similar } from "./cliente";

// Ficha de Componer, lote 2 (supuesto S1, aprobado por Eugenio el 2026-11-23). Eugenio: «no sabía qué datos colocar
// porque no domino el lenguaje de este tema». Cada campo con palabras del oficio dice qué es en una línea. Un ejemplo
// con cifra solo sale de una partida real del catálogo (las similares); si no hay, la línea explica sin cifra. Los
// ejemplos de texto (qué escribir) no llevan números.

export const AYUDA_DESCRIPCION = "Como en el pliego o el cómputo. Al escribirla, Sílice muestra abajo partidas parecidas del catálogo.";

export const AYUDA_CONDICIONES =
  "Obligatorio. Diga cómo se logra ese rendimiento; por ejemplo: «cuadrilla de un albañil y un ayudante, a poca altura y con el material a pie de obra».";

const QUE_ES_EL_RENDIMIENTO = "Cuánto de esta partida hace la cuadrilla en un día de trabajo";

// La ayuda del rendimiento: qué es, en la unidad de la partida, y el rendimiento real de la primera parecida que lo trae.
export function ayudaDelRendimiento(similares: readonly Similar[], unidad: string): string {
  const escrita = unidadEscrita(unidad.trim());
  const base = escrita === "" ? `${QUE_ES_EL_RENDIMIENTO}.` : `${QUE_ES_EL_RENDIMIENTO}, en ${escrita} por día.`;
  const parecida = similares.find((s) => s.rendimiento !== null && s.rendimiento.trim() !== "");
  if (parecida === undefined) return base;
  const suUnidad = unidadEscrita((parecida.unidad ?? "").trim());
  const rinde = `${formatoEsVe(parecida.rendimiento!)}${suUnidad === "" ? "" : ` ${suUnidad}`} por día`;
  return `${base} Por ejemplo, la partida parecida ${parecida.codigo} (${parecida.descripcion}) rinde ${rinde}.`;
}

// La ayuda de la columna «Consumo por unidad» de las tres tablas, en la unidad de la partida.
export function ayudaDelConsumo(unidad: string): string {
  const escrita = unidadEscrita(unidad.trim());
  const una = escrita === "" ? "una unidad" : `un ${escrita}`;
  return `En «Consumo por unidad» escriba cuánto de cada insumo entra en ${una} de la partida; por ejemplo, cuántos sacos de cemento lleva ${una}.`;
}
