// Zoom de la hoja de Excel (Univer). Dos factores se combinan: el zoom propio de la hoja (50 a 300 %, de 10 en 10,
// control de la barra de la hoja) y el factor del tamaño de letra de la interfaz (1, 1,25 o 1,5). La razón que se le
// pide a Univer es el producto de los dos: zoom_efectivo = zoom_propio × factor. Univer acepta de 0,1 a 4 (la facade
// recorta ahí), así que 300 % con «Muy grande» (4,5) se queda en 4.
//
// El zoom propio es una preferencia de pantalla, no un dato de la obra: se guarda en localStorage con una clave propia
// y todo acceso va en try/catch (sin almacenamiento la hoja funciona al 100 %).
import { TAMANOS_DE_LETRA, tamanoAplicado } from "../comun/preferenciaDeLetra";

export const ZOOM_MINIMO = 50;
export const ZOOM_MAXIMO = 300;
export const ZOOM_PASO = 10;
export const ZOOM_INICIAL = 100;
export const RAZON_MAXIMA_UNIVER = 4;
export const RAZON_MINIMA_UNIVER = 0.1;
export const CLAVE_ZOOM_HOJA = "silice.zoom-hoja";

// Cuánto hay que acumular de rueda para dar un paso: una muesca de ratón (100) da uno; un pellizco de trackpad
// (muchos deltas pequeños) suma hasta llegar.
const UMBRAL_DE_RUEDA = 40;

export function ajustarZoom(valor: number): number {
  if (!Number.isFinite(valor)) return ZOOM_INICIAL;
  const aPaso = Math.round(valor / ZOOM_PASO) * ZOOM_PASO;
  return Math.min(ZOOM_MAXIMO, Math.max(ZOOM_MINIMO, aPaso));
}

// El factor del tamaño de letra que de verdad se ve (el que dejó `aplicarTamanoLetra` en la raíz).
export function factorDeLetra(): number {
  const vigente = tamanoAplicado();
  return TAMANOS_DE_LETRA.find((t) => t.valor === vigente)?.escala ?? 1;
}

// Razón que se le pide a Univer (1 = 100 %), con tres decimales y dentro de lo que Univer admite.
export function razonEfectiva(zoomPropio: number, factor: number): number {
  const razon = Math.round((zoomPropio / 100) * factor * 1000) / 1000;
  return Math.min(RAZON_MAXIMA_UNIVER, Math.max(RAZON_MINIMA_UNIVER, razon));
}

export function leerZoomHoja(): number {
  try {
    const crudo = window.localStorage.getItem(CLAVE_ZOOM_HOJA);
    if (crudo === null || !/^\d{2,3}$/.test(crudo)) return ZOOM_INICIAL;
    const n = Number(crudo);
    return n >= ZOOM_MINIMO && n <= ZOOM_MAXIMO && n % ZOOM_PASO === 0 ? n : ZOOM_INICIAL;
  } catch {
    return ZOOM_INICIAL;
  }
}

export function guardarZoomHoja(zoom: number): void {
  try {
    window.localStorage.setItem(CLAVE_ZOOM_HOJA, String(zoom));
  } catch {
    // Sin almacenamiento el zoom vale para esta pantalla y no se recuerda.
  }
}

// Rueda hacia arriba (delta negativo) acerca; hacia abajo aleja. `deltaMode` del WheelEvent: 0 pixeles, 1 lineas (Firefox
// da ±3 por muesca), 2 paginas; se lleva todo a pixeles para comparar con el umbral.
const PIXELES_POR_LINEA = 40;
const PIXELES_POR_PAGINA = 800;
export function pasoDeRueda(acumulado: number, delta: number, deltaMode = 0): { paso: number; resto: number } {
  const px = deltaMode === 1 ? delta * PIXELES_POR_LINEA : deltaMode === 2 ? delta * PIXELES_POR_PAGINA : delta;
  const total = acumulado + px;
  if (Math.abs(total) >= UMBRAL_DE_RUEDA) return { paso: total < 0 ? 1 : -1, resto: 0 };
  return { paso: 0, resto: total };
}

// Subir solo tiene sentido si cambia lo dibujado: no en el tope propio y no cuando Univer ya esta en su tope (con
// «Muy grande», de 270 % en adelante la razon es 4 y un paso mas no se veria).
export function puedeSubirZoom(zoom: number, factor: number): boolean {
  if (zoom >= ZOOM_MAXIMO) return false;
  return razonEfectiva(zoom + ZOOM_PASO, factor) !== razonEfectiva(zoom, factor);
}

// Cada pedido de zoom a Univer ejecuta un comando que vuelve a avisar un cambio: sin tope, una escala que nunca iguala a la
// pedida (contenedor de tamano 0, otra version de Univer) haria un ciclo a 60 Hz. Se reintenta pocas veces por racha.
export const MAX_REINTENTOS_ZOOM = 3;
const TOLERANCIA_DE_ESCALA = 0.001;

export function debeReaplicarZoom(entrada: {
  escalaDibujada: number | undefined;
  razonVigente: number;
  intentos: number;
}): boolean {
  const { escalaDibujada, razonVigente, intentos } = entrada;
  if (escalaDibujada === undefined || !Number.isFinite(escalaDibujada)) return false;
  if (Math.abs(escalaDibujada - razonVigente) <= TOLERANCIA_DE_ESCALA) return false;
  return intentos < MAX_REINTENTOS_ZOOM;
}
