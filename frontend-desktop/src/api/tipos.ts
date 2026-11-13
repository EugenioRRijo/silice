// Espejo de las respuestas de la API que usa el visor. Los montos y numeros viajan como texto decimal y la
// interfaz nunca los convierte a numero para calcular: solo los muestra.
import type { ConteoPorSeveridad, IndicadorRespuesta, Severidad } from "../indicadores/tipos";

export type { ConteoPorSeveridad, IndicadorRespuesta, Severidad };

export interface SesionRespuesta {
  login: string;
  nombre: string;
  roles: string[];
  csrf: string;
  // Contrato de la ola 0a. `acciones` son las `Accion` que permite el rol (el menu se arma con ellas) y
  // `modo_entrega` esconde la seccion Investigacion. Una API anterior no los trae: useSesion los normaliza.
  debe_cambiar_clave: boolean;
  acciones: string[];
  modo_entrega: boolean;
  // MOD-0: lo que la cuenta recuerda (carpeta, obra, ultimo modulo, sidebar fijado). `eleccion` es null con la
  // contrasena temporal. Opcionales en el tipo porque una API anterior no los trae y las pruebas de las paginas
  // arman sesiones sin ellos; useSesion siempre los llena.
  eleccion?: EleccionDeSesion | null;
  preferencias?: PreferenciasDeSesion;
}

export type ModuloDeSilice = "auditoria" | "obras" | "produccion";

export interface EleccionDeSesion {
  caso: string | null;
  proyecto: string | null;
  aviso: string | null;
}

export interface PreferenciasDeSesion {
  modulo: ModuloDeSilice | null;
  sidebar_fijado: boolean;
}

export interface CasoRespuesta {
  nombre: string;
  ruta_relativa: string;
}

export interface CasosRespuesta {
  actual: CasoRespuesta;
  casos: CasoRespuesta[];
  // MOD-3a: la carpeta de la empresa (la del proceso, la de omision de la instalacion; null si no usa un archivo) y si
  // la de esta sesion es la de demostracion.
  empresa: CasoRespuesta | null;
  es_demostracion: boolean;
}

// `GET /v1/obras/todas` (rediseño del marco, Tarea 3): las obras de todas las carpetas que la cuenta puede abrir (solo
// la abierta sin `abrir_carpeta`). `carpeta` es el nombre con su .db que acepta `POST /v1/casos/actual`; null = la
// carpeta de la empresa, la primera de la lista.
export interface ObraDeCarpetaRespuesta {
  carpeta: string | null;
  carpeta_titulo: string;
  obra_id: number;
  obra: string;
  version_codigo: string | null;
}

export interface ObrasTodasRespuesta {
  // La carpeta abierta en la sesion; null si es la de la empresa.
  carpeta_actual: string | null;
  // Su titulo, como `carpeta_titulo`, aunque no tenga obras: lo da el servidor.
  carpeta_actual_titulo: string;
  obras: ObraDeCarpetaRespuesta[];
}

// `GET /v1/obras/pendientes/todas` (rediseño F3, Tarea 1): lo que requiere atención en las obras de las carpetas de
// `GET /v1/obras/todas`, ya ordenado (lo que bloquea primero). `carpeta` como en `ObraDeCarpetaRespuesta`; `accion.pagina`
// es el id de la pantalla en `shell/rutas.ts`. `carpetas_omitidas`: las que no se pudieron leer.
export interface PendienteDeObra {
  carpeta: string | null;
  obra_id: number;
  obra: string;
  grupo: string;
  urgencia: "bloquea" | "aviso";
  texto: string;
  accion: { texto: string; pagina: string };
}

export interface PendientesTodasRespuesta {
  pendientes: PendienteDeObra[];
  carpetas_omitidas: number;
}

// `GET /v1/obras/resumen/todas` (F6, T7): la cartera de las carpetas que la cuenta puede abrir, una fila por moneda (nunca
// sumadas entre sí) y una por obra. Los montos y los porcentajes llegan como texto decimal («334570.50», «62.5») y la
// interfaz solo los formatea. `carpeta` como en `ObraDeCarpetaRespuesta`; `etapa` es una de `Etapa`; `total` es el del
// presupuesto: el de la línea base o, sin ella, el de la versión vigente (null sin ninguna); los avances son null sin
// línea base. `carpetas_omitidas`: las que no se pudieron leer. La demostración nunca entra junto a otras carpetas.
export interface MonedaDeLaCartera {
  moneda: string;
  obras: number;
  total: string;
  en_ejecucion: number;
}

export interface ObraDeLaCartera {
  carpeta: string | null;
  carpeta_titulo: string;
  obra_id: number;
  nombre: string;
  moneda: string;
  etapa: string;
  etapa_texto: string;
  total: string | null;
  avance_real: string | null;
  avance_plan: string | null;
}

export interface ResumenTodasRespuesta {
  hoy: string;
  por_moneda: MonedaDeLaCartera[];
  obras: ObraDeLaCartera[];
  carpetas_omitidas: number;
}

// `GET /v1/carpeta` y `PUT /v1/carpeta/moneda` (MP T2): la moneda de trabajo de la carpeta abierta.
export interface CarpetaRespuesta {
  moneda: string | null;
  declarada: boolean;
  lista: { nombre: string; moneda: string; fecha: string; origen: string } | null;
  aviso: string | null;
}

export interface ProyectoRespuesta {
  codigo: string;
  nombre: string;
  version_vigente: number | null;
  actualizado: string | null;
  // MOD-3a: la ficha de la obra (vacios si no se dieron).
  cliente: string;
  ubicacion: string;
}

export interface HallazgoLibroRespuesta {
  codigo: string;
  severidad: string;
  descripcion: string;
  // "HOJA!REF" sin comillas ni $; puede no ser A1 ("APU-01!Rendimiento") o venir vacia.
  celda: string;
  impacto: string | null;
  accion: string;
}

export interface LibroAuditadoRespuesta {
  libro: { nombre: string; sha256: string };
  fecha_libro: string | null;
  fecha_devolucion: string | null;
  cumple: boolean;
  por_severidad: Record<string, number>;
  totales_libro: Record<string, string>;
  totales_silice: Record<string, string>;
  hallazgos: HallazgoLibroRespuesta[];
  // Campo aditivo de la 2.3b: una API anterior no lo trae.
  indicadores?: IndicadorRespuesta[];
  // Campo aditivo de V-16: numeros de las partidas con el costo directo incompleto (L4). Una API anterior no lo trae.
  partidas_con_omision?: number[];
}

export interface EstiloVisualRespuesta {
  relleno: string | null;
  fuente: string | null;
  tamano: string | null;
  negrita: boolean;
  cursiva: boolean;
  subrayado: boolean;
  color: string | null;
  alineacion_h: string | null;
  alineacion_v: string | null;
  ajustar_texto: boolean;
  formato_numero: string;
  // arriba, derecha, abajo, izquierda
  bordes: (string | null)[];
}

export interface CeldaVisualRespuesta {
  ref: string;
  fila: number;
  columna: number;
  mostrado: string;
  formula: string | null;
  estilo: number;
}

export interface HojaVisualRespuesta {
  nombre: string;
  visible: boolean;
  filas: number;
  columnas: number;
  anchos: Record<string, string>;
  altos: Record<string, string>;
  ocultas_filas: number[];
  ocultas_columnas: number[];
  combinadas: string[];
  fijas: string | null;
  celdas: CeldaVisualRespuesta[];
}

export interface LibroVisualRespuesta {
  nombre: string;
  sha256: string;
  hojas: HojaVisualRespuesta[];
  estilos: EstiloVisualRespuesta[];
}

// Informe de auditoria como JSON (ola 2 de la migracion; api/esquemas_informe.py). Los montos ya vienen con los dos
// decimales del sistema; la interfaz los muestra tal cual.
export interface HallazgoInformeRespuesta {
  numero: number;
  regla: string;
  severidad: string;
  partida: string | null;
  descripcion: string;
  impacto: string | null;
  observado: string | null;
  esperado: string | null;
  origen: string[];
}

export interface InformeAuditoriaRespuesta {
  codigo_presupuesto: string;
  cumple: boolean;
  veredicto: string;
  total_hallazgos: number;
  por_severidad: { severidad: string; total: number }[];
  reglas_evaluadas: { regla: string; nombre: string; hallazgos: number }[];
  hallazgos: HallazgoInformeRespuesta[];
  // El texto que declara que se verifico y no hubo nada (UC-05 5a); null si hay hallazgos.
  sin_hallazgos: string | null;
}

// `GET /v1/obras/resumen` (una fila por obra de la carpeta abierta): la cabecera de la obra y el Resumen leen la suya
// (plan F4, Tarea 1). Montos y porcentajes llegan como texto con punto decimal y solo se formatean.
export interface SiguienteRespuesta {
  texto: string;
  // El id de la pantalla (rutas.ts) a la que lleva.
  pagina: string;
}

export type Etapa = "en_elaboracion" | "en_aprobacion" | "aprobada" | "en_ejecucion" | "atrasada";

export interface ObraFilaRespuesta {
  codigo: string;
  nombre: string;
  cliente: string;
  etapa: Etapa;
  etapa_texto: string;
  version: string | null;
  total: string | null;
  moneda: string;
  avance_real: string | null;
  avance_plan: string | null;
  que_pasa: string | null;
  siguiente: SiguienteRespuesta | null;
}
