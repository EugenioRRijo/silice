// Qué notificaciones recibe la cuenta (`/v1/notificaciones/preferencias`, C11b). Solo las propias; la sesión manda.
import { pedir } from "../../api/cliente";

const RUTA = "/v1/notificaciones/preferencias";

export interface CategoriaDeNotificacion {
  categoria: string;
  titulo: string;
  descripcion: string;
  activa: boolean;
  // Si a la cuenta le llega esta categoría por su papel; las que no, no se muestran.
  aplica: boolean;
  // Si su papel no la deja apagar.
  obligatoria: boolean;
}

export interface PreferenciasDeNotificacion {
  categorias: CategoriaDeNotificacion[];
}

export function leerPreferencias(): Promise<PreferenciasDeNotificacion> {
  return pedir<PreferenciasDeNotificacion>(RUTA);
}

// Cambia solo esa categoría: las demás quedan como estaban en el servidor.
export function fijarPreferencia(categoria: string, activa: boolean): Promise<PreferenciasDeNotificacion> {
  return pedir<PreferenciasDeNotificacion>(RUTA, { metodo: "PUT", cuerpo: { categorias: [{ categoria, activa }] } });
}
