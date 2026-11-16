// Llamadas de la pagina «Componer una partida» a la API (plan de la ola 3 B, §2). Todo monto viaja como texto.
import { pedir } from "../../api/cliente";
import { avisarCambioDeLaCarpeta } from "../../shell/ListaDeLaCarpeta";
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

// RF-200 (ola 2, 2026-11-13): los cuatro parámetros del precio unitario, como se teclean (coma decimal). Viajan al evaluar,
// al prever y al guardar; el servidor calcula con ellos y no los guarda con la partida.
export type ClaveDeParametro = "fcas" | "bono_alimentacion" | "administracion" | "utilidad";
export type ParametrosDeTexto = Record<ClaveDeParametro, string>;

// Un parámetro con su rótulo y su valor escrito: la forma de `GET /v1/composicion/parametros` y de los `campos` de la vista
// `parametros` de la Hoja.
export interface CampoDeParametro {
  clave: string;
  rotulo: string;
  valor: string;
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

// La cantidad con desperdicio de una fila de materiales, dicha por el servidor: «0,52 (0,50 + 4 %)» (F5 vial).
export interface DesperdicioDeFila {
  fila: number;
  descripcion: string;
  leyenda: string;
}

export interface Evaluacion {
  estado: "vacio" | "incompleto" | "valido";
  aviso: string | null;
  desglose: Desglose | null;
  advertencias: Advertencia[];
  requiere_justificacion: boolean;
  contraste: Contraste | null;
  desperdicios?: DesperdicioDeFila[];
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

// Crea la lista para armar de la carpeta a partir de MaPreX, convirtiendo la que tiene (con la tasa del BCV) o copiando
// la lista de la empresa `listaId` en su moneda (sin tasa). Después avisa del cambio: la cabecera de la obra la vuelve a
// leer (E2E-3).
export async function crearListaParaArmar(
  desde: "maprex" | "convertir" | "empresa",
  listaId?: number,
): Promise<CarpetaRespuesta> {
  const cuerpo = desde === "empresa" ? { desde, lista_id: listaId } : { desde };
  const carpeta = await pedir<CarpetaRespuesta>("/v1/carpeta/lista-para-armar", { metodo: "POST", cuerpo });
  avisarCambioDeLaCarpeta();
  return carpeta;
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

// Sin parámetros (null) el servidor calcula con los de omisión.
const conParametros = (parametros: ParametrosDeTexto | null) => (parametros === null ? {} : { parametros });

export function evaluar(cabecera: Cabecera, tablas: Tablas, parametros: ParametrosDeTexto | null = null): Promise<Evaluacion> {
  return pedir<Evaluacion>(`${BASE}/evaluar`, { metodo: "POST", cuerpo: { ...cabecera, ...tablas, ...conParametros(parametros) } });
}

// Los parámetros de omisión (sin obra abierta), con su rótulo.
export function parametrosDeOmision(): Promise<{ campos: CampoDeParametro[] }> {
  return pedir<{ campos: CampoDeParametro[] }>(`${BASE}/parametros`);
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

export function guardar(
  cabecera: Cabecera,
  tablas: Tablas,
  datos: DatosDeGuardado,
  parametros: ParametrosDeTexto | null = null,
): Promise<Guardado> {
  return pedir<Guardado>(`${BASE}/guardar`, {
    metodo: "POST",
    cuerpo: { ...cabecera, ...tablas, ...datos, ...conParametros(parametros) },
  });
}

export function prever(
  cabecera: Cabecera,
  tablas: Tablas,
  datos: DatosDeGuardado,
  parametros: ParametrosDeTexto | null = null,
): Promise<Prevision> {
  return pedir<Prevision>(`${BASE}/prever`, {
    metodo: "POST",
    cuerpo: { ...cabecera, ...tablas, ...datos, ...conParametros(parametros) },
  });
}
