// Logica pura de CampoConBusqueda (diseno de autocompletado 2026-10-21, §3.2 a §3.6 y §5.4): las entradas de la lista,
// el movimiento con el teclado, los textos de la region de estado, los errores, el resaltado y el adaptador de la
// busqueda de partidas del catalogo. Sin React y sin estado: cada funcion se prueba sola (logicaBusqueda.test.ts).
import { ErrorDeApi, pedir } from "../api/cliente";

export interface OpcionDeBusqueda<T> {
  clave: string; // estable y unica en toda la lista: "partida:LB-02-TUB"
  principal: string; // linea 1: lo que la persona reconoce (la descripcion)
  secundaria: string[]; // linea 2, ya como texto: [codigo, unidad, ...]; el primero es el codigo (va en Plex Mono)
  valor: T; // lo que recibe el padre al elegir
}

export interface GrupoDeResultados<T> {
  rotulo: string; // "Partidas del catálogo"
  opciones: OpcionDeBusqueda<T>[];
  hayMas: boolean; // viene del servidor, por grupo (§5.1)
  aviso?: string; // texto fijo del servidor
}

export const PAUSA_MS = 300;
export const MINIMO_DE_LETRAS = 2;
export const LIMITE_INICIAL = 8;
export const LIMITE_AMPLIADO = 20;
export const LARGO_MAXIMO = 80; // el tope de `q` del servidor
export const RETARDO_DEL_ANUNCIO_MS = 400; // para no pisar la lectura del campo
export const ESPERA_DE_BUSCANDO_MS = 700; // «Buscando…» solo si la respuesta tarda
const SALTO = 5; // RePag y AvPag
const LARGO_DEL_ANUNCIO = 60;

export type Entrada<T> =
  | { tipo: "opcion"; grupo: number; opcion: OpcionDeBusqueda<T> }
  | { tipo: "ver_mas"; grupo: number }
  | { tipo: "propio" };

// Cuantas opciones se ven de un grupo: el limite inicial, o 20 si la persona pidio «Ver más resultados».
export function limiteDelGrupo(indice: number, ampliados: ReadonlySet<number>, limite: number): number {
  return ampliados.has(indice) ? LIMITE_AMPLIADO : limite;
}

// Las entradas navegables de la lista, en orden: las opciones de cada grupo (a lo sumo su limite), «Ver más resultados»
// al final de un grupo que trae mas y todavia no se amplio, y el valor propio al final de todo.
export function entradasDeLaLista<T>(
  grupos: GrupoDeResultados<T>[],
  ampliados: ReadonlySet<number>,
  limite: number,
  conPropio: boolean,
): Entrada<T>[] {
  const entradas: Entrada<T>[] = [];
  grupos.forEach((g, indice) => {
    const tope = limiteDelGrupo(indice, ampliados, limite);
    for (const opcion of g.opciones.slice(0, tope)) entradas.push({ tipo: "opcion", grupo: indice, opcion });
    if (g.hayMas && tope < LIMITE_AMPLIADO) entradas.push({ tipo: "ver_mas", grupo: indice });
  });
  if (conPropio) entradas.push({ tipo: "propio" });
  return entradas;
}

export type TeclaDeMovimiento = "ArrowDown" | "ArrowUp" | "PageDown" | "PageUp";

// La opcion activa tras una tecla (`null` = el foco esta en el texto del campo). ↓ desde la ultima vuelve al campo y ↑
// desde la primera tambien; ↑ desde el campo va a la ultima. RePag y AvPag saltan de 5 en 5 sin salirse (§3.6).
export function moverActiva(actual: number | null, tecla: TeclaDeMovimiento, total: number): number | null {
  if (total === 0) return null;
  const ultima = total - 1;
  switch (tecla) {
    case "ArrowDown":
      if (actual === null) return 0;
      return actual < ultima ? actual + 1 : null;
    case "ArrowUp":
      if (actual === null) return ultima;
      return actual > 0 ? actual - 1 : null;
    case "PageDown":
      return Math.min((actual ?? -1) + SALTO, ultima);
    case "PageUp":
      return actual === null ? 0 : Math.max(actual - SALTO, 0);
  }
}

export function recortarParaAnuncio(texto: string): string {
  return texto.length > LARGO_DEL_ANUNCIO ? `${texto.slice(0, LARGO_DEL_ANUNCIO)}…` : texto;
}

export function textoDelResultado(cuenta: number, texto: string): string {
  if (cuenta === 0) return `Sin resultados para «${recortarParaAnuncio(texto)}».`;
  if (cuenta === 1) return "1 resultado.";
  return `${cuenta} resultados. Use las flechas para recorrerlos.`;
}

export function textoDelMinimo(minimo: number): string {
  return `Escriba al menos ${minimo} ${minimo === 1 ? "letra" : "letras"} o un código`;
}

export function esAborto(error: unknown): boolean {
  return typeof error === "object" && error !== null && (error as { name?: unknown }).name === "AbortError";
}

// El mensaje de un fallo de la busqueda, o `null` si la sesion vencio (401: la pagina la cierra). El 422 no repite lo
// escrito; el 403, el 503 y la red caida dicen el `detalle` de la API tal cual (§3.3-10).
export function mensajeDeError(error: unknown): string | null {
  if (error instanceof ErrorDeApi) {
    if (error.estado === 401) return null;
    if (error.estado === 403) return `Su cuenta no puede usar esta búsqueda. ${error.detalle}`;
    if (error.estado === 422) return "La búsqueda no es válida: escriba otra cosa.";
    return error.detalle;
  }
  return "No se pudo buscar. Inténtelo de nuevo.";
}

export interface Tramo {
  texto: string;
  resaltado: boolean;
}

function plano(texto: string): string {
  return texto.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
}

// Parte `texto` en tramos y marca los que coinciden con alguna palabra de `busqueda`, sin tildes ni mayusculas. Las
// posiciones se calculan sobre el mismo texto: nunca se arma HTML (el componente pinta cada tramo como texto).
export function tramosResaltados(texto: string, busqueda: string): Tramo[] {
  const palabras = plano(busqueda).split(/\s+/).filter(Boolean);
  // Cada caracter del texto plano apunta a su caracter de origen (una letra con tilde puede dar uno o mas).
  let normalizado = "";
  const origen: number[] = [];
  Array.from(texto).forEach((caracter, indice) => {
    for (const c of plano(caracter)) {
      normalizado += c;
      origen.push(indice);
    }
  });
  const caracteres = Array.from(texto);
  const marcados = new Array<boolean>(caracteres.length).fill(false);
  for (const palabra of palabras) {
    let desde = normalizado.indexOf(palabra);
    while (desde !== -1) {
      for (let i = desde; i < desde + palabra.length; i++) marcados[origen[i]] = true;
      desde = normalizado.indexOf(palabra, desde + 1);
    }
  }
  const tramos: Tramo[] = [];
  caracteres.forEach((caracter, indice) => {
    const ultimo = tramos[tramos.length - 1];
    if (ultimo && ultimo.resaltado === marcados[indice]) ultimo.texto += caracter;
    else tramos.push({ texto: caracter, resaltado: marcados[indice] });
  });
  return tramos.length > 0 ? tramos : [{ texto, resaltado: false }];
}

// --- Partidas del catalogo: GET /v1/buscar/partidas (§5.4) ---

export interface PartidaHallada {
  clave: string;
  codigo: string;
  descripcion: string;
  unidad: string;
  dominio: string;
  tiene_composicion: boolean;
}

export interface PartidasHalladas {
  rotulo: string;
  resultados: PartidaHallada[];
  hay_mas: boolean;
}

const TIPO_DE_OBRA: Record<string, string> = {
  civil: "obra civil",
  telecom: "telecomunicaciones",
  industrial: "industrial",
  sistemas: "sistemas",
};

export function rutaDePartidas(q: string, limite: number, dominio?: string): string {
  const parametros = new URLSearchParams({ q, limite: String(limite) });
  if (dominio) parametros.set("dominio", dominio);
  return `/v1/buscar/partidas?${parametros.toString()}`;
}

// Un grupo con una opcion por partida: la descripcion arriba; abajo el codigo, la unidad, el tipo de obra y si ya tiene
// composicion (una sin ella tambien se puede elegir).
export function gruposDePartidas(respuesta: PartidasHalladas): GrupoDeResultados<PartidaHallada>[] {
  return [
    {
      rotulo: respuesta.rotulo,
      hayMas: respuesta.hay_mas,
      opciones: respuesta.resultados.map((p) => ({
        clave: p.clave,
        principal: p.descripcion,
        secundaria: [
          p.codigo,
          p.unidad,
          TIPO_DE_OBRA[p.dominio] ?? p.dominio,
          p.tiene_composicion ? "con composición" : "sin composición todavía",
        ],
        valor: p,
      })),
    },
  ];
}

// La funcion `buscar` de CampoConBusqueda para las partidas del catalogo (de un dominio, si se da).
export function buscadorDePartidas(dominio?: string) {
  return (q: string, senal: AbortSignal, limite: number): Promise<GrupoDeResultados<PartidaHallada>[]> =>
    pedir<PartidasHalladas>(rutaDePartidas(q, limite, dominio), { senal }).then(gruposDePartidas);
}
