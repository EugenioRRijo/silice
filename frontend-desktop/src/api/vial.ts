// Los tramos viales de una versión (`/v1/vial`, plan vial Tarea 8). Las cifras y las cantidades viajan como texto
// decimal con punto: la coma es cosa de la pantalla. La hora y el usuario los pone el servidor.
import { pedir } from "./cliente";

const RUTA = "/v1/vial";

export interface CapaDeTramo {
  tipo: string;
  espesor_m: string | null;
  densidad_t_m3: string | null;
  dosis_l_m2: string | null;
  // Porcentaje de asfalto de la mezcla de la carpeta o del bacheo (columna opcional del CSV); lo compara VR2.
  asfalto_pct?: string | null;
  // F5 vial: esponjamiento del fresado, limpieza de un riego y la otra medición («m2» del fresado, «t» de la carpeta).
  esponjamiento?: string | null;
  limpieza?: boolean;
  medicion?: string | null;
}

// Una línea de demarcación o, con tipo «superficie», elementos iguales de `area_m2` cada uno (F5 vial).
export interface DemarcacionDeTramo {
  tipo: string;
  lineas: number;
  area_m2?: string | null;
  captafaros?: number | null;
}

export interface TramoGuardado {
  id: string;
  progresiva_ini_km: string;
  progresiva_fin_km: string;
  ancho_m: string;
  distancia_planta_km: string | null;
  capas: CapaDeTramo[];
  demarcacion: DemarcacionDeTramo[];
}

// Una cantidad de obra derivada de un tramo; `regla` y `origen_id` dicen de dónde sale.
export interface CantidadDeTramo {
  tramo: string;
  codigo: string;
  descripcion: string;
  unidad: string;
  cantidad: string;
  origen_id: string;
  regla: string;
}

export interface TramosDeVersion {
  proyecto: string;
  version: string;
  editable: boolean;
  // Por qué ya no se editan (versión en aprobación, aprobada o devuelta); null si se pueden editar.
  bloqueo: string | null;
  // La versión de la que hereda sus tramos (no tiene guardado propio); null si son suyos o no hay.
  heredados_de: string | null;
  guardado: { usuario: string; fecha_hora: string; fuente: string } | null;
  tramos: TramoGuardado[];
  cantidades: CantidadDeTramo[];
}

function consulta(proyecto: string, version: string): string {
  return `proyecto=${encodeURIComponent(proyecto)}&version=${encodeURIComponent(version)}`;
}

export function tramosDeVersion(proyecto: string, version: string, senal?: AbortSignal): Promise<TramosDeVersion> {
  return pedir<TramosDeVersion>(`${RUTA}/tramos?${consulta(proyecto, version)}`, { senal });
}

// Todo o nada: una fila mala es un 422 que nombra el archivo y la fila, y no se guarda nada.
export function importarTramos(proyecto: string, version: string, archivo: File): Promise<TramosDeVersion> {
  const cuerpo = new FormData();
  cuerpo.append("archivo", archivo);
  return pedir<TramosDeVersion>(`${RUTA}/tramos/importar?${consulta(proyecto, version)}`, { metodo: "POST", cuerpo });
}

export function obrasConTramos(): Promise<{ obras: number[] }> {
  return pedir<{ obras: number[] }>(`${RUTA}/obras`);
}

// Lo que devuelve llevar los tramos al presupuesto: el borrador de la Hoja de la obra, cuántos renglones de tramo tiene
// y la versión de la que salieron.
export interface TramosLlevados {
  borrador_id: string;
  renglones: number;
  version: string;
}

// Lleva las cantidades de los tramos al borrador de la Hoja de la obra (sin guardar versión); llevar otra vez sincroniza.
// Todo o nada: si una partida vial no tiene APU, un 404 las nombra todas y no se lleva nada. `version` es la que se ve:
// si la Hoja de la obra tiene (o abriría) un borrador de otra versión, un 409 lo dice y no se lleva nada.
export function llevarTramos(proyecto: string, version: string): Promise<TramosLlevados> {
  return pedir<TramosLlevados>(`${RUTA}/tramos/llevar`, { metodo: "POST", cuerpo: { proyecto, version } });
}
