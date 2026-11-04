// El riesgo de precios de una obra (`/v1/riesgo`, plan vial Tarea 16). Los montos llegan como texto decimal con punto,
// exactos: la pantalla los redondea al presentarlos. Los parámetros de la proyección van como enteros JSON (la coma y el
// punto de miles se leen antes de enviar, con `leerCifra`). Proyectar y comprobar no guardan nada.
import { pedir } from "./cliente";

const RUTA = "/v1/riesgo";

export interface SerieOfrecida {
  codigo: string;
  nombre: string;
}

// La mezcla propia que se recalcula con su receta y el n.º del cálculo publicado de donde sale.
export interface MezclaUsada {
  insumo: string;
  calculo: number;
}

export interface InsumosDeLaObra {
  proyecto: string;
  version: string;
  moneda: string;
  insumos: string[];
  // Los componentes de las recetas de las mezclas propias: siguen una serie por su código.
  componentes: string[];
  mezclas: MezclaUsada[];
  series: SerieOfrecida[];
  inicio_linea_base: string | null;
}

// Insumo (descripción en el APU o código del componente) -> código de la serie que lo mueve.
export type MapaDeSeries = Record<string, string>;

export interface PedidoDeProyeccion {
  proyecto: string;
  version: string;
  // null: la fecha de inicio de la línea base de la versión.
  inicio: string | null;
  meses: number;
  trayectorias: number;
  semilla: number;
  ventana_meses: number;
  mapa: MapaDeSeries;
}

export interface ProyeccionDeLaObra {
  proyecto: string;
  version: string;
  moneda: string;
  inicio: string;
  inicio_de: "linea_base" | "declarado";
  meses: number;
  trayectorias: number;
  semilla: number;
  total_base: string;
  p50: string;
  p80: string;
  reserva: string;
  // De mayor a menor: cuánto sube el total con solo ese insumo a su factor medio.
  contribucion: { insumo: string; monto: string }[];
  meses_usados: number;
  supuestos: string[];
  mezclas: MezclaUsada[];
}

export interface PedidoDeComprobacion {
  proyecto: string;
  version: string;
  meses: number;
  trayectorias_por_corte: number;
  semilla: number;
  ventana_meses: number;
  mapa: MapaDeSeries;
}

export interface ComprobacionDeLaObra {
  moneda: string;
  meses: number;
  trayectorias_por_corte: number;
  cortes: { corte: string; p50: string; p80: string; real: string; dentro: boolean }[];
  // Exacta (dentro ÷ cortes) y en porcentaje con dos decimales, del servidor.
  cobertura: string;
  cobertura_pct: string;
  dentro: number;
  n_cortes: number;
}

export function insumosDeLaObra(proyecto: string, version: string, senal?: AbortSignal): Promise<InsumosDeLaObra> {
  const consulta = `proyecto=${encodeURIComponent(proyecto)}&version=${encodeURIComponent(version)}`;
  return pedir<InsumosDeLaObra>(`${RUTA}/insumos?${consulta}`, { senal });
}

export function proyectarObra(pedido: PedidoDeProyeccion): Promise<ProyeccionDeLaObra> {
  return pedir<ProyeccionDeLaObra>(`${RUTA}/proyeccion`, { metodo: "POST", cuerpo: pedido });
}

// Con 500 trayectorias por corte tarda del orden de medio minuto en una obra mediana: la pantalla avisa mientras espera.
export function comprobarObra(pedido: PedidoDeComprobacion): Promise<ComprobacionDeLaObra> {
  return pedir<ComprobacionDeLaObra>(`${RUTA}/comprobacion`, { metodo: "POST", cuerpo: pedido });
}

// El informe de mejora de la estimación (Tarea 15): las tres cifras como texto con punto decimal (la pantalla ya leyó la
// coma), en la misma moneda y a la misma fecha de precios. El servidor responde los dos errores y la mejora en puntos,
// con dos decimales y punto; la mejora es negativa si Sílice acertó menos. No guarda nada.
export interface PedidoDeMejora {
  costo_final_real: string;
  presupuesto_original: string;
  estimacion_silice: string;
}

export interface MejoraDeLaEstimacion {
  error_original_pct: string;
  error_silice_pct: string;
  mejora_pp: string;
}

export function calcularMejora(pedido: PedidoDeMejora): Promise<MejoraDeLaEstimacion> {
  return pedir<MejoraDeLaEstimacion>(`${RUTA}/mejora`, { metodo: "POST", cuerpo: pedido });
}

// El mismo informe en Excel (`GET /v1/riesgo/reportes/mejora`), con las cifras en la consulta.
export function rutaDelInformeDeMejora(pedido: PedidoDeMejora): string {
  return `${RUTA}/reportes/mejora?${new URLSearchParams({ ...pedido }).toString()}`;
}
