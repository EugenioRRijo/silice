// Lógica pura del Resumen de la obra (Tarea 2 del plan F4). Montos, índices y porcentajes llegan como texto con punto
// decimal (`GET /v1/obras/resumen`, `api/rutas/obras.py`) y aquí solo se formatean (es-VE), nunca se convierten en número
// ni se recalculan.
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { paginaPorId, usable } from "../../shell/rutas";
import type { ObraFilaRespuesta } from "../../api/tipos";

// «30,0 % de 37,5 %»: lo avanzado contra lo planificado al corte. Sin alguno de los dos no hay avance que decir.
export function etiquetaAvance(real: string | null, plan: string | null): string {
  if (real === null || plan === null) return "Sin avance";
  return `${formatoEsVe(real)} % de ${formatoEsVe(plan)} %`;
}

// Un boton de la mesa solo se ofrece si su pantalla existe en el registro y la cuenta puede usarla: la de aprobar aun no
// existe y quien revisa no abre la Hoja ni el Control (la API lo negaria igual).
export function pantallaVisible(pagina: string, acciones: readonly string[], modoEntrega: boolean): boolean {
  const def = paginaPorId(pagina);
  return def !== undefined && usable(def, acciones, modoEntrega);
}

// «4.876,56 Bs»; una obra sin version todavia no tiene total.
export function textoTotal(total: string | null, moneda: string): string | null {
  return total === null ? null : `${formatoEsVe(total)} ${moneda}`;
}

// Lo que la franja del Resumen dice de la obra (Tarea 2 del plan F4): «Te falta» si el servidor dice qué pasa, «Siguiente
// paso» si solo trae la acción, y nada si no trae ninguna. La acción es la que da el servidor (`siguiente`); si la cuenta
// puede abrir su pantalla lo decide quien pinta (`pantallaVisible`).
export interface Paso {
  tipo: "falta" | "siguiente";
  texto: string;
  accion: { texto: string; pagina: string } | null;
}

export function pasoDeLaObra(obra: ObraFilaRespuesta): Paso | null {
  if (obra.que_pasa) return { tipo: "falta", texto: obra.que_pasa, accion: obra.siguiente };
  if (obra.siguiente !== null) return { tipo: "siguiente", texto: obra.siguiente.texto, accion: obra.siguiente };
  return null;
}
