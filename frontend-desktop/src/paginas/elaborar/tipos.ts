// Tipos de las rutas de «Elaborar un presupuesto» (api/esquemas_ola2.py, api/esquemas.py). Los montos y las
// cantidades llegan como texto y se muestran tal cual; el unico numero es el puntaje de una propuesta, que es una
// similitud adimensional y no un monto.
import type { InformeAuditoriaRespuesta } from "../../api/tipos";

export type Dominio = "civil" | "telecom" | "industrial" | "sistemas";

// GET /partidas
export interface PartidaCatalogo {
  codigo: string;
  descripcion: string;
  unidad: string;
  dominio: string;
}

// POST /v1/computos/{dominio}: tal como se devuelve se reenvia a /presupuestos/calcular.
export interface ItemComputo {
  codigo_partida: string;
  descripcion: string;
  unidad: string;
  cantidad: string;
  origen_id: string;
  origen_tipo: string;
  dominio: string;
  regla: string | null;
  parametros: Record<string, string>;
  especificaciones: Record<string, string>;
}

export interface FilaPlan {
  periodo: string;
  codigo_partida: string;
  fraccion: string;
}

export interface CuerpoCalculo {
  codigo: string;
  fecha: string;
  moneda: string;
  items: ItemComputo[];
  plan?: FilaPlan[];
}

export interface PartidaPresupuestada {
  codigo_partida: string;
  descripcion: string;
  unidad: string;
  cantidad: string;
  precio_unitario: string;
  total: string;
}

export interface PropuestaPartida {
  codigo: string;
  descripcion: string;
  puntaje: number;
}

export interface PendienteConPropuestas {
  codigo_partida: string;
  descripcion: string;
  unidad: string;
  cantidad: string;
  origen_id: string;
  propuestas: PropuestaPartida[];
  falla: string | null;
}

// POST /presupuestos/calcular
export interface CalculoRespuesta {
  codigo: string;
  fecha: string;
  moneda: string;
  total: string;
  partidas: PartidaPresupuestada[];
  por_severidad: { severidad: string; total: number }[];
  informe: InformeAuditoriaRespuesta;
  pendientes: PendienteConPropuestas[];
  plan_por_defecto: FilaPlan[];
}

export interface RendimientoHistorico {
  valor: string;
  tipo: string;
  fecha: string;
  condiciones: string;
  referencia_ejecucion: string | null;
}

export interface Dispersion {
  observaciones: number;
  media: string;
  minimo: string;
  maximo: string;
  medidos: number;
  estimados: number;
}

export interface RendimientoPorDeclarar {
  codigo_partida: string;
  propuesta: { rendimiento: RendimientoHistorico; dispersion: Dispersion } | null;
}

// El cuerpo del 409 de /presupuestos/calcular cuando falta un rendimiento estimado vigente (UC-01 3b).
export interface RendimientosPorDeclararRespuesta {
  detalle: string;
  rendimientos_por_declarar: RendimientoPorDeclarar[];
}

export type TipoRendimiento = "estimado" | "medido";
