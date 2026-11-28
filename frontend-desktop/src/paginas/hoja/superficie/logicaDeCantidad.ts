// Lógica pura de la celda de cantidad de la grilla del Presupuesto (lote B1-5, ficha-b1 §1.10 pruebas 5 y 6). El archivo no
// se llama celdaDeCantidad.ts porque en Windows chocaría con CeldaDeCantidad.tsx al resolver `./CeldaDeCantidad`.
// Decide, sin React ni DOM, qué teclas abren la edición, qué hacen Enter, Esc y Tab con el campo abierto y de quién es el
// rechazo del servidor. Las reglas de teclado son las de la grilla (`eventoDesdeTecla`: sin Ctrl, Alt ni Meta, sin
// eventos ya prevenidos, sin composición de teclas); aquí solo se traducen a lo que hace una celda.
import { eventoDesdeTecla } from "../../../comun/logicaGrilla";
import type { EntradaDeTeclado } from "../../../comun/logicaGrilla";
import { FRASES_DE_RECHAZO } from "../logicaSecciones";

// Solo importan Enter, F2, Esc, Tab y los caracteres: la forma de la grilla (una fila y una columna) no interviene.
const CONTEXTO = { filas: 1, columnas: 1, valorCelda: "" } as const;

export interface AperturaPorTecla {
  // El carácter que reemplaza al texto de la celda (se escribió sobre ella), o null si se abre con el texto que tiene.
  texto: string | null;
}

// Qué hace una tecla pulsada sobre la celda en reposo: F2 y Enter abren con lo que hay; un carácter imprimible abre y
// reemplaza el texto por ese carácter. Cualquier otra (flechas, Tab, Esc, Inicio, Fin) es de la grilla.
export function aperturaPorTecla(tecla: EntradaDeTeclado): AperturaPorTecla | null {
  const evento = eventoDesdeTecla(tecla, CONTEXTO);
  if (evento === null) return null;
  if (evento.tipo === "f2") return { texto: null };
  if (evento.tipo === "enter" && evento.componiendo !== true) return { texto: null };
  if (evento.tipo === "caracter" && evento.componiendo !== true) return { texto: evento.caracter };
  return null;
}

export type AccionEnCampo = "confirmar-y-bajar" | "restaurar" | "confirmar-y-seguir";

// Qué hace una tecla pulsada dentro del campo abierto. Solo Enter, Esc y Tab suben a la celda; las flechas, Inicio, Fin y
// las letras son del campo y no son una acción.
export function accionEnCampo(tecla: EntradaDeTeclado): AccionEnCampo | null {
  const evento = eventoDesdeTecla(tecla, CONTEXTO);
  if (evento === null) return null;
  if (evento.tipo === "enter" && evento.componiendo !== true) return "confirmar-y-bajar";
  if (evento.tipo === "escape" && evento.componiendo !== true) return "restaurar";
  if (evento.tipo === "tab") return "confirmar-y-seguir";
  return null;
}

// El rechazo del servidor (un 422) es de la celda cuando su mensaje dice la fila de esta celda (`n`, desde 1, como en el
// servidor). Un conflicto (409) o cualquier otro fallo no marcan una celda: los dice el aviso de la sección. Devuelve el
// mismo objeto que recibió, para que quien lo compare sepa si es un rechazo nuevo aunque repita el texto.
export function rechazoDeLaCelda<E extends { tipo: string; ubicacion: number | null }>(error: E | null, n: number): E | null {
  return error !== null && error.tipo === "rechazo" && error.ubicacion === n ? error : null;
}

const UBICACION = /^presupuesto, fila \d+ \([^)]*\): /;
const CAMPO = /^cantidad: /;

// El mensaje del servidor sin lo que ya dice la celda: la ubicación («presupuesto, fila 2 (AF-SALIDA): »), el nombre del
// campo y la frase que la clásica agrega tras el error (esa la dice el aviso de la sección). Queda lo que hay que corregir.
export function textoDeRechazoDeCelda(mensaje: string): string {
  const sinFrase = mensaje.endsWith(` ${FRASES_DE_RECHAZO.cantidades}`)
    ? mensaje.slice(0, -(FRASES_DE_RECHAZO.cantidades.length + 1))
    : mensaje;
  const limpio = sinFrase.replace(UBICACION, "").replace(CAMPO, "");
  if (limpio === "") return mensaje;
  return limpio.charAt(0).toUpperCase() + limpio.slice(1);
}
