// Lógica pura de «Archivos y planos» (Tarea 11 del plan F4): las filas del registro de importaciones de la obra
// (`GET /v1/hoja/importaciones`, Tarea 10) y qué flujo sigue cada archivo que se sube. La interfaz no calcula: el resumen
// («33 filas en el espacio») y la versión llegan como texto del servidor; aquí solo se presentan (la fecha, en es-VE).
import type { FilaDensa } from "../../comun/TablaDensa";
import { fechaEsVe } from "../../indicadores/formatoEsVe";
import { EXTENSIONES_DE_PLANO } from "./logicaPlano";

export interface ImportacionDeObra {
  tipo: "plano" | "computo";
  // Solo el nombre, sin ruta (el servidor no guarda copia del archivo).
  archivo: string;
  // ISO a segundos, hora del servidor: «2026-10-31T14:05:09».
  fecha_hora: string;
  // «Nombre <login>», como el responsable de una versión.
  usuario: string;
  resumen: string;
  // La versión que la guardó; null mientras siga en un borrador sin guardar.
  version: string | null;
  guardada: boolean;
}

export interface ImportacionesRespuesta {
  importaciones: ImportacionDeObra[];
}

export const rutaDeImportaciones = (proyecto: string) => `/v1/hoja/importaciones?proyecto=${encodeURIComponent(proyecto)}`;

// Las seis columnas del registro, en este orden. El servidor ya las manda de la más nueva a la más vieja: no se ordenan
// aquí (la fecha en es-VE no se ordena bien como texto).
export const COLUMNAS_DEL_REGISTRO = [
  { clave: "nombre", titulo: "Nombre" },
  { clave: "tipo", titulo: "Tipo" },
  { clave: "fecha", titulo: "Fecha y hora" },
  { clave: "quien", titulo: "Quién" },
  { clave: "produjo", titulo: "Qué produjo" },
  { clave: "version", titulo: "Versión" },
] as const;

const NOMBRE_DEL_TIPO: Record<ImportacionDeObra["tipo"], string> = { plano: "Plano", computo: "Cómputo" };
const EXTENSION_DEL_TIPO: Record<ImportacionDeObra["tipo"], readonly string[]> = { plano: EXTENSIONES_DE_PLANO, computo: [".csv"] };
export const SIN_GUARDAR = "sin guardar";

function extension(nombre: string): string {
  const punto = nombre.lastIndexOf(".");
  return punto <= 0 ? "" : nombre.slice(punto).toLowerCase();
}

// «Plano .dxf», «Plano .ifc» o «Cómputo .csv»; con una extensión que no es la del tipo, solo el tipo.
export function tipoDeImportacion(tipo: ImportacionDeObra["tipo"], archivo: string): string {
  const ext = extension(archivo);
  return EXTENSION_DEL_TIPO[tipo].includes(ext) ? `${NOMBRE_DEL_TIPO[tipo]} ${ext}` : NOMBRE_DEL_TIPO[tipo];
}

// El `id` de cada fila es su lugar en la respuesta: así la pantalla encuentra la importación que la persona elige.
export function filasDeImportaciones(r: ImportacionesRespuesta): FilaDensa[] {
  return r.importaciones.map((i, lugar) => ({
    id: `importacion-${lugar}`,
    nombre: i.archivo,
    tipo: tipoDeImportacion(i.tipo, i.archivo),
    fecha: fechaEsVe(i.fecha_hora),
    quien: i.usuario,
    produjo: i.resumen,
    version: i.guardada ? (i.version ?? "") : SIN_GUARDAR,
  }));
}

export type FlujoDeArchivo = "plano" | "computo";

// El diálogo «Subir plano o cómputo» elige el flujo por la extensión: .dxf y .ifc van al plano y .csv al cómputo.
export function flujoDelArchivo(nombre: string): FlujoDeArchivo | null {
  const ext = extension(nombre);
  if (EXTENSIONES_DE_PLANO.includes(ext)) return "plano";
  if (ext === ".csv") return "computo";
  return null;
}

// Mientras no hay flujo del cómputo (llega con la Tarea 12) la subida no acepta .csv: no hay pantallas «pronto».
export function extensionesDeSubida(conComputo: boolean): string[] {
  return conComputo ? [...EXTENSIONES_DE_PLANO, ".csv"] : [...EXTENSIONES_DE_PLANO];
}

export function etiquetaDeSubida(conComputo: boolean): string {
  return conComputo
    ? "Suelte aquí el plano .dxf o .ifc, o el cómputo .csv, o haga clic para elegirlo"
    : "Suelte aquí el plano .dxf o .ifc, o haga clic para elegirlo";
}
