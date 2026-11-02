// Lógica pura del flujo «Importar plano (DXF o IFC)» de la pestaña Espacio (rebanada 3e-2: P1 a P6 del contrato
// docs/bitacora/2026-10-20-hoja-3e-contrato-rutas.md). Los textos son los de la clásica (ui/paginas/hoja.py:1238-1385) con
// sus tildes. Lo que escribe la persona (alturas, circuitos) viaja como TEXTO, tal cual: la coma decimal la decide el
// servidor. Aquí nada se convierte a número.
import type { FilaDensa } from "../../comun/TablaDensa";
import type { Resumen } from "./logica";

export const ROTULO_IMPORTAR = "Importar plano (DXF o IFC)";
export const ROTULO_LEER_PLANO = "Leer plano";
export const ROTULO_CARGAR_ALTURAS = "Cargar alturas";
export const ROTULO_DECLARAR_CIRCUITOS = "Declarar circuitos";
export const ROTULO_CONTINUAR_UNIDAD = "Continuar con esta unidad";
export const ROTULO_FUSIONAR = "Fusionar con el espacio del borrador";
export const ROTULO_DESCARTAR_PLANO = "Descartar la importación";

export const ETIQUETA_DE_SUBIDA = "Suelte aquí el plano .dxf o .ifc, o haga clic para elegirlo";
export const EXTENSIONES_DE_PLANO = [".dxf", ".ifc"];

export const AYUDA_PLANO =
  "Suba un plano en formato DXF o IFC. El plano crea filas en el borrador de esta hoja, con el archivo como origen de medida, y un informe de lo que importó, lo que no reconoció, lo que aproximó y lo que queda pendiente. Nada salta la hoja ni la auditoría: las filas entran para que las revise.";
export const AYUDA_ALTURAS =
  "El plano no trae la altura de estos ambientes. Escríbala en metros (por ejemplo 2,50); los que deje en blanco siguen pendientes.";
export const AYUDA_CIRCUITOS =
  "El plano no dice cuántos conductores tiene cada circuito ni cuántos puntos admite: se supusieron. Confírmelos o corríjalos; mientras sean supuestos, la auditoría lo advierte.";
export const AVISO_SIN_ARCHIVO = "Elija primero un archivo de plano (DXF o IFC) y pulse Leer plano.";

// Las cuatro columnas de la tabla del informe (COLUMNAS_DEL_INFORME de la clásica).
export const COLUMNAS_DEL_INFORME = [
  { clave: "tipo", titulo: "Tipo" },
  { clave: "referencia", titulo: "En el plano" },
  { clave: "fila", titulo: "Fila de la hoja" },
  { clave: "mensaje", titulo: "Qué pasó" },
];

// Los cuatro campos de cada circuito, en el orden en que viajan (fase, neutro, tierra, puntos).
export const CAMPOS_DE_CIRCUITO = [
  { clave: "fase", rotulo: "Conductores de fase" },
  { clave: "neutro", rotulo: "Conductores de neutro" },
  { clave: "tierra", rotulo: "Conductores de tierra" },
  { clave: "puntos", rotulo: "Puntos máximos" },
] as const;

// --- lo que contesta el servidor (esquemas del contrato) ---

export interface ConteoDePlano {
  rotulo: string;
  cantidad: number;
}

export interface FilaDeInforme {
  tipo: string;
  referencia: string;
  fila: string;
  mensaje: string;
}

export interface AlturaPendiente {
  id: string;
  nombre: string;
}

export interface CircuitoSupuesto {
  id: string;
  fase: string;
  neutro: string;
  tierra: string;
  puntos: string;
}

export interface ImportacionRespuesta {
  estado: "importada" | "detenida" | "rechazada";
  archivo: string;
  mensaje: string;
  pide_unidad: boolean;
  unidades: string[];
  conteos: ConteoDePlano[];
  informe: FilaDeInforme[];
  alturas_pendientes: AlturaPendiente[];
  circuitos_supuestos: CircuitoSupuesto[];
  aviso_pendientes: string | null;
}

export interface ResumenDeFusionRespuesta {
  por_tipo: ConteoDePlano[];
  filas_por_tabla: ConteoDePlano[];
  origenes: number;
}

// P5: el `rev` es el nuevo (= `resumen.rev`); `informe` es el de la fusión y `mensaje` el de éxito de la clásica.
export interface RespuestaDeFusion {
  rev: number;
  resumen: Resumen;
  fusion: ResumenDeFusionRespuesta;
  informe: FilaDeInforme[];
  mensaje: string;
}

export type ValoresDeCircuito = [string, string, string, string];

// --- rutas (P1 a P6) ---

const rutaDelBorrador = (id: string) => `/v1/hoja/borradores/${id}`;

export const rutaDePlano = (id: string) => `${rutaDelBorrador(id)}/plano`;
export const rutaDeUnidad = (id: string) => `${rutaDePlano(id)}/unidad`;
export const rutaDeAlturas = (id: string) => `${rutaDePlano(id)}/alturas`;
export const rutaDeCircuitos = (id: string) => `${rutaDePlano(id)}/circuitos`;
export const rutaDeFusion = (id: string) => `${rutaDePlano(id)}/fusionar`;

// --- lo que se manda ---

// P1: el archivo y el `rev` como campos del formulario (el `rev` va como texto, el servidor lo lee entero).
export function formularioDeLectura(rev: number, archivo: File): FormData {
  const formulario = new FormData();
  formulario.append("archivo", archivo);
  formulario.append("rev", String(rev));
  return formulario;
}

export function cuerpoDeUnidad(rev: number, unidades: string): { rev: number; unidades: string } {
  return { rev, unidades };
}

// P3: un texto por ambiente pendiente (en blanco si la persona no escribió). Lo escrito para un ambiente que ya no está
// pendiente no viaja.
export function cuerpoDeAlturas(
  rev: number,
  pendientes: AlturaPendiente[],
  textos: Record<string, string>,
): { rev: number; alturas: Record<string, string> } {
  return { rev, alturas: Object.fromEntries(pendientes.map((p) => [p.id, textos[p.id] ?? ""])) };
}

// Los valores con que arranca cada circuito: los que supuso el servidor, como texto.
export function valoresDeCircuitos(supuestos: CircuitoSupuesto[]): Record<string, ValoresDeCircuito> {
  return Object.fromEntries(supuestos.map((c) => [c.id, [c.fase, c.neutro, c.tierra, c.puntos] as ValoresDeCircuito]));
}

// P4: los cuatro textos de cada circuito supuesto, en el orden fase, neutro, tierra, puntos.
export function cuerpoDeCircuitos(
  rev: number,
  supuestos: CircuitoSupuesto[],
  valores: Record<string, ValoresDeCircuito>,
): { rev: number; circuitos: Record<string, ValoresDeCircuito> } {
  const base = valoresDeCircuitos(supuestos);
  return { rev, circuitos: Object.fromEntries(supuestos.map((c) => [c.id, valores[c.id] ?? base[c.id]!])) };
}

// --- etiquetas ---

// Como la clásica (ui/paginas/hoja.py:1383): el id y, si el nombre difiere, el nombre entre paréntesis.
export function etiquetaDeAltura(p: AlturaPendiente): string {
  const nombre = p.nombre === p.id ? p.id : `${p.id} (${p.nombre})`;
  return `Altura de ${nombre}, en metros`;
}

export function etiquetaDeCampoDeCircuito(rotulo: string, id: string): string {
  return `${rotulo} del circuito ${id}`;
}

// --- el informe ---

export function filasDelInforme(informe: FilaDeInforme[]): FilaDensa[] {
  return informe.map((f, i) => ({ id: `informe-${i}`, tipo: f.tipo, referencia: f.referencia, fila: f.fila, mensaje: f.mensaje }));
}

// --- textos de resultado ---

// Lo que se dice tras «Cargar alturas»: cuántas se escribieron y cuántos ambientes siguen pendientes (cuentas, no montos).
export function textoDeAlturasCargadas(escritas: string[], pendientes: number): string {
  const cargadas = escritas.filter((t) => t.trim() !== "").length;
  const primera =
    cargadas === 0
      ? "No escribió ninguna altura."
      : cargadas === 1
        ? "Se cargó 1 altura."
        : `Se cargaron ${cargadas} alturas.`;
  const segunda =
    pendientes === 0
      ? "No quedan ambientes pendientes."
      : pendientes === 1
        ? "Queda 1 ambiente pendiente."
        : `Quedan ${pendientes} ambientes pendientes.`;
  return `${primera} ${segunda}`;
}

export function textoDeCircuitosDeclarados(n: number): string {
  return n === 1 ? "Se declaró 1 circuito." : `Se declararon ${n} circuitos.`;
}

// ui/paginas/hoja.py:1385-1390.
export function lineaDeFilasPorTabla(filasPorTabla: ConteoDePlano[]): string {
  const texto = filasPorTabla.map((f) => `${f.rotulo} ${f.cantidad}`).join(" · ");
  return `Filas que entraron al borrador: ${texto || "ninguna"}.`;
}

export function lineaDeOrigenes(origenes: number): string {
  return `${origenes} orígenes de medida del plano, aparte de las filas: cada fila importada cita el suyo.`;
}

// --- textos del servidor ---

// El texto de la clásica cuando falta el lector (`uv sync --extra planos|civil`) habla de un comando que quien usa Sílice
// no corre (VB-18). Solo se reemplaza el texto EXACTO de las dos plantillas del servidor; cualquier otro queda tal cual. La
// comparación es de igualdad (costo lineal en el largo, sin expresiones regulares ni búsquedas sobre el texto del usuario).
const LECTORES: Array<[string, string]> = [
  ["DXF", "planos"],
  ["IFC", "civil"],
];

export function textoDeLector(detalle: string): string {
  for (const [formato, extra] of LECTORES) {
    const servidor = `Falta instalar el componente para leer planos ${formato}. Instale el extra «${extra}» con el comando «uv sync --extra ${extra}» y vuelva a intentarlo.`;
    if (detalle === servidor) {
      return `Falta instalar el componente para leer planos ${formato}. Pídalo a quien instaló Sílice y vuelva a intentarlo.`;
    }
  }
  return detalle;
}

// El 409 de P2 a P5 cuando el servidor ya no tiene la importación (reinicio, vencimiento): hay que subir el plano otra vez.
export function esImportacionPerdida(detalle: string): boolean {
  return detalle.startsWith("Vuelva a subir el plano");
}
