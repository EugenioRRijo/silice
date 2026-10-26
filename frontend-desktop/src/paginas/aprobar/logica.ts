// «Aprobar una versión» (Tarea 20): lo que la pantalla lee de la API (api/rutas/aprobaciones.py, Tarea 18) y los textos
// que la API no da. La interfaz no calcula: solo da formato a los montos y cantidades que llegan como texto.
import type { InformeAuditoriaRespuesta } from "../../api/tipos";

export interface PartidaDelEnvio {
  codigo: string;
  descripcion: string;
  unidad: string;
  cantidad: string;
  precio_unitario: string | null;
  total: string | null;
  pendiente: boolean;
}

export interface DetalleDeEnvio {
  envio_id: number;
  proyecto: string;
  obra: string;
  version: string;
  estado: string;
  moneda: string;
  total: string;
  partidas: PartidaDelEnvio[];
  hallazgos: {
    error: number;
    advertencia: number;
    info: number;
    lista: { regla: string; severidad: string; descripcion: string }[];
  };
  rastro: { integro: boolean; mensaje: string };
  cadena: { integra: boolean; mensaje: string };
  envio: { por: string; el: string; nota: string };
  armo: boolean;
}

// Una fila del indice de envios (`GET /v1/aprobaciones/pendientes`).
export interface FilaDeEnvio {
  caso: string;
  envio_id: number;
  proyecto: string;
  obra: string;
  version: string;
  total: string;
  moneda: string;
  estado: string;
  enviado_por: string;
  enviado_el: string;
}

export type Resultado = "aprobada" | "aprobada_con_observaciones" | "devuelta";

export const OPCIONES: readonly { valor: Resultado; texto: string }[] = [
  { valor: "aprobada", texto: "Aprobada" },
  { valor: "aprobada_con_observaciones", texto: "Aprobada con observaciones" },
  { valor: "devuelta", texto: "Devuelta" },
];

export const SIN_ELEGIR = "Elija el dictamen: aprobada, aprobada con observaciones o devuelta.";
export const SIN_NOTAS = "Escriba las notas: son obligatorias para devolver o aprobar con observaciones.";

// El dictamen dicho en minusculas, para las frases («quedará devuelta»).
export function frase(resultado: Resultado): string {
  return resultado === "aprobada_con_observaciones" ? "aprobada con observaciones" : resultado;
}

export const necesitaNotas = (resultado: Resultado): boolean => resultado !== "aprobada";

// La carpeta de trabajo como la nombra la persona: el nombre de su archivo sin la extension.
export function nombreDeCarpeta(nombre: string): string {
  return nombre.replace(/\.db$/i, "");
}

// El informe de auditoria de la version, armado con los hallazgos que dio la API para que lo pinte `InformeAuditoria`.
export function informeDe(detalle: DetalleDeEnvio): InformeAuditoriaRespuesta {
  const { hallazgos } = detalle;
  const conError = hallazgos.error > 0;
  return {
    codigo_presupuesto: detalle.version,
    cumple: !conError,
    veredicto: conError ? "NO CUMPLE" : "CUMPLE",
    total_hallazgos: hallazgos.lista.length,
    por_severidad: [
      { severidad: "error", total: hallazgos.error },
      { severidad: "advertencia", total: hallazgos.advertencia },
      { severidad: "info", total: hallazgos.info },
    ],
    reglas_evaluadas: [],
    hallazgos: hallazgos.lista.map((h, i) => ({
      numero: i + 1,
      regla: h.regla,
      severidad: h.severidad,
      partida: null,
      descripcion: h.descripcion,
      impacto: null,
      observado: null,
      esperado: null,
      origen: [],
    })),
    sin_hallazgos: hallazgos.lista.length === 0 ? "La auditoría de esta versión no encontró hallazgos." : null,
  };
}
