// Tablero del proyecto (UC-13): contrato de `GET /v1/tablero` y las funciones puras que arman lo que se dibuja.
// Los textos ya vienen presentados por la API; `valor` y `fraccion` son decimales exactos en texto y solo sirven para
// dibujar (el numero que se lee es siempre el texto).
import type { SerieDeCurva } from "../../comun/CurvaPlanAvance";

export interface Tarjeta {
  rotulo: string;
  valor: string;
  detalle: string;
}

export interface Anillo {
  rotulo: string;
  fraccion: string | null;
  texto: string;
  favorable: boolean | null;
}

export interface ControlDelTablero {
  disponible: boolean;
  motivo: string;
  anillos: Anillo[];
  tarjetas: Tarjeta[];
}

export interface PuntoApi {
  orden: number;
  periodo: string;
  valor: string;
}

export interface CurvasDelTablero {
  titulo: string;
  series: { serie: string; puntos: PuntoApi[] }[];
}

export interface Rubro {
  rubro: string;
  monto: string;
  peso: string;
  valor: string;
}

export interface FilaPareto {
  partida: string;
  descripcion: string;
  total: string;
  peso: string;
  acumulado: string;
  valor: string;
}

export interface VersionDelTablero {
  version: string;
  fecha: string;
  motivo: string;
  costo_directo: string;
  total: string;
  vigente: boolean;
  valor: string;
}

export interface TableroRespuesta {
  proyecto: string;
  version: string | null;
  fecha: string | null;
  moneda: string | null;
  renglones: number;
  tarjetas: Tarjeta[];
  control: ControlDelTablero | null;
  curvas: CurvasDelTablero | null;
  desglose: Rubro[];
  pareto: FilaPareto[];
  versiones: VersionDelTablero[];
}

export const RUTA_TABLERO = "/v1/tablero";

export function rutaDelTablero(proyecto: string): string {
  return `${RUTA_TABLERO}?proyecto=${encodeURIComponent(proyecto)}`;
}

// Un anillo de progreso es una dona de dos porciones: lo hecho y lo que falta (tope en 100 %). Sin dato, null.
export function datosDeAnillo(anillo: Anillo): { group: string; value: number }[] | null {
  if (anillo.fraccion === null) return null;
  const hecho = Math.min(Math.max(Number(anillo.fraccion), 0), 1);
  return [
    { group: "Logrado", value: hecho },
    { group: "Falta", value: 1 - hecho },
  ];
}

// El plan (PV) es lo previsto; EV y AC son lo ocurrido. El pronostico aun no viene en el tablero (lo trae Control).
export function rolDeSerie(nombre: string): SerieDeCurva["rol"] {
  return nombre === "EV" || nombre === "AC" ? "real" : "plan";
}

export function seriesDeCurva(curvas: CurvasDelTablero): SerieDeCurva[] {
  return curvas.series.map((s) => ({
    nombre: s.serie,
    rol: rolDeSerie(s.serie),
    puntos: [...s.puntos].sort((a, b) => a.orden - b.orden).map((p) => ({ periodo: p.periodo, valor: p.valor })),
  }));
}

export function datosDeDesglose(desglose: Rubro[]): { group: string; value: number }[] {
  return desglose.map((r) => ({ group: r.rubro, value: Number(r.valor) }));
}

export function datosDePareto(pareto: FilaPareto[]): { group: string; value: number }[] {
  return pareto.map((f) => ({ group: f.partida, value: Number(f.valor) }));
}

export function datosDeVersiones(versiones: VersionDelTablero[]): { group: string; value: number }[] {
  return versiones.map((v) => ({ group: v.vigente ? `${v.version} (vigente)` : v.version, value: Number(v.valor) }));
}
