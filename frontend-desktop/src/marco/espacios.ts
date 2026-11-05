// La ruta a la que lleva cada pantalla (plan F6, Tarea 1). Quien enlaza a una pantalla (recorridos guiados, buscador,
// pendientes, botones de las pantallas) pide aquí su ruta y no la escribe: cuando las pantallas cambien de sitio (T5)
// se cambia este lugar y quien llama no se entera. Los tres espacios de la empresa ya viven en /<espacio>/<segmento> (T4).
import { PAGINAS, paginaPorId, rutaDe, usable } from "../shell/rutas";
import { RUTA_DE_PENDIENTES, SECCIONES_DE_OBRA, rutaDeObra } from "./secciones";
import type { SeccionDef, SeccionId } from "./secciones";

export interface ObraDeLaRuta {
  carpeta: string | null;
  obraId: number;
}

// `paginaId` es el id de la pantalla en `shell/rutas.ts`. Una sección de obra va a la ruta de la obra dada; una subvista, a
// `/obra/<c>/<o>/<sección>/<subvista>` (contrato 2.1); sin obra, ambas van a su dirección corta (`/<id>`), que redirige a la
// obra de la sesión. Una herramienta de Producción, Auditoría o Precios va a
// `/<espacio>/<segmento>` (contrato 2.2), con o sin obra. Administración y Acerca de van a la Cuenta (contrato 2.3 y 3):
// Administración está repartida en cuatro secciones y su ruta canónica es la primera, «Cuentas y permisos»; Acerca de es la
// Ayuda. Las demás, a `/<id>`. Un id que no es pantalla da null.
export function rutaCanonica(paginaId: string, obra?: ObraDeLaRuta): string | null {
  const pagina = paginaPorId(paginaId, PAGINAS);
  if (pagina === undefined) return null;
  const seccion = SECCIONES_DE_OBRA.find((s) => s.pagina === paginaId);
  if (seccion !== undefined && obra !== undefined) return rutaDeObra(obra.carpeta, obra.obraId, seccion.id);
  if (seccion !== undefined) return rutaDe(pagina);
  const deSubvista = subvistaDeLaPagina(paginaId);
  if (deSubvista !== undefined) {
    return obra === undefined ? rutaDe(pagina) : rutaDeObra(obra.carpeta, obra.obraId, deSubvista.seccion, deSubvista.subvista.id);
  }
  const delEspacio = espacioDeLaPagina(paginaId);
  if (delEspacio !== undefined) return rutaDeHerramienta(delEspacio.espacio, delEspacio.herramienta.id);
  const deCuenta = SECCIONES_DE_CUENTA.find((c) => c.pagina === paginaId);
  if (deCuenta !== undefined) return rutaDeCuenta(deCuenta.id);
  return rutaDe(pagina);
}

// Para los enlaces cuya pantalla es una constante del código: si el id no existiera, el enlace no queda muerto, lleva a
// Pendientes (la prueba de `rutaCanonica` y la de cada enlace vigilan que no pase).
export function rutaOPendientes(paginaId: string, obra?: ObraDeLaRuta): string {
  return rutaCanonica(paginaId, obra) ?? RUTA_DE_PENDIENTES;
}

// --- La tabla declarativa del contrato (plan F6, T2) -------------------------------------------------------------------
// Dónde vive cada pantalla (contrato de rutas 2026-11-04, §2 y §3): las nueve secciones de la obra (`secciones.ts`) con
// sus subvistas, los tres espacios de la empresa y las seis secciones de la Cuenta. Ninguna pantalla cambia de permiso ni
// de módulo: eso lo sigue diciendo `PAGINAS`. Esta tabla solo dice dónde se ve y con qué texto. T2 no cambia rutas ni
// pantallas: quien la usa llega con T3 a T5.

// Una herramienta de un espacio, o una subvista de una sección de obra. `id` es el segmento de la ruta (en una subvista,
// `""` es la raíz: la pantalla principal de la sección); `pagina` es el `id` de la pantalla en `shell/rutas.ts`.
export interface HerramientaDef {
  id: string;
  titulo: string;
  pagina: string;
}

export type EspacioId = "produccion" | "auditoria" | "precios";

// El orden de los espacios en la barra lateral, grupo «Costos y producción» (diseño visual 3.1); ESPACIOS sigue el de la tabla.
export const ESPACIOS_EN_LA_BARRA: readonly EspacioId[] = ["auditoria", "precios", "produccion"];

export function esEspacio(segmento: string): segmento is EspacioId {
  return Object.hasOwn(ESPACIOS, segmento);
}

export function rutaDeHerramienta(espacio: EspacioId, herramienta: string): string {
  return `/${espacio}/${herramienta}`;
}

// El espacio y la herramienta donde vive una pantalla, o undefined si no es de ningún espacio.
export function espacioDeLaPagina(paginaId: string): { espacio: EspacioId; herramienta: HerramientaDef } | undefined {
  for (const espacio of Object.keys(ESPACIOS) as EspacioId[]) {
    const herramienta = ESPACIOS[espacio].herramientas.find((h) => h.pagina === paginaId);
    if (herramienta !== undefined) return { espacio, herramienta };
  }
  return undefined;
}

export const ESPACIOS: Record<EspacioId, { titulo: string; herramientas: readonly HerramientaDef[] }> = {
  produccion: {
    titulo: "Costos de producción",
    herramientas: [
      { id: "resumen", titulo: "Resumen de arenera", pagina: "produccion" },
      { id: "existencias", titulo: "Existencias", pagina: "existencias" },
      { id: "costos", titulo: "Costos del período", pagina: "costos" },
      { id: "costo-tonelada", titulo: "Costo por tonelada", pagina: "costo_tonelada" },
      { id: "receta", titulo: "Receta de la planta", pagina: "receta_planta" },
      { id: "mezcla", titulo: "Producir mezcla", pagina: "producir_mezcla" },
    ],
  },
  auditoria: {
    titulo: "Auditar un presupuesto",
    herramientas: [
      { id: "subir", titulo: "Subir y auditar Excel", pagina: "auditoria" },
      { id: "libros", titulo: "Libro de la empresa", pagina: "libros" },
      { id: "historial", titulo: "Historial de auditorías", pagina: "historial" },
    ],
  },
  precios: {
    titulo: "Precios y catálogo",
    herramientas: [
      { id: "listas", titulo: "Precios de la empresa", pagina: "precios_empresa" },
      { id: "catalogo", titulo: "Catálogo de partidas e insumos", pagina: "catalogo" },
      { id: "indices", titulo: "Índices del BCV", pagina: "indices" },
      { id: "simulador", titulo: "Simulador de listas", pagina: "simulador" },
    ],
  },
};

// Las subvistas de las secciones de obra que las tienen (contrato 2.1, adenda A.1). La raíz (`id: ""`) es la pantalla
// de la propia sección y va primero; «tablero» es subvista de Resumen, no una sección.
export const SUBVISTAS: Partial<Record<SeccionId, readonly HerramientaDef[]>> = {
  resumen: [
    { id: "", titulo: "Resumen", pagina: "obras" },
    { id: "tablero", titulo: "Tablero", pagina: "tablero" },
  ],
  presupuesto: [
    { id: "", titulo: "Partidas", pagina: "hoja" },
    { id: "componer", titulo: "Componer", pagina: "componer" },
  ],
  aprobaciones: [
    { id: "", titulo: "Aprobar", pagina: "aprobar" },
    { id: "revisar", titulo: "Revisar un paquete", pagina: "revisar" },
    { id: "entregar", titulo: "Entregar", pagina: "entregar" },
  ],
  mercado: [
    { id: "", titulo: "Estudio", pagina: "mercado" },
    { id: "actualizar", titulo: "Actualizar precios", pagina: "actualizacion" },
  ],
  control: [
    { id: "", titulo: "Control", pagina: "control" },
    { id: "reajuste", titulo: "Reajuste", pagina: "reajuste" },
    { id: "escenarios", titulo: "Escenarios", pagina: "escenarios" },
  ],
};

// La sección y la subvista donde vive una pantalla que es subvista (no la raíz de una sección), o undefined.
export function subvistaDeLaPagina(paginaId: string): { seccion: SeccionId; subvista: HerramientaDef } | undefined {
  for (const seccion of Object.keys(SUBVISTAS) as SeccionId[]) {
    const subvista = SUBVISTAS[seccion]?.find((v) => v.id !== "" && v.pagina === paginaId);
    if (subvista !== undefined) return { seccion, subvista };
  }
  return undefined;
}

// Qué pantalla abre una sección de la obra según el cuarto segmento de la ruta (contrato 2.1 y 1), y a qué subvista hay que
// llevar la dirección con replace (`redirigeA`; `""` es la pantalla principal; null si ya es la buena):
// - una subvista conocida abre su pantalla, aunque la cuenta no pueda usarla (la ruta dirá «Sin permiso» o «Apagada»);
// - sin segmento, la pantalla principal si la cuenta puede usarla y, si no, la primera subvista que sí (Aprobaciones para
//   quien solo revisa paquetes abre «Revisar un paquete»); sin ninguna usable, la principal, que da el aviso;
// - un segmento desconocido lleva a la primera usable de la sección y, sin ninguna, a la principal;
// - una sección sin subvistas lleva a su pantalla principal con cualquier cuarto segmento.
export function vistaDeLaSeccion(
  seccion: SeccionDef,
  segmento: string | undefined,
  acciones: readonly string[],
  modoEntrega: boolean,
  apagados: readonly string[],
): { pagina: string | null; redirigeA: string | null } {
  const vistas = SUBVISTAS[seccion.id];
  if (vistas === undefined) return { pagina: seccion.pagina, redirigeA: segmento === undefined ? null : "" };
  const conocida = segmento === undefined || segmento === "" ? undefined : vistas.find((v) => v.id === segmento);
  if (conocida !== undefined) return { pagina: conocida.pagina, redirigeA: null };
  const destino = primeraUsable(vistas, acciones, modoEntrega, apagados) ?? vistas[0]!;
  return { pagina: destino.pagina, redirigeA: segmento === undefined && destino.id === "" ? null : destino.id };
}

export type CuentaId = "preferencias" | "cuentas" | "empresa" | "carpetas" | "sistema" | "ayuda";

// `pagina` es la pantalla que monta la sección (null: la sección no tiene pantalla en `PAGINAS`, como el tamaño de
// letra). «Administración» se reparte en cuatro secciones: las cuatro nombran su pantalla para que `usable` aplique
// `administrar_cuentas`; `ademas` es la acción que una sección pide además de la de su pantalla: «Carpetas» pide también
// `cambiar_caso` (contrato 3). `ayuda` es la línea corta que lee el buscador.
export interface CuentaDef {
  id: CuentaId;
  titulo: string;
  pagina: string | null;
  ademas?: string;
  ayuda: string;
}

// «Carpetas» y no «Carpetas de trabajo»: la guardia de jerga prohíbe esa frase en `src/marco/`.
export const SECCIONES_DE_CUENTA: readonly CuentaDef[] = [
  { id: "preferencias", titulo: "Pantalla y tamaño de letra", pagina: null, ayuda: "El tamaño de la letra de la pantalla y los datos de su cuenta." },
  { id: "cuentas", titulo: "Cuentas y permisos", pagina: "administracion", ayuda: "Las cuentas de las personas, sus permisos y los accesos." },
  { id: "empresa", titulo: "Empresa y tema", pagina: "administracion", ayuda: "Los datos de la empresa, su clave de firma y los colores del programa." },
  { id: "carpetas", titulo: "Carpetas", pagina: "administracion", ademas: "cambiar_caso", ayuda: "Las carpetas de la instalación: abrir, crear, subir y la demostración." },
  { id: "sistema", titulo: "Especialidades, IA e instalación", pagina: "administracion", ayuda: "Especialidades, asistente de IA, claves de API y respaldos." },
  { id: "ayuda", titulo: "Ayuda y acerca de Sílice", pagina: "acerca", ayuda: "La versión y la licencia del programa, y los recorridos guiados." },
];

export function esCuenta(segmento: string): segmento is CuentaId {
  return SECCIONES_DE_CUENTA.some((c) => c.id === segmento);
}

export function rutaDeCuenta(id: CuentaId): string {
  return `/cuenta/${id}`;
}

// Si la cuenta puede usar la sección: la regla de su pantalla (`usable`: permiso, modo entrega y módulos apagados) y, si
// la sección la pide, la acción de más. Una sección sin pantalla (el tamaño de letra) es de toda cuenta.
export function cuentaUsable(def: CuentaDef, acciones: readonly string[], modoEntrega: boolean, apagados: readonly string[]): boolean {
  if (def.ademas !== undefined && !acciones.includes(def.ademas)) return false;
  if (def.pagina === null) return true;
  const pagina = paginaPorId(def.pagina);
  return pagina !== undefined && usable(pagina, acciones, modoEntrega, apagados);
}

// La primera opción que la cuenta puede usar, o null si no puede ninguna (el espacio entonces no se ofrece, o se abre en
// la primera definida para mostrar su aviso: lo decide quien enruta). Quien arma entra a Precios por el Catálogo; con
// `administrar_precios`, por los precios de la empresa.
export function primeraUsable(
  opciones: readonly HerramientaDef[],
  acciones: readonly string[],
  modoEntrega: boolean,
  apagados: readonly string[],
): HerramientaDef | null {
  for (const opcion of opciones) {
    const pagina = paginaPorId(opcion.pagina);
    if (pagina !== undefined && usable(pagina, acciones, modoEntrega, apagados)) return opcion;
  }
  return null;
}
