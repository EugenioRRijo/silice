// Logica pura de «Elaborar un presupuesto» (UC-01): arma cuerpos, textos y filas con lo que manda la API. No calcula
// ni redondea montos (llegan como texto); el unico numero es el puntaje de una propuesta, que se muestra a 2 decimales.
// Las cifras se leen en es-VE con todos los decimales que trae la API (VB-6).
import { ErrorDeApi } from "../../api/cliente";
import type { FilaDensa } from "../../comun/TablaDensa";
import { fechaEsVe, formatoEsVe } from "../../indicadores/formatoEsVe";
import type {
  CalculoRespuesta,
  CuerpoCalculo,
  Dominio,
  ItemComputo,
  PartidaParaLlevar,
  PendienteConPropuestas,
  PropuestaPartida,
  RendimientoPorDeclarar,
  RendimientosPorDeclararRespuesta,
} from "./tipos";

// Valores de core/contracts/dominio.py.
export const DOMINIOS: Dominio[] = ["civil", "telecom", "industrial", "sistemas"];
export const AVISO_SIN_PARTIDAS_CIVILES =
  "El catálogo no tiene partidas del dominio civil todavía (o la base de datos no se pudo leer; revise el mensaje " +
  "de error de arriba, si lo hay): cargue primero un presupuesto civil (por ejemplo, sembrando la línea base en la " +
  "página de Actualización) antes de extraer un cómputo civil.";
export const TEXTO_PENDIENTES =
  "Estos ítems del cómputo no tienen partida en el catálogo: el presupuesto se elaboró sin ellos y el informe de " +
  "auditoría los declara.";
export const ERROR_COMPUTO_CAMBIO =
  "El cómputo cambió después de esta elaboración: extráigalo de nuevo y vuelva a elaborar el presupuesto antes de " +
  "aceptar una propuesta.";
export const ERROR_SIN_ITEMS_RENDIMIENTO = "Extraiga de nuevo el cómputo antes de registrar el rendimiento.";
export const TEXTO_RENDIMIENTOS =
  "Estas partidas no tienen rendimiento estimado vigente a la fecha del presupuesto: se propone el del histórico " +
  "con su dispersión. Declare si es estimado o medido para registrarlo y volver a elaborar.";

export interface SeleccionCivil {
  concreto: string;
  encofrado: string;
  excavacion: string;
  tuberia: string;
  // null = sin relleno (casilla desmarcada).
  relleno: string | null;
}

// El JSON `codigos` que espera POST /computos/civil (adapters/civil/reglas.py).
export function mapeoCodigos(s: SeleccionCivil): Record<string, string> {
  const mapeo: Record<string, string> = {
    concreto: s.concreto,
    encofrado: s.encofrado,
    excavacion: s.excavacion,
    tuberia: s.tuberia,
  };
  if (s.relleno !== null) mapeo.relleno = s.relleno;
  return mapeo;
}

// Los items se reenvian tal cual salieron de /computos (RA-5): solo cambia el codigo del aceptado.
export function aceptarPropuesta(
  items: ItemComputo[],
  pendiente: Pick<ItemComputo, "origen_id" | "codigo_partida">,
  elegido: string,
): ItemComputo[] | null {
  const posicion = items.findIndex(
    (i) => i.origen_id === pendiente.origen_id && i.codigo_partida === pendiente.codigo_partida,
  );
  if (posicion < 0) return null;
  return items.map((i, n) => (n === posicion ? { ...i, codigo_partida: elegido } : i));
}

export function lineaPendiente(p: Pick<PendienteConPropuestas, "origen_id" | "codigo_partida" | "descripcion">): string {
  return `${p.origen_id} · ${p.codigo_partida} · ${p.descripcion}`;
}

// El puntaje es una similitud adimensional del normalizador (no un monto): dos decimales.
export function lineaPropuesta(s: PropuestaPartida): string {
  return `${s.codigo} · ${s.descripcion} (${formatoEsVe(s.puntaje.toFixed(2))})`;
}

export function textoPropuestaRendimiento(e: RendimientoPorDeclarar): string {
  const r = e.propuesta?.rendimiento;
  if (!r) return "";
  return `rendimiento propuesto ${formatoEsVe(r.valor)} unidades por día (${r.tipo} del ${fechaEsVe(r.fecha)})`;
}

export function textoDispersion(e: RendimientoPorDeclarar): string {
  const d = e.propuesta?.dispersion;
  if (!d) return "";
  return (
    `Dispersión del histórico: ${d.observaciones} observaciones (${d.medidos} medidas, ${d.estimados} estimadas), ` +
    `media ${formatoEsVe(d.media)}, rango [${formatoEsVe(d.minimo)}; ${formatoEsVe(d.maximo)}].`
  );
}

export function errorSinPropuestaDeRendimiento(codigo: string): string {
  return `${codigo}: la partida no tiene ningún rendimiento registrado que proponer; declárelo con sus condiciones en «Componer una partida».`;
}

export function errorSinTipo(codigo: string): string {
  return `Declare si el rendimiento de ${codigo} es estimado o medido.`;
}

export function filasDeItems(items: ItemComputo[]): FilaDensa[] {
  return items.map((i, n) => ({
    id: String(n),
    codigo_partida: i.codigo_partida,
    descripcion: i.descripcion,
    unidad: i.unidad,
    cantidad: i.cantidad,
    origen_id: i.origen_id,
    origen_tipo: i.origen_tipo,
    regla: i.regla ?? "",
  }));
}

export type ResultadoCalculo =
  | { tipo: "ok"; respuesta: CalculoRespuesta }
  | { tipo: "rendimientos"; detalle: string; lista: RendimientoPorDeclarar[] };

function detalleDe(cuerpo: unknown, estado: number): string {
  if (cuerpo && typeof cuerpo === "object") {
    const { detalle, detail } = cuerpo as { detalle?: unknown; detail?: unknown };
    if (typeof detalle === "string" && detalle) return detalle;
    if (typeof detail === "string" && detail) return detail;
  }
  return `La API respondió con el estado ${estado}.`;
}

// POST /presupuestos/calcular. `pedir` lanza ErrorDeApi con solo el `detalle`, pero el 409 de UC-01 3b trae ademas
// `rendimientos_por_declarar`; por eso esta llamada lee el cuerpo ella misma. El token CSRF es el de la sesion
// (`sesion.csrf` del contexto), el mismo que guarda el cliente. Un 409 sin lista (p. ej. sin lista de precios
// vigente) y cualquier otro error siguen siendo ErrorDeApi, como con `pedir`.
export async function calcular(cuerpo: CuerpoCalculo, csrf: string | null): Promise<ResultadoCalculo> {
  const cabeceras = new Headers({ "Content-Type": "application/json" });
  if (csrf) cabeceras.set("X-Silice-CSRF", csrf);
  let respuesta: Response;
  try {
    respuesta = await fetch("/presupuestos/calcular", {
      method: "POST",
      headers: cabeceras,
      body: JSON.stringify(cuerpo),
      credentials: "same-origin",
    });
  } catch {
    throw new ErrorDeApi(0, "No se pudo hablar con el servidor de Sílice. Compruebe que la API esté encendida.");
  }
  if (respuesta.ok) return { tipo: "ok", respuesta: (await respuesta.json()) as CalculoRespuesta };

  const contenido: unknown = await respuesta.json().catch(() => null);
  if (respuesta.status === 409) {
    const lista = (contenido as Partial<RendimientosPorDeclararRespuesta> | null)?.rendimientos_por_declarar;
    if (Array.isArray(lista) && lista.length > 0) {
      return { tipo: "rendimientos", detalle: detalleDe(contenido, 409), lista };
    }
  }
  const espera = Number(respuesta.headers.get("Retry-After"));
  throw new ErrorDeApi(
    respuesta.status,
    detalleDe(contenido, respuesta.status),
    Number.isFinite(espera) && espera > 0 ? espera : null,
  );
}

// --- Tarea 12 de montar un presupuesto: llevar los items a la Hoja de la obra ---------------------------------------

// Los items del computo con que se elaboro, sin los pendientes (no tienen partida en el catalogo: la API los rechazaria
// y no llevaria ninguno). La cantidad viaja tal cual salio de /computos: la pagina no la convierte ni la redondea.
export function partidasParaLlevar(
  items: ItemComputo[],
  pendientes: Pick<PendienteConPropuestas, "origen_id" | "codigo_partida">[],
): PartidaParaLlevar[] {
  const pendiente = (i: ItemComputo) =>
    pendientes.some((p) => p.origen_id === i.origen_id && p.codigo_partida === i.codigo_partida);
  return items.filter((i) => !pendiente(i)).map((i) => ({ codigo: i.codigo_partida, cantidad: i.cantidad, calculo: "" }));
}

// Esbozo del rojo de la Tarea 12 de F4: todavia arma el cuerpo como Elaborar.
export function cuerpoDeValoracion(p: { proyecto: string; moneda: string; fecha: string; items: ItemComputo[] }): CuerpoCalculo {
  return { codigo: "", fecha: "", moneda: "", items: p.items };
}
