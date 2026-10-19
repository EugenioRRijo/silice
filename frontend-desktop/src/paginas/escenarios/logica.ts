// Logica pura de «Escenarios de sensibilidad» (UC-08). Sin React; los montos son texto tal como llegan.
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";
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
  "Precios de ensayo (opcional): descripción exacta del insumo y precio nuevo. Lo no mencionado conserva su precio vigente.";
export const EJEMPLO_PRECIOS = "p. ej. Cemento Portland → 18.50";
export const SIN_ESCENARIOS = "Defina un escenario para compararlo contra el presupuesto base.";
export const TITULO_COMPARACION = "Comparación contra el base";
export const AVISO_PENDIENTES = "El presupuesto base tiene ítems pendientes, sin partida en el catálogo:";
export const NOTA_PENDIENTES =
  "Pendientes del base: los escenarios solo recalculan los renglones valorados; estos ítems no suman al total " +
  "del base ni de ningún escenario.";

export const CAMPOS_PARAMETROS: CampoParametro[] = ["fcas", "bono_alimentacion", "administracion", "utilidad"];

export const ROTULOS_PARAMETROS: Record<CampoParametro, string> = {
  fcas: "FCAS (fracción; 6.00 = prestaciones del 600 %)",
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

// Las filas con insumo en blanco se ignoran; el insumo se recorta (la API lo busca por descripcion exacta).
export function preciosDeFilas(filas: FilaPrecio[]): Record<string, string> {
  const precios: Record<string, string> = {};
  for (const fila of filas) {
    const insumo = fila.insumo.trim();
    if (insumo) precios[insumo] = fila.precio;
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
    fcas: parametros.fcas,
    bono_alimentacion: parametros.bono_alimentacion,
    administracion: parametros.administracion,
    utilidad: parametros.utilidad,
    precios: preciosDeFilas(filas),
  };
}

export const COLUMNAS_COMPARACION: ColumnaDensa[] = [
  { clave: "escenario", titulo: "Escenario" },
  { clave: "total", titulo: "Total", numerica: true },
  { clave: "variacion", titulo: "Variación", numerica: true, celda: "variacion" },
  { clave: "variacion_pct", titulo: "Variación %", numerica: true, celda: "variacion" },
];

// Lo importante primero: los totales y su variacion antes que el desglose del precio unitario.
export const COLUMNAS_PARTIDAS: ColumnaDensa[] = [
  { clave: "codigo_partida", titulo: "Partida" },
  { clave: "descripcion", titulo: "Descripción" },
  { clave: "total_anterior", titulo: "Total anterior", numerica: true },
  { clave: "total_nuevo", titulo: "Total nuevo", numerica: true },
  { clave: "variacion_pct", titulo: "Variación %", numerica: true, celda: "variacion" },
  { clave: "incidencia_pct", titulo: "Incidencia %", numerica: true, celda: "variacion" },
  { clave: "pu_anterior", titulo: "P.U. anterior", numerica: true },
  { clave: "pu_nuevo", titulo: "P.U. nuevo", numerica: true },
  { clave: "cantidad", titulo: "Cantidad", numerica: true },
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

export function rutaEscenarios(codigo: string, proyecto: string, sufijo = ""): string {
  return `/presupuestos/${encodeURIComponent(codigo)}/escenarios${sufijo}?proyecto=${encodeURIComponent(proyecto)}`;
}
