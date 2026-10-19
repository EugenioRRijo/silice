// Cliente minimo de la API de Sílice. La sesion viaja en una cookie HttpOnly que el navegador manda solo
// (credentials same-origin); el token anti-CSRF se guarda SOLO en memoria y va en X-Silice-CSRF en los
// POST y DELETE. Nada se escribe en localStorage ni en sessionStorage (RT-9).

export class ErrorDeApi extends Error {
  readonly estado: number;
  readonly detalle: string;
  readonly reintentarEnSegundos: number | null;

  constructor(estado: number, detalle: string, reintentarEnSegundos: number | null = null) {
    super(detalle);
    this.name = "ErrorDeApi";
    this.estado = estado;
    this.detalle = detalle;
    this.reintentarEnSegundos = reintentarEnSegundos;
  }
}

let csrf: string | null = null;

export function fijarCsrf(valor: string | null): void {
  csrf = valor;
}

export interface OpcionesDePeticion {
  metodo?: "GET" | "POST" | "DELETE";
  cuerpo?: FormData | object;
}

export interface OpcionesBinarias extends OpcionesDePeticion {
  // Nombre del archivo si la respuesta no trae Content-Disposition.
  respaldo?: string;
}

export interface DescargaBinaria {
  blob: Blob;
  nombre: string;
  // Cabeceras de la respuesta (p. ej. X-Silice-SHA256 de una entrega).
  cabeceras: Headers;
}

const CON_TOKEN = new Set(["POST", "DELETE"]);

function detalleDe(cuerpo: unknown, estado: number): string {
  if (cuerpo && typeof cuerpo === "object") {
    const { detalle, detail } = cuerpo as { detalle?: unknown; detail?: unknown };
    if (typeof detalle === "string" && detalle) return detalle;
    if (typeof detail === "string" && detail) return detail;
  }
  return `El programa de Sílice respondió con el estado ${estado}.`;
}

// Arma la peticion (token CSRF, cuerpo JSON o multipart), la manda y, si la API contesta con error, lanza
// ErrorDeApi con el `detalle` tal cual. Comparten esto `pedir` (JSON) y `pedirBinario` (archivos).
async function enviar(ruta: string, opciones: OpcionesDePeticion): Promise<Response> {
  const metodo = opciones.metodo ?? "GET";
  const cabeceras = new Headers();
  if (CON_TOKEN.has(metodo) && csrf) cabeceras.set("X-Silice-CSRF", csrf);

  let cuerpo: BodyInit | undefined;
  if (opciones.cuerpo instanceof FormData) {
    cuerpo = opciones.cuerpo; // el navegador pone el boundary del multipart
  } else if (opciones.cuerpo !== undefined) {
    cabeceras.set("Content-Type", "application/json");
    cuerpo = JSON.stringify(opciones.cuerpo);
  }

  let respuesta: Response;
  try {
    respuesta = await fetch(ruta, { method: metodo, headers: cabeceras, body: cuerpo, credentials: "same-origin" });
  } catch {
    throw new ErrorDeApi(0, "No se pudo hablar con el programa de Sílice. Compruebe que esté encendido.");
  }

  if (!respuesta.ok) {
    const contenido: unknown = await respuesta.json().catch(() => null);
    const espera = Number(respuesta.headers.get("Retry-After"));
    throw new ErrorDeApi(
      respuesta.status,
      detalleDe(contenido, respuesta.status),
      Number.isFinite(espera) && espera > 0 ? espera : null,
    );
  }
  return respuesta;
}

export async function pedir<T = unknown>(ruta: string, opciones: OpcionesDePeticion = {}): Promise<T> {
  const respuesta = await enviar(ruta, opciones);
  if (respuesta.status === 204) return undefined as T;
  return (await respuesta.json()) as T;
}

function quitarRuta(nombre: string): string {
  return nombre.split(/[\\/]/).pop() ?? nombre;
}

// Nombre de archivo de un Content-Disposition: prefiere filename* (RFC 5987, UTF-8) sobre filename. Solo queda
// el ultimo tramo del nombre: una ruta (../, C:\) no puede escaparse de la carpeta de descargas.
export function nombreDeDescarga(cabecera: string | null, respaldo: string): string {
  if (!cabecera) return respaldo;
  const extendido = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(cabecera);
  if (extendido) {
    try {
      const nombre = quitarRuta(decodeURIComponent(extendido[1].trim()));
      if (nombre) return nombre;
    } catch {
      // codificacion rota: se prueba con filename
    }
  }
  const simple = /filename\s*=\s*(?:"([^"]*)"|([^;]+))/i.exec(cabecera);
  const nombre = quitarRuta((simple?.[1] ?? simple?.[2] ?? "").trim());
  return nombre || respaldo;
}

// Respuestas que no son JSON (PDF, xlsx, zip): devuelve el contenido y el nombre que propone la API.
export async function pedirBinario(ruta: string, opciones: OpcionesBinarias = {}): Promise<DescargaBinaria> {
  const respuesta = await enviar(ruta, opciones);
  const blob = await respuesta.blob();
  const nombre = nombreDeDescarga(respuesta.headers.get("Content-Disposition"), opciones.respaldo ?? "descarga");
  return { blob, nombre, cabeceras: respuesta.headers };
}
