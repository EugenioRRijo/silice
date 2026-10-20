// Lógica pura de «Hoja del proyecto» (marco de la rebanada 3b-1). Los montos llegan como texto
// `{texto, exacto}` y la página solo los formatea: no calcula ni convierte nada a número.
import { ErrorDeApi } from "../../api/cliente";
import type { HallazgoInformeRespuesta, InformeAuditoriaRespuesta } from "../../api/tipos";

export const TITULO = "Hoja del proyecto";
export const SIN_VERSIONES = "Este proyecto aún no tiene versiones";

// El orden de la página clásica (ui/paginas/hoja.py, PESTANAS).
export const PESTANAS = [
  "Espacio y metrajes",
  "APU",
  "Presupuesto",
  "Plan y curva",
  "Punto de equilibrio",
  "Precios",
  "Parámetros",
  "Auditoría",
  "Trazabilidad",
] as const;

export interface Monto {
  texto: string;
  exacto: string;
}

export interface VersionFila {
  codigo: string;
  fecha: string;
  motivo: string;
  origen: string;
  vigente: boolean;
  descartada: boolean;
  cambios: number;
}

export interface VersionesRespuesta {
  proyecto: string;
  moneda: string;
  // La versión que se preselecciona (la regla de la clásica, calculada en el servidor).
  por_omision: string | null;
  versiones: VersionFila[];
}

export interface BaseAbierta {
  proyecto: string;
  version: string | null;
  vigente: string | null;
  lista: string | null;
  espacio_de: string | null;
  solo_lectura: boolean;
  moneda: string;
}

export interface Hallazgos {
  severidad: string;
  total: number;
}

export interface Resumen {
  rev: number;
  moneda: string;
  total: Monto;
  cambios: number;
  pendientes_catalogo: number;
  hallazgos: Hallazgos[];
  hay_plan: boolean;
  version_mas_nueva: string | null;
  guardado_como: string | null;
}

export interface BorradorVivo {
  id: string;
  base: BaseAbierta;
  resumen: Resumen;
}

export interface BorradorAbierto extends BorradorVivo {
  instantanea: { creadas: number; mensaje: string | null };
}

export function rutaDeVersiones(proyecto: string): string {
  return `/v1/hoja/versiones?proyecto=${encodeURIComponent(proyecto)}`;
}

// Las no descartadas; si todas lo están, todas (ui/paginas/hoja.py:417).
export function versionesOfrecidas(versiones: VersionFila[]): VersionFila[] {
  const vivas = versiones.filter((v) => !v.descartada);
  return vivas.length > 0 ? vivas : versiones;
}

export function rotuloDeVersion(version: VersionFila): string {
  return version.vigente ? `${version.codigo} (vigente)` : version.codigo;
}

export function textoDeCambios(cambios: number): string {
  if (cambios === 0) return "Sin cambios sin guardar";
  return cambios === 1 ? "1 cambio sin guardar" : `${cambios} cambios sin guardar`;
}

// El 404 de un borrador que el servidor ya no tiene (reinicio, vencimiento, descarte), no el de un proyecto.
export function esBorradorAusente(error: unknown): boolean {
  return error instanceof ErrorDeApi && error.estado === 404 && error.detalle.startsWith("Ese borrador ya no está");
}

// --- vistas de las pestañas (rebanada 3b-2): lo que contesta `GET /v1/hoja/borradores/{id}/vistas/{nombre}` ---

export type NombreDeVista =
  | "espacio"
  | "presupuesto"
  | "apu"
  | "plan"
  | "equilibrio"
  | "parametros"
  | "auditoria";

export function rutaDeVista(
  id: string,
  nombre: NombreDeVista,
  parametros: Record<string, string | undefined> = {},
): string {
  const consulta = new URLSearchParams();
  for (const [clave, valor] of Object.entries(parametros)) if (valor) consulta.set(clave, valor);
  const texto = consulta.toString();
  return `/v1/hoja/borradores/${id}/vistas/${nombre}${texto ? `?${texto}` : ""}`;
}

export interface EstadoFila {
  // Peor severidad de la fila (CRITICO, ERROR, ADVERTENCIA, INFO) o null si ningún hallazgo la toca.
  severidad: string | null;
  texto: string;
}

export interface OpcionLista {
  valor: string;
  rotulo: string;
}

export interface ColumnaTabla {
  clave: string;
  rotulo: string;
  lista: OpcionLista[] | null;
}

export interface TablaEspacio {
  clave: string;
  rotulo: string;
  columnas: ColumnaTabla[];
  con_estado: boolean;
}

export interface CantidadDerivada {
  partida: string;
  descripcion: string;
  unidad: string;
  cantidad: Monto;
  origen: string;
}

export interface VistaEspacio {
  ayuda: string;
  tablas: TablaEspacio[];
  filas: Record<string, Array<Record<string, string>>>;
  estado: Record<string, EstadoFila>;
  derivadas: CantidadDerivada[];
  total: Monto;
  moneda: string;
  pendientes: number;
  vacio_mensaje: string | null;
}

export interface FilaPresupuesto {
  clave: string;
  partida: string;
  descripcion: string;
  unidad: string;
  cantidad: string;
  cantidad_calculada: string;
  escrita: boolean;
  pu: Monto | null;
  total: Monto | null;
  estado: EstadoFila;
}

export interface VistaPresupuesto {
  filas: FilaPresupuesto[];
  total: Monto;
  moneda: string;
  vacio_mensaje: string | null;
}

export interface PartidaDeLista {
  codigo: string;
  descripcion: string;
}

export interface GrupoApu {
  clave: string;
  rotulo: string;
  columnas: Array<{ clave: string; rotulo: string }>;
  filas: Array<Record<string, string>>;
  subtotal: Monto;
}

export interface DetalleApu {
  codigo: string;
  descripcion: string;
  unidad: string;
  rendimiento: string;
  grupos: GrupoApu[];
  cierre: Array<{ concepto: string; monto: Monto; nota: string }>;
  metricas: { materiales: Monto; equipos: Monto; mano_obra: Monto; precio_unitario: Monto };
  estados: string[];
  solo_lectura_insumos: boolean;
}

export interface VistaApu {
  partidas: PartidaDeLista[];
  sin_coincidencias: boolean;
  seleccionada: string | null;
  detalle: DetalleApu | null;
  vacio_mensaje: string | null;
}

export interface VistaPlan {
  hay_plan: boolean;
  etiquetas: string[];
  filas: Array<{ partida: string; valores: Record<string, string> }>;
  curva: Array<{ periodo: string; monto: Monto; acumulado: Monto; porcentaje: Monto }>;
  moneda: string;
  mensaje: string | null;
}

// Prefijo con que el servidor nombra el Estado de cada fila editable (`esp_puntos:P1`).
export const PREFIJO_DE_ESTADO: Record<string, string> = {
  ambientes: "esp_ambientes",
  fuentes: "esp_fuentes",
  puntos: "esp_puntos",
};

export function textoDeFilas(n: number): string {
  return n === 1 ? "1 fila" : `${n} filas`;
}

// El valor de una celda como lo ve la persona: el rótulo de su lista cerrada, o el texto tal cual.
export function celdaVisible(columna: ColumnaTabla, valor: string): string {
  if (columna.lista === null) return valor;
  return columna.lista.find((o) => o.valor === valor)?.rotulo ?? valor;
}

// Filas de una tabla del espacio listas para `TablaDensa`: sus columnas llevan prefijo (`c_id`) porque `id` es de la fila.
export function filasDeTabla(
  tabla: TablaEspacio,
  filas: Array<Record<string, string>>,
  estado: Record<string, EstadoFila>,
): Array<{ id: string } & Record<string, string>> {
  const prefijo = PREFIJO_DE_ESTADO[tabla.clave];
  return filas.map((fila, i) => {
    const salida: { id: string } & Record<string, string> = { id: `${tabla.clave}-${i}` };
    for (const c of tabla.columnas) salida[`c_${c.clave}`] = celdaVisible(c, fila[c.clave] ?? "");
    const e = prefijo ? estado[`${prefijo}:${fila.id ?? ""}`] : undefined;
    salida.estado_severidad = e?.severidad ?? "";
    salida.estado_texto = e?.texto ?? "";
    salida.estado_origen = prefijo && fila.id ? `${prefijo}:${fila.id}` : "";
    return salida;
  });
}

export const LIMITE_SIN_PAGINAR = 100;
export const FILAS_POR_PAGINA = 50;

// --- rebanada 3b-3: Punto de equilibrio, Parámetros, Auditoría, Precios y Trazabilidad ---

export interface VistaEquilibrio {
  estado: string;
  moneda: string;
  venta: Monto;
  costo_variable: Monto;
  costo_fijo: Monto;
  utilidad: Monto;
  // Sin punto (no hay ventas, el margen no es positivo...) el servidor manda null y la frase que lo explica.
  punto: Monto | null;
  porcentaje: Monto | null;
  periodo: string | null;
  fraccion_periodo: string | null;
  mensaje: string;
}

export interface VistaParametros {
  campos: Array<{ clave: string; rotulo: string; valor: string }>;
  moneda_proyecto: string | null;
  total: Monto;
  puede_convertir: boolean;
}

export type VistaAuditoria = InformeAuditoriaRespuesta;

export interface ColumnaPrecio {
  clave: string;
  rotulo: string;
  numerica: boolean;
}

// Cada celda llega como texto, como `{texto, exacto}` (los montos) o null (sin dato).
export type CeldaPrecio = string | Monto | null;

export interface PreciosRespuesta {
  moneda: string;
  fecha_evaluacion: string;
  columnas: ColumnaPrecio[];
  filas: Array<Record<string, CeldaPrecio>>;
}

export interface AvisoAtipicos {
  nivel: "info" | "success";
  texto: string;
}

export interface VariacionAtipica {
  insumo: string;
  porcentaje: string;
  porcentaje_exacto: string;
  desde: string;
  hasta: string;
  severidad: string;
  descripcion: string;
}

export interface AtipicosRespuesta {
  disponible: boolean;
  avisos: AvisoAtipicos[];
  variaciones: VariacionAtipica[];
}

export interface RegistroDeCambio {
  objeto: string;
  clave: string;
  campo: string;
  antes: string;
  despues: string;
  fuente: string;
  responsable: string;
  fecha_hora: string;
}

export interface TrazabilidadRespuesta {
  versiones: VersionFila[];
  registros: RegistroDeCambio[];
  vacio_mensaje: string | null;
}

function consultaDeVersion(proyecto: string, version: string): string {
  return new URLSearchParams({ proyecto, version }).toString();
}

export const rutaDePrecios = (proyecto: string, version: string) =>
  `/v1/hoja/precios?${consultaDeVersion(proyecto, version)}`;
export const rutaDeAtipicos = (proyecto: string, version: string) =>
  `/v1/hoja/precios/atipicos?${consultaDeVersion(proyecto, version)}`;
export const rutaDeTrazabilidad = (proyecto: string, version: string) =>
  `/v1/hoja/trazabilidad?${consultaDeVersion(proyecto, version)}`;

const NOMBRE_DE_PREFIJO: Record<string, string> = {
  esp_origenes: "Origen",
  esp_ambientes: "Ambiente",
  esp_fuentes: "Fuente",
  esp_puntos: "Punto",
  esp_tramos: "Tramo",
};

function rotuloDeFila(texto: string): string {
  const m = /^(esp_[a-z]+):(.+)$/.exec(texto);
  const nombre = m ? NOMBRE_DE_PREFIJO[m[1]!] : undefined;
  return m && nombre ? `${nombre} ${m[2]}` : texto;
}

// La clave de fila del servidor («esp_puntos:P1», «AF-LLAVE|esp_puntos:P1#2») como la nombra la persona.
export function rotuloDeOrigen(origen: string): string {
  const repetido = /^(.*)#(\d+)$/.exec(origen);
  const base = repetido ? repetido[1]! : origen;
  const sufijo = repetido ? ` (${repetido[2]})` : "";
  const barra = base.indexOf("|");
  const texto = barra < 0 ? rotuloDeFila(base) : `${base.slice(0, barra)}, ${rotuloDeFila(base.slice(barra + 1))}`;
  return texto + sufijo;
}

// Con qué claves se busca, en el origen de los hallazgos, un renglón del presupuesto (`partida|origen#2`).
export function clavesDeAuditoria(clave: string): string[] {
  const claves = [clave];
  const sinRepeticion = clave.replace(/#\d+$/, "");
  if (sinRepeticion !== clave) claves.push(sinRepeticion);
  const barra = sinRepeticion.indexOf("|");
  if (barra >= 0) claves.push(sinRepeticion.slice(barra + 1));
  return claves;
}

export function hallazgosDeOrigen(hallazgos: HallazgoInformeRespuesta[], claves: string[]): HallazgoInformeRespuesta[] {
  return hallazgos.filter((h) => h.origen.some((o) => claves.includes(o)));
}

const PRINCIPALES_DE_PRECIOS = [
  "Insumo",
  "Código",
  "Precio",
  "Lista",
  "Moneda",
  "Fecha del precio",
  "Referencia",
  "Cotización",
  "Estado",
];
const EROSION_POR_INDICE = "Erosión por índice";

// Las columnas que van en la tabla y las que se leen en el detalle del insumo. «Erosión por índice» solo se ofrece si
// algún valor viene (DV-11): la clásica nunca la llenaba.
export function partirColumnasDePrecios(
  columnas: ColumnaPrecio[],
  hayIndice: boolean,
): { principales: ColumnaPrecio[]; detalle: ColumnaPrecio[] } {
  return {
    principales: columnas.filter((c) => PRINCIPALES_DE_PRECIOS.includes(c.rotulo)),
    detalle: columnas.filter(
      (c) => !PRINCIPALES_DE_PRECIOS.includes(c.rotulo) && (c.rotulo !== EROSION_POR_INDICE || hayIndice),
    ),
  };
}

// 2026-07-01 -> 01/07/2026 (y «2026-10-06 09:30:00» -> «06/10/2026 09:30:00»); lo que no empieza por una fecha queda igual.
export function fechaCorta(texto: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})(.*)$/.exec(texto);
  return m ? `${m[3]}/${m[2]}/${m[1]}${m[4]!.replace(/^T/, " ")}` : texto;
}
