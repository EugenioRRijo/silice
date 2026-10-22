// Logica pura de «Índices del BCV» (UC-17 pasos 1-3): arma los formularios y las tablas con lo que manda la API. No
// calcula ni redondea nada: la API solo trae recuentos y rangos de fechas, y los mensajes se muestran tal cual.
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";

export const AYUDA =
  "Importe la tasa de referencia del BCV, el INPC o una serie en CSV. «Leer» no escribe nada: muestra lo que se " +
  "importaría. «Confirmar» guarda los valores con la huella del archivo; el mismo archivo dos veces no escribe nada.";
export const SIN_ARCHIVO = "Elija el archivo que bajó del BCV.";
// Es el mismo texto que da la API al leer un .xls sin xlrd: aquí se adelanta, antes de enviar.
export const AVISO_SIN_XLRD =
  "No se puede leer un archivo .xls: falta el componente xlrd (extra «bcv» de la instalación). " +
  "Instálelo, o use el .xlsx o el CSV canónico.";
export const PERIODICIDAD_POR_DEFECTO = "mensual";

export interface TipoArchivo {
  id: string;
  rotulo: string;
}
export interface Contexto {
  tipos: TipoArchivo[];
  periodicidades: string[];
  unidad_por_defecto: string;
  extensiones: string[];
  lee_xls: boolean;
  responsable: string;
}
export interface SerieLeida {
  clave: string;
  valores: number;
  desde: string;
  hasta: string;
}
export interface Rechazo {
  lugar: string;
  motivo: string;
}
export interface Informe {
  archivo: string;
  huella: string;
  fuente: string;
  fecha_descarga: string;
  filas_leidas: number;
  filas_rechazadas: number;
  provisionales: number;
  series: SerieLeida[];
  rechazos: Rechazo[];
  rechazos_omitidos: number;
  advertencias: string[];
}
export interface Confirmacion {
  mensajes: string[];
}
// Una serie de un CSV no trae nombre, organismo, unidad ni periodicidad: los declara la persona.
export interface Definicion {
  serie: string;
  nombre: string;
  organismo: string;
  unidad: string;
  periodicidad: string;
}
// Lo que se leyó y con qué: «confirmar» vuelve a mandar exactamente esto.
export interface Lectura {
  tipo: string;
  archivo: File;
  fuente: string;
  fechaDescarga: string;
  informe: Informe;
}

export const COLUMNAS_SERIES: ColumnaDensa[] = [
  { clave: "serie", titulo: "Serie" },
  { clave: "valores", titulo: "Valores", numerica: true },
  { clave: "desde", titulo: "Desde" },
  { clave: "hasta", titulo: "Hasta" },
];
export const COLUMNAS_RECHAZOS: ColumnaDensa[] = [
  { clave: "lugar", titulo: "Lugar" },
  { clave: "motivo", titulo: "Motivo" },
];

export function filasSeries(series: SerieLeida[]): FilaDensa[] {
  return series.map((s, i) => ({
    id: `${i}-${s.clave}`,
    serie: s.clave,
    valores: String(s.valores),
    desde: s.desde,
    hasta: s.hasta,
  }));
}

export function filasRechazos(rechazos: Rechazo[]): FilaDensa[] {
  return rechazos.map((r, i) => ({ id: `${i}`, lugar: r.lugar, motivo: r.motivo }));
}

export function textoOmitidos(omitidos: number): string {
  return `Hay ${omitidos} ${omitidos === 1 ? "fila rechazada más" : "filas rechazadas más"} que no se muestran aquí.`;
}

// Fecha local de hoy en YYYY-MM-DD (lo que manda el input de fecha y lo que lee la API).
export function hoyIso(ahora: Date = new Date()): string {
  const mes = String(ahora.getMonth() + 1).padStart(2, "0");
  const dia = String(ahora.getDate()).padStart(2, "0");
  return `${ahora.getFullYear()}-${mes}-${dia}`;
}

export function esXls(archivo: File | null): boolean {
  return archivo !== null && archivo.name.toLowerCase().endsWith(".xls");
}

// Un .xls de tasa o INPC necesita xlrd; el CSV no lo usa.
export function faltaXlrd(tipo: string, archivo: File | null, leeXls: boolean): boolean {
  return !leeXls && tipo !== "csv" && esXls(archivo);
}

export function formularioLectura(d: {
  tipo: string;
  archivo: File;
  fuente: string;
  fechaDescarga: string;
}): FormData {
  const f = new FormData();
  f.append("tipo", d.tipo);
  f.append("archivo", d.archivo);
  f.append("fuente", d.fuente);
  f.append("fecha_descarga", d.fechaDescarga);
  return f;
}

export function formularioConfirmacion(lectura: Lectura, definiciones: Definicion[]): FormData {
  const f = formularioLectura(lectura);
  f.append("huella", lectura.informe.huella);
  // Solo un CSV lleva definiciones; para tasa e INPC la API las ignora y no hace falta mandarlas.
  f.append("definiciones", JSON.stringify(lectura.tipo === "csv" ? definiciones : []));
  return f;
}

export function definicionesIniciales(series: SerieLeida[], unidad: string, periodicidades: string[]): Definicion[] {
  const periodicidad = periodicidades.includes(PERIODICIDAD_POR_DEFECTO)
    ? PERIODICIDAD_POR_DEFECTO
    : (periodicidades[0] ?? PERIODICIDAD_POR_DEFECTO);
  return series.map((s) => ({ serie: s.clave, nombre: s.clave, organismo: "", unidad, periodicidad }));
}

export function cambiarDefinicion(
  definiciones: Definicion[],
  posicion: number,
  campo: keyof Omit<Definicion, "serie">,
  valor: string,
): Definicion[] {
  return definiciones.map((d, i) => (i === posicion ? { ...d, [campo]: valor } : d));
}
