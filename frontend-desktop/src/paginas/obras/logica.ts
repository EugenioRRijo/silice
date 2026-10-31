// Mesa de control, inicio de «Presupuestos y obras» (plan de modulos, MOD-4b). Los tipos son los de `GET /v1/obras/resumen`
// y `GET /v1/obras/pendientes` (`api/rutas/obras.py`): montos, indices y porcentajes llegan como texto con punto decimal y
// aqui solo se formatean (es-VE), nunca se convierten en numero ni se recalculan.
import { nombreDeResponsable } from "../../comun/responsable";
import { fechaEsVe, formatoEsVe } from "../../indicadores/formatoEsVe";
import type { IndicadorRespuesta } from "../../indicadores/tipos";
import type { Carga } from "../inicio/useCarga";
import { paginaPorId, usable } from "../../shell/rutas";
import { unirConY } from "../../shell/salida";
import { nombreDeCarpeta } from "../../api/carpetaYObra";
import type { ObraFilaRespuesta, SiguienteRespuesta } from "../../api/tipos";

// Una cifra de la franja: la forma del indicador Fiori mas una linea debajo («1 obra atrasada; la mas atrasada, …»).
export type CifraRespuesta = IndicadorRespuesta & { detalle: string | null };

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

export type Bloque = "cifras" | "obras" | "pendientes" | "por_aprobar" | "accesos";

// Que bloques se piden segun las acciones de la cuenta (diseno de modulos §12.3 y §12.6): el resumen exige `leer_proyecto`
// (arma y revisa), los pendientes de las obras `editar_hoja` (arma) y lo de aprobar (la cifra «Por aprobar» y los envios de
// todas las carpetas, Tarea 19) `aprobar_version` (arma y revisa); sin ninguno, los accesos del modulo (el administrador).
export function bloquesPedidos(acciones: readonly string[]): Bloque[] {
  const bloques: Bloque[] = [];
  if (acciones.includes("leer_proyecto")) bloques.push("cifras", "obras");
  if (acciones.includes("editar_hoja")) bloques.push("pendientes");
  if (acciones.includes("aprobar_version")) bloques.push("por_aprobar");
  return bloques.length > 0 ? bloques : ["accesos"];
}

// --- Tarea 19: lo que espera dictamen -------------------------------------------------------------------------------

// La cifra «Por aprobar» (`GET /v1/aprobaciones/resumen`): la forma de las cifras de la mesa y si se marca (desde 3 dias
// habiles de espera de la mas antigua; lo decide la API).
export type CifraPorAprobar = CifraRespuesta & { marcada: boolean };

// Una fila del indice de aprobaciones de la instalacion (`GET /v1/aprobaciones/pendientes`): lo que espera dictamen en
// todas las carpetas, lo mas antiguo primero. `caso` es el archivo de la carpeta («s2.db»); `proyecto`, el codigo de la
// obra en su carpeta. Fechas ISO; `total`, texto con punto decimal.
export interface EnvioPorAprobar {
  caso: string;
  envio_id: number;
  proyecto: string;
  obra: string;
  version: string;
  total: string;
  moneda: string;
  estado: string;
  enviado_por: string;
  enviado_el: string;
  nota: string;
}

// Un pendiente de la columna: el de la API o, si viene de un envio del indice, con lo que hace falta para abrirlo.
export interface PendienteDeLaMesa extends PendienteRespuesta {
  // Lineas que acompanan al texto (total, quien y cuando; la nota del envio).
  detalles?: string[];
  envio?: { caso: string; envio_id: number };
}

export interface GrupoDeLaMesa {
  clave: string;
  titulo: string;
  items: PendienteDeLaMesa[];
}

const GRUPO_APROBAR = { clave: "aprobar", titulo: "Aprobar" };
// El mismo verbo para toda fila del grupo «Aprobar», venga del indice o de la API («Ver el envío»).
const ABRIR_ENVIO = { texto: "Abrir el envío", pagina: "aprobar" };

// «4.876,56 Bs · enviada por Ana Pérez el 20/10/2026», con « · carpeta s2» si el envio es de otra carpeta.
export function lineaDelEnvio(envio: EnvioPorAprobar, casoActual: string | null): string {
  const base = `${formatoEsVe(envio.total)} ${envio.moneda} · enviada por ${nombreDeResponsable(envio.enviado_por)} el ${fechaEsVe(envio.enviado_el.slice(0, 10))}`;
  return envio.caso === casoActual ? base : `${base} · carpeta ${nombreDeCarpeta(envio.caso)}`;
}

function pendienteDeEnvio(envio: EnvioPorAprobar, casoActual: string | null): PendienteDeLaMesa {
  const nota = envio.nota.trim();
  return {
    obra: envio.proyecto,
    obra_nombre: envio.obra,
    texto: `${envio.version} espera dictamen`,
    accion: ABRIR_ENVIO,
    detalles: [lineaDelEnvio(envio, casoActual), ...(nota ? [`Nota: ${nota}`] : [])],
    envio: { caso: envio.caso, envio_id: envio.envio_id },
  };
}

// Un pendiente de la API que lleva a la pantalla de aprobar dice el mismo verbo que los del indice.
function conElVerbo(item: PendienteDeLaMesa): PendienteDeLaMesa {
  return item.accion.pagina === ABRIR_ENVIO.pagina ? { ...item, accion: ABRIR_ENVIO } : item;
}

// Los grupos de la columna de pendientes (Tarea 19, con los cambios por el diseno de modulos y los menores de su arbitro):
// - sin los pendientes de las obras (quien revisa: no tiene `editar_hoja`), un solo grupo «Aprobar» con todos los envios;
// - con ellos, los de la API tal cual y, en su grupo «Aprobar» (primero si la API no lo trae), los envios del indice de
//   todas las carpetas, con su total, quien y cuando. El «… espera dictamen» que la API dice de una obra de la carpeta
//   abierta lo reemplaza su fila del indice (que trae el envio que abrir). Sin saber cual es la abierta no se suma ninguno
//   (no se repite nada) y quedan los de la API.
export function gruposDeLaMesa(
  pendientes: PendientesRespuesta | null,
  envios: readonly EnvioPorAprobar[] | null,
  casoActual: string | null,
): GrupoDeLaMesa[] {
  const todos = envios ?? [];
  if (pendientes === null) return [{ ...GRUPO_APROBAR, items: todos.map((e) => pendienteDeEnvio(e, casoActual)) }];
  const delIndice = casoActual === null ? [] : todos;
  const obrasAqui = new Set(delIndice.filter((e) => e.caso === casoActual).map((e) => e.proyecto));
  const filas = delIndice.map((e) => pendienteDeEnvio(e, casoActual));
  const grupos: GrupoDeLaMesa[] = pendientes.grupos.map((g) => {
    if (g.clave !== GRUPO_APROBAR.clave) return g;
    const propios = g.items.filter((i) => !(i.accion.pagina === ABRIR_ENVIO.pagina && obrasAqui.has(i.obra))).map(conElVerbo);
    return { ...g, items: [...propios, ...filas] };
  });
  if (filas.length > 0 && !grupos.some((g) => g.clave === GRUPO_APROBAR.clave)) grupos.unshift({ ...GRUPO_APROBAR, items: filas });
  return grupos;
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
  return def !== undefined && usable(def, acciones, modoEntrega);
}

// Lo que pinta la columna de pendientes con las dos lecturas que la alimentan: los pendientes de las obras (con
// `editar_hoja`) y los envios por aprobar de todas las carpetas (con `aprobar_version`). La columna se oculta solo si las
// dos son prohibidas (o los envios no existen en la API); quien solo revisa ve el grupo «Aprobar» con los envios. Con los
// pendientes, un fallo de los envios no los tapa: se dice aparte (`falloEnvios`), y un 403 de los envios no se dice.
export function columnaDeLaMesa(
  pendientes: Carga<PendientesRespuesta>,
  envios: Carga<EnvioPorAprobar[]>,
  casoActual: string | null,
): { carga: Carga<{ grupos: GrupoDeLaMesa[] }>; falloEnvios: unknown } {
  const sinEnvios = envios.estado === "sin_permiso" || envios.estado === "no_disponible";
  if (pendientes.estado === "sin_permiso") {
    if (sinEnvios) return { carga: { estado: "sin_permiso", error: null }, falloEnvios: null };
    if (envios.estado !== "listo") return { carga: envios, falloEnvios: null };
    return { carga: { estado: "listo", datos: { grupos: gruposDeLaMesa(null, envios.datos, casoActual) } }, falloEnvios: null };
  }
  if (pendientes.estado !== "listo") return { carga: pendientes, falloEnvios: null };
  if (envios.estado === "cargando") return { carga: { estado: "cargando" }, falloEnvios: null };
  const lista = envios.estado === "listo" ? envios.datos : null;
  return {
    carga: { estado: "listo", datos: { grupos: gruposDeLaMesa(pendientes.datos, lista, casoActual) } },
    falloEnvios: envios.estado === "error" ? envios.error : null,
  };
}

// Los grupos con algo que decir, en el orden de la API.
export function gruposConItems<G extends GrupoRespuesta | GrupoDeLaMesa>(grupos: G[]): G[] {
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
