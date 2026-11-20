// Lógica pura de «Series del riesgo vial» en «Índices del BCV»: las dos series de precios que usa «Riesgo de la obra»
// (el índice del asfalto y el gasoil). La API trae la definición, la historia ya cargada (fecha ISO y valor exacto con
// punto) y, al importar, cuántos valores entraron; aquí solo se arman los textos, las filas y el formulario. La interfaz
// no calcula nada: las fechas y las cifras se leen en es-VE con los ayudantes de siempre.
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";
import { fechaEsVe, formatoEsVe } from "../../indicadores/formatoEsVe";

export const RUTA_SERIES_VIALES = "/v1/indices/series-viales";
export const RUTA_IMPORTAR_SERIE_VIAL = "/v1/indices/series-viales/importar";

export const AYUDA_SERIES_VIALES =
  "«Riesgo de la obra» proyecta los precios de una obra vial con dos series: el índice de precios del asfalto y el " +
  "precio del gasoil en dólares. Elija la serie, suba su CSV (serie, fecha, valor, provisional, fuente; el valor con " +
  "punto decimal) y pulse «Importar»: se guarda solo esa serie del archivo, todo o nada, y el mismo archivo dos veces " +
  "no escribe nada. Un archivo con las dos series se importa una vez por cada una.";
export const SIN_ARCHIVO_VIAL = "Elija el archivo CSV de la serie.";
export const SIN_FUENTE_VIAL = "Escriba de dónde bajó la serie.";
export const SIN_FECHA_VIAL = "Escriba la fecha en que bajó el archivo.";
export const FECHA_FUTURA_VIAL = "La fecha de descarga no puede ser posterior a hoy.";
export const MAXIMO_FUENTE = 500;
export const SIN_VALORES = "Todavía no hay valores cargados de esta serie.";
export const EXTENSIONES_VIALES = [".csv"];

export interface ObservacionVial {
  fecha: string;
  valor: string;
  provisional: boolean;
}
export interface SerieVial {
  codigo: string;
  nombre: string;
  organismo: string;
  unidad: string;
  periodicidad: string;
  observaciones: number;
  desde: string;
  hasta: string;
  historia: ObservacionVial[];
  omitidas: number;
}
export interface SeriesViales {
  series: SerieVial[];
  responsable: string;
}
export interface ImportacionVial {
  serie: string;
  importada: boolean;
  observaciones: number | null;
  desde: string | null;
  hasta: string | null;
  mensaje: string;
}

export const COLUMNAS_HISTORIA: ColumnaDensa[] = [
  // La API manda aaaa-mm-dd; se lee dd/mm/aaaa. Con `celda` y no con `presentar`, para que el `title` no repita la forma ISO.
  { clave: "fecha", titulo: "Fecha", celda: (f) => fechaEsVe(f["fecha"] ?? "") },
  // Con `celda` y no con `presentar`: este dejaría el decimal con punto en el `title` (VD-5 vale también para las cifras de aquí).
  { clave: "valor", titulo: "Valor", numerica: true, celda: (f) => formatoEsVe(f["valor"] ?? "") },
  { clave: "estado", titulo: "Estado" },
];

export function filasDeHistoria(historia: ObservacionVial[]): FilaDensa[] {
  return historia.map((o) => ({
    id: o.fecha,
    fecha: o.fecha,
    valor: o.valor,
    estado: o.provisional ? "Provisional" : "Definitivo",
  }));
}

// La API nombra la unidad de un índice sin tilde (`indice`): aquí se lee «índice».
export function unidadLegible(unidad: string): string {
  return unidad === "indice" ? "índice" : unidad;
}

// «36 valores, del 01/10/2023 al 01/09/2026 (USD/l, mensual).»; sin valores, SIN_VALORES.
export function resumenDeLaSerie(serie: SerieVial): string {
  if (serie.observaciones === 0) return SIN_VALORES;
  const cuantos = serie.observaciones === 1 ? "1 valor" : `${formatoEsVe(String(serie.observaciones))} valores`;
  const rango =
    serie.desde === serie.hasta ? `el ${fechaEsVe(serie.desde)}` : `del ${fechaEsVe(serie.desde)} al ${fechaEsVe(serie.hasta)}`;
  return `${cuantos}, ${rango} (${unidadLegible(serie.unidad)}, ${serie.periodicidad}).`;
}

export function textoDeOmitidas(omitidas: number): string {
  const cuantas = omitidas === 1 ? "1 valor más antiguo no se muestra" : `${formatoEsVe(String(omitidas))} valores más antiguos no se muestran`;
  return `Se muestran los últimos valores; ${cuantas}.`;
}

export interface ErroresDeImportacion {
  fuente?: string;
  fecha?: string;
  archivo?: string;
}

// Lo que falta o sobra antes de enviar: la API lo diría igual, pero el campo lo dice sin ir y volver. La fecha ISO se
// compara como texto (aaaa-mm-dd ordena igual que el calendario).
export function validarImportacion(d: { archivo: File | null; fuente: string; fechaDescarga: string; hoy: string }): ErroresDeImportacion {
  const errores: ErroresDeImportacion = {};
  if (d.fuente.trim() === "") errores.fuente = SIN_FUENTE_VIAL;
  if (d.fechaDescarga === "") errores.fecha = SIN_FECHA_VIAL;
  else if (d.fechaDescarga > d.hoy) errores.fecha = FECHA_FUTURA_VIAL;
  if (d.archivo === null) errores.archivo = SIN_ARCHIVO_VIAL;
  return errores;
}

export function formularioDeImportacion(d: { serie: string; archivo: File; fuente: string; fechaDescarga: string }): FormData {
  const f = new FormData();
  f.append("serie", d.serie);
  f.append("archivo", d.archivo);
  f.append("fuente", d.fuente);
  f.append("fecha_descarga", d.fechaDescarga);
  return f;
}
