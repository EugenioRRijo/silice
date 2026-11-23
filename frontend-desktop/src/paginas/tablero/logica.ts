// Tablero del proyecto (UC-13): contrato de `GET /v1/tablero` y las funciones puras que arman lo que se dibuja.
// Los textos ya vienen presentados por la API; `valor` y `fraccion` son decimales exactos en texto y solo sirven para
// dibujar (el numero que se lee es siempre el texto).
import { periodoLegible } from "../../comun/CurvaPlanAvance";
import type { SerieDeCurva } from "../../comun/CurvaPlanAvance";
import { centesimasEsVe, formatoMontoEsVe } from "../../indicadores/formatoEsVe";

export interface Tarjeta {
  rotulo: string;
  valor: string;
  detalle: string;
  // El monto sin redondear de una tarjeta de dinero ("" o ausente en las demas): va en el `title` (VB-21).
  exacto?: string;
}

export interface Anillo {
  rotulo: string;
  fraccion: string | null;
  texto: string;
  favorable: boolean | null;
  referencia?: string | null;
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

// VD-8: el detalle de la tarjeta «Punto de equilibrio» es la frase fija del nucleo «se alcanza en {periodo}»
// (core/budget/equilibrio.py), con el periodo de la curva («Dia N [partida]», core/budget/curva.py). Se lee con el
// mismo arreglo que el eje de la curva (`periodoLegible`), solo en esa ranura y solo en esa tarjeta: el resto, y un
// detalle mas largo que el tope, sale tal cual. Es solo la vista: el valor guardado no cambia.
const FRASE_DEL_EQUILIBRIO = "se alcanza en ";
const LARGO_MAXIMO_DETALLE = 2_000;

export function detalleDeTarjeta(tarjeta: Tarjeta): string {
  const { rotulo, detalle } = tarjeta;
  if (rotulo !== "Punto de equilibrio" || detalle.length > LARGO_MAXIMO_DETALLE) return detalle;
  if (!detalle.startsWith(FRASE_DEL_EQUILIBRIO)) return detalle;
  return FRASE_DEL_EQUILIBRIO + periodoLegible(detalle.slice(FRASE_DEL_EQUILIBRIO.length));
}

export function rutaDelTablero(proyecto: string): string {
  return `${RUTA_TABLERO}?proyecto=${encodeURIComponent(proyecto)}`;
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

// La etiqueta de cada porcion del anillo es el peso que manda la API, en es-VE («37,6 %»): no el porcentaje que
// Carbon Charts recalcula con floats y escribe con punto (VB-21).
export function etiquetaDePeso(desglose: Rubro[]): (d: { data: { group: string } }) => string {
  const peso = new Map(desglose.map((r) => [r.rubro, r.peso]));
  return (d) => formatoMontoEsVe(peso.get(d.data.group) ?? "");
}

// Los anillos del control que se dibujan como medidor: los de un porcentaje (el avance fisico, «62.5 %») con su fraccion.
// SPI y CPI son indices, no partes de un todo, y siguen en sus tarjetas (V-21); sin fraccion no hay arco ni un «0 %».
export function anillosDePorcentaje(anillos: Anillo[]): Anillo[] {
  return anillos.filter((a) => a.fraccion !== null && a.texto.includes("%") && Number.isFinite(Number(a.fraccion)));
}

// El numero del centro del anillo: el total del contrato de la API en centesimas («95.066,60»), no la suma en float de
// las porciones («95.066,60006249999»). Sin la tarjeta del total, null (se deja el del grafico).
export function centroDelAnillo(tarjetas: Tarjeta[]): string | null {
  const total = tarjetas.find((t) => t.rotulo === "Total del contrato");
  if (!total) return null;
  if (total.exacto) return centesimasEsVe(total.exacto);
  return formatoMontoEsVe(total.valor.split(" ")[0] ?? total.valor);
}

export function datosDeDesglose(desglose: Rubro[]): { group: string; value: number }[] {
  return desglose.map((r) => ({ group: r.rubro, value: Number(r.valor) }));
}

// La API manda el Pareto de la mayor partida a la menor y «Resto» al final. Carbon dibuja el primer rótulo del eje izquierdo
// ABAJO, así que a la gráfica se le da el orden inverso: la mayor queda arriba y «Resto» abajo, como lee la tabla de al lado
// (prueba en vivo del 18/11/2026: salía al revés).
export function datosDePareto(pareto: FilaPareto[]): { group: string; value: number }[] {
  return pareto.map((f) => ({ group: f.partida, value: Number(f.valor) })).reverse();
}

// Como el Pareto: la gráfica se lee igual que su tabla (DS-70), y Carbon dibuja el primer rótulo del eje izquierdo abajo, así
// que va en orden inverso: la primera versión de la tabla queda arriba.
export function datosDeVersiones(versiones: VersionDelTablero[]): { group: string; value: number }[] {
  return versiones.map((v) => ({ group: v.vigente ? `${v.version} (vigente)` : v.version, value: Number(v.valor) })).reverse();
}
