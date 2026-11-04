// Por qué existe (Tarea 5 del plan F4): la franja «Te falta / Siguiente paso» del Presupuesto dice un solo paso, el que
// toca, y su botón es el único principal de la pantalla. La regla es pura para probarla sin pintar nada; la pinta
// `FranjaDelPresupuesto.tsx` y la regla de las filas afectadas, `PestanaPresupuesto.tsx`. Los textos viven en
// `textos.ts`. La interfaz no calcula montos: solo cuenta hallazgos que ya da la API.
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { ESTADOS_APROBADOS } from "../../comun/aprobacion";
import type { Hallazgos } from "./logica";
import { TEXTOS_DEL_PASO } from "./textos";

export type AccionDelPresupuesto = "agregar_partida" | "guardar" | "ver_revision" | "version_nueva" | "enviar_a_aprobacion";

export interface EntradaDelPaso {
  version: string | null;
  vigente: string | null;
  cambios: number;
  // CRITICO + ERROR del resumen del borrador (`gravesDe`).
  graves: number;
  // La clave de `comun/aprobacion.ts`, o null si no hay lectura (borrador en blanco, sin registro o la lectura falló).
  aprobacion: string | null;
  // `HojaDeLaObra.puedeEditar` (Tarea 2b): editar_hoja y un borrador que no es de solo lectura.
  puedeEditar: boolean;
  // El permiso de editar la Hoja y una lectura de la aprobación que no falló. No mira el borrador: enviar obra sobre la
  // versión guardada (decisión 16 de la Tarea 2b, Eugenio, 2026-10-31).
  puedeEnviar: boolean;
}

export interface PasoDelPresupuesto {
  tipo: "falta" | "siguiente";
  texto: string;
  accion: AccionDelPresupuesto | null;
}

// Las que escriben en el borrador: sin `puedeEditar` no se ofrecen (Foco 3). «Ver en Revisión» solo lee.
const DEL_BORRADOR: ReadonlySet<AccionDelPresupuesto> = new Set(["agregar_partida", "guardar", "version_nueva"]);

const cifra = (n: number) => formatoEsVe(String(n));

function sinPermiso(paso: PasoDelPresupuesto, e: EntradaDelPaso): PasoDelPresupuesto {
  const { accion } = paso;
  if (accion === null) return paso;
  if (DEL_BORRADOR.has(accion) && !e.puedeEditar) return { ...paso, accion: null };
  if (accion === "enviar_a_aprobacion" && !e.puedeEnviar) return { ...paso, accion: null };
  return paso;
}

// Las reglas del plan, en su orden: la primera que se cumple gana.
function regla(e: EntradaDelPaso): PasoDelPresupuesto | null {
  const { version, vigente, cambios, graves, aprobacion } = e;
  if (version === null && cambios === 0) return { tipo: "falta", texto: TEXTOS_DEL_PASO.primeraPartida, accion: "agregar_partida" };
  if (cambios > 0 || version === null) {
    return { tipo: "siguiente", texto: TEXTOS_DEL_PASO.sinGuardar(cifra(cambios), cambios === 1), accion: "guardar" };
  }
  if (graves > 0) return { tipo: "falta", texto: TEXTOS_DEL_PASO.graves(cifra(graves), graves === 1), accion: "ver_revision" };
  if (aprobacion === "devuelta") return { tipo: "falta", texto: TEXTOS_DEL_PASO.devuelta(version), accion: "version_nueva" };
  if (aprobacion === "en_aprobacion") return { tipo: "siguiente", texto: TEXTOS_DEL_PASO.enAprobacion(version), accion: null };
  if (aprobacion !== null && ESTADOS_APROBADOS.has(aprobacion)) return null;
  // Solo la vigente se envía (Foco 5): con otra abierta no hay paso que dar aquí.
  if (version !== vigente) return null;
  return { tipo: "siguiente", texto: TEXTOS_DEL_PASO.enviar(version), accion: "enviar_a_aprobacion" };
}

export function pasoDelPresupuesto(e: EntradaDelPaso): PasoDelPresupuesto | null {
  const paso = regla(e);
  return paso === null ? null : sinPermiso(paso, e);
}

// Las tres primeras reglas no dependen de la aprobación; las demás sí. Mientras se lee, la franja espera en vez de
// adelantar «Envíe…» y quitarlo un instante después (parpadeo).
export function necesitaLaAprobacion(e: Pick<EntradaDelPaso, "version" | "cambios" | "graves">): boolean {
  return e.version !== null && e.cambios === 0 && e.graves === 0;
}

const GRAVES: ReadonlySet<string> = new Set(["CRITICO", "ERROR"]);
const AFECTAN: ReadonlySet<string> = new Set(["CRITICO", "ERROR", "ADVERTENCIA"]);

// Los hallazgos graves del borrador (CRITICO + ERROR), con los totales por severidad que da la API.
export function gravesDe(hallazgos: readonly Hallazgos[]): number {
  return hallazgos.filter((h) => GRAVES.has(h.severidad.toUpperCase())).reduce((suma, h) => suma + h.total, 0);
}

// Un renglón con un hallazgo crítico, de error o de advertencia lleva el fondo de precaución (`silice-fila--afectada`).
export function esFilaAfectada(severidad: string | null): boolean {
  return severidad !== null && AFECTAN.has(severidad.toUpperCase());
}
