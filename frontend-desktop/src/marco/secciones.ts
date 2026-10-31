// Las secciones de una obra y las entradas de la zona Empresa del marco nuevo, con sus rutas (plan del rediseño del
// marco, Tarea 4; especificación 2026-10-26, §8 ter). Cada una monta, por ahora, una pantalla existente por su `id` de
// `shell/rutas.ts` (patrón estrangulador): `pagina` es ese id. Una sección con `pagina: null` aún no tiene pantalla
// propia (llega en F4): no se pinta en el árbol ni se abre por enlace, y no hay pantallas «próximamente».
//
// Rutas (HashRouter): `#/pendientes`, `#/obra/<carpeta>/<obra>/<sección>` y `#/empresa/<entrada>`. La carpeta viaja
// con su .db, que es el nombre que acepta `POST /v1/casos/actual`; la de la empresa se escribe `empresa` (ningún
// nombre de carpeta puede serlo, porque todos terminan en .db).

export type SeccionId = "resumen" | "presupuesto" | "tramos" | "archivos" | "versiones" | "aprobaciones" | "mercado" | "control";

export interface SeccionDef {
  id: SeccionId;
  titulo: string;
  pagina: string | null;
  // Para qué sirve, en una frase de hasta 90 caracteres, con las palabras de quien la usa.
  ayuda: string;
  // Solo se ofrece en las obras viales (las que ya tienen tramos guardados): no hay otra marca de «obra vial» hasta el
  // plan de módulos activables (Tarea 19). La pantalla igual se alcanza por el buscador para quien aún no tiene tramos.
  soloVial?: boolean;
}

export const SECCIONES_DE_OBRA: readonly SeccionDef[] = [
  { id: "resumen", titulo: "Resumen", pagina: "obras", ayuda: "La obra de un vistazo: sus cifras, su versión vigente y lo pendiente." },
  { id: "presupuesto", titulo: "Presupuesto", pagina: "hoja", ayuda: "Las partidas de la obra con sus cantidades, precios y APU." },
  { id: "tramos", titulo: "Tramos", pagina: "tramos", soloVial: true, ayuda: "Los tramos de la vía con sus cantidades de obra." },
  { id: "archivos", titulo: "Archivos y planos", pagina: null, ayuda: "Los planos y documentos de la obra." },
  { id: "versiones", titulo: "Versiones", pagina: null, ayuda: "Las versiones guardadas del presupuesto y qué cambió entre ellas." },
  { id: "aprobaciones", titulo: "Aprobaciones", pagina: "aprobar", ayuda: "Las versiones que esperan dictamen y lo que se entregó al cliente." },
  { id: "mercado", titulo: "Mercado", pagina: "mercado", ayuda: "Los precios del mercado para los insumos de la obra; elija los suyos." },
  { id: "control", titulo: "Control de obra", pagina: "control", ayuda: "Lo avanzado en obra frente a lo planificado, con sus valuaciones." },
];

export type EntradaId = "precios" | "auditoria" | "produccion" | "personas" | "ayuda";

export interface EntradaDef {
  id: EntradaId;
  titulo: string;
  pagina: string;
  ayuda: string;
}

// En este orden. Ayuda monta «Acerca de Sílice» hasta que F6 traiga las guías.
export const ENTRADAS_DE_EMPRESA: readonly EntradaDef[] = [
  { id: "precios", titulo: "Precios y catálogo", pagina: "catalogo", ayuda: "Las partidas, insumos y precios que la empresa usa en todas sus obras." },
  { id: "auditoria", titulo: "Auditar un presupuesto", pagina: "auditoria", ayuda: "Suelte un Excel, propio o de terceros, y vea lo que no cuadra." },
  { id: "produccion", titulo: "Producción", pagina: "existencias", ayuda: "Cuánto hay y cuánto queda de cada material de la arenera." },
  { id: "personas", titulo: "Empresa y personas", pagina: "administracion", ayuda: "Los datos de la empresa, las cuentas de las personas y sus permisos." },
  { id: "ayuda", titulo: "Ayuda", pagina: "acerca", ayuda: "Cómo hacer cada tarea en Sílice, y la versión y licencia del programa." },
];

// Busca solo entre las propias (un `id` como «toString» no es sección).
export function seccionPorId(id: string): SeccionDef | undefined {
  return SECCIONES_DE_OBRA.find((s) => s.id === id);
}

export const RUTA_DE_PENDIENTES = "/pendientes";
export const PATRON_DE_OBRA = "/obra/:carpeta/:obraId/:seccion";
export const PATRON_DE_EMPRESA = "/empresa/:entrada";
const SEGMENTO_DE_LA_EMPRESA = "empresa";

export function rutaDeObra(carpeta: string | null, obraId: number, seccion: SeccionId): string {
  const segmento = carpeta === null ? SEGMENTO_DE_LA_EMPRESA : encodeURIComponent(carpeta);
  return `/obra/${segmento}/${obraId}/${seccion}`;
}

// La carpeta de un segmento ya decodificado (el que da `useParams`): `empresa` es la de la empresa (null).
export function carpetaDeLaRuta(segmento: string): string | null {
  return segmento === SEGMENTO_DE_LA_EMPRESA ? null : segmento;
}

export function rutaDeEmpresa(entrada: EntradaId): string {
  return `/empresa/${entrada}`;
}
