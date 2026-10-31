// Las especialidades y módulos activables de la instalación (`/v1/modulos`, plan vial Tarea 19). Apagar una no borra nada:
// la API deja de contestarla y el marco deja de ofrecerla; al encenderla todo vuelve igual.
import { pedir } from "./cliente";

const RUTA = "/v1/modulos";

export interface ModuloRespuesta {
  clave: string;
  // Cómo se nombra ante la persona (producción, vial, edificación, riesgo).
  nombre: string;
  activo: boolean;
  // Quién y cuándo lo cambió por última vez; null si nunca se tocó.
  cambiado_por: string | null;
  cambiado_el: string | null;
}

export interface ModulosRespuesta {
  modulos: ModuloRespuesta[];
}

export function leerModulos(): Promise<ModulosRespuesta> {
  return pedir<ModulosRespuesta>(RUTA);
}

export function fijarModulo(clave: string, activo: boolean): Promise<ModulosRespuesta> {
  return pedir<ModulosRespuesta>(`${RUTA}/${encodeURIComponent(clave)}`, { metodo: "PUT", cuerpo: { activo } });
}
