// Logica pura de «Escenarios de sensibilidad» (UC-08). Sin React; los montos son texto tal como llegan.
import type { FilaDensa } from "../../comun/TablaDensa";
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
  "Recalcula un presupuesto guardado variando parametros de costo o precios de insumos. " +
  "El presupuesto base no se altera y ningun escenario se guarda.";
export const SIN_PRESUPUESTOS = "No hay presupuestos guardados todavia: elabore uno primero (UC-01).";
export const NOTA_PARAMETROS =
  "Parametros de costo del escenario (por defecto, los del presupuesto base). Fracciones: 6.00 = prestaciones del 600 %.";
export const NOTA_PRECIOS =
  "Precios de ensayo (opcional): descripcion exacta del insumo y precio nuevo. Lo no mencionado conserva su precio vigente.";
export const SIN_ESCENARIOS = "Defina un escenario para compararlo contra el presupuesto base.";
export const TITULO_COMPARACION = "Comparacion contra el base (RF-31)";
export const AVISO_PENDIENTES = "El presupuesto base tiene items pendientes, sin partida en el catalogo:";
export const NOTA_PENDIENTES =
  "Pendientes del base: los escenarios solo recalculan los renglones valorados; estos items no suman al total " +
  "del base ni de ningun escenario (UC-01 3a).";

export const CAMPOS_PARAMETROS: CampoParametro[] = ["fcas", "bono_alimentacion", "administracion", "utilidad"];

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

export const COLUMNAS_COMPARACION = [
  { clave: "escenario", titulo: "escenario" },
  { clave: "total", titulo: "total", numerica: true },
  { clave: "variacion", titulo: "variacion", numerica: true },
  { clave: "variacion_pct", titulo: "variacion_pct", numerica: true },
];

export const COLUMNAS_PARTIDAS = [
  { clave: "codigo_partida", titulo: "codigo_partida" },
  { clave: "descripcion", titulo: "descripcion" },
  { clave: "cantidad", titulo: "cantidad", numerica: true },
  { clave: "pu_anterior", titulo: "pu_anterior", numerica: true },
  { clave: "pu_nuevo", titulo: "pu_nuevo", numerica: true },
  { clave: "variacion_pct", titulo: "variacion_pct", numerica: true },
  { clave: "total_anterior", titulo: "total_anterior", numerica: true },
  { clave: "total_nuevo", titulo: "total_nuevo", numerica: true },
  { clave: "incidencia_pct", titulo: "incidencia_pct", numerica: true },
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
    `Hallazgos de la auditoria del escenario: ${e.hallazgos} (el informe se genera siempre). ` +
    `Insumos variados: ${e.insumos_variados}.`
  );
}

export function rutaEscenarios(codigo: string, proyecto: string, sufijo = ""): string {
  return `/presupuestos/${encodeURIComponent(codigo)}/escenarios${sufijo}?proyecto=${encodeURIComponent(proyecto)}`;
}
