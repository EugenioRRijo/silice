// Tipos de las rutas de «Elaborar un presupuesto» (api/esquemas_ola2.py, api/esquemas.py). Los montos y las
// cantidades llegan como texto y se muestran tal cual; el unico numero es el puntaje de una propuesta, que es una
// similitud adimensional y no un monto.
export type Dominio = "civil" | "telecom" | "industrial" | "sistemas";

// GET /partidas
export interface PartidaCatalogo {
  codigo: string;
  descripcion: string;
  unidad: string;
  dominio: string;
}

// POST /computos/{dominio}: tal como se devuelve se reenvia a /presupuestos/calcular.
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

export interface CuerpoCalculo {
  codigo: string;
  fecha: string;
  moneda: string;
  items: ItemComputo[];
  // El codigo de la obra elegida: con el, la API valora con la lista de la obra y en su moneda (Tarea 12).
  proyecto?: string;
}

// Un renglon de POST /v1/hoja/llevar: la cantidad tal como salio del computo (texto de maquina, punto decimal).
export interface PartidaParaLlevar {
  codigo: string;
  cantidad: string;
  calculo: string;
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
  pendientes: PendienteConPropuestas[];
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
