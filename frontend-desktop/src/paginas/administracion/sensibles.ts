// Lógica pura de las pestañas «Empresa y clave de firma», «Claves de API» e «Instalación» (sin React).

export interface Sensible {
  permitida: boolean;
  motivo: string;
}

export interface EmpresaEstado {
  empresa: { nombre: string; rif: string; ciudad: string } | null;
  clave: { estado: string; huella: string } | null;
  sensible: Sensible;
}

export interface ClaveApi {
  id: number;
  etiqueta: string;
  nombre: string;
  estado: "vigente" | "revocada";
  ultimo_uso: string | null;
}

export interface Juego {
  nombre: string;
  motivo: string;
  bases: number;
}

export interface Pendiente {
  nombre: string;
  diferencias: string[];
  eventos: number;
}

export interface InstalacionEstado {
  red_local: boolean;
  direccion: string;
  puerto: number;
  api_activa: boolean;
  puerto_api: number;
  avisos: string[];
  respaldos: Juego[];
  pendientes: Pendiente[];
  sensible: Sensible;
}

export const MENSAJE_NO_COINCIDEN = "Las dos contraseñas no coinciden.";

export function contrasenasCoinciden(uno: string, dos: string): boolean {
  return uno === dos;
}

export function avisoDeRevocacion(conAviso: boolean): string {
  return conAviso
    ? "Clave revocada: los paquetes firmados con ella dejan de verificar."
    : "Clave revocada: los paquetes firmados con ella dejan de verificar. Sin la contraseña no hay aviso firmado: avise por teléfono a quienes reciben sus paquetes.";
}

export function bytesDeBase64(texto: string): Uint8Array<ArrayBuffer> {
  const binario = atob(texto);
  const bytes = new Uint8Array(binario.length);
  for (let i = 0; i < binario.length; i++) bytes[i] = binario.charCodeAt(i);
  return bytes;
}

export function textoDeRed(i: InstalacionEstado): string {
  return i.red_local
    ? `Red local: encendida en http://${i.direccion}:${i.puerto}`
    : `Red local: apagada (solo http://127.0.0.1:${i.puerto})`;
}

export function textoDeApi(i: InstalacionEstado): string {
  return `API: ${i.api_activa ? "activa" : "apagada"} (puerto ${i.puerto_api})`;
}
