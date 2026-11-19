// La lógica pura de la bandeja de Pendientes (rediseño F3, Tarea 2): adónde lleva cada pendiente, cuántos tiene cada
// obra y cómo se mueve la elección con el teclado. Sin React, probada aparte (logica.test.ts).
import type { PendienteDeObra } from "../../api/tipos";
import { SECCIONES_DE_CUENTA, espacioDeLaPagina, rutaOPendientes, subvistaDeLaPagina } from "../../marco/espacios";
import { SECCIONES_DE_OBRA, seccionPorId } from "../../marco/secciones";

interface Destino {
  ruta: string;
  // La pantalla que se monta al llegar (id de `shell/rutas.ts`): con ella se sabe si la cuenta puede usarla.
  pagina: string;
  // La pantalla es una herramienta de un espacio (Precios, Auditoría, Producción): trabaja con la carpeta abierta y su ruta no lleva carpeta.
  deEspacio: boolean;
}

// La sección de la obra que monta la pantalla de la acción o, si es una subvista («actualizar precios», «entregar»…), la
// propia subvista (contrato de rutas 2.4, tabla `SUBVISTAS`); si no, la herramienta de un espacio (Precios, Auditoría,
// Producción) o la sección de la Cuenta que la monta; y una pantalla desconocida, el Resumen de la obra (nunca un enlace muerto).
// `pagina` es siempre la pantalla que se monta al llegar: con ella la bandeja sabe si la cuenta puede usarla.
function destino(carpeta: string | null, obraId: number, id: string): Destino {
  const obra = { carpeta, obraId };
  const deLaObra = SECCIONES_DE_OBRA.some((s) => s.pagina === id) || subvistaDeLaPagina(id) !== undefined;
  const fueraDeLaObra = !deLaObra && (espacioDeLaPagina(id) !== undefined || SECCIONES_DE_CUENTA.some((c) => c.pagina === id));
  if (fueraDeLaObra) return { ruta: rutaOPendientes(id), pagina: id, deEspacio: espacioDeLaPagina(id) !== undefined };
  const pagina = deLaObra ? id : (seccionPorId("resumen")?.pagina ?? id);
  return { ruta: rutaOPendientes(pagina, obra), pagina, deEspacio: false };
}

// Adónde lleva una acción (`accion.pagina`) de una obra: lo usan la bandeja, por cada pendiente, y el Resumen, por la
// acción de su franja (Tarea 2 del plan F4).
export function destinoDeLaAccion(carpeta: string | null, obraId: number, pagina: string): string {
  return destino(carpeta, obraId, pagina).ruta;
}

export function destinoDelPendiente(p: PendienteDeObra): string {
  return destinoDeLaAccion(p.carpeta, p.obra_id, p.accion.pagina);
}

export function paginaQueAbre(p: PendienteDeObra): string {
  return destino(p.carpeta, p.obra_id, p.accion.pagina).pagina;
}

// La acción del pendiente abre una herramienta de un espacio: su ruta no lleva carpeta y trabaja con la abierta.
export function esDeEspacio(p: PendienteDeObra): boolean {
  return destino(p.carpeta, p.obra_id, p.accion.pagina).deEspacio;
}

// La carpeta que hay que abrir antes de ir a lo que el pendiente pide: la herramienta de un espacio (el Catálogo, Auditoría…)
// trabaja con la carpeta abierta, no con la de la obra del pendiente. null si no hace falta cambiar (la acción es de la
// obra o de la Cuenta, el pendiente ya es de la carpeta abierta, o no se sabe cuál está abierta: `undefined`).
export function carpetaPorAbrir(p: PendienteDeObra, carpetaAbierta: string | null | undefined): { carpeta: string | null } | null {
  if (carpetaAbierta === undefined || p.carpeta === carpetaAbierta) return null;
  return esDeEspacio(p) ? { carpeta: p.carpeta } : null;
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
