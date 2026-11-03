// La lógica pura de la bandeja de Pendientes (rediseño F3, Tarea 2): adónde lleva cada pendiente, cuántos tiene cada
// obra y cómo se mueve la elección con el teclado. Sin React, probada aparte (logica.test.ts).
import type { PendienteDeObra } from "../../api/tipos";
import { ENTRADAS_DE_EMPRESA, SECCIONES_DE_OBRA, rutaDeEmpresa, rutaDeObra, seccionPorId } from "../../marco/secciones";
import type { SeccionDef } from "../../marco/secciones";

// D-F3-2: las dos pantallas que todavía no son sección van a la que las absorberá (especificación, §6.2).
const ABSORBIDAS = new Map<string, SeccionDef["id"]>([
  ["actualizacion", "mercado"],
  ["entregar", "aprobaciones"],
]);

interface Destino {
  ruta: string;
  // La pantalla que se monta al llegar (id de `shell/rutas.ts`): con ella se sabe si la cuenta puede usarla.
  pagina: string;
}

// La sección de la obra que monta la pantalla de la acción, o la que la absorberá; si no, la entrada de Empresa que la
// monta; y una pantalla desconocida, el Resumen de la obra (nunca un enlace muerto).
function destino(carpeta: string | null, obraId: number, id: string): Destino {
  const seccion = SECCIONES_DE_OBRA.find((s) => s.pagina === id) ?? seccionPorId(ABSORBIDAS.get(id) ?? "");
  const entrada = seccion ? undefined : ENTRADAS_DE_EMPRESA.find((e) => e.pagina === id);
  if (entrada) return { ruta: rutaDeEmpresa(entrada.id), pagina: entrada.pagina };
  const llegada = seccion ?? seccionPorId("resumen");
  return { ruta: rutaDeObra(carpeta, obraId, llegada?.id ?? "resumen"), pagina: llegada?.pagina ?? id };
}

// Adónde lleva una acción (`accion.pagina`) de una obra: lo usan la bandeja, por cada pendiente, y el Resumen, por la
// acción de su franja (Tarea 2 del plan F4).
export function destinoDeLaAccion(carpeta: string | null, obraId: number, pagina: string): string {
  return destino(carpeta, obraId, pagina).ruta;
}

export function destinoDelPendiente(p: PendienteDeObra): string {
  return destinoDeLaAccion(p.carpeta, p.obra_id, p.accion.pagina);
}

// El texto de un botón que trae el servidor (`aplicacion/mesa.py`). La sección se llama «Presupuesto» desde F4 (DESIGN.md
// retira «Hoja de la obra») y el servidor aún dice «Abrir la Hoja»: el botón lo dice al día (pasada del cierre de F4, H9).
// Lo usan la franja y los pendientes del Resumen y la bandeja de Pendientes.
const TEXTOS_AL_DIA: Readonly<Record<string, string>> = { "Abrir la Hoja": "Abrir el presupuesto" };

export function textoDeLaAccion(accion: { texto: string; pagina: string }): string {
  return TEXTOS_AL_DIA[accion.texto] ?? accion.texto;
}

export function paginaQueAbre(p: PendienteDeObra): string {
  return destino(p.carpeta, p.obra_id, p.accion.pagina).pagina;
}

// La misma clave que usa el marco para una obra: la carpeta (vacía la de la empresa) y su número.
export function claveDeObra(carpeta: string | null, obraId: number): string {
  return `${carpeta ?? ""}|${obraId}`;
}

export function contarPorObra(pendientes: readonly PendienteDeObra[]): Map<string, number> {
  const cuenta = new Map<string, number>();
  for (const p of pendientes) {
    const clave = claveDeObra(p.carpeta, p.obra_id);
    cuenta.set(clave, (cuenta.get(clave) ?? 0) + 1);
  }
  return cuenta;
}

// Cuántos pendientes hay de cada urgencia (el resumen encima de la lista).
export function contarUrgencias(pendientes: readonly PendienteDeObra[]): { bloquea: number; aviso: number } {
  const cuenta = { bloquea: 0, aviso: 0 };
  for (const p of pendientes) cuenta[p.urgencia] += 1;
  return cuenta;
}

// Patrón listbox de WAI-ARIA: ↑ y ↓ no dan la vuelta; Inicio y Fin van a los extremos. null = la tecla no mueve.
export function indiceTrasTecla(tecla: string, actual: number, total: number): number | null {
  switch (tecla) {
    case "ArrowDown":
      return Math.min(actual + 1, total - 1);
    case "ArrowUp":
      return Math.max(actual - 1, 0);
    case "Home":
      return 0;
    case "End":
      return total - 1;
    default:
      return null;
  }
}
