// Llamadas de la pagina «Componer una partida» a la API (plan de la ola 3 B, §2). Todo monto viaja como texto.
import { pedir } from "../../api/cliente";
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

export function referencia(tipo: TipoTabla, q: string): Promise<FilaReferencia[]> {
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
