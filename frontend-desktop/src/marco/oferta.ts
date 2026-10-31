import { useContext } from "react";
import { ContextoAplicacion } from "../shell/contexto";
import { PAGINAS, paginaPorId, usable, type PaginaDef } from "../shell/rutas";
import { ENTRADAS_DE_EMPRESA, SECCIONES_DE_OBRA, type EntradaDef, type SeccionDef } from "./secciones";
import type { ObraDeCarpeta } from "./useObras";

// Lo que una cuenta puede ofrecerse en el marco: la barra lateral y el buscador comparten estas reglas para que ninguna
// de las dos muestre algo que la cuenta no puede usar (la API vuelve a exigirlo, pero aquí no se ofrece).
export interface Oferta {
  // Las de toda obra.
  secciones: readonly SeccionDef[];
  // Las que solo tiene una obra vial (hoy «Tramos»): se suman a `secciones` con `seccionesDeLaObra`.
  soloVial: readonly SeccionDef[];
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
  const usables = SECCIONES_DE_OBRA.filter((s) => usableLa(s.pagina, acciones, modoEntrega));
  const secciones = usables.filter((s) => !s.soloVial);
  const soloVial = usables.filter((s) => s.soloVial);
  const entradas = ENTRADAS_DE_EMPRESA.filter((e) => usableLa(e.pagina, acciones, modoEntrega));
  // Una sección solo de obras viales no es "sitio" de su pantalla: la pantalla sigue entre las sueltas, para que quien
  // aún no tiene tramos la encuentre con el buscador (Ctrl+K).
  const conSitio = new Set<string | null>([
    ...SECCIONES_DE_OBRA.filter((s) => !s.soloVial).map((s) => s.pagina),
    ...ENTRADAS_DE_EMPRESA.map((e) => e.pagina),
  ]);
  const sueltas = PAGINAS.filter((p) => !conSitio.has(p.id) && usable(p, acciones, modoEntrega));
  return { secciones, soloVial, entradas, sueltas };
}

// Las secciones de una obra, en el orden del marco: las de toda obra y, si la obra es vial, también las viales.
export function seccionesDeLaObra(oferta: Oferta, esVial: boolean): readonly SeccionDef[] {
  return SECCIONES_DE_OBRA.filter((s) => oferta.secciones.includes(s) || (esVial && oferta.soloVial.includes(s)));
}

// Nunca se ofrece una obra que al abrirla daría 403: sin permiso para cambiar de carpeta, solo las de la abierta.
// Siempre devuelve una lista nueva (copia o filtro), nunca `obras`: quien la reciba puede ordenarla sin mutar la fuente.
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
