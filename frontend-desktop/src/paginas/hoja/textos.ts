// El catálogo de ayudas de las pestañas del Presupuesto (Tarea 4 del plan F4, baja 25). Por qué existe: el texto largo que
// iba encima de cada pestaña pasa aquí, a un solo lugar, y se ve tras «¿Qué es esto?» (`AyudaDePestana`). Lo lee cada
// pestaña por su id; F6 lo convertirá en el panel de ayuda. Los títulos de las pestañas viven en `logica.ts` (`PESTANAS`),
// que es lo que ve la persona en la lista; aquí solo está la explicación. Desde la Tarea 5 lleva también los textos de la
// franja del paso (`pasoDelPresupuesto.ts`) y de su botón.
import type { AccionDelPresupuesto } from "./pasoDelPresupuesto";
import type { PestanaId } from "./logica";

const SE_APLICAN = "Los cambios se aplican al borrador cuando deja de escribir; no se guardan como versión hasta que lo pida.";

export interface AyudaDePestana {
  // Lo que ve cualquiera que abra la pestaña.
  general: string;
  // Lo que solo sirve a quien puede editar: cómo se escribe y cuándo se aplica (F4 2b: quien revisa no ve controles).
  alEditar: string;
  // La pestaña tiene cifras que se escriben: quien edita ve `AYUDA_CIFRAS` a la vista, no plegada (Tarea 5, menor de la 4).
  cifras: boolean;
}

export const AYUDAS: Record<PestanaId, AyudaDePestana> = {
  // La explicación de las tablas llega con la vista (`vista.ayuda`): aquí solo va lo de escribir.
  espacio: {
    general: "",
    alEditar: `En «Vértices» cada punto se escribe x,y,z: ahí la coma separa las coordenadas y los decimales van con punto (0,0,0; 2.5,0,0). ${SE_APLICAN}`,
    cifras: true,
  },
  partidas: {
    general:
      "Las cantidades salen del espacio o de las partidas que agrega con «Agregar partida», y los precios de la composición de cada partida.",
    alEditar: `Aquí se edita la cantidad: una cantidad escrita a mano se marca en el Estado y puede volver a la calculada. ${SE_APLICAN}`,
    cifras: true,
  },
  apu: {
    general: "El análisis de precio de la partida elegida: las líneas de cada rubro, su subtotal y el cierre de la partida.",
    alEditar: `Se edita la cantidad de cada línea y el rendimiento, y se puede agregar una línea (un insumo de la lista de la versión o uno nuevo con su precio) o quitar otra, en la copia de esta versión: el catálogo no cambia. ${SE_APLICAN}`,
    cifras: true,
  },
  plan: {
    general: "La matriz reparte cada partida entre los períodos del plan; la curva de inversión y el punto de equilibrio se calculan con ese reparto.",
    alEditar: `Reparta cada partida entre los períodos: cada fila debe sumar exactamente 1. Los montos, los acumulados y los porcentajes de la curva se calculan. ${SE_APLICAN}`,
    cifras: true,
  },
  precios: {
    general:
      "Lista, referencia, fecha, moneda y tasa de cada insumo, su origen y cuánto valor perdió hasta hoy (erosión). Una cotización (con su proveedor, número y fecha) vale solo para esta obra y prevalece sobre la lista global hasta que se retire.",
    alEditar: "",
    cifras: false,
  },
  revision: {
    general: "El informe se genera siempre, con todas las reglas, sobre el borrador vigente.",
    alEditar: "",
    cifras: false,
  },
  ajustes: {
    general: "Los parámetros de costo del borrador. Cambiarlos recalcula todos los APU y el total.",
    alEditar: "Los cambios se aplican al borrador cuando deja de escribir y no se guardan como versión hasta que lo pida.",
    cifras: true,
  },
};

// La franja del Presupuesto (Tarea 5): lo que dice cada regla de `pasoDelPresupuesto`. `n` llega ya en es-VE.
export const TEXTOS_DEL_PASO = {
  primeraPartida: "Agregue la primera partida",
  sinGuardar: (n: string, uno: boolean) => (uno ? "Hay 1 cambio sin guardar" : `Hay ${n} cambios sin guardar`),
  graves: (n: string, uno: boolean) =>
    uno ? "Hay 1 hallazgo grave: revíselo antes de enviar" : `Hay ${n} hallazgos graves: revíselos antes de enviar`,
  devuelta: (version: string) => `La versión ${version} fue devuelta: corrija lo observado`,
  enAprobacion: (version: string) => `La versión ${version} espera dictamen`,
  enviar: (version: string) => `Envíe la versión ${version} a aprobación`,
} as const;

// El botón de la franja. «Agregar la primera partida» no repite el nombre de «Agregar partida» de encima de la tabla: dos
// botones con el mismo nombre en la misma pantalla no se distinguen con un lector de pantalla.
export function textoDelBoton(accion: AccionDelPresupuesto, enBlanco: boolean): string {
  switch (accion) {
    case "agregar_partida":
      return "Agregar la primera partida";
    case "guardar":
      return enBlanco ? "Guardar primera versión…" : "Guardar versión…";
    case "ver_revision":
      return "Ir a Revisión";
    case "version_nueva":
      return "Hacer una versión nueva";
    case "enviar_a_aprobacion":
      return "Enviar a aprobación…";
  }
}

// Tarea 5b: el IVA debajo del total del presupuesto. La fuente de la alícuota llega del servidor (`fuente_alicuota`) y se
// cita en la ayuda «¿Qué es esto?», no en una nota suelta.
export const TEXTOS_DEL_IVA = {
  region: "IVA del presupuesto",
  subtotal: "Subtotal",
  iva: (porcentaje: string) => `IVA (${porcentaje} %)`,
  totalConIva: "Total con IVA",
  explicacion:
    "El IVA se calcula sobre el total del presupuesto, nunca dentro del análisis de precio: el precio unitario y el total del presupuesto son costo sin IVA.",
  fuente: (porcentaje: string, fuente: string) => `Alícuota: ${porcentaje} %. Fuente: ${fuente}.`,
} as const;
