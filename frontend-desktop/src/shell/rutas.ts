// Registro de paginas de la interfaz (plan de la sesion 2b). Es la unica lista que el menu, el enrutador y los
// permisos leen: 22 paginas con su seccion y su accion.
//
// Como se agrega una pagina: crear `src/paginas/<id>/index.tsx` con un `export default` (el componente de la
// pagina, sin props: lo que necesita sale de `useAplicacion()`) y agregar su linea de abajo con
// `cargar: () => import("../paginas/<id>")`.
import type { ComponentType } from "react";

export const SECCIONES = ["Trabajo", "Revisión", "Investigación", "Administración"] as const;
export type Seccion = (typeof SECCIONES)[number];

export interface PaginaDef {
  // La ruta de la pagina es `/<id>`.
  id: string;
  titulo: string;
  seccion: Seccion;
  // La `Accion` de seguridad/permisos.py que exige la pagina (ui_sesion.exigir); null = toda cuenta la ve.
  accion: string | null;
  // Carga perezosa: un archivo aparte en el dist, que solo se baja al abrir la pagina.
  cargar: () => Promise<{ default: ComponentType }>;
}

export const PAGINAS: readonly PaginaDef[] = [
  {
    id: "inicio",
    titulo: "Inicio",
    seccion: "Trabajo",
    accion: null,
    cargar: () => import("../paginas/inicio"),
  },
  {
    id: "tablero",
    titulo: "Tablero del proyecto",
    seccion: "Trabajo",
    accion: "leer_proyecto",
    cargar: () => import("../paginas/tablero"),
  },
  {
    id: "catalogo",
    titulo: "Catálogo de partidas e insumos",
    seccion: "Trabajo",
    accion: "leer_proyecto",
    cargar: () => import("../paginas/catalogo"),
  },
  {
    id: "componer",
    titulo: "Componer una partida",
    seccion: "Trabajo",
    accion: "editar_hoja",
    cargar: () => import("../paginas/componer"),
  },
  {
    id: "elaborar",
    titulo: "Elaborar un presupuesto",
    seccion: "Trabajo",
    accion: "editar_hoja",
    cargar: () => import("../paginas/elaborar"),
  },
  {
    id: "hoja",
    titulo: "Hoja del proyecto",
    seccion: "Trabajo",
    accion: "editar_hoja",
    cargar: () => import("../paginas/hoja"),
  },
  {
    id: "actualizacion",
    titulo: "Actualizar precios",
    seccion: "Trabajo",
    accion: "editar_hoja",
    cargar: () => import("../paginas/actualizacion"),
  },
  {
    id: "historico",
    titulo: "Histórico de cambios de precio",
    seccion: "Trabajo",
    accion: "leer_proyecto",
    cargar: () => import("../paginas/historico"),
  },
  {
    id: "precios_empresa",
    titulo: "Precios de la empresa",
    seccion: "Trabajo",
    accion: "administrar_precios",
    cargar: () => import("../paginas/precios_empresa"),
  },
  {
    id: "indices",
    titulo: "Índices del BCV",
    seccion: "Trabajo",
    accion: "administrar_precios",
    cargar: () => import("../paginas/indices"),
  },
  {
    id: "reajuste",
    titulo: "Reajuste de precios",
    seccion: "Trabajo",
    accion: "convertir_y_reajustar",
    cargar: () => import("../paginas/reajuste"),
  },
  {
    id: "control",
    titulo: "Control de obra",
    seccion: "Trabajo",
    accion: "control_de_obra",
    cargar: () => import("../paginas/control"),
  },
  {
    id: "acerca",
    titulo: "Acerca de Sílice",
    seccion: "Trabajo",
    accion: null,
    cargar: () => import("../paginas/acerca"),
  },
  {
    id: "entregar",
    titulo: "Entregar paquete",
    seccion: "Trabajo",
    accion: "entregar_paquete",
    cargar: () => import("../paginas/entregar"),
  },
  {
    id: "existencias",
    titulo: "Existencias de la arenera",
    seccion: "Trabajo",
    accion: "operar_arenera",
    cargar: () => import("../paginas/existencias"),
  },
  {
    id: "revisar",
    titulo: "Revisar un paquete",
    seccion: "Revisión",
    accion: "revisar_paquete",
    cargar: () => import("../paginas/revisar"),
  },
  {
    id: "libros",
    titulo: "Libro de la empresa",
    seccion: "Revisión",
    accion: "leer_proyecto",
    cargar: () => import("../paginas/libros"),
  },
  // Pagina propia de esta interfaz (UC-30): el historial de auditorias.
  {
    id: "historial",
    titulo: "Historial de auditorías",
    seccion: "Revisión",
    accion: "leer_proyecto",
    cargar: () => import("../paginas/historial"),
  },
  {
    id: "escenarios",
    titulo: "Escenarios de sensibilidad",
    seccion: "Investigación",
    accion: "editar_hoja",
    cargar: () => import("../paginas/escenarios"),
  },
  {
    id: "similares",
    titulo: "Partidas similares",
    seccion: "Investigación",
    accion: "editar_hoja",
    cargar: () => import("../paginas/similares"),
  },
  {
    id: "simulador",
    titulo: "Simulador de listas",
    seccion: "Investigación",
    accion: "editar_hoja",
    cargar: () => import("../paginas/simulador"),
  },
  {
    id: "administracion",
    titulo: "Administración",
    seccion: "Administración",
    accion: "administrar_cuentas",
    cargar: () => import("../paginas/administracion"),
  },
];

export function paginaPorId(id: string, paginas: readonly PaginaDef[] = PAGINAS): PaginaDef | undefined {
  return paginas.find((p) => p.id === id);
}

export function rutaDe(pagina: Pick<PaginaDef, "id">): string {
  return `/${pagina.id}`;
}

// La navegacion no es el control (S3 5.1): la API vuelve a exigir cada accion. Aqui solo se decide que se muestra.
// Con `modo_entrega` (SILICE_MODO_ENTREGA=1) la seccion Investigacion desaparece.
export function visible(pagina: PaginaDef, acciones: readonly string[], modoEntrega: boolean): boolean {
  if (modoEntrega && pagina.seccion === "Investigación") return false;
  return pagina.accion === null || acciones.includes(pagina.accion);
}

export interface SeccionVisible {
  seccion: Seccion;
  paginas: PaginaDef[];
}

export function seccionesVisibles(
  acciones: readonly string[],
  modoEntrega: boolean,
  paginas: readonly PaginaDef[] = PAGINAS,
): SeccionVisible[] {
  return SECCIONES.map((seccion) => ({
    seccion,
    paginas: paginas.filter((p) => p.seccion === seccion && visible(p, acciones, modoEntrega)),
  })).filter((s) => s.paginas.length > 0);
}

// Menu por cinco areas (spec 2026-10-18 del Inicio, §2.2). `seccion` sigue mandando en los permisos y en el modo
// entrega; el area solo decide como se agrupa y en que orden se ve. Una sola lista por area (ids en orden): una
// pagina que no este en ninguna cae al final de «Más» en vez de desaparecer, y un id que aun no esta en el registro
// (el historial de auditorias) se ignora hasta que exista.
export interface AreaDef {
  id: string;
  titulo: string;
  descripcion: string;
  paginas: readonly string[];
}

export const AREAS: readonly AreaDef[] = [
  { id: "inicio", titulo: "Inicio", descripcion: "Empiece aquí", paginas: ["inicio"] },
  {
    id: "auditar",
    titulo: "Auditar",
    descripcion: "Revisar presupuestos y paquetes",
    paginas: ["libros", "revisar", "historial"],
  },
  {
    id: "crear",
    titulo: "Crear",
    descripcion: "APU, presupuestos y entregas",
    paginas: ["componer", "elaborar", "hoja", "catalogo", "tablero", "entregar"],
  },
  { id: "produccion", titulo: "Producción", descripcion: "Arenera: existencias y báscula", paginas: ["existencias"] },
  {
    id: "mas",
    titulo: "Más",
    descripcion: "Precios, obra, análisis y ajustes",
    paginas: [
      "actualizacion",
      "historico",
      "precios_empresa",
      "indices",
      "reajuste",
      "control",
      "escenarios",
      "similares",
      "simulador",
      "administracion",
      "acerca",
    ],
  },
];

export interface AreaVisible {
  id: string;
  titulo: string;
  descripcion: string;
  paginas: PaginaDef[];
}

export function areasVisibles(
  acciones: readonly string[],
  modoEntrega: boolean,
  paginas: readonly PaginaDef[] = PAGINAS,
): AreaVisible[] {
  const asignadas = new Set(AREAS.flatMap((a) => a.paginas));
  const huerfanas = paginas.filter((p) => !asignadas.has(p.id));
  return AREAS.map((area) => {
    const ids = area.id === "mas" ? [...area.paginas, ...huerfanas.map((p) => p.id)] : area.paginas;
    const delArea = ids
      .map((id) => paginaPorId(id, paginas))
      .filter((p): p is PaginaDef => p !== undefined && visible(p, acciones, modoEntrega));
    return { id: area.id, titulo: area.titulo, descripcion: area.descripcion, paginas: delArea };
  }).filter((a) => a.paginas.length > 0);
}

// Las tres herramientas del dia a dia de la empresa (spec §2.3), siempre arriba del menu.
// Lleva el nombre de su pantalla (la misma pantalla no se ve con dos nombres en el menu); lo suyo es la ayuda.
export interface HerramientaPrincipal {
  pagina: string;
  ayuda: string;
}

export interface HerramientaVisible extends HerramientaPrincipal {
  titulo: string;
}

export const HERRAMIENTAS_PRINCIPALES: readonly HerramientaPrincipal[] = [
  { pagina: "libros", ayuda: "Suba un Excel y vea lo que no cuadra" },
  { pagina: "componer", ayuda: "Componga una partida o arme un presupuesto" },
  { pagina: "existencias", ayuda: "Cuánto hay y cuánto queda de cada material" },
];

// Solo las que esta cuenta puede usar.
export function herramientasVisibles(
  acciones: readonly string[],
  modoEntrega: boolean,
  paginas: readonly PaginaDef[] = PAGINAS,
): HerramientaVisible[] {
  return HERRAMIENTAS_PRINCIPALES.flatMap((h) => {
    const pagina = paginaPorId(h.pagina, paginas);
    return pagina !== undefined && visible(pagina, acciones, modoEntrega)
      ? [{ ...h, titulo: pagina.titulo }]
      : [];
  });
}
