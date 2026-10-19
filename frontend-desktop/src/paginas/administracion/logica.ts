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
  { id: "empresa", titulo: "Empresa y clave de firma", migrada: true },
  { id: "registradas", titulo: "Empresas registradas", migrada: false },
  { id: "api", titulo: "Claves de API", migrada: true },
  { id: "asistente", titulo: "Asistente de IA", migrada: false },
  { id: "accesos", titulo: "Accesos", migrada: true },
  { id: "instalacion", titulo: "Instalación", migrada: true },
] as const;

// El tope sale de la API (`maximo`); antes de que llegue se usa el texto sin cifra.
export function notaAccesos(maximo: number | null): string {
  const cuantos = maximo === null ? "Los últimos" : `Los ${maximo} últimos`;
  return `${cuantos} eventos de acceso; este registro solo se agrega, no se edita.`;
}

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

// «2026-10-18 14:32:05» (la API manda ISO con espacio, hora local de la instalacion) -> «18 oct 2026, 14:32».
// Es texto puro, sin zonas horarias. Lo que no tiene esa forma se muestra tal cual.
export function formatearFecha(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/.exec(iso);
  if (!m) return iso;
  const mes = MESES[Number(m[2]) - 1];
  if (!mes) return iso;
  return `${Number(m[3])} ${mes} ${m[1]}, ${m[4]}:${m[5]}`;
}

export const AYUDA_CONTRASENA =
  "De 10 a 128 caracteres. Anótela y entréguela en persona; la persona la cambiará al entrar.";
export const AYUDA_USUARIO = "Minúsculas, sin espacios; de 3 a 40 caracteres.";
export const AYUDA_DESBLOQUEAR = "Permite entrar de nuevo a una cuenta bloqueada por intentos fallidos.";
export const MINIMO_CONTRASENA = 10;
export const MAXIMO_CONTRASENA = 128;
export const TEXTO_CONTRASENA_INVALIDA = "La contraseña debe tener entre 10 y 128 caracteres.";

export function contrasenaValida(clave: string): boolean {
  const largo = [...clave].length;
  return largo >= MINIMO_CONTRASENA && largo <= MAXIMO_CONTRASENA;
}

// Texto de error de la contraseña mientras se escribe: nada si esta vacia (aun no se escribio) o si es valida.
export function errorDeContrasena(clave: string): string | null {
  return clave === "" || contrasenaValida(clave) ? null : TEXTO_CONTRASENA_INVALIDA;
}

export function puedeCrear(login: string, nombre: string, clave: string): boolean {
  return login.trim() !== "" && nombre.trim() !== "" && contrasenaValida(clave);
}
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
    fecha: formatearFecha(e.fecha_hora),
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
    propia:
      "Es su propia cuenta: se cerrará su sesión y perderá el acceso hasta que otro administrador la reactive.",
    boton: "Desactivar",
  },
  restablecer: {
    titulo: "Restablecer la contraseña",
    texto: (login: string) =>
      `La cuenta «${login}» pasará a la contraseña temporal que escribió y sus sesiones se cerrarán.`,
    propia:
      "Es su propia cuenta: se cerrará su sesión y tendrá que entrar de nuevo con la contraseña temporal.",
    boton: "Restablecer",
  },
} as const;
