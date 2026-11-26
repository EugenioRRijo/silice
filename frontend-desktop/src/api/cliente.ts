// Cliente minimo de la API de Sílice. La sesion viaja en una cookie HttpOnly que el navegador manda solo
// (credentials same-origin); el token anti-CSRF se guarda SOLO en memoria y va en X-Silice-CSRF en los
// POST y DELETE. Nada se escribe en localStorage ni en sessionStorage (RT-9).

const MENSAJE_RESPUESTA_INVALIDA =
  "El servidor respondió algo que esta pantalla no esperaba. Vuelva a intentarlo; si se repite, avise al equipo de Sílice.";

function codigoPorEstado(estado: number): string {
  if (estado === 0) return "sin_conexion";
  if (estado === 401) return "no_autenticado";
  if (estado === 403) return "sin_permiso";
  if (estado === 404) return "no_encontrado";
  if (estado === 409) return "conflicto";
  if (estado === 422) return "datos_invalidos";
  if (estado >= 500 && estado < 600) return "error_del_servidor";
  return "error_http";
}

function codigoDe(cuerpo: unknown, estado: number): string {
  if (cuerpo && typeof cuerpo === "object") {
    const { codigo } = cuerpo as { codigo?: unknown };
    if (typeof codigo === "string" && codigo) return codigo;
  }
  return codigoPorEstado(estado);
}

function campoDe(cuerpo: unknown): string | undefined {
  if (cuerpo && typeof cuerpo === "object") {
    const { campo } = cuerpo as { campo?: unknown };
    if (typeof campo === "string" && campo) return campo;
  }
  return undefined;
}

export class ErrorDeApi extends Error {
  readonly estado: number;
  readonly detalle: string;
  readonly reintentarEnSegundos: number | null;
  // El cuerpo JSON de la respuesta tal cual (o null si no era JSON): algunas rutas traen campos extra, como `faltan`
  // en la importacion de la bascula. No se muestra: lo que se le dice a la persona es siempre `detalle`.
  readonly cuerpo: unknown;
  readonly codigo: string;
  readonly campo?: string;

  constructor(
    estado: number,
    detalle: string,
    reintentarEnSegundos: number | null = null,
    cuerpo: unknown = null,
    codigo?: string,
  ) {
    super(detalle);
    this.name = "ErrorDeApi";
    this.estado = estado;
    this.detalle = detalle;
    this.reintentarEnSegundos = reintentarEnSegundos;
    this.cuerpo = cuerpo;
    this.codigo = codigo ?? codigoDe(cuerpo, estado);
    const campo = campoDe(cuerpo);
    if (campo !== undefined) this.campo = campo;
  }
}

let csrf: string | null = null;
const oyentesDeSesion = new Set<() => void>();
// Bandera por episodio de 401: evita disparar N avisos seguidos y se limpia con la próxima respuesta exitosa (o al cambiar el CSRF).
let sesionPerdidaAvisada = false;

export function fijarCsrf(valor: string | null): void {
  csrf = valor;
  sesionPerdidaAvisada = false;
}

export function alPerderSesion(fn: () => void): () => void {
  oyentesDeSesion.add(fn);
  return () => {
    oyentesDeSesion.delete(fn);
  };
}

export interface OpcionesDePeticion<T = unknown> {
  metodo?: "GET" | "POST" | "PUT" | "DELETE";
  cuerpo?: FormData | object;
  // Para abortar una peticion que ya no sirve (un buscador que recibe otro texto). Un aborto se relanza tal cual
  // (AbortError), sin envolverlo en ErrorDeApi: no es un servidor caido (diseno de autocompletado, H-13).
  senal?: AbortSignal;
  // Analizador opcional en la frontera: valida o transforma el JSON recibido antes de entregarlo a la pantalla.
  leer?: (datos: unknown) => T;
}

export interface OpcionesBinarias extends Omit<OpcionesDePeticion, "leer"> {
  // Nombre del archivo si la respuesta no trae Content-Disposition.
  respaldo?: string;
}

export interface DescargaBinaria {
  blob: Blob;
  nombre: string;
  // Cabeceras de la respuesta (p. ej. X-Silice-SHA256 de una entrega).
  cabeceras: Headers;
}

const CON_TOKEN = new Set(["POST", "PUT", "DELETE"]);

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
async function enviar(ruta: string, opciones: Pick<OpcionesDePeticion, "metodo" | "cuerpo" | "senal">): Promise<Response> {
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
    respuesta = await fetch(ruta, {
      method: metodo,
      headers: cabeceras,
      body: cuerpo,
      credentials: "same-origin",
      signal: opciones.senal,
    });
  } catch (error) {
    if (typeof error === "object" && error !== null && (error as { name?: unknown }).name === "AbortError") throw error;
    throw new ErrorDeApi(0, "No se pudo hablar con el programa de Sílice. Compruebe que esté encendido.");
  }

  if (!respuesta.ok) {
    const contenido: unknown = await respuesta.json().catch(() => null);
    const espera = Number(respuesta.headers.get("Retry-After"));
    const error = new ErrorDeApi(
      respuesta.status,
      detalleDe(contenido, respuesta.status),
      Number.isFinite(espera) && espera > 0 ? espera : null,
      contenido,
    );
    if (respuesta.status === 401 && !sesionPerdidaAvisada && oyentesDeSesion.size > 0) {
      sesionPerdidaAvisada = true;
      for (const oyente of [...oyentesDeSesion]) oyente();
    }
    throw error;
  }
  sesionPerdidaAvisada = false;
  return respuesta;
}

export async function pedir<T>(ruta: string, opciones: OpcionesDePeticion<T> & { leer: (datos: unknown) => T }): Promise<T>;
export async function pedir<T = unknown>(ruta: string, opciones?: OpcionesDePeticion<T>): Promise<T>;
export async function pedir<T = unknown>(ruta: string, opciones: OpcionesDePeticion<T> = {}): Promise<T> {
  const respuesta = await enviar(ruta, opciones);
  if (!opciones.leer) {
    if (respuesta.status === 204) return undefined as T;
    return (await respuesta.json()) as T;
  }
  let datos: unknown = null;
  try {
    datos = respuesta.status === 204 ? undefined : await respuesta.json();
    return opciones.leer(datos);
  } catch {
    throw new ErrorDeApi(respuesta.status, MENSAJE_RESPUESTA_INVALIDA, null, datos, "respuesta_invalida");
  }
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
