// Registro de pantallas de la interfaz: el enrutador del marco y los permisos lo leen. Cada pantalla con su seccion de
// permisos (modo entrega), su accion y su linea de ayuda. Dónde se ve cada una lo dice el marco: las secciones de la obra
// y las entradas de Empresa de `marco/secciones.ts` montan una pantalla de aquí por su `id`; las demás se alcanzan por el
// buscador (Ctrl+K).
//
// Como se agrega una pantalla: crear `src/paginas/<id>/index.tsx` con un `export default` (el componente, sin props: lo
// que necesita sale de `useAplicacion()`) y agregar su linea de abajo con `cargar: () => import("../paginas/<id>")`.
import type { ComponentType } from "react";

export const SECCIONES = ["Trabajo", "Revisión", "Investigación", "Administración"] as const;
export type Seccion = (typeof SECCIONES)[number];

export interface PaginaDef {
  // La ruta de la pagina es `/<id>`.
  id: string;
  titulo: string;
  // Una linea (1 a 60 caracteres) que dice para que sirve la pantalla, sin jerga (imperativo o frase nominal): la leen
  // el buscador y «Lo que puede hacer aquí» de la mesa. Es el unico lugar donde vive ese texto.
  enUnaLinea: string;
  seccion: Seccion;
  // La `Accion` de seguridad/permisos.py que exige la pagina (la declara su router en api/acceso.py); null = toda cuenta la ve.
  accion: string | null;
  // El módulo activable (`MODULOS` de aplicacion/modulos.py) al que pertenece: si la instalación lo apagó, la pantalla ni
  // se ofrece ni se abre (plan vial, Tarea 19). Sin módulo, la pantalla es de siempre.
  modulo?: "produccion" | "vial" | "riesgo" | "edificacion";
  // Carga perezosa: un archivo aparte en el dist, que solo se baja al abrir la pagina.
  cargar: () => Promise<{ default: ComponentType }>;
}

// Cada entrada de PAGINAS queda en una sola llave (sin objetos anidados): `scripts/recorrido_ux_playwright.py` lee
// el registro como texto.
export const PAGINAS: readonly PaginaDef[] = [
  // F6, T8: la Vista general, entrada de la app (`/inicio/general`, contrato de rutas 1 y 4). La ve toda cuenta; sus bloques
  // piden por su cuenta lo que cada rol puede leer (cartera y auditorías con `leer_proyecto`, arenera con `operar_arenera`).
  {
    id: "inicio",
    titulo: "Vista general",
    enUnaLinea: "Lo que bloquea, la cartera y el avance de las obras",
    seccion: "Trabajo",
    accion: null,
    cargar: () => import("../paginas/inicio"),
  },
  {
    id: "auditoria",
    titulo: "Inicio de auditoría",
    enUnaLinea: "Suelte un Excel y vea las últimas auditorías",
    seccion: "Revisión",
    accion: null,
    cargar: () => import("../paginas/auditoria"),
  },
  {
    id: "libros",
    titulo: "Libro de la empresa",
    enUnaLinea: "Suba un Excel y vea lo que no cuadra",
    seccion: "Revisión",
    accion: "leer_proyecto",
    cargar: () => import("../paginas/libros"),
  },
  {
    id: "revisar",
    titulo: "Revisar un paquete",
    enUnaLinea: "Verifique un paquete o un presupuesto recibido",
    seccion: "Revisión",
    accion: "revisar_paquete",
    cargar: () => import("../paginas/revisar"),
  },
  // Pagina propia de esta interfaz (UC-30): el historial de auditorias.
  {
    id: "historial",
    titulo: "Historial de auditorías",
    enUnaLinea: "Consulte las auditorías ya hechas",
    seccion: "Revisión",
    accion: "leer_proyecto",
    cargar: () => import("../paginas/historial"),
  },
  {
    id: "obras",
    titulo: "Resumen de la obra",
    enUnaLinea: "La obra abierta de un vistazo: cifras y pendientes",
    seccion: "Trabajo",
    accion: null,
    cargar: () => import("../paginas/obras"),
  },
  {
    id: "hoja",
    titulo: "Presupuesto",
    enUnaLinea: "El presupuesto completo, como en Excel",
    seccion: "Trabajo",
    // F4 2b (Eugenio, 2026-10-31): quien revisa la ve en solo lectura; lo que escribe lo decide `puedeEditarLaHoja`.
    accion: "leer_proyecto",
    cargar: () => import("../paginas/hoja"),
  },
  {
    id: "versiones",
    titulo: "Versiones",
    enUnaLinea: "Las versiones guardadas y lo que cambió en cada una",
    seccion: "Trabajo",
    // F4, Tarea 6: lee lo mismo que la Hoja (Tarea 2b); restaurar y guardar los decide `puedeEditarLaHoja`.
    accion: "leer_proyecto",
    cargar: () => import("../paginas/versiones"),
  },
  {
    id: "archivos",
    titulo: "Archivos y planos",
    enUnaLinea: "Suba un plano o un cómputo y vea lo que se importó",
    seccion: "Trabajo",
    // F4, Tarea 11: quien revisa ve el registro; subir lo decide `puedeEditarLaHoja` (la API exige `editar_hoja`). F4,
    // Tarea 12: no es de ningún módulo. Con «edificación» apagada no hay planos, pero el cómputo se sigue cargando aquí.
    accion: "leer_proyecto",
    cargar: () => import("../paginas/archivos"),
  },
  {
    id: "tablero",
    titulo: "Tablero del proyecto",
    enUnaLinea: "Cómo va el proyecto de un vistazo",
    seccion: "Trabajo",
    accion: "leer_proyecto",
    cargar: () => import("../paginas/tablero"),
  },
  {
    id: "entregar",
    titulo: "Entregar paquete",
    enUnaLinea: "Prepare lo que se envía al cliente",
    seccion: "Trabajo",
    accion: "entregar_paquete",
    cargar: () => import("../paginas/entregar"),
  },
  {
    id: "componer",
    titulo: "Componer una partida",
    enUnaLinea: "Arme el análisis de precio de una partida",
    seccion: "Trabajo",
    accion: "editar_hoja",
    cargar: () => import("../paginas/componer"),
  },
  {
    id: "catalogo",
    titulo: "Catálogo de partidas e insumos",
    enUnaLinea: "Partidas e insumos guardados",
    seccion: "Trabajo",
    accion: "leer_proyecto",
    cargar: () => import("../paginas/catalogo"),
  },
  {
    id: "mercado",
    titulo: "Estudio de mercado",
    enUnaLinea: "Compare precios del mercado, su histórico y las cotizaciones",
    seccion: "Trabajo",
    // F4, Tarea 13 (ronda 2): quien revisa entra a leer el histórico y las cotizaciones de la obra; las pestañas que
    // anotan y usan precios, y las operaciones de cotizar, solo se pintan con `editar_hoja` (la API lo vuelve a exigir).
    accion: "leer_proyecto",
    cargar: () => import("../paginas/mercado"),
  },
  {
    id: "precios_empresa",
    titulo: "Precios de la empresa",
    enUnaLinea: "Cargue y cree las listas de precios de la empresa",
    seccion: "Trabajo",
    accion: "administrar_precios",
    cargar: () => import("../paginas/precios_empresa"),
  },
  {
    id: "actualizacion",
    titulo: "Actualizar precios",
    enUnaLinea: "Ponga al día los precios de un presupuesto",
    seccion: "Trabajo",
    accion: "editar_hoja",
    cargar: () => import("../paginas/actualizacion"),
  },
  {
    id: "indices",
    titulo: "Índices del BCV",
    enUnaLinea: "Cargue los índices publicados por el BCV",
    seccion: "Trabajo",
    accion: "administrar_precios",
    cargar: () => import("../paginas/indices"),
  },
  {
    id: "simulador",
    titulo: "Simulador de listas",
    enUnaLinea: "Simule variaciones en una lista de precios",
    seccion: "Investigación",
    accion: "editar_hoja",
    cargar: () => import("../paginas/simulador"),
  },
  {
    id: "aprobar",
    titulo: "Aprobar una versión",
    enUnaLinea: "Revise y dé su dictamen sobre una versión",
    seccion: "Revisión",
    accion: "aprobar_version",
    cargar: () => import("../paginas/aprobar"),
  },
  {
    id: "control",
    titulo: "Control de obra",
    enUnaLinea: "Compare lo avanzado con lo planificado en obra",
    seccion: "Trabajo",
    accion: "control_de_obra",
    cargar: () => import("../paginas/control"),
  },
  {
    id: "reajuste",
    titulo: "Reajuste de precios",
    enUnaLinea: "Reajuste los precios del contrato por índices",
    seccion: "Trabajo",
    accion: "convertir_y_reajustar",
    cargar: () => import("../paginas/reajuste"),
  },
  {
    id: "escenarios",
    titulo: "Escenarios de sensibilidad",
    enUnaLinea: "Pruebe qué pasa si cambian costos o precios",
    seccion: "Investigación",
    accion: "editar_hoja",
    cargar: () => import("../paginas/escenarios"),
  },
  {
    id: "produccion",
    titulo: "Inicio de producción",
    enUnaLinea: "Lo que requiere atención en la arenera",
    seccion: "Trabajo",
    accion: "operar_arenera",
    modulo: "produccion",
    cargar: () => import("../paginas/produccion"),
  },
  {
    id: "existencias",
    titulo: "Existencias de la arenera",
    enUnaLinea: "Cuánto hay y cuánto queda de cada material",
    seccion: "Trabajo",
    accion: "operar_arenera",
    modulo: "produccion",
    cargar: () => import("../paginas/existencias"),
  },
  {
    id: "costos",
    titulo: "Costos del período",
    enUnaLinea: "Registre los costos de la cantera y la planta",
    seccion: "Trabajo",
    accion: "registrar_costos_produccion",
    modulo: "produccion",
    cargar: () => import("../paginas/produccion/CostosDelPeriodo"),
  },
  {
    id: "receta_planta",
    titulo: "Receta de la planta",
    enUnaLinea: "Qué lleva una tonelada de cada mezcla",
    seccion: "Trabajo",
    accion: "operar_arenera",
    modulo: "produccion",
    cargar: () => import("../paginas/produccion/RecetaPlanta"),
  },
  {
    id: "producir_mezcla",
    titulo: "Producir mezcla",
    enUnaLinea: "Registre lo que produjo la planta con su receta",
    seccion: "Trabajo",
    accion: "operar_arenera",
    modulo: "produccion",
    cargar: () => import("../paginas/produccion/ProducirMezcla"),
  },
  {
    id: "costo_tonelada",
    titulo: "Costo por tonelada",
    enUnaLinea: "Calcule el costo propio de cada agregado y mezcla",
    seccion: "Trabajo",
    accion: "registrar_costos_produccion",
    modulo: "produccion",
    cargar: () => import("../paginas/produccion/CostoPorTonelada"),
  },
  {
    id: "tramos",
    titulo: "Tramos de la vía",
    enUnaLinea: "Importe los tramos de una vía y vea sus cantidades",
    seccion: "Trabajo",
    accion: "editar_hoja",
    modulo: "vial",
    cargar: () => import("../paginas/vial/Tramos"),
  },
  {
    id: "riesgo",
    titulo: "Riesgo de la obra",
    enUnaLinea: "Cuánto puede subir el presupuesto si suben los precios",
    seccion: "Trabajo",
    accion: "ver_riesgo",
    modulo: "riesgo",
    cargar: () => import("../paginas/riesgo/RiesgoDeLaObra"),
  },
  {
    id: "administracion",
    titulo: "Administración",
    enUnaLinea: "Cuentas, claves y ajustes de la instalación",
    seccion: "Administración",
    accion: "administrar_cuentas",
    cargar: () => import("../paginas/administracion"),
  },
  {
    id: "acerca",
    titulo: "Acerca de Sílice",
    enUnaLinea: "Versión, licencia y datos del programa",
    seccion: "Trabajo",
    accion: null,
    cargar: () => import("../paginas/acerca"),
  },
];

export function paginaPorId(id: string, paginas: readonly PaginaDef[] = PAGINAS): PaginaDef | undefined {
  return paginas.find((p) => p.id === id);
}

export function rutaDe(pagina: Pick<PaginaDef, "id">): string {
  return `/${pagina.id}`;
}

// Permisos y modo entrega. Con `modo_entrega` (SILICE_MODO_ENTREGA=1) la seccion Investigacion desaparece. La
// navegacion no es el control (S3 5.1): la API vuelve a exigir cada accion; aqui solo se decide que se ofrece. `apagados`
// son los modulos que la instalacion apago (plan vial, Tarea 19): sus pantallas no se ofrecen.
export function usable(pagina: PaginaDef, acciones: readonly string[], modoEntrega: boolean, apagados: readonly string[] = []): boolean {
  if (modoEntrega && pagina.seccion === "Investigación") return false;
  if (pagina.modulo !== undefined && apagados.includes(pagina.modulo)) return false;
  return pagina.accion === null || acciones.includes(pagina.accion);
}
