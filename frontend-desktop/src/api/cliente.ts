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

const CON_TOKEN = new Set(["POST", "DELETE"]);

function detalleDe(cuerpo: unknown, estado: number): string {
  if (cuerpo && typeof cuerpo === "object") {
    const { detalle, detail } = cuerpo as { detalle?: unknown; detail?: unknown };
    if (typeof detalle === "string" && detalle) return detalle;
    if (typeof detail === "string" && detail) return detail;
  }
  return `El programa de Sílice respondió con el estado ${estado}.`;
}

export async function pedir<T = unknown>(ruta: string, opciones: OpcionesDePeticion = {}): Promise<T> {
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
  if (respuesta.status === 204) return undefined as T;
  return (await respuesta.json()) as T;
}
