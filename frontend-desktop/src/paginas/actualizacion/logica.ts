// Logica pura de «Actualizar precios» (UC-02): arma los textos y el formulario con lo que manda la API. No calcula ni
// redondea importes: los montos llegan como texto y se muestran tal cual.
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";
import type { InformeAuditoriaRespuesta } from "../../api/tipos";

export const AYUDA =
  "Carga una lista de precios nueva (CSV o XLSX con las columnas tipo, insumo, unidad y precio) y el sistema revalora el presupuesto guardado, registra qué cambió y audita la versión nueva.";
export const CODIGO_NUEVO_POR_DEFECTO = "002";
export const MONEDA_POR_DEFECTO = "USD";
export const EXTENSIONES = [".csv", ".xlsx"];
export const SIN_PRESUPUESTOS = "No hay presupuestos guardados todavía";
export const INDICACION_SIN_PRESUPUESTOS =
  "Elabore un presupuesto en la página Elaborar y guárdelo; después podrá revalorarlo aquí con una lista de precios nueva.";

export interface PresupuestoListado {
  codigo: string;
  total: string;
  proyecto: string;
}
export interface InsumoDesconocido {
  descripcion: string;
  tipo: string;
  unidad: string | null;
  precio: string;
  etiqueta: string;
}
export interface VistaPrevia {
  desconocidos: InsumoDesconocido[];
  motivo: string | null;
}
export interface Aviso {
  nivel: "info" | "advertencia";
  texto: string;
}
export interface FilaComparativo {
  codigo_partida: string;
  descripcion: string;
  cantidad: string;
  pu_anterior: string;
  pu_nuevo: string;
  variacion_pct: string;
  total_anterior: string;
  total_nuevo: string;
  incidencia_pct: string;
}
export interface Revaloracion {
  proyecto: string;
  codigo_base: string;
  codigo_nuevo: string;
  moneda: string;
  resumen: string;
  total_anterior: string;
  total_nuevo: string;
  variacion: string;
  variacion_pct: string;
  filas: FilaComparativo[];
  dados_de_alta: string[];
  ignorados: string[];
  rechazados: string[];
  version_guardada: string | null;
  avisos: Aviso[];
  informe: InformeAuditoriaRespuesta;
}

export const COLUMNAS_COMPARATIVO: ColumnaDensa[] = [
  { clave: "codigo_partida", titulo: "Partida" },
  { clave: "descripcion", titulo: "Descripción" },
  { clave: "cantidad", titulo: "Cantidad", numerica: true },
  { clave: "pu_anterior", titulo: "P.U. anterior", numerica: true },
  { clave: "pu_nuevo", titulo: "P.U. nuevo", numerica: true },
  { clave: "variacion_pct", titulo: "Variación %", numerica: true, celda: "variacion" },
  { clave: "total_anterior", titulo: "Total anterior", numerica: true },
  { clave: "total_nuevo", titulo: "Total nuevo", numerica: true },
  { clave: "incidencia_pct", titulo: "Incidencia %", numerica: true, celda: "variacion" },
];

export function filasComparativo(filas: FilaComparativo[]): FilaDensa[] {
  return filas.map((f, i) => ({ ...f, id: `${i}-${f.codigo_partida}` }));
}

// «proyecto / codigo», como lo lee la persona.
export function etiquetaPresupuesto(p: PresupuestoListado): string {
  return `${p.proyecto} / ${p.codigo}`;
}

// Fecha local de hoy en YYYY-MM-DD (lo que mandan el input de fecha y la API).
export function hoyIso(ahora: Date = new Date()): string {
  const mes = String(ahora.getMonth() + 1).padStart(2, "0");
  const dia = String(ahora.getDate()).padStart(2, "0");
  return `${ahora.getFullYear()}-${mes}-${dia}`;
}

// «Lista dd/mm/aaaa» segun la vigencia (YYYY-MM-DD).
export function nombreDeLista(vigenciaIso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(vigenciaIso);
  if (!m) return "Lista";
  return `Lista ${m[3]}/${m[2]}/${m[1]}`;
}

export function etiquetasDeDesconocidos(desconocidos: InsumoDesconocido[]): string {
  return desconocidos.map((d) => d.etiqueta).join(", ");
}

export function avisoDesconocidos(desconocidos: InsumoDesconocido[]): string {
  return (
    `El archivo trae ${desconocidos.length} insumo(s) que no están en el catálogo: ` +
    `${etiquetasDeDesconocidos(desconocidos)}. Elija en "Dar de alta" los que quiera crear antes de revalorar; ` +
    "los demás se ignoran."
  );
}

// La posicion hace unica cada opcion aunque el archivo repita una fila.
export function etiquetaDeAlta(numero: number, d: InsumoDesconocido): string {
  return `${numero}. ${d.etiqueta}, precio ${d.precio}`;
}

export function textoDadosDeAlta(nombres: string[]): string {
  return `Se dieron de alta en el catálogo, con precio solo en la lista nueva: ${nombres.join(", ")}`;
}
export function textoIgnorados(nombres: string[]): string {
  return (
    "Se ignoraron los insumos del archivo que no están en el catálogo y no se eligieron para el alta " +
    `(no intervienen en el recálculo): ${nombres.join(", ")}`
  );
}
export function textoRechazados(nombres: string[]): string {
  return (
    "Se rechazaron las filas cuyo insumo está en el catálogo con otra unidad " +
    `(no intervienen en el recálculo): ${nombres.join(", ")}`
  );
}
export function preguntaDescartar(codigo: string): string {
  return `¿Descartar la versión ${codigo}? La versión sigue guardada y su historial se conserva.`;
}
export function textoDescartada(codigo: string): string {
  return `Versión ${codigo} descartada: sigue guardada como documento y su historial de cambios se conserva.`;
}

export interface DatosDeRevaloracion {
  archivo: File;
  proyecto: string;
  codigo: string;
  codigoNuevo: string;
  nombre: string;
  moneda: string;
  vigenciaIso: string;
  // Posiciones marcadas en la lista de desconocidos.
  marcadas: ReadonlySet<number>;
  desconocidos: InsumoDesconocido[];
}

export function formularioRevaloracion(d: DatosDeRevaloracion): FormData {
  const f = new FormData();
  f.append("archivo", d.archivo);
  f.append("proyecto", d.proyecto);
  f.append("codigo", d.codigo);
  f.append("codigo_nuevo", d.codigoNuevo);
  f.append("nombre", d.nombre);
  f.append("moneda", d.moneda);
  f.append("fecha_vigencia", d.vigenciaIso);
  d.desconocidos.forEach((x, i) => {
    if (d.marcadas.has(i)) f.append("dar_de_alta", x.descripcion);
  });
  return f;
}

export function rutaExcel(codigo: string, proyecto: string): string {
  return `/presupuestos/${encodeURIComponent(codigo)}/excel?proyecto=${encodeURIComponent(proyecto)}`;
}
export function rutaDescartar(codigo: string, proyecto: string): string {
  return `/presupuestos/${encodeURIComponent(codigo)}/descartar?proyecto=${encodeURIComponent(proyecto)}`;
}
