// Las secciones de una obra y las entradas de la zona Empresa del marco nuevo, con sus rutas (plan del rediseño del
// marco, Tarea 4; especificación 2026-10-26, §8 ter). Cada una monta, por ahora, una pantalla existente por su `id` de
// `shell/rutas.ts` (patrón estrangulador): `pagina` es ese id. Una sección con `pagina: null` aún no tiene pantalla
// propia (llega en F4): no se pinta en el árbol ni se abre por enlace, y no hay pantallas «próximamente».
//
// Rutas (HashRouter): `#/pendientes`, `#/obra/<carpeta>/<obra>/<sección>[/<subvista>]` y `#/empresa/<entrada>`. La carpeta viaja
// con su .db, que es el nombre que acepta `POST /v1/casos/actual`; la de la empresa se escribe `empresa` (ningún
// nombre de carpeta puede serlo, porque todos terminan en .db).

export type SeccionId = "resumen" | "presupuesto" | "tramos" | "archivos" | "versiones" | "aprobaciones" | "mercado" | "control" | "riesgo";

export interface SeccionDef {
  id: SeccionId;
  titulo: string;
  pagina: string | null;
  // Para qué sirve, en una frase de hasta 90 caracteres, con las palabras de quien la usa.
  ayuda: string;
}

export const SECCIONES_DE_OBRA: readonly SeccionDef[] = [
  { id: "resumen", titulo: "Resumen", pagina: "obras", ayuda: "La obra de un vistazo: sus cifras, su versión vigente y lo pendiente." },
  { id: "presupuesto", titulo: "Presupuesto", pagina: "hoja", ayuda: "Las partidas de la obra con sus cantidades, precios y APU." },
  { id: "tramos", titulo: "Tramos", pagina: "tramos", ayuda: "Los tramos de la vía con sus cantidades de obra." },
  { id: "archivos", titulo: "Archivos y planos", pagina: "archivos", ayuda: "Los planos y documentos de la obra." },
  { id: "versiones", titulo: "Versiones", pagina: "versiones", ayuda: "Las versiones guardadas del presupuesto y lo que cambió en cada una." },
  { id: "aprobaciones", titulo: "Aprobaciones", pagina: "aprobar", ayuda: "Las versiones que esperan dictamen y lo que se entregó al cliente." },
  { id: "mercado", titulo: "Mercado", pagina: "mercado", ayuda: "Los precios del mercado para los insumos de la obra, su histórico y las cotizaciones." },
  { id: "control", titulo: "Control de obra", pagina: "control", ayuda: "Lo avanzado en obra frente a lo planificado, con sus valuaciones." },
  { id: "riesgo", titulo: "Riesgo", pagina: "riesgo", ayuda: "Cuánto puede subir el presupuesto de la obra si cambian los precios." },
];

export type EntradaId = "personas" | "ayuda";

export interface EntradaDef {
  id: EntradaId;
  titulo: string;
  pagina: string;
  ayuda: string;
}

// En este orden. Ayuda monta «Acerca de Sílice» hasta que F6 traiga las guías. Precios, Auditoría y Producción dejaron de
// ser entradas (F6, T4): son espacios con su propia ruta (`espacios.ts`).
export const ENTRADAS_DE_EMPRESA: readonly EntradaDef[] = [
  { id: "personas", titulo: "Empresa y personas", pagina: "administracion", ayuda: "Los datos de la empresa, las cuentas de las personas y sus permisos." },
  { id: "ayuda", titulo: "Ayuda", pagina: "acerca", ayuda: "Cómo hacer cada tarea en Sílice, y la versión y licencia del programa." },
];

// Busca solo entre las propias (un `id` como «toString» no es sección).
export function seccionPorId(id: string): SeccionDef | undefined {
  return SECCIONES_DE_OBRA.find((s) => s.id === id);
}

// Las secciones que trabajan sobre el borrador de la Hoja (Tarea 3 del plan F4): lo comparten por `ProveedorDeLaHoja`,
// así que pasar de una a otra de la misma obra no lo cierra ni pregunta por sus cambios.
export const SECCIONES_CON_HOJA: readonly SeccionId[] = ["presupuesto", "archivos", "versiones"];

// Si `destino` (una ruta, con o sin consulta) es una sección con Hoja de esa misma obra. Compara el segmento de la sección
// y no la ruta entera: una subvista de esa sección (Componer, en `/presupuesto/componer`) comparte el borrador igual
// (nota H-F6-1 de Antigravity).
export function quedaEnLaHoja(destino: string, carpeta: string | null, obraId: number): boolean {
  const camino = destino.split(/[?#]/)[0];
  return SECCIONES_CON_HOJA.some((s) => {
    const seccion = rutaDeObra(carpeta, obraId, s);
    return camino === seccion || camino.startsWith(`${seccion}/`);
  });
}

export const RUTA_DE_PENDIENTES = "/pendientes";
// El cuarto segmento (`:subvista`) es opcional: sin él, la ruta es la de la pantalla principal de la sección.
export const PATRON_DE_OBRA = "/obra/:carpeta/:obraId/:seccion/:subvista?";
export const PATRON_DE_EMPRESA = "/empresa/:entrada";
const SEGMENTO_DE_LA_EMPRESA = "empresa";

// `subvista` es el `id` de una subvista de la sección (`SUBVISTAS`); vacío o ausente, la pantalla principal.
export function rutaDeObra(carpeta: string | null, obraId: number, seccion: SeccionId, subvista?: string): string {
  const segmento = carpeta === null ? SEGMENTO_DE_LA_EMPRESA : encodeURIComponent(carpeta);
  const base = `/obra/${segmento}/${obraId}/${seccion}`;
  return subvista ? `${base}/${subvista}` : base;
}

// La carpeta de un segmento ya decodificado (el que da `useParams`): `empresa` es la de la empresa (null).
export function carpetaDeLaRuta(segmento: string): string | null {
  return segmento === SEGMENTO_DE_LA_EMPRESA ? null : segmento;
}

export function rutaDeEmpresa(entrada: EntradaId): string {
  return `/empresa/${entrada}`;
}
