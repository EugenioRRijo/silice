// El ciclo de aprobacion de una version (Tarea 17/18; diseno de montar un presupuesto §5.4), como lo leen las pantallas
// de Entregar, Control, Trazabilidad y Aprobar. La API dice el estado con su clave; aqui se dice con palabras.

export const NOMBRES_DE_ESTADO: Record<string, string> = {
  guardada: "Guardada",
  en_aprobacion: "En aprobación",
  retirada: "Retirada",
  aprobada: "Aprobada",
  aprobada_con_observaciones: "Aprobada con observaciones",
  devuelta: "Devuelta",
};

export const ESTADOS_APROBADOS: ReadonlySet<string> = new Set(["aprobada", "aprobada_con_observaciones"]);

export function nombreDeEstado(estado: string): string {
  return NOMBRES_DE_ESTADO[estado] ?? estado;
}

// «VIV-002 · Aprobada»; un estado que la interfaz no conoce se dice tal cual y sin estado, solo el codigo.
export function versionConEstado(codigo: string, estado: string | undefined): string {
  return estado === undefined ? codigo : `${codigo} · ${nombreDeEstado(estado)}`;
}

// `GET /v1/aprobaciones?proyecto=` (api/rutas/aprobaciones.py, Tarea 18).
export interface EstadoDeAprobacion {
  estado: string;
  por: string | null;
  el: string | null;
  notas: string;
  armo: boolean;
}

export interface EventoDeAprobacion {
  id: number;
  tipo: string;
  version: string;
  resultado: string | null;
  notas: string;
  por: string;
  el: string;
  armo: boolean;
  cierre_de: number | null;
}

export interface AprobacionesDeObra {
  rastro: { integro: boolean; mensaje: string };
  fases: string;
  versiones: Record<string, EstadoDeAprobacion>;
  eventos: EventoDeAprobacion[];
  // La version del ultimo dictamen que aprobo (con o sin observaciones), o null: la decide la API.
  ultima_aprobada: string | null;
}
