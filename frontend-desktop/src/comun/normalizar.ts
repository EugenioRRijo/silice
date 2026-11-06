// Buscar texto en una lista ya cargada, sin tildes ni mayusculas (modo local del diseno de autocompletado, §5.4): las
// partidas del contrato, las series de indices, los proveedores ya usados y los insumos de Mercado. Una sola regla de
// normalizacion para todas. Solo texto: aqui no se calcula ningun monto.
//
// Pendiente (no se toca en este cambio): `paginas/componer/unidades.ts` tiene todavia su propia copia de esta normalizacion.
import type { GrupoDeResultados, OpcionDeBusqueda } from "./logicaBusqueda";

// Sin tildes ni mayusculas: «Tubería» y «TUBERIA» dan «tuberia». Se quitan las marcas combinadas que deja la descomposicion
// (`\p{M}`: tilde, dieresis, virgulilla), no `\p{Diacritic}`, que tambien se llevaria los signos sueltos ^ ` ´ ¨ · y haria que
// buscar «x^2» diera «x2». La ñ pierde su virgulilla a proposito («caneria» encuentra «Cañería»): una busqueda no calla lo que
// la persona no pudo teclear, y la misma regla siguen los otros normalizadores de la interfaz y aplicacion/casos.py.
export function plano(texto: string): string {
  return texto.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
}

// Los elementos cuyo texto tiene todas las palabras de `q`, en cualquier orden. Con `codigoDe`, los de codigo que empieza
// por lo escrito van primero; si no, se conserva el orden de la lista. Sin texto, todos.
export function filtrarPorPalabras<T>(
  lista: readonly T[],
  q: string,
  textoDe: (elemento: T) => string,
  codigoDe?: (elemento: T) => string,
): T[] {
  const palabras = plano(q).split(/\s+/).filter(Boolean);
  const halladas = lista.filter((elemento) => {
    const texto = plano(textoDe(elemento));
    return palabras.every((palabra) => texto.includes(palabra));
  });
  const inicio = plano(q).trim();
  if (codigoDe === undefined || inicio === "") return halladas;
  const empiezan = halladas.filter((elemento) => plano(codigoDe(elemento)).startsWith(inicio));
  return [...empiezan, ...halladas.filter((elemento) => !empiezan.includes(elemento))];
}

export interface BuscadorLocal<T> {
  rotulo: string; // el del unico grupo de resultados
  textoDe: (elemento: T) => string; // donde se buscan las palabras
  codigoDe: (elemento: T) => string; // lo que, si empieza por lo escrito, va primero
  opcionDe: (elemento: T) => OpcionDeBusqueda<T>;
}

// La funcion `buscar` de CampoConBusqueda sobre una lista ya cargada: un solo grupo, sin una peticion por tecla.
export function buscadorLocal<T>(lista: readonly T[], { rotulo, textoDe, codigoDe, opcionDe }: BuscadorLocal<T>) {
  return async (q: string, _senal: AbortSignal, limite: number): Promise<GrupoDeResultados<T>[]> => {
    const halladas = filtrarPorPalabras(lista, q, textoDe, codigoDe);
    if (halladas.length === 0) return [];
    return [{ rotulo, hayMas: halladas.length > limite, opciones: halladas.slice(0, limite).map(opcionDe) }];
  };
}
