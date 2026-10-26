// Mesa de control, inicio de «Presupuestos y obras» (plan de modulos, MOD-4b). Los tipos son los de `GET /v1/obras/resumen`
// y `GET /v1/obras/pendientes` (`api/rutas/obras.py`): montos, indices y porcentajes llegan como texto con punto decimal y
// aqui solo se formatean (es-VE), nunca se convierten en numero ni se recalculan.
import { fechaEsVe, formatoEsVe } from "../../indicadores/formatoEsVe";
import type { IndicadorRespuesta } from "../../indicadores/tipos";
import { paginaPorId, visible } from "../../shell/rutas";
import { unirConY } from "../../shell/salida";

// Una cifra de la franja: la forma del indicador Fiori mas una linea debajo («1 obra atrasada; la mas atrasada, …»).
export type CifraRespuesta = IndicadorRespuesta & { detalle: string | null };

export interface SiguienteRespuesta {
  texto: string;
  // El id de la pantalla (rutas.ts) a la que lleva.
  pagina: string;
}

export interface ConversionRespuesta {
  obra: string;
  // La moneda de la obra convertida.
  moneda: string;
  // Bs por USD.
  tasa: string;
  // El corte de la obra (ISO).
  fecha: string;
  // La fecha valor de la tasa del BCV que se uso (ISO): la que se declara.
  fecha_tasa: string;
}

export type Etapa = "en_elaboracion" | "en_aprobacion" | "aprobada" | "en_ejecucion" | "atrasada";

export interface ObraFilaRespuesta {
  codigo: string;
  nombre: string;
  cliente: string;
  etapa: Etapa;
  etapa_texto: string;
  version: string | null;
  total: string | null;
  moneda: string;
  avance_real: string | null;
  avance_plan: string | null;
  que_pasa: string | null;
  siguiente: SiguienteRespuesta | null;
}

export interface ResumenObrasRespuesta {
  // La moneda en que se sumo (null si no se sumo nada).
  moneda: string | null;
  hoy: string;
  cifras: CifraRespuesta[];
  conversiones: ConversionRespuesta[];
  fuera_de_suma: string[];
  obras: ObraFilaRespuesta[];
}

export interface PendienteRespuesta {
  // El codigo de la obra.
  obra: string;
  obra_nombre: string;
  texto: string;
  accion: SiguienteRespuesta;
}

export interface GrupoRespuesta {
  clave: string;
  titulo: string;
  items: PendienteRespuesta[];
}

export interface PendientesRespuesta {
  grupos: GrupoRespuesta[];
}

export type Bloque = "cifras" | "obras" | "pendientes" | "accesos";

// Que bloques se piden segun las acciones de la cuenta (diseno de modulos §12.3): el resumen exige `leer_proyecto` (arma y
// revisa) y los pendientes `editar_hoja` (arma); sin ninguno de los dos, los accesos del modulo (el administrador).
export function bloquesPedidos(acciones: readonly string[]): Bloque[] {
  const bloques: Bloque[] = [];
  if (acciones.includes("leer_proyecto")) bloques.push("cifras", "obras");
  if (acciones.includes("editar_hoja")) bloques.push("pendientes");
  return bloques.length > 0 ? bloques : ["accesos"];
}

// «30,0 % de 37,5 %»: lo avanzado contra lo planificado al corte. Sin alguno de los dos no hay avance que decir.
export function etiquetaAvance(real: string | null, plan: string | null): string {
  if (real === null || plan === null) return "Sin avance";
  return `${formatoEsVe(real)} % de ${formatoEsVe(plan)} %`;
}

// Un boton de la mesa solo se ofrece si su pantalla existe en el registro y la cuenta puede usarla: la de aprobar aun no
// existe y quien revisa no abre la Hoja ni el Control (la API lo negaria igual).
export function pantallaVisible(pagina: string, acciones: readonly string[], modoEntrega: boolean): boolean {
  const def = paginaPorId(pagina);
  return def !== undefined && visible(def, acciones, modoEntrega);
}

// Los grupos con algo que decir, en el orden de la API.
export function gruposConItems(grupos: GrupoRespuesta[]): GrupoRespuesta[] {
  return grupos.filter((g) => g.items.length > 0);
}

// «C convertida a Bs con la tasa del BCV de 40,00 del 22/10/2026»: la fecha es la de la tasa, no la del corte.
export function textoConversion(conversion: ConversionRespuesta, monedaDeLaSuma: string | null): string {
  const destino = monedaDeLaSuma ?? "la moneda de la carpeta";
  return `${conversion.obra} convertida a ${destino} con la tasa del BCV de ${formatoEsVe(conversion.tasa)} del ${fechaEsVe(conversion.fecha_tasa)}`;
}

// «Sin tasa del BCV: C no se sumó»; con varias, «C y D no se sumaron».
export function textoFueraDeSuma(obras: readonly string[]): string | null {
  if (obras.length === 0) return null;
  return `Sin tasa del BCV: ${unirConY(obras)} ${obras.length === 1 ? "no se sumó" : "no se sumaron"}`;
}

// «4.876,56 Bs»; una obra sin version todavia no tiene total.
export function textoTotal(total: string | null, moneda: string): string | null {
  return total === null ? null : `${formatoEsVe(total)} ${moneda}`;
}
