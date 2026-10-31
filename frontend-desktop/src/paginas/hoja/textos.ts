// El catálogo de ayudas de las pestañas del Presupuesto (Tarea 4 del plan F4, baja 25). Por qué existe: el texto largo que
// iba encima de cada pestaña pasa aquí, a un solo lugar, y se ve tras «¿Qué es esto?» (`AyudaDePestana`). Lo lee cada
// pestaña por su id; F6 lo convertirá en el panel de ayuda. Los títulos de las pestañas viven en `logica.ts` (`PESTANAS`),
// que es lo que ve la persona en la lista; aquí solo está la explicación.
import { AYUDA_CIFRAS } from "../../indicadores/cifraEscrita";
import type { PestanaId } from "./logica";

const SE_APLICAN = "Los cambios se aplican al borrador cuando deja de escribir; no se guardan como versión hasta que lo pida.";

export interface AyudaDePestana {
  // Lo que ve cualquiera que abra la pestaña.
  general: string;
  // Lo que solo sirve a quien puede editar: cómo se escribe y cuándo se aplica (F4 2b: quien revisa no ve controles).
  alEditar: string;
}

export const AYUDAS: Record<Exclude<PestanaId, "trazabilidad">, AyudaDePestana> = {
  // La explicación de las tablas llega con la vista (`vista.ayuda`): aquí solo va lo de escribir.
  espacio: {
    general: "",
    alEditar: `${AYUDA_CIFRAS} En «Vértices» cada punto se escribe x,y,z: ahí la coma separa las coordenadas y los decimales van con punto (0,0,0; 2.5,0,0). ${SE_APLICAN}`,
  },
  partidas: {
    general:
      "Las cantidades salen del espacio o de las partidas que agrega con «Agregar partida», y los precios de la composición de cada partida.",
    alEditar: `Aquí se edita la cantidad: una cantidad escrita a mano se marca en el Estado y puede volver a la calculada. ${AYUDA_CIFRAS} ${SE_APLICAN}`,
  },
  apu: {
    general: "El análisis de precio de la partida elegida: las líneas de cada rubro, su subtotal y el cierre de la partida.",
    alEditar: `Se edita la cantidad de cada línea y el rendimiento, y se puede agregar una línea (un insumo de la lista de la versión o uno nuevo con su precio) o quitar otra, en la copia de esta versión: el catálogo no cambia. ${AYUDA_CIFRAS} ${SE_APLICAN}`,
  },
  plan: {
    general: "La matriz reparte cada partida entre los períodos del plan; la curva de inversión y el punto de equilibrio se calculan con ese reparto.",
    alEditar: `Reparta cada partida entre los períodos: cada fila debe sumar exactamente 1. Los montos, los acumulados y los porcentajes de la curva se calculan. ${AYUDA_CIFRAS} ${SE_APLICAN}`,
  },
  precios: {
    general:
      "Lista, referencia, fecha, moneda y tasa de cada insumo, su origen y cuánto valor perdió hasta hoy (erosión). Una cotización (con su proveedor, número y fecha) vale solo para este proyecto y prevalece sobre la lista global hasta que se retire.",
    alEditar: "",
  },
  revision: {
    general: "El informe se genera siempre, con todas las reglas, sobre el borrador vigente.",
    alEditar: "",
  },
  ajustes: {
    general: "Los parámetros de costo del borrador. Cambiarlos recalcula todos los APU y el total.",
    alEditar: `${AYUDA_CIFRAS} Los cambios se aplican al borrador cuando deja de escribir y no se guardan como versión hasta que lo pida.`,
  },
};
