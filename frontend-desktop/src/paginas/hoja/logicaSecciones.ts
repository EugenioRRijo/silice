// Lógica pura de la edición de cantidades, parámetros y plan de trabajo (rebanada 3c-2: E2 a E5 del diseño §4.4).
// Todo lo que escribe la persona viaja como texto, tal cual; el servidor valida con los mensajes de la clásica. Aquí no
// se convierte nada a número.
import { enteroDeDigitos } from "./logica";
import type { FilaPresupuesto, VistaParametros, VistaPlan } from "./logica";

const rutaDelBorrador = (id: string) => `/v1/hoja/borradores/${id}`;

export const rutaDeCantidades = (id: string) => `${rutaDelBorrador(id)}/cantidades`;
export const rutaDeParametros = (id: string) => `${rutaDelBorrador(id)}/parametros`;
export const rutaDePlan = (id: string) => `${rutaDelBorrador(id)}/plan`;
export const rutaDePlanSecuencial = (id: string) => `${rutaDelBorrador(id)}/plan/secuencial`;

// Lo que la clásica agrega tras el error de cada sección (ui/paginas/hoja.py:1674, 1773, 1827, 2053).
export const FRASES_DE_RECHAZO = {
  cantidades: "La hoja sigue con las últimas cantidades válidas.",
  parametros: "La hoja sigue con los últimos parámetros válidos.",
  plan: "La hoja sigue con el último plan válido.",
} as const;

// Cómo reparte el texto de un 409 (los tres que puede dar una edición): solo el `rev` viejo se arregla recargando;
// si el caso cambió o el borrador ya se guardó, recargar también fallaría y solo queda abrir de nuevo.
export type ClaseDeConflicto = "rev" | "perdido" | "otro";

export function claseDeConflicto(detalle: string): ClaseDeConflicto {
  if (detalle.startsWith("El borrador cambió")) return "rev";
  if (detalle.startsWith("El caso cambió") || detalle.startsWith("Este borrador ya se guardó")) return "perdido";
  return "otro";
}

// --- cantidades (E2) ---

// Lo que se edita en el Presupuesto: el texto de cada renglón y cuáles toca la persona. Solo los tocados viajan.
export interface EdicionDeCantidades {
  orden: string[];
  textos: Record<string, string>;
  tocadas: string[];
}

export function sembrarCantidades(filas: FilaPresupuesto[]): EdicionDeCantidades {
  return {
    orden: filas.map((f) => f.clave),
    textos: Object.fromEntries(filas.map((f) => [f.clave, f.cantidad])),
    tocadas: [],
  };
}

export function cambiarCantidad(edicion: EdicionDeCantidades, clave: string, texto: string): EdicionDeCantidades {
  return {
    ...edicion,
    textos: { ...edicion.textos, [clave]: texto },
    tocadas: edicion.tocadas.includes(clave) ? edicion.tocadas : [...edicion.tocadas, clave],
  };
}

export function cuerpoDeCantidades(rev: number, edicion: EdicionDeCantidades): { rev: number; filas: Array<{ clave: string; cantidad: string }> } {
  return {
    rev,
    filas: edicion.orden.filter((c) => edicion.tocadas.includes(c)).map((c) => ({ clave: c, cantidad: edicion.textos[c] ?? "" })),
  };
}

// «presupuesto, fila {n} (…)» (ui/hoja.py:855-863): la fila desde 1 en la tabla completa del servidor.
export function ubicarErrorDeCantidad(detalle: string): number | null {
  const m = /^presupuesto, fila (\d+)/.exec(detalle);
  return m ? enteroDeDigitos(m[1]!) : null;
}

// --- parámetros (E3) ---

export const CAMPOS_DE_PARAMETROS = ["fcas", "bono_alimentacion", "administracion", "utilidad"] as const;

export type ValoresDeParametros = Record<string, string>;

export function sembrarParametros(campos: VistaParametros["campos"]): ValoresDeParametros {
  return Object.fromEntries(campos.map((c) => [c.clave, c.valor]));
}

export function cuerpoDeParametros(rev: number, valores: ValoresDeParametros): Record<string, string | number> {
  const cuerpo: Record<string, string | number> = { rev };
  for (const campo of CAMPOS_DE_PARAMETROS) cuerpo[campo] = valores[campo] ?? "";
  return cuerpo;
}

export interface UbicacionDeParametro {
  campo: string;
  // El mensaje del campo sin el prefijo «parametros: {campo}: ».
  texto: string;
}

// «parametros: {campo}: {error}» (ui/hoja.py:1124).
export function ubicarErrorDeParametro(detalle: string): UbicacionDeParametro | null {
  const m = /^parametros: ([a-z_]+): ([\s\S]*)$/.exec(detalle);
  if (!m || !(CAMPOS_DE_PARAMETROS as readonly string[]).includes(m[1]!)) return null;
  return { campo: m[1]!, texto: m[2]! };
}

// --- plan (E4) ---

export interface FilaDePlan {
  partida: string;
  valores: Record<string, string>;
}

export interface EdicionDelPlan {
  etiquetas: string[];
  filas: FilaDePlan[];
}

export function sembrarPlan(vista: Pick<VistaPlan, "etiquetas" | "filas">): EdicionDelPlan {
  return {
    etiquetas: [...vista.etiquetas],
    filas: vista.filas.map((f) => ({ partida: f.partida, valores: { ...f.valores } })),
  };
}

export function cambiarFraccion(edicion: EdicionDelPlan, partida: string, etiqueta: string, texto: string): EdicionDelPlan {
  return {
    ...edicion,
    filas: edicion.filas.map((f) => (f.partida === partida ? { ...f, valores: { ...f.valores, [etiqueta]: texto } } : f)),
  };
}

export function cuerpoDelPlan(rev: number, edicion: EdicionDelPlan): { rev: number; etiquetas: string[]; filas: FilaDePlan[] } {
  return {
    rev,
    etiquetas: edicion.etiquetas,
    filas: edicion.filas.map((f) => ({
      partida: f.partida,
      valores: Object.fromEntries(edicion.etiquetas.map((e) => [e, f.valores[e] ?? ""])),
    })),
  };
}

// «plan, partida {c}: …» (ui/hoja.py:1202-1212). El código de la partida llega hasta los dos puntos que siguen.
export function ubicarErrorDePlan(detalle: string): string | null {
  const m = /^plan, partida (.+?): /.exec(detalle);
  return m ? m[1]! : null;
}
