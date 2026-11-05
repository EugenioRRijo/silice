// Llamadas de la pagina «Componer una partida» a la API (plan de la ola 3 B, §2). Todo monto viaja como texto.
import { pedir } from "../../api/cliente";
import type { CarpetaRespuesta } from "../../api/tipos";
import type { Fila, Tablas, TipoTabla } from "./tablas";

export interface Cabecera {
  codigo: string;
  descripcion: string;
  unidad: string;
  dominio: string;
  rendimiento: string;
}

export interface Opciones {
  dominios: string[];
  modalidades: string[];
}

export interface Desglose {
  materiales: string;
  equipos: string;
  mano_obra: string;
  costo_directo: string;
  con_administracion: string;
  precio_unitario: string;
}

export interface Advertencia {
  tipo: "rendimiento" | "rendimiento_ml" | "precio_atipico" | "contraste_aace" | "partida_nueva";
  texto: string;
}

export interface Contraste {
  tecnica: string;
  registros: number;
  pu_estimado: string;
  dentro_de_rango: boolean;
}

export interface Evaluacion {
  estado: "vacio" | "incompleto" | "valido";
  aviso: string | null;
  desglose: Desglose | null;
  advertencias: Advertencia[];
  requiere_justificacion: boolean;
  contraste: Contraste | null;
}

export interface PartidaExistente {
  existe: boolean;
  tablas: Tablas;
  rendimiento_propuesto: string | null;
  hay_historial: boolean;
}

export interface FilaReferencia {
  etiqueta: string;
  ref_maprex: string;
  fila: Fila;
}

export interface Similar {
  codigo: string;
  descripcion: string;
  puntaje: number | string;
  rendimiento: string | null;
  unidad: string | null;
  tablas: Tablas | null;
  aviso: string | null;
}

export interface DatosDeGuardado {
  fecha: string;
  condiciones: string;
  justificacion: string | null;
}

export interface Guardado {
  precio_unitario: string;
  mensaje: string;
  justificada: boolean;
  avisos: string[];
}

// La moneda de trabajo de la carpeta y su lista para armar (`GET /v1/carpeta`, plan de montar, T2; D-MP1): Componer
// arma en esa moneda y, sin lista para armar, no guarda (la API responde 409).
export function carpeta(): Promise<CarpetaRespuesta> {
  return pedir<CarpetaRespuesta>("/v1/carpeta");
}

// Crea la lista para armar de la carpeta a partir de MaPreX o convirtiendo la que tiene (con la tasa del BCV).
export function crearListaParaArmar(desde: "maprex" | "convertir"): Promise<CarpetaRespuesta> {
  return pedir<CarpetaRespuesta>("/v1/carpeta/lista-para-armar", { metodo: "POST", cuerpo: { desde } });
}

// Lo que haria `guardar` con el mismo cuerpo, sin escribir nada (`POST /v1/composicion/prever`, T3; D-MP2): la lista
// donde quedarian los precios y los insumos que quedarian como variante solo para este APU. Montos con punto.
export interface VariantePrevista {
  descripcion: string;
  unidad: string;
  precio_en_lista: string;
  precio_tecleado: string;
  codigo_variante: string;
}

export interface Prevision {
  lista: { nombre: string; moneda: string; fecha: string };
  lista_nueva: boolean;
  variantes: VariantePrevista[];
}

const BASE = "/v1/composicion";

export function opciones(): Promise<Opciones> {
  return pedir<Opciones>(`${BASE}/opciones`);
}

export function evaluar(cabecera: Cabecera, tablas: Tablas): Promise<Evaluacion> {
  return pedir<Evaluacion>(`${BASE}/evaluar`, { metodo: "POST", cuerpo: { ...cabecera, ...tablas } });
}

export function partida(codigo: string): Promise<PartidaExistente> {
  return pedir<PartidaExistente>(`${BASE}/partidas/${encodeURIComponent(codigo)}`);
}

// El `tipo` que acepta `GET /v1/composicion/referencia` para cada tabla: la API habla en singular (`material`,
// `equipo`), la pagina en el nombre de la tabla (`materiales`, `equipos`). Mandar el de la tabla era un 422 (prueba en
// vivo 2026-10-25); `contratoReferencia.test.ts` compara este mapa con `docs/api.json`.
export const TIPO_DE_REFERENCIA: Record<TipoTabla, "material" | "equipo" | "mano_obra"> = {
  materiales: "material",
  equipos: "equipo",
  mano_obra: "mano_obra",
};

export function referencia(tabla: TipoTabla, q: string): Promise<FilaReferencia[]> {
  const tipo = TIPO_DE_REFERENCIA[tabla];
  return pedir<FilaReferencia[]>(`${BASE}/referencia?tipo=${encodeURIComponent(tipo)}&q=${encodeURIComponent(q)}`);
}

export function similares(dominio: string, descripcion: string): Promise<Similar[]> {
  return pedir<Similar[]>(
    `${BASE}/similares?dominio=${encodeURIComponent(dominio)}&descripcion=${encodeURIComponent(descripcion)}`,
  );
}

export function guardar(cabecera: Cabecera, tablas: Tablas, datos: DatosDeGuardado): Promise<Guardado> {
  return pedir<Guardado>(`${BASE}/guardar`, { metodo: "POST", cuerpo: { ...cabecera, ...tablas, ...datos } });
}

export function prever(cabecera: Cabecera, tablas: Tablas, datos: DatosDeGuardado): Promise<Prevision> {
  return pedir<Prevision>(`${BASE}/prever`, { metodo: "POST", cuerpo: { ...cabecera, ...tablas, ...datos } });
}

// Un insumo del catalogo de la carpeta (`GET /insumos`): lo unico que trae unidad y precio vigente por separado. El
// precio llega como decimal con punto; la pagina lo muestra con coma (`autocompletado.ts`) y nunca lo opera.
export interface InsumoCatalogo {
  codigo: string;
  descripcion: string;
  tipo: string;
  unidad: string | null;
  precio_vigente: string | null;
}

// La lista se pide una vez y se reusa un rato: elegir varios insumos seguidos no repite la peticion, pero un insumo
// que se acaba de dar de alta (al guardar una composicion) aparece en menos de un minuto. Si falla, se pide de nuevo.
const VIGENCIA_DEL_CATALOGO_MS = 60_000;
let catalogo: { pedida: Promise<InsumoCatalogo[]>; en: number } | null = null;

export function olvidarInsumosDelCatalogo(): void {
  catalogo = null;
}

export function insumosDelCatalogo(): Promise<InsumoCatalogo[]> {
  if (catalogo !== null && Date.now() - catalogo.en < VIGENCIA_DEL_CATALOGO_MS) return catalogo.pedida;
  const pedida = pedir<InsumoCatalogo[]>("/insumos");
  const mia = { pedida, en: Date.now() };
  catalogo = mia;
  pedida.catch(() => {
    if (catalogo === mia) catalogo = null;
  });
  return pedida;
}
