import type { SesionRespuesta } from "../api/tipos";
import type { PaginaDef } from "../shell/rutas";
import type { AlmacenDelVisor } from "../visor/almacen";
import type { CrearHojaVisor } from "../visor/hojaVisor";
import type { VigilanteDeObra } from "./otraPestana";

export interface PropsDelMarco {
  sesion: SesionRespuesta;
  alSalir: () => void;
  alExpirar: () => void;
  paginas?: readonly PaginaDef[];
  almacen?: AlmacenDelVisor;
  crearHoja?: CrearHojaVisor;
  vigilante?: VigilanteDeObra;
}

// Esqueleto para que las pruebas de la Tarea 8 fallen por comportamiento y no por módulo ausente.
export function Marco(props: PropsDelMarco) {
  void props;
  return null;
}
