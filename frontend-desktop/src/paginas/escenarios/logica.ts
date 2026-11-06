// Logica pura de «Escenarios de sensibilidad» (UC-08). Sin React; los montos son texto tal como llegan.
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";
import { leerCifra, textoParaEscribir } from "../../indicadores/cifraEscrita";
import { formatoMontoEsVe } from "../../indicadores/formatoEsVe";
import type {
  CampoParametro,
  EscenarioPeticion,
  EscenarioRespuesta,
  EscenariosRespuesta,
  FilaComparativo,
  Pendiente,
  PresupuestoResumen,
} from "./tipos";

export const AYUDA =
  "Recalcula un presupuesto guardado variando parámetros de costo o precios de insumos. " +
  "El presupuesto base no se altera y ningún escenario se guarda.";
export const SIN_PRESUPUESTOS = "No hay presupuestos guardados todavía: elabore uno primero.";
export const NOTA_PARAMETROS = "Parámetros de costo del escenario (por defecto, los del presupuesto base).";
export const NOTA_PRECIOS =
  "Precios de ensayo (opcional): busque el insumo, elíjalo de la lista y escriba el precio nuevo. Lo no mencionado conserva su precio vigente.";
export const EJEMPLO_PRECIOS = "p. ej. Cemento Portland → 18,50";
export const SIN_ESCENARIOS = "Defina un escenario para compararlo contra el presupuesto base.";
export const TITULO_COMPARACION = "Comparación contra el base";
export const AVISO_PENDIENTES = "El presupuesto base tiene ítems pendientes, sin partida en el catálogo:";
export const NOTA_PENDIENTES =
  "Pendientes del base: los escenarios solo recalculan los renglones valorados; estos ítems no suman al total " +
  "del base ni de ningún escenario.";

export const CAMPOS_PARAMETROS: CampoParametro[] = ["fcas", "bono_alimentacion", "administracion", "utilidad"];

export const ROTULOS_PARAMETROS: Record<CampoParametro, string> = {
  fcas: "FCAS (fracción; 6,00 = prestaciones del 600 %)",
  bono_alimentacion: "Bono de alimentación",
  administracion: "Administración",
  utilidad: "Utilidad",
};

// Si el detalle de un rechazo nombra un parametro, ese campo se marca ademas del aviso.
export function campoNombrado(detalle: string): CampoParametro | null {
  const texto = detalle.toLowerCase();
  return CAMPOS_PARAMETROS.find((c) => texto.includes(c)) ?? null;
}

export interface FilaPrecio {
  id: number;
  insumo: string;
  precio: string;
  // La descripcion que se eligio de la lista del catalogo (AC3); lo que difiera de ella es texto escrito a mano.
  elegido?: string;
}

// El calculo empareja la descripcion por igualdad exacta y descarta en silencio la que no existe (core/budget/escenarios.py:
// `precios.get(descripcion, precio)`; la API la nombra en `precios_sin_insumo` y `avisoPreciosSinEfecto` lo dice). Por eso no se ofrece «usar tal cual»: se
// permite escribirla, pero queda avisado.
export const AVISO_ESCRITO_A_MANO =
  "Escrito a mano: si no es exactamente un insumo de la lista, no cambia ningún precio.";

export function esEscritoAMano(fila: FilaPrecio): boolean {
  return fila.insumo.trim() !== "" && fila.elegido !== fila.insumo;
}

export function etiquetaDePresupuesto(p: PresupuestoResumen): string {
  return `${p.proyecto} / ${p.codigo}`;
}

export function nombrePorOmision(definidos: number): string {
  return `escenario ${definidos + 1}`;
}

export function lineaPendiente(p: Pendiente): string {
  return `- ${p.origen_id}: ${p.codigo_partida} (${p.descripcion})`;
}

// --- cifras tecleadas (regla de Eugenio, 2026-10-25: coma decimal, punto de miles) ----------------
// Los parametros y los precios de ensayo se escriben con coma; la API los recibe con punto. Los parametros del base
// llegan con punto («6.00») y se ponen en los campos con coma («6,00»): sin tocarlos, vuelven iguales.

export function parametrosParaEditar(parametros: Record<string, string>): Record<CampoParametro, string> {
  const editar = (valor: string | undefined) => (valor === undefined ? "" : textoParaEscribir(valor));
  return {
    fcas: editar(parametros.fcas),
    bono_alimentacion: editar(parametros.bono_alimentacion),
    administracion: editar(parametros.administracion),
    utilidad: editar(parametros.utilidad),
  };
}

function cifraParaApi(texto: string): string {
  const lectura = leerCifra(texto);
  return "valor" in lectura ? lectura.valor : texto;
}

// El error de una cifra escrita, o null si se lee. Un campo en blanco no se juzga aqui: la API dice lo que falta.
function errorDeCifra(texto: string): string | null {
  if (texto.trim() === "") return null;
  const lectura = leerCifra(texto);
  return "error" in lectura ? lectura.error : null;
}

export interface ErroresDeCifras {
  parametros: Partial<Record<CampoParametro, string>>;
  // Por id de fila; solo las filas con insumo (las otras no se mandan).
  precios: Record<number, string>;
}

export function erroresDeCifras(parametros: Record<CampoParametro, string>, filas: FilaPrecio[]): ErroresDeCifras {
  const errores: ErroresDeCifras = { parametros: {}, precios: {} };
  for (const campo of CAMPOS_PARAMETROS) {
    const error = errorDeCifra(parametros[campo]);
    if (error) errores.parametros[campo] = error;
  }
  for (const fila of filas) {
    const error = fila.insumo.trim() ? errorDeCifra(fila.precio) : null;
    if (error) errores.precios[fila.id] = error;
  }
  return errores;
}

export function hayErrores(e: ErroresDeCifras): boolean {
  return Object.keys(e.parametros).length > 0 || Object.keys(e.precios).length > 0;
}

// Las filas con insumo en blanco se ignoran; el insumo se recorta (la API lo busca por descripcion exacta). El precio
// va con punto.
export function preciosDeFilas(filas: FilaPrecio[]): Record<string, string> {
  const precios: Record<string, string> = {};
  for (const fila of filas) {
    const insumo = fila.insumo.trim();
    if (insumo) precios[insumo] = cifraParaApi(fila.precio);
  }
  return precios;
}

export function armarEscenario(
  nombre: string,
  parametros: Record<CampoParametro, string>,
  filas: FilaPrecio[],
  definidos: number,
): EscenarioPeticion {
  return {
    nombre: nombre.trim() === "" ? nombrePorOmision(definidos) : nombre,
    fcas: cifraParaApi(parametros.fcas),
    bono_alimentacion: cifraParaApi(parametros.bono_alimentacion),
    administracion: cifraParaApi(parametros.administracion),
    utilidad: cifraParaApi(parametros.utilidad),
    precios: preciosDeFilas(filas),
  };
}

export const COLUMNAS_COMPARACION: ColumnaDensa[] = [
  { clave: "escenario", titulo: "Escenario" },
  // Los montos se leen en es-VE (el exacto queda en el title); las variaciones llevan su flecha IBCS.
  { clave: "total", titulo: "Total", numerica: true, presentar: formatoMontoEsVe },
  { clave: "variacion", titulo: "Variación", numerica: true, celda: "variacion" },
  { clave: "variacion_pct", titulo: "Variación %", numerica: true, celda: "variacion" },
];

// Lo importante primero: los totales y su variacion antes que el desglose del precio unitario.
export const COLUMNAS_PARTIDAS: ColumnaDensa[] = [
  { clave: "codigo_partida", titulo: "Partida" },
  { clave: "descripcion", titulo: "Descripción" },
  { clave: "total_anterior", titulo: "Total anterior", numerica: true, presentar: formatoMontoEsVe },
  { clave: "total_nuevo", titulo: "Total nuevo", numerica: true, presentar: formatoMontoEsVe },
  { clave: "variacion_pct", titulo: "Variación %", numerica: true, celda: "variacion" },
  { clave: "incidencia_pct", titulo: "Incidencia %", numerica: true, celda: "variacion" },
  { clave: "pu_anterior", titulo: "P.U. anterior", numerica: true, presentar: formatoMontoEsVe },
  { clave: "pu_nuevo", titulo: "P.U. nuevo", numerica: true, presentar: formatoMontoEsVe },
  { clave: "cantidad", titulo: "Cantidad", numerica: true, presentar: formatoMontoEsVe },
];

// La fila del base: variacion cero, escrita como la API escribe los montos.
export function filasComparacion(r: EscenariosRespuesta): FilaDensa[] {
  const base: FilaDensa = {
    id: "base",
    escenario: r.codigo_base,
    total: r.total_base,
    variacion: "0.00",
    variacion_pct: "0.00",
  };
  return [
    base,
    ...r.escenarios.map((e: EscenarioRespuesta, i: number) => ({
      id: `e${i}`,
      escenario: e.nombre,
      total: e.total,
      variacion: e.variacion,
      variacion_pct: e.variacion_pct,
    })),
  ];
}

export function filasPartidas(partidas: FilaComparativo[]): FilaDensa[] {
  return partidas.map((p, i) => ({ id: `p${i}`, ...p }));
}

export function notaHallazgos(e: EscenarioRespuesta): string {
  return (
    `Hallazgos de la auditoría del escenario: ${e.hallazgos} (el informe se genera siempre). ` +
    `Insumos variados: ${e.insumos_variados}.`
  );
}

// «A», «B» y «C»
function enumerar(nombres: string[]): string {
  const citados = nombres.map((n) => `«${n}»`);
  return citados.length <= 1 ? (citados[0] ?? "") : `${citados.slice(0, -1).join(", ")} y ${citados[citados.length - 1]}`;
}

// En espanol llano, los precios de ensayo de un escenario que no cambiaron nada y por que; null si todos cambiaron algo.
export function avisoPreciosSinEfecto(e: EscenarioRespuesta): string | null {
  const sinInsumo = e.precios_sin_insumo ?? [];
  const sinCambio = e.precios_sin_cambio ?? [];
  const total = sinInsumo.length + sinCambio.length;
  if (total === 0) return null;
  const partes: string[] = [];
  if (sinInsumo.length > 0) {
    partes.push(
      `${enumerar(sinInsumo)} no ${sinInsumo.length === 1 ? "es un insumo" : "son insumos"} del presupuesto base ` +
        "(el nombre tiene que ser exactamente el de la lista)",
    );
  }
  if (sinCambio.length > 0) partes.push(`${enumerar(sinCambio)} ya ${sinCambio.length === 1 ? "tenía" : "tenían"} ese precio`);
  const cuantos = total === 1 ? "1 precio de ensayo no cambió nada" : `${total} precios de ensayo no cambiaron nada`;
  return `En «${e.nombre}», ${cuantos}: ${partes.join("; ")}.`;
}

export function rutaEscenarios(codigo: string, proyecto: string, sufijo = ""): string {
  return `/presupuestos/${encodeURIComponent(codigo)}/escenarios${sufijo}?proyecto=${encodeURIComponent(proyecto)}`;
}
