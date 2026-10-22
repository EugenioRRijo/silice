// Logica pura de Administracion (pestanas Cuentas, Accesos, Empresas registradas y Asistente de IA): tipos del
// contrato de /v1/cuentas, /v1/accesos, /v1/admin/empresas-registradas y /v1/admin/asistente, los rotulos de
// Streamlit (ui/paginas/administracion.py) y las filas de las tablas. No guarda ningun secreto.
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
  { id: "registradas", titulo: "Empresas registradas", migrada: true },
  { id: "api", titulo: "Claves de API", migrada: true },
  { id: "asistente", titulo: "Asistente de IA", migrada: true },
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

// --- Empresas registradas (claves publicas de otras empresas, spec S3 §7) ---

export interface Registrada {
  id: number;
  empresa: string;
  huella: string;
  estado: string;
  comprobada_con: string;
  metodo: string;
}

// Como se comprobo la huella: `valor` es lo que se guarda, `etiqueta` lo que se lee (los dos los da la API).
export interface MetodoDeComprobacion {
  valor: string;
  etiqueta: string;
}

export interface RegistradasRespuesta {
  registradas: Registrada[];
  metodos: MetodoDeComprobacion[];
}

// Lo que trae el `.silice-clave` elegido: la empresa que declara y la huella que CALCULA la API.
export interface ClaveLeida {
  empresa: string;
  huella: string;
}

export const MENSAJE_REVOCAR_SIN_MOTIVO = "Escriba el motivo o suba el aviso de revocación.";

export function filasDeRegistradas(
  registradas: readonly Registrada[],
  metodos: readonly MetodoDeComprobacion[],
): FilaDensa[] {
  const etiquetas = new Map(metodos.map((m) => [m.valor, m.etiqueta]));
  return registradas.map((r) => ({
    id: String(r.id),
    empresa: r.empresa,
    huella: r.huella,
    estado: r.estado,
    comprobada_con: r.comprobada_con,
    metodo: etiquetas.get(r.metodo) ?? r.metodo,
  }));
}

// Como en la clasica: sin aviso firmado, revocar exige el motivo escrito.
export function puedeRevocarRegistrada(motivo: string, hayAviso: boolean): boolean {
  return hayAviso || motivo.trim() !== "";
}

// La fecha del reloj local en AAAA-MM-DD (el valor de un <input type="date">), sin pasar por UTC.
export function fechaDeHoy(ahora: Date = new Date()): string {
  const dos = (n: number) => String(n).padStart(2, "0");
  return `${ahora.getFullYear()}-${dos(ahora.getMonth() + 1)}-${dos(ahora.getDate())}`;
}

// --- Asistente de IA (S4 §3.1, §8.3) ---

export interface AsistenteEstado {
  activo: boolean;
  proveedor: string;
  proveedores: { valor: string; etiqueta: string }[];
  modelo_claude: string;
  modelo_local: string;
  anfitrion_ollama: string;
  // Texto decimal de la API («2.50»): la interfaz no lo convierte en numero.
  tope_usd: string;
  // Solo los 4 ultimos caracteres («…5678»): la clave nunca llega al navegador.
  clave_registrada: string | null;
  clave_guardada: boolean;
  pide_contrasena: boolean;
  falta_el_componente: string | null;
  aviso_de_nube: string;
  sensible: { permitida: boolean; motivo: string };
}

export interface ResultadoAsistente {
  mensaje: string;
  estado: AsistenteEstado;
}

// La linea «Clave registrada: …» de la clasica (`_seccion_clave`).
export function textoDeLaClaveDeIA(e: AsistenteEstado): string {
  if (e.clave_registrada === null && !e.activo && e.clave_guardada) {
    return "Clave registrada: hay una guardada, pero no se carga mientras el asistente esté apagado (se carga al activarlo).";
  }
  if (e.clave_registrada === null && e.pide_contrasena) {
    return "Clave registrada: hay una en el respaldo cifrado (el almacén de credenciales no la tiene); escriba la contraseña del respaldo para cargarla.";
  }
  return `Clave registrada: ${e.clave_registrada ?? "ninguna"}`;
}

// El tope en el campo de texto con coma decimal (la API acepta coma o punto). Solo cambia el separador del texto.
export function topeParaEditar(tope: string): string {
  return tope.replace(".", ",");
}
