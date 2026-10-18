// Registro de paginas de la interfaz nueva (plan de la sesion 2b). Es la unica lista que el menu, el enrutador y
// los permisos leen: espeja las 21 paginas de Streamlit (ui/app.py: PAGINAS) con su seccion y su accion.
//
// Como se migra una pagina: crear `src/paginas/<id>/index.tsx` con un `export default` (el componente de la
// pagina, sin props: lo que necesita sale de `useAplicacion()`) y agregar a su linea de abajo
// `cargar: () => import("../paginas/<id>")`. Mientras no tenga `cargar`, el menu la muestra deshabilitada con el
// texto «En la interfaz clásica».
import type { ComponentType } from "react";

export const SECCIONES = ["Trabajo", "Revisión", "Investigación", "Administración"] as const;
export type Seccion = (typeof SECCIONES)[number];

export interface PaginaDef {
  // Es el nombre del modulo de Streamlit (ui/paginas/<id>.py): la ruta de aqui es `/<id>` y la de alla tambien.
  id: string;
  titulo: string;
  seccion: Seccion;
  // La `Accion` de seguridad/permisos.py que exige la pagina (ui_sesion.exigir); null = toda cuenta la ve.
  accion: string | null;
  // Carga perezosa: un archivo aparte en el dist, que solo se baja al abrir la pagina. Sin esto no esta migrada.
  cargar?: () => Promise<{ default: ComponentType }>;
}

export const PAGINAS: readonly PaginaDef[] = [
  {
    id: "inicio",
    titulo: "Inicio",
    seccion: "Trabajo",
    accion: null,
    cargar: () => import("../paginas/inicio"),
  },
  { id: "tablero", titulo: "Tablero del proyecto", seccion: "Trabajo", accion: "leer_proyecto" },
  { id: "catalogo", titulo: "Catálogo de partidas e insumos", seccion: "Trabajo", accion: "leer_proyecto" },
  {
    id: "componer",
    titulo: "Componer una partida",
    seccion: "Trabajo",
    accion: "editar_hoja",
    cargar: () => import("../paginas/componer"),
  },
  { id: "elaborar", titulo: "Elaborar un presupuesto", seccion: "Trabajo", accion: "editar_hoja" },
  { id: "hoja", titulo: "Hoja del proyecto", seccion: "Trabajo", accion: "editar_hoja" },
  { id: "actualizacion", titulo: "Actualizar precios", seccion: "Trabajo", accion: "editar_hoja" },
  { id: "historico", titulo: "Histórico de cambios de precio", seccion: "Trabajo", accion: "leer_proyecto" },
  { id: "precios_empresa", titulo: "Precios de la empresa", seccion: "Trabajo", accion: "administrar_precios" },
  { id: "indices", titulo: "Índices del BCV", seccion: "Trabajo", accion: "administrar_precios" },
  { id: "reajuste", titulo: "Reajuste de precios", seccion: "Trabajo", accion: "convertir_y_reajustar" },
  { id: "control", titulo: "Control de obra", seccion: "Trabajo", accion: "control_de_obra" },
  { id: "acerca", titulo: "Acerca de Sílice", seccion: "Trabajo", accion: null },
  { id: "entregar", titulo: "Entregar paquete", seccion: "Trabajo", accion: "entregar_paquete" },
  { id: "revisar", titulo: "Revisar un paquete", seccion: "Revisión", accion: "revisar_paquete" },
  {
    id: "libros",
    titulo: "Libro de la empresa",
    seccion: "Revisión",
    accion: "leer_proyecto",
    cargar: () => import("../paginas/libros"),
  },
  { id: "escenarios", titulo: "Escenarios de sensibilidad", seccion: "Investigación", accion: "editar_hoja" },
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
  { id: "visor", titulo: "Visor 3D del modelo", seccion: "Investigación", accion: "editar_hoja" },
  { id: "administracion", titulo: "Administración", seccion: "Administración", accion: "administrar_cuentas" },
];

export function paginaPorId(id: string, paginas: readonly PaginaDef[] = PAGINAS): PaginaDef | undefined {
  return paginas.find((p) => p.id === id);
}

export function rutaDe(pagina: PaginaDef): string {
  return `/${pagina.id}`;
}

export function estaMigrada(pagina: PaginaDef): boolean {
  return pagina.cargar !== undefined;
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

// Direccion de la pagina en la interfaz Streamlit, o null si no se conoce la base (solo http o https). En
// Streamlit la pagina de inicio es la raiz.
export function enlaceClasico(base: string | null | undefined, pagina: PaginaDef): string | null {
  if (!base) return null;
  let url: URL;
  try {
    url = new URL(base);
  } catch {
    return null;
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") return null;
  const raiz = url.href.replace(/\/+$/, "");
  return pagina.id === "inicio" ? `${raiz}/` : `${raiz}/${pagina.id}`;
}
