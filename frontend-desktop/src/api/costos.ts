// Costos del período de la cantera y la planta (`/v1/produccion/costos`). Los montos viajan como texto decimal con
// punto: la coma decimal es cosa de la pantalla. La hora de registro la pone el servidor, así que ninguna petición
// lleva `ahora`.
import { pedir } from "./cliente";

const RUTA = "/v1/produccion/costos";

export interface CostoRespuesta {
  id: number;
  periodo: string;
  centro: string;
  concepto: string;
  monto: string;
  moneda: string;
  fecha: string;
  fuente: string;
  nota: string;
  usuario: string;
  registrado: string;
  // Verdadero en el costo anulado y en la fila de su anulación: ninguno de los dos suma.
  anulado: boolean;
  // Solo la fila de anulación lo trae: el número del costo que anula.
  anula_id: number | null;
  motivo: string;
}

export interface CostoNuevo {
  periodo: string; // AAAA-MM
  centro: string;
  concepto: string;
  monto: string; // decimal con punto
  moneda: string;
  fecha: string; // AAAA-MM-DD, dentro del período
  fuente: string;
  nota: string;
}

export function listarCostos(periodo: string, incluirAnulados = false, senal?: AbortSignal): Promise<CostoRespuesta[]> {
  const consulta = `periodo=${encodeURIComponent(periodo)}${incluirAnulados ? "&incluir_anulados=true" : ""}`;
  return pedir<CostoRespuesta[]>(`${RUTA}?${consulta}`, { senal });
}

export interface TotalDeCostos {
  centro: string;
  moneda: string;
  // Decimal con punto: la suma exacta de los costos vigentes que calcula el servidor.
  total: string;
}

// Total vigente del mes por centro y moneda, sin convertir moneda. Lo calcula el servidor: la interfaz no suma montos.
export function totalesDeCostos(periodo: string, senal?: AbortSignal): Promise<TotalDeCostos[]> {
  return pedir<TotalDeCostos[]>(`${RUTA}/totales?periodo=${encodeURIComponent(periodo)}`, { senal });
}

export function registrarCosto(costo: CostoNuevo): Promise<{ id: number }> {
  return pedir<{ id: number }>(RUTA, { metodo: "POST", cuerpo: costo });
}

export function anularCosto(id: number, motivo: string): Promise<{ id: number }> {
  return pedir<{ id: number }>(`${RUTA}/${id}/anular`, { metodo: "POST", cuerpo: { motivo } });
}
