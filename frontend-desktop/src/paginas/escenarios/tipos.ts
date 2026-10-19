// Tipos de la API de escenarios (api/esquemas.py, api/esquemas_ola2.py). Los montos viajan como texto decimal.

export interface PresupuestoResumen {
  codigo: string;
  total: string;
  proyecto: string;
}

export interface Pendiente {
  codigo_partida: string;
  descripcion: string;
  unidad: string;
  cantidad: string;
  origen_id: string;
}

export interface EscenariosBaseRespuesta {
  codigo: string;
  proyecto: string;
  moneda: string;
  total: string;
  parametros: Record<string, string>;
  pendientes_base: Pendiente[];
}

export interface FilaComparativo {
  codigo_partida: string;
  descripcion: string;
  cantidad: string;
  pu_anterior: string;
  pu_nuevo: string;
  variacion_pct: string;
  total_anterior: string;
  total_nuevo: string;
  incidencia_pct: string;
}

export interface EscenarioRespuesta {
  nombre: string;
  total: string;
  variacion: string;
  variacion_pct: string;
  hallazgos: number;
  insumos_variados: number;
  partidas: FilaComparativo[];
}

export interface EscenariosRespuesta {
  codigo_base: string;
  total_base: string;
  pendientes_base: Pendiente[];
  escenarios: EscenarioRespuesta[];
}

export type CampoParametro = "fcas" | "bono_alimentacion" | "administracion" | "utilidad";

// La peticion de un escenario: lo que la persona declaro (la API recalcula sin estado).
export interface EscenarioPeticion extends Record<CampoParametro, string> {
  nombre: string;
  precios: Record<string, string>;
}
