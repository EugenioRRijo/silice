// Registro de paginas de la interfaz. Es la unica lista que la barra, el enrutador y los permisos leen: cada pantalla
// con su seccion, su accion y el modulo y el area a los que pertenece (diseno 2026-10-25-modulos-design.md, §3 y §5).
//
// Como se agrega una pagina: crear `src/paginas/<id>/index.tsx` con un `export default` (el componente de la
// pagina, sin props: lo que necesita sale de `useAplicacion()`) y agregar su linea de abajo con
// `ubicacion: en("<modulo>", "<area>")` (o `null`, fuera de los modulos) y `cargar: () => import("../paginas/<id>")`.
import type { ComponentType } from "react";

export const SECCIONES = ["Trabajo", "Revisión", "Investigación", "Administración"] as const;
export type Seccion = (typeof SECCIONES)[number];

export type ModuloId = "auditoria" | "obras" | "produccion";

export interface AreaDef {
  id: string;
  titulo: string;
}

export interface ModuloDef {
  id: ModuloId;
  titulo: string;
  // Para que sirve el modulo, en una linea (1 a 60 caracteres): la lee el selector de modulos.
  enUnaLinea: string;
  // En el orden de la barra. El area «inicio» es la del inicio del modulo.
  areas: readonly AreaDef[];
}

export interface UbicacionDef {
  modulo: ModuloId;
  area: string;
}

// Los tres modulos, en este orden (plan de modulos, «Restricciones globales»). Un area sin pantallas visibles para la
// cuenta no se pinta (Aprobaciones espera su pantalla).
export const MODULOS: readonly ModuloDef[] = [
  {
    id: "auditoria",
    titulo: "Auditoría",
    enUnaLinea: "Revise presupuestos propios o de terceros",
    areas: [
      { id: "inicio", titulo: "Inicio" },
      { id: "auditar", titulo: "Auditar" },
      { id: "paquetes", titulo: "Paquetes" },
      { id: "historial", titulo: "Historial" },
    ],
  },
  {
    id: "obras",
    titulo: "Presupuestos y obras",
    enUnaLinea: "Arme, apruebe y controle sus obras",
    areas: [
      { id: "inicio", titulo: "Inicio" },
      { id: "obras", titulo: "Obras" },
      { id: "partidas", titulo: "Partidas" },
      { id: "mercado", titulo: "Mercado" },
      { id: "aprobaciones", titulo: "Aprobaciones" },
      { id: "control", titulo: "Control" },
    ],
  },
  {
    id: "produccion",
    titulo: "Producción",
    enUnaLinea: "Existencias y báscula de la arenera",
    areas: [
      { id: "inicio", titulo: "Inicio" },
      { id: "existencias", titulo: "Existencias" },
    ],
  },
];

export interface PaginaDef {
  // La ruta de la pagina es `/<id>`.
  id: string;
  titulo: string;
  // Una linea (1 a 60 caracteres) que dice para que sirve la pantalla, sin jerga (imperativo o frase nominal): la leen
  // el panel de area y los accesos del modulo. Es el unico lugar donde vive ese texto.
  enUnaLinea: string;
  seccion: Seccion;
  // La `Accion` de seguridad/permisos.py que exige la pagina (la declara su router en api/acceso.py); null = toda cuenta la ve.
  accion: string | null;
  // Modulo y area a los que pertenece; null = fuera de los modulos (al pie del selector de modulos).
  ubicacion: UbicacionDef | null;
  // Carga perezosa: un archivo aparte en el dist, que solo se baja al abrir la pagina.
  cargar: () => Promise<{ default: ComponentType }>;
}

// Cada entrada de PAGINAS queda en una sola llave (sin objetos anidados): `scripts/recorrido_ux_playwright.py` lee
// el registro como texto.
function en(modulo: ModuloId, area: string): UbicacionDef {
  return { modulo, area };
}

// El orden manda dentro de cada area (es el de su panel en la barra).
export const PAGINAS: readonly PaginaDef[] = [
  {
    id: "auditoria",
    titulo: "Inicio de auditoría",
    enUnaLinea: "Suelte un Excel y vea las últimas auditorías",
    seccion: "Revisión",
    accion: null,
    ubicacion: en("auditoria", "inicio"),
    cargar: () => import("../paginas/auditoria"),
  },
  {
    id: "libros",
    titulo: "Libro de la empresa",
    enUnaLinea: "Suba un Excel y vea lo que no cuadra",
    seccion: "Revisión",
    accion: "leer_proyecto",
    ubicacion: en("auditoria", "auditar"),
    cargar: () => import("../paginas/libros"),
  },
  {
    id: "revisar",
    titulo: "Revisar un paquete",
    enUnaLinea: "Verifique un paquete o un presupuesto recibido",
    seccion: "Revisión",
    accion: "revisar_paquete",
    ubicacion: en("auditoria", "paquetes"),
    cargar: () => import("../paginas/revisar"),
  },
  // Pagina propia de esta interfaz (UC-30): el historial de auditorias.
  {
    id: "historial",
    titulo: "Historial de auditorías",
    enUnaLinea: "Consulte las auditorías ya hechas",
    seccion: "Revisión",
    accion: "leer_proyecto",
    ubicacion: en("auditoria", "historial"),
    cargar: () => import("../paginas/historial"),
  },
  {
    id: "obras",
    titulo: "Inicio de presupuestos y obras",
    enUnaLinea: "Cifras, obras y pendientes de un vistazo",
    seccion: "Trabajo",
    accion: null,
    ubicacion: en("obras", "inicio"),
    cargar: () => import("../paginas/obras"),
  },
  {
    id: "hoja",
    titulo: "Hoja de la obra",
    enUnaLinea: "El presupuesto completo, como en Excel",
    seccion: "Trabajo",
    accion: "editar_hoja",
    ubicacion: en("obras", "obras"),
    cargar: () => import("../paginas/hoja"),
  },
  {
    id: "elaborar",
    titulo: "Elaborar un presupuesto",
    enUnaLinea: "Junte partidas y cantidades",
    seccion: "Trabajo",
    accion: "editar_hoja",
    ubicacion: en("obras", "obras"),
    cargar: () => import("../paginas/elaborar"),
  },
  {
    id: "tablero",
    titulo: "Tablero del proyecto",
    enUnaLinea: "Cómo va el proyecto de un vistazo",
    seccion: "Trabajo",
    accion: "leer_proyecto",
    ubicacion: en("obras", "obras"),
    cargar: () => import("../paginas/tablero"),
  },
  {
    id: "entregar",
    titulo: "Entregar paquete",
    enUnaLinea: "Prepare lo que se envía al cliente",
    seccion: "Trabajo",
    accion: "entregar_paquete",
    ubicacion: en("obras", "obras"),
    cargar: () => import("../paginas/entregar"),
  },
  {
    id: "componer",
    titulo: "Componer una partida",
    enUnaLinea: "Arme el análisis de precio de una partida",
    seccion: "Trabajo",
    accion: "editar_hoja",
    ubicacion: en("obras", "partidas"),
    cargar: () => import("../paginas/componer"),
  },
  {
    id: "catalogo",
    titulo: "Catálogo de partidas e insumos",
    enUnaLinea: "Partidas e insumos guardados",
    seccion: "Trabajo",
    accion: "leer_proyecto",
    ubicacion: en("obras", "partidas"),
    cargar: () => import("../paginas/catalogo"),
  },
  {
    id: "similares",
    titulo: "Partidas similares",
    enUnaLinea: "Encuentre partidas parecidas a la que busca",
    seccion: "Investigación",
    accion: "editar_hoja",
    ubicacion: en("obras", "partidas"),
    cargar: () => import("../paginas/similares"),
  },
  {
    id: "mercado",
    titulo: "Estudio de mercado",
    enUnaLinea: "Compare precios del mercado y elija los suyos",
    seccion: "Trabajo",
    accion: "editar_hoja",
    ubicacion: en("obras", "mercado"),
    cargar: () => import("../paginas/mercado"),
  },
  {
    id: "precios_empresa",
    titulo: "Precios de la empresa",
    enUnaLinea: "Cargue y cree las listas de precios de la empresa",
    seccion: "Trabajo",
    accion: "administrar_precios",
    ubicacion: en("obras", "mercado"),
    cargar: () => import("../paginas/precios_empresa"),
  },
  {
    id: "actualizacion",
    titulo: "Actualizar precios",
    enUnaLinea: "Ponga al día los precios de un presupuesto",
    seccion: "Trabajo",
    accion: "editar_hoja",
    ubicacion: en("obras", "mercado"),
    cargar: () => import("../paginas/actualizacion"),
  },
  {
    id: "historico",
    titulo: "Histórico de cambios de precio",
    enUnaLinea: "Vea cómo cambió el precio de un insumo",
    seccion: "Trabajo",
    accion: "leer_proyecto",
    ubicacion: en("obras", "mercado"),
    cargar: () => import("../paginas/historico"),
  },
  {
    id: "indices",
    titulo: "Índices del BCV",
    enUnaLinea: "Cargue los índices publicados por el BCV",
    seccion: "Trabajo",
    accion: "administrar_precios",
    ubicacion: en("obras", "mercado"),
    cargar: () => import("../paginas/indices"),
  },
  {
    id: "simulador",
    titulo: "Simulador de listas",
    enUnaLinea: "Simule variaciones en una lista de precios",
    seccion: "Investigación",
    accion: "editar_hoja",
    ubicacion: en("obras", "mercado"),
    cargar: () => import("../paginas/simulador"),
  },
  // Plan de montar un presupuesto, T20: el area Aprobaciones de Presupuestos y obras (diseno de modulos, §3 y §8).
  {
    id: "aprobar",
    titulo: "Aprobar una versión",
    enUnaLinea: "Revise y dé su dictamen sobre una versión",
    seccion: "Revisión",
    accion: "aprobar_version",
    ubicacion: en("obras", "aprobaciones"),
    cargar: () => import("../paginas/aprobar"),
  },
  {
    id: "control",
    titulo: "Control de obra",
    enUnaLinea: "Compare lo avanzado con lo planificado en obra",
    seccion: "Trabajo",
    accion: "control_de_obra",
    ubicacion: en("obras", "control"),
    cargar: () => import("../paginas/control"),
  },
  {
    id: "reajuste",
    titulo: "Reajuste de precios",
    enUnaLinea: "Reajuste los precios del contrato por índices",
    seccion: "Trabajo",
    accion: "convertir_y_reajustar",
    ubicacion: en("obras", "control"),
    cargar: () => import("../paginas/reajuste"),
  },
  {
    id: "escenarios",
    titulo: "Escenarios de sensibilidad",
    enUnaLinea: "Pruebe qué pasa si cambian costos o precios",
    seccion: "Investigación",
    accion: "editar_hoja",
    ubicacion: en("obras", "control"),
    cargar: () => import("../paginas/escenarios"),
  },
  {
    id: "produccion",
    titulo: "Inicio de producción",
    enUnaLinea: "Lo que requiere atención en la arenera",
    seccion: "Trabajo",
    accion: "operar_arenera",
    ubicacion: en("produccion", "inicio"),
    cargar: () => import("../paginas/produccion"),
  },
  {
    id: "existencias",
    titulo: "Existencias de la arenera",
    enUnaLinea: "Cuánto hay y cuánto queda de cada material",
    seccion: "Trabajo",
    accion: "operar_arenera",
    ubicacion: en("produccion", "existencias"),
    cargar: () => import("../paginas/existencias"),
  },
  {
    id: "administracion",
    titulo: "Administración",
    enUnaLinea: "Cuentas, claves y ajustes de la instalación",
    seccion: "Administración",
    accion: "administrar_cuentas",
    ubicacion: null,
    cargar: () => import("../paginas/administracion"),
  },
  {
    id: "acerca",
    titulo: "Acerca de Sílice",
    enUnaLinea: "Versión, licencia y datos del programa",
    seccion: "Trabajo",
    accion: null,
    ubicacion: null,
    cargar: () => import("../paginas/acerca"),
  },
];

export function paginaPorId(id: string, paginas: readonly PaginaDef[] = PAGINAS): PaginaDef | undefined {
  return paginas.find((p) => p.id === id);
}

export function rutaDe(pagina: Pick<PaginaDef, "id">): string {
  return `/${pagina.id}`;
}

function esInicio(pagina: PaginaDef): boolean {
  return pagina.ubicacion?.area === "inicio";
}

// Permisos y modo entrega, sin mirar el modulo. Con `modo_entrega` (SILICE_MODO_ENTREGA=1) la seccion Investigacion
// desaparece.
export function usable(pagina: PaginaDef, acciones: readonly string[], modoEntrega: boolean): boolean {
  if (modoEntrega && pagina.seccion === "Investigación") return false;
  return pagina.accion === null || acciones.includes(pagina.accion);
}

// Las pantallas del modulo que la cuenta puede usar, sin su inicio.
function delModulo(modulo: ModuloId, acciones: readonly string[], modoEntrega: boolean, paginas: readonly PaginaDef[]): PaginaDef[] {
  return paginas.filter((p) => p.ubicacion?.modulo === modulo && !esInicio(p) && usable(p, acciones, modoEntrega));
}

// La navegacion no es el control (S3 5.1): la API vuelve a exigir cada accion. Aqui solo se decide que se muestra. Un
// inicio se ve si su modulo tiene otra pantalla visible: un modulo sin nada que usar no tiene inicio.
export function visible(
  pagina: PaginaDef,
  acciones: readonly string[],
  modoEntrega: boolean,
  paginas: readonly PaginaDef[] = PAGINAS,
): boolean {
  if (!usable(pagina, acciones, modoEntrega)) return false;
  if (!esInicio(pagina)) return true;
  return delModulo(pagina.ubicacion!.modulo, acciones, modoEntrega, paginas).length > 0;
}

export function moduloDePagina(id: string, paginas: readonly PaginaDef[] = PAGINAS): ModuloId | null {
  return paginaPorId(id, paginas)?.ubicacion?.modulo ?? null;
}

// El inicio de un modulo. Que falte es un error del registro (la prueba de rutas lo vigila), no de la persona.
export function inicioDe(modulo: ModuloId, paginas: readonly PaginaDef[] = PAGINAS): PaginaDef {
  const inicio = paginas.find((p) => p.ubicacion?.modulo === modulo && esInicio(p));
  if (!inicio) throw new Error(`El módulo «${modulo}» no tiene inicio en el registro de páginas.`);
  return inicio;
}

// Un modulo aparece si la cuenta puede usar al menos una de sus pantallas que no sea su inicio.
export function modulosVisibles(
  acciones: readonly string[],
  modoEntrega: boolean,
  paginas: readonly PaginaDef[] = PAGINAS,
): ModuloDef[] {
  return MODULOS.filter((m) => delModulo(m.id, acciones, modoEntrega, paginas).length > 0);
}

// Administracion y Acerca de Silice: van al pie del selector de modulos.
export function fueraDeModulos(
  acciones: readonly string[],
  modoEntrega: boolean,
  paginas: readonly PaginaDef[] = PAGINAS,
): PaginaDef[] {
  return paginas.filter((p) => p.ubicacion === null && visible(p, acciones, modoEntrega, paginas));
}
