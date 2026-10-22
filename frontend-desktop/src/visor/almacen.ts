// Lo que el visor tiene abierto, guardado SOLO en memoria por encima de la puerta de sesion (App), para que una
// sesion vencida no pierda el libro (UC-26). Nunca va a localStorage ni a sessionStorage: es el mismo objeto de
// JavaScript mientras la pagina siga abierta.
import type { LibroAuditadoRespuesta, LibroVisualRespuesta } from "../api/tipos";
import type { Severidad } from "../indicadores/tipos";

export interface EstadoDelVisor {
  archivo: File | null;
  fecha: string;
  replica: LibroVisualRespuesta;
  auditoria: LibroAuditadoRespuesta;
  hojaActiva: string;
  filtro: Severidad[];
  seleccionado: number | null;
}

export interface AlmacenDelVisor {
  leer(): EstadoDelVisor | null;
  guardar(estado: EstadoDelVisor | null): void;
}

export function crearAlmacen(): AlmacenDelVisor {
  let actual: EstadoDelVisor | null = null;
  return {
    leer: () => actual,
    guardar: (estado) => {
      actual = estado;
    },
  };
}
