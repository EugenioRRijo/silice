// Las secciones de una obra del marco nuevo, con sus rutas (plan del rediseño del marco, Tarea 4; especificación
// 2026-10-26, §8 ter). Cada una monta, por ahora, una pantalla existente por su `id` de
// `shell/rutas.ts` (patrón estrangulador): `pagina` es ese id. Una sección con `pagina: null` aún no tiene pantalla
// propia (llega en F4): no se pinta en el árbol ni se abre por enlace, y no hay pantallas «próximamente».
//
// Rutas (HashRouter): `#/inicio/<vista>` y `#/obra/<carpeta>/<obra>/<sección>[/<subvista>]`. Los espacios de la empresa y la
// Cuenta viven en `espacios.ts`; `#/empresa/<entrada>` quedó solo como dirección vieja que redirige (F6, T6). La carpeta viaja
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
  { id: "resumen", titulo: "Resumen", pagina: "obras", ayuda: "La obra de un vistazo: sus cifras, su versión y lo pendiente." },
  { id: "presupuesto", titulo: "Presupuesto", pagina: "hoja", ayuda: "Las partidas de la obra con sus cantidades, precios y APU." },
  { id: "tramos", titulo: "Tramos", pagina: "tramos", ayuda: "Los tramos de la vía con sus cantidades de obra." },
  { id: "archivos", titulo: "Archivos y planos", pagina: "archivos", ayuda: "Los planos y documentos de la obra." },
  { id: "versiones", titulo: "Versiones", pagina: "versiones", ayuda: "Las versiones guardadas del presupuesto y lo que cambió en cada una." },
  { id: "aprobaciones", titulo: "Aprobaciones", pagina: "aprobar", ayuda: "Las versiones que esperan dictamen y lo que se entregó al cliente." },
  { id: "mercado", titulo: "Mercado", pagina: "mercado", ayuda: "Los precios del mercado para los insumos de la obra, su histórico y las cotizaciones." },
  { id: "control", titulo: "Control de obra", pagina: "control", ayuda: "Lo avanzado en obra frente a lo planificado, con sus valuaciones." },
  { id: "riesgo", titulo: "Riesgo", pagina: "riesgo", ayuda: "Cuánto puede subir el presupuesto de la obra si cambian los precios." },
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

// Inicio (F6, T8; contrato de rutas 1 y 4): `/inicio/:vista` con dos vistas, la Vista general y la bandeja de Pendientes.
export const RUTA_DE_VISTA_GENERAL = "/inicio/general";
export const RUTA_DE_PENDIENTES = "/inicio/pendientes";
// El nombre de antes de F6: hoy solo redirige a `RUTA_DE_PENDIENTES`, conservando la consulta.
export const RUTA_VIEJA_DE_PENDIENTES = "/pendientes";
// La ruta índice: la marca «Sílice» de la barra de arriba lleva allí, y de allí se va a la Vista general.
export const RUTA_DE_INICIO = "/";

// Si la ruta es de Inicio (`/inicio/general`, `/inicio/pendientes`): ahí se vuelven a pedir los pendientes al entrar.
export function esRutaDeInicio(pathname: string): boolean {
  return pathname === RUTA_DE_VISTA_GENERAL || pathname === RUTA_DE_PENDIENTES || pathname.startsWith("/inicio/");
}
// El cuarto segmento (`:subvista`) es opcional: sin él, la ruta es la de la pantalla principal de la sección.
export const PATRON_DE_OBRA = "/obra/:carpeta/:obraId/:seccion/:subvista?";
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
