// Espejo de las respuestas de /v1/produccion (api/rutas/produccion.py). Las cantidades viajan como texto decimal
// con punto y la interfaz nunca las convierte a numero: solo las muestra.

export interface MaterialRespuesta {
  id: number;
  codigo: string;
  nombre: string;
  unidad_venta: string; // "m3" o "t"
  densidad_t_m3: string | null;
  existencia_minima: string;
  activo: boolean;
}

export interface ExistenciaRespuesta {
  codigo: string;
  nombre: string;
  unidad_venta: string;
  existencia: string;
  minima: string;
  queda_poco: boolean;
  negativa: boolean;
  // El ultimo conteo fisico no anulado: el unico que se puede anular (tanda 2026-11-19). `null` si no hay ninguno.
  ultimo_conteo: ConteoVigente | null;
}

export interface ConteoVigente {
  id: number;
  fecha: string; // ISO
  diferencia: string; // el ajuste que dejo, con signo
  usuario: string;
}

export interface MovimientoRespuesta {
  id: number;
  material_codigo: string;
  fecha: string;
  tipo: string;
  cantidad: string; // del ajuste: la diferencia con signo
  ticket: string | null;
  placa: string;
  cliente: string;
  nota: string;
  origen: string;
  usuario: string;
  registrado: string;
  anula_id: number | null; // la anulacion de un conteo: el conteo que anula
  motivo: string; // de la anulacion; vacio en el resto
}

export interface ImportacionRespuesta {
  registrados: number;
  ya_registrados: number;
  a_la_bandeja: number;
  huella: string;
}

export interface SospechosoRespuesta {
  id: number;
  huella_archivo: string;
  fila: number;
  ticket: string;
  fecha_texto: string;
  placa: string;
  material_texto: string;
  bruto_texto: string;
  tara_texto: string;
  neto_texto: string;
  motivo: string;
  estado: string;
}

export type TipoDeMovimiento = "entrada" | "despacho" | "ajuste";
