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
  // Propuesta aditiva: direccion de la interfaz Streamlit, para el enlace de las paginas aun no migradas.
  url_clasica?: string | null;
}

export interface CasoRespuesta {
  nombre: string;
  ruta_relativa: string;
}

export interface CasosRespuesta {
  actual: CasoRespuesta;
  casos: CasoRespuesta[];
}

export interface ProyectoRespuesta {
  codigo: string;
  nombre: string;
  version_vigente: number | null;
  actualizado: string | null;
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
