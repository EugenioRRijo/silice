// Logica pura de «Precios de la empresa» (UC-17 4-5): textos de la pagina clasica y el formulario que recibe la API.
// No calcula ni redondea: el impacto de cada hallazgo llega como texto y se muestra tal cual.
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";
import { formatoEsVe } from "../../indicadores/formatoEsVe";

export const TITULO = "Precios de la empresa";
export const AYUDA =
  "La lista de su empresa: una copia de la lista base con sus precios encima, cada uno con su fecha y su fuente. No cambia la valoracion de ningun proyecto que no la use.";
export const TITULO_REFERENCIA = "1. La referencia MaPreX en bolivares";
export const ROTULO_REFERENCIA = "Cargar la referencia MaPreX en Bs";
export const TITULO_LISTA = "2. La lista de la empresa";
export const SIN_BASES = "El caso no tiene listas de precios: cargue una en Actualizar precios.";
export const TITULO_HALLAZGOS = "3. Precios vencidos o fuera de rango (R11 y R12)";
export const SIN_LISTAS = "Todavia no hay listas de empresa en este caso.";
export const MENSAJE_FALTA = "Elija la moneda de la lista y el archivo de precios: no tienen valor por defecto.";
export const EXTENSIONES = [".csv", ".xlsx"];
export const MONEDAS = ["Bs", "USD"];

export interface Base {
  id: number;
  nombre: string;
  moneda: string;
}
export interface ListaEmpresa {
  id: number;
  nombre: string;
}
export interface Estado {
  bases: Base[];
  listas: ListaEmpresa[];
}
export interface ListaCreada {
  nombre: string;
  propios: number;
  desconocidos: string[];
  mensaje: string;
  aviso: string | null;
}
export interface Hallazgos {
  columnas: string[];
  filas: Record<string, string>[];
  nota: string;
}

export interface DatosLista {
  empresa: string;
  rif: string;
  baseId: string;
  moneda: string;
  fecha: string;
  fuente: string;
  nombre: string;
  archivo: File | null;
}

export const COLUMNAS_DESCONOCIDOS: ColumnaDensa[] = [{ clave: "insumo", titulo: "Insumo" }];

export function columnasHallazgos(columnas: string[]): ColumnaDensa[] {
  return columnas.map((titulo) => {
    if (titulo === "Severidad") return { clave: titulo, titulo, celda: "severidad" as const };
    if (titulo === "Impacto") return { clave: titulo, titulo, numerica: true };
    return { clave: titulo, titulo };
  });
}

export function filasHallazgos(h: Hallazgos): FilaDensa[] {
  return h.filas.map((fila, i) => ({ ...fila, id: String(i) }));
}

export function filasDesconocidos(desconocidos: string[]): FilaDensa[] {
  return desconocidos.map((insumo, i) => ({ id: String(i), insumo }));
}

// «nombre (moneda)», como lista la pagina clasica las listas base.
export function etiquetaBase(b: Base): string {
  return `${b.nombre} (${b.moneda})`;
}

// Fecha local de hoy en YYYY-MM-DD (lo que mandan el input de fecha y la API).
export function hoyIso(ahora: Date = new Date()): string {
  const mes = String(ahora.getMonth() + 1).padStart(2, "0");
  const dia = String(ahora.getDate()).padStart(2, "0");
  return `${ahora.getFullYear()}-${mes}-${dia}`;
}

// La moneda y el archivo no tienen valor por defecto: sin ellos no se envia nada.
export function faltaAlgo(d: DatosLista): boolean {
  return d.moneda === "" || d.archivo === null;
}

export function formularioLista(d: DatosLista): FormData {
  const cuerpo = new FormData();
  cuerpo.append("empresa", d.empresa);
  cuerpo.append("rif", d.rif);
  cuerpo.append("base_id", d.baseId);
  cuerpo.append("moneda", d.moneda);
  cuerpo.append("fecha", d.fecha);
  cuerpo.append("fuente", d.fuente);
  cuerpo.append("nombre", d.nombre);
  if (d.archivo) cuerpo.append("archivo", d.archivo);
  return cuerpo;
}

export function rutaHallazgos(listaId: number, fechaIso: string): string {
  return `/v1/precios-empresa/listas/${listaId}/hallazgos?fecha=${encodeURIComponent(fechaIso)}`;
}

// --- RF-100: variaciones atipicas de precio (el boton de la pagina clasica) -----------------------
// El rotulo y los avisos son los de `aplicacion/atipicos.py`; los avisos llegan de la API tal cual.
export const ROTULO_ATIPICOS = "Buscar variaciones atípicas de precio";
export const ETIQUETA_ATIPICOS = "Variaciones atípicas de precio";
// Las palabras de la descripcion de cada hallazgo y del aviso sin el extra `ml` de la pagina clasica.
export const NOTA_ATIPICOS =
  "Cada variación (en USD) se aparta del historial de variaciones del insumo. Nada de esto se guarda ni se bloquea.";

export interface AvisoAtipicos {
  nivel: "info" | "success";
  texto: string;
}
export interface VariacionAtipica {
  insumo: string;
  // En por ciento con dos decimales, como texto ("0.39"), y sin redondear ("0.390625").
  porcentaje: string;
  porcentaje_exacto: string;
  desde: string;
  hasta: string;
  severidad: string;
  descripcion: string;
}
export interface Atipicos {
  disponible: boolean;
  avisos: AvisoAtipicos[];
  variaciones: VariacionAtipica[];
}

export function rutaAtipicos(listaId: number): string {
  return `/v1/precios-empresa/listas/${listaId}/atipicos`;
}

// "0.39" -> "0,39 %": formato es-VE sobre el texto, sin Number (la interfaz no calcula).
export function porcentajeEsVe(porcentaje: string): string {
  return `${formatoEsVe(porcentaje)} %`;
}

// 2026-09-01 -> 01/09/2026, como en la pantalla de Streamlit. Lo que no es AAAA-MM-DD queda igual.
export function fechaCorta(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : iso;
}

// La celda de la variacion guarda el exacto (su `title` y el orden) y se lee con el redondeo que hizo la API: la
// interfaz no redondea. Un exacto que no vino en la respuesta se muestra entero.
export function columnasAtipicos(a: Atipicos): ColumnaDensa[] {
  const redondeo = new Map(a.variaciones.map((v) => [v.porcentaje_exacto, v.porcentaje]));
  return [
    { clave: "insumo", titulo: "Insumo" },
    {
      clave: "porcentaje",
      titulo: "Variación (en USD)",
      numerica: true,
      presentar: (exacto) => porcentajeEsVe(redondeo.get(exacto) ?? exacto),
    },
    { clave: "desde", titulo: "Desde", presentar: fechaCorta },
    { clave: "hasta", titulo: "Hasta", presentar: fechaCorta },
    { clave: "severidad", titulo: "Severidad", celda: "severidad" },
  ];
}

export function filasAtipicos(a: Atipicos): FilaDensa[] {
  return a.variaciones.map((v, i) => ({
    id: String(i),
    insumo: v.insumo,
    porcentaje: v.porcentaje_exacto,
    desde: v.desde,
    hasta: v.hasta,
    severidad: v.severidad,
  }));
}
