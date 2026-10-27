import { useContext } from "react";
import { ContextoAplicacion } from "../shell/contexto";
import { PAGINAS, paginaPorId, usable, type PaginaDef } from "../shell/rutas";
import { ENTRADAS_DE_EMPRESA, SECCIONES_DE_OBRA, type EntradaDef, type SeccionDef } from "./secciones";
import type { ObraDeCarpeta } from "./useObras";

// Lo que una cuenta puede ofrecerse en el marco: la barra lateral y el buscador comparten estas reglas para que ninguna
// de las dos muestre algo que la cuenta no puede usar (la API vuelve a exigirlo, pero aquí no se ofrece).
export interface Oferta {
  secciones: readonly SeccionDef[];
  entradas: readonly EntradaDef[];
  // Pantallas usables que no tienen sitio en el árbol (histórico, índices, simulador…): se alcanzan por el buscador.
  sueltas: readonly PaginaDef[];
}

function usableLa(pagina: string | null, acciones: readonly string[], modoEntrega: boolean): boolean {
  const def = pagina === null ? undefined : paginaPorId(pagina);
  return def !== undefined && usable(def, acciones, modoEntrega);
}

export function ofertaDe(acciones: readonly string[], modoEntrega: boolean): Oferta {
  // Una sección con `pagina: null` aún no tiene pantalla: no se ofrece.
  const secciones = SECCIONES_DE_OBRA.filter((s) => usableLa(s.pagina, acciones, modoEntrega));
  const entradas = ENTRADAS_DE_EMPRESA.filter((e) => usableLa(e.pagina, acciones, modoEntrega));
  const conSitio = new Set<string | null>([...SECCIONES_DE_OBRA.map((s) => s.pagina), ...ENTRADAS_DE_EMPRESA.map((e) => e.pagina)]);
  const sueltas = PAGINAS.filter((p) => !conSitio.has(p.id) && usable(p, acciones, modoEntrega));
  return { secciones, entradas, sueltas };
}

// Nunca se ofrece una obra que al abrirla daría 403: sin permiso para cambiar de carpeta, solo las de la abierta.
export function obrasAlcanzables(
  obras: readonly ObraDeCarpeta[],
  carpetaActual: string | null,
  puedeCambiarDeCarpeta: boolean,
): ObraDeCarpeta[] {
  return puedeCambiarDeCarpeta ? [...obras] : obras.filter((o) => o.carpeta === carpetaActual);
}

export function useOferta() {
  const sesion = useContext(ContextoAplicacion)?.sesion;
  const acciones = sesion?.acciones ?? [];
  return {
    acciones,
    puedeCambiarDeCarpeta: acciones.includes("cambiar_caso"),
    oferta: ofertaDe(acciones, sesion?.modo_entrega ?? false),
  };
}
