// Las ediciones que salen al irse de una pestaña o de la página (la pausa de 400 ms no llegó a cumplirse) y el borrador que
// las recibe. Quien descarta el borrador al irse de la página espera a que terminen: si el PUT del vaciado y el DELETE del
// descarte compitieran, el DELETE podría ganar y la edición se perdería (borde declarado en 3c-1).
import type { Resumen } from "./logica";

const enCurso = new Map<string, Set<Promise<Resumen | null>>>();
const vaciadores = new Map<string, Set<() => Promise<Resumen | null>>>();

// Anota cómo vaciar la edición pendiente (la pausa de 400 ms o un PUT en vuelo) de una sección montada de `borrador`.
// Devuelve la función para quitarlo al desmontar.
export function registrarVaciador(borrador: string, vaciar: () => Promise<Resumen | null>): () => void {
  const grupo = vaciadores.get(borrador) ?? new Set<() => Promise<Resumen | null>>();
  grupo.add(vaciar);
  vaciadores.set(borrador, grupo);
  return () => {
    grupo.delete(vaciar);
    if (grupo.size === 0 && vaciadores.get(borrador) === grupo) vaciadores.delete(borrador);
  };
}

// Anota un envío del borrador `borrador`. La promesa resuelve con el resumen que contestó el servidor, o null si no se aceptó.
export function registrarEnvio(borrador: string, envio: Promise<Resumen | null>): void {
  const grupo = enCurso.get(borrador) ?? new Set<Promise<Resumen | null>>();
  grupo.add(envio);
  enCurso.set(borrador, grupo);
  const quitar = () => {
    grupo.delete(envio);
    if (grupo.size === 0 && enCurso.get(borrador) === grupo) enCurso.delete(borrador);
  };
  envio.then(quitar, quitar);
}

// Vacía las secciones montadas de `borrador` y espera a todos sus envíos anotados (también los que se anoten mientras tanto).
export async function esperarEnvios(borrador: string): Promise<Array<Resumen | null>> {
  const resultados: Array<Resumen | null> = [];
  const activos = vaciadores.get(borrador);
  if (activos !== undefined && activos.size > 0) {
    resultados.push(...(await Promise.all([...activos].map((v) => v().catch(() => null)))));
  }
  for (;;) {
    const grupo = enCurso.get(borrador);
    if (grupo === undefined || grupo.size === 0) return resultados;
    resultados.push(...(await Promise.all([...grupo].map((p) => p.catch(() => null)))));
  }
}
