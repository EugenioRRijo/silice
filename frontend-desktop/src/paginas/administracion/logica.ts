// Logica pura de Administracion (pestanas Cuentas y Accesos): tipos del contrato de /v1/cuentas y /v1/accesos,
// los rotulos de Streamlit (ui/paginas/administracion.py) y las filas de las tablas. No guarda ningun secreto.
import type { FilaDensa } from "../../comun/TablaDensa";

export interface Cuenta {
  id: number;
  login: string;
  nombre: string;
  roles: string[];
  activa: boolean;
}

export interface CuentasRespuesta {
  cuentas: Cuenta[];
  aviso_arma_y_revisa: string;
}

export interface ResultadoCuenta {
  cuenta: Cuenta;
  mensaje: string;
  aviso: string | null;
}

export interface EventoAcceso {
  id: number;
  fecha_hora: string;
  tipo: string;
  usuario: string;
  ip: string;
  detalle: string;
}

export interface AccesosRespuesta {
  maximo: number;
  eventos: EventoAcceso[];
}

export const ROLES = ["arma", "revisa", "administrador"] as const;
export const ETIQUETAS_DE_ROL: Record<string, string> = {
  arma: "arma presupuestos (arma)",
  revisa: "revisa paquetes (revisa)",
  administrador: "administra la instalación (administrador)",
};

export const PESTANAS = [
  { id: "cuentas", titulo: "Cuentas", migrada: true },
  { id: "empresa", titulo: "Empresa y clave de firma", migrada: false },
  { id: "registradas", titulo: "Empresas registradas", migrada: false },
  { id: "api", titulo: "Claves de API", migrada: false },
  { id: "asistente", titulo: "Asistente de IA", migrada: false },
  { id: "accesos", titulo: "Accesos", migrada: true },
  { id: "instalacion", titulo: "Instalación", migrada: false },
] as const;

export const NOTA_ACCESOS = "Los 200 últimos eventos de acceso; este registro solo se agrega, no se edita.";
export const AVISO_TEMPORAL = "La persona deberá cambiar la contraseña al entrar.";

export function etiquetaDeRol(rol: string): string {
  return ETIQUETAS_DE_ROL[rol] ?? rol;
}

export function rolesEnTexto(roles: readonly string[]): string {
  return roles.join(", ");
}

// El aviso de Streamlit al elegir arma y revisa a la vez: el texto lo manda la API (una sola fuente).
export function avisoDeRoles(elegidos: readonly string[], aviso: string): string | null {
  return elegidos.includes("arma") && elegidos.includes("revisa") ? aviso : null;
}

export function filasDeCuentas(cuentas: readonly Cuenta[]): FilaDensa[] {
  return cuentas.map((c) => ({
    id: String(c.id),
    usuario: c.login,
    nombre: c.nombre,
    roles: rolesEnTexto(c.roles),
    activa: c.activa ? "sí" : "no",
  }));
}

export function filasDeAccesos(eventos: readonly EventoAcceso[]): FilaDensa[] {
  return eventos.map((e) => ({
    id: String(e.id),
    fecha: e.fecha_hora,
    evento: e.tipo,
    usuario: e.usuario,
    ip: e.ip,
    detalle: e.detalle,
  }));
}

// Botones de «Cambiar una cuenta» y lo que se confirma antes de actuar (Streamlit no confirmaba: aqui si, porque
// cierran sesiones o dejan sin acceso).
export const CONFIRMACIONES = {
  desactivar: {
    titulo: "Desactivar la cuenta",
    texto: (login: string) =>
      `La cuenta «${login}» no podrá entrar y sus sesiones se cerrarán. Sus registros se conservan.`,
    boton: "Desactivar",
  },
  restablecer: {
    titulo: "Restablecer la contraseña",
    texto: (login: string) =>
      `La cuenta «${login}» pasará a la contraseña temporal que escribió y sus sesiones se cerrarán.`,
    boton: "Restablecer",
  },
} as const;
