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
