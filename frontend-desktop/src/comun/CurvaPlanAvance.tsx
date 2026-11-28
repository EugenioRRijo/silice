import type { LineChartOptions } from "@carbon/charts-react";
import { lazy, Suspense, useEffect, useRef } from "react";
import { formatoMontoEsVe } from "../indicadores/formatoEsVe";
import { EsqueletoPagina } from "./EsqueletoPagina";
import { coloresDeSerie, ESCALA_DE_ETIQUETAS, escalaDeColor, formatoNumeroEsVe, slotsPorRol, useModoEfectivo, valorParaDibujar } from "./paletaGraficos";
import { TablaDensa } from "./TablaDensa";

const GraficoCarbon = lazy(() => import("./GraficoCarbon"));

// Curva comun plan / avance / pronostico (tablero y control de obra). El rol decide como se dibuja y no depende solo
// del color: el plan va punteado y neutro, lo ejecutado continuo, lo gastado con puntos redondos y el pronostico con raya
// larga. Cada rol tiene su color fijo (paletaGraficos.slotsPorRol), asi una serie no cambia de color cuando otra falta.
export type RolDeSerie = "plan" | "real" | "gastado" | "pronostico";

export interface PuntoDeCurva {
  periodo: string;
  // Monto exacto tal como lo manda la API (texto decimal): la tabla lo muestra sin tocarlo.
  valor: string;
}

export interface SerieDeCurva {
  nombre: string;
  rol: RolDeSerie;
  puntos: PuntoDeCurva[];
}

interface Props {
  titulo: string;
  series: SerieDeCurva[];
  // Unidad del eje (por ejemplo «USD»).
  unidad?: string;
}

export const TRAZO_DE_PLAN = "4 4";
export const TRAZO_DE_PRONOSTICO = "10 4";
export const TRAZO_DE_GASTADO = "1 5";
// Lineas de 2 px (el plan, mas fino, queda de referencia).
export const GROSOR: Record<RolDeSerie, number> = { plan: 1.5, real: 2, gastado: 2, pronostico: 2 };
const TRAZO: Record<RolDeSerie, string> = { plan: TRAZO_DE_PLAN, real: "none", gastado: TRAZO_DE_GASTADO, pronostico: TRAZO_DE_PRONOSTICO };

const ORDEN_DE_ROLES: readonly RolDeSerie[] = ["plan", "real", "gastado", "pronostico"];

const LEYENDA_DE_ROL: Record<RolDeSerie, string> = {
  plan: "Línea punteada gris: planificado",
  real: "Línea continua: ejecutado (EV)",
  gastado: "Línea de puntos: gastado (AC)",
  pronostico: "Línea discontinua larga: pronóstico",
};

// Como se dice cada rol al rotular un valor y en el globo.
const ROTULO_DE_ROL: Record<RolDeSerie, string> = { plan: "planificado", real: "real", gastado: "gastado", pronostico: "pronóstico" };

// Con mas periodos que esto los puntos estorban (el globo sigue apareciendo al pasar por cada periodo).
const MAXIMO_DE_PUNTOS = 16;

// La API nombra los periodos del control «Dia N» (convencion de la regla R7): se leen «Día N».
export function periodoLegible(periodo: string): string {
  return periodo.replace(/^Dia (?=[0-9])/, "Día ");
}

export function filasDeGrafico(series: SerieDeCurva[]): { group: string; key: string; value: number }[] {
  return series.flatMap((s) =>
    s.puntos.map((p) => ({ group: s.nombre, key: periodoLegible(p.periodo), value: valorParaDibujar(p.valor) })),
  );
}

// Los periodos en el orden en que aparecen (la primera serie que los trae manda).
export function periodos(series: SerieDeCurva[]): string[] {
  const vistos: string[] = [];
  for (const s of series) for (const p of s.puntos) if (!vistos.includes(p.periodo)) vistos.push(p.periodo);
  return vistos;
}

// El ultimo periodo con dato de lo ejecutado: hasta ahi llega lo real y de ahi en adelante solo hay plan o pronostico.
function periodoDeCorte(series: SerieDeCurva[]): string | undefined {
  const reales = series.filter((s) => s.rol === "real");
  return [...periodos(series)].reverse().find((p) => reales.some((s) => s.puntos.some((q) => q.periodo === p)));
}

export interface RotuloDeCurva {
  etiqueta: "Inicio" | "Corte" | "Final" | "Corte y final";
  periodo: string;
  // «planificado 100,00 USD», «real 80,00 USD»: el valor de cada serie en ese periodo, en es-VE.
  partes: string[];
}

function partesDelPeriodo(series: SerieDeCurva[], periodo: string, unidad: string | undefined): string[] {
  const porRol = (rol: RolDeSerie) => series.filter((s) => s.rol === rol);
  return ORDEN_DE_ROLES.flatMap((rol) =>
    porRol(rol).flatMap((s) => {
      const punto = s.puntos.find((p) => p.periodo === periodo);
      if (!punto) return [];
      const quien = porRol(rol).length > 1 ? s.nombre : ROTULO_DE_ROL[rol];
      return [`${quien} ${formatoMontoEsVe(unidad ? `${punto.valor} ${unidad}` : punto.valor)}`];
    }),
  );
}

// Los rotulos directos de la curva: el valor de cada serie en el inicio, en el corte y en el final. Son solo tres para que
// se lean (un numero en cada punto no se lee); el resto esta en el globo y en la tabla.
export function rotulosDeCurva(series: SerieDeCurva[], unidad?: string): RotuloDeCurva[] {
  const todos = periodos(series);
  const inicio = todos[0];
  if (inicio === undefined) return [];
  const final = todos[todos.length - 1]!;
  const corte = periodoDeCorte(series);
  const hechos: [RotuloDeCurva["etiqueta"], string][] = [["Inicio", inicio]];
  if (corte !== undefined && corte !== inicio) hechos.push([corte === final ? "Corte y final" : "Corte", corte]);
  if (final !== inicio && final !== corte) hechos.push(["Final", final]);
  return hechos.map(([etiqueta, periodo]) => ({ etiqueta, periodo: periodoLegible(periodo), partes: partesDelPeriodo(series, periodo, unidad) }));
}

const ESCAPES: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
function esc(texto: string): string {
  return texto.replace(/[&<>"']/g, (c) => ESCAPES[c]!);
}

// El globo de un punto (Carbon lo pide como HTML): la fecha y el valor de cada serie en ella (el valor primero, el nombre
// despues), tal como los manda el servidor: la pantalla no resta ni calcula cifras. Los nombres de serie vienen de la API:
// se escapan.
export function globoDelPunto(
  series: SerieDeCurva[],
  clave: string,
  unidad: string | undefined,
  colores: Readonly<Record<string, string>>,
): string {
  const en = (s: SerieDeCurva) => s.puntos.find((p) => periodoLegible(p.periodo) === clave);
  const monto = (valor: string) => formatoMontoEsVe(unidad ? `${valor} ${unidad}` : valor);
  const filas = ORDEN_DE_ROLES.flatMap((rol) =>
    series
      .filter((s) => s.rol === rol)
      .flatMap((s) => {
        const punto = en(s);
        if (!punto) return [];
        const trazo = colores[s.nombre];
        const llave = trazo ? `<span style="display:inline-block;inline-size:12px;border-top:2px solid ${esc(trazo)}"></span>` : "";
        const rotulo = `${ROTULO_DE_ROL[rol][0]!.toUpperCase()}${ROTULO_DE_ROL[rol].slice(1)} (${s.nombre})`;
        return [`<li style="display:flex;gap:8px;align-items:center">${llave}<strong>${esc(monto(punto.valor))}</strong><span>${esc(rotulo)}</span></li>`];
      }),
  );
  return `<div style="padding:8px 12px"><p style="margin:0 0 4px;font-weight:600">${esc(clave)}</p><ul style="list-style:none;margin:0;padding:0">${filas.join("")}</ul></div>`;
}

function claveDelGlobo(data: unknown): string | null {
  const primero: unknown = Array.isArray(data) ? data[0] : data;
  return typeof primero === "object" && primero !== null && "key" in primero && typeof primero.key === "string" ? primero.key : null;
}

// Carbon tipa el valor de un umbral como numero o fecha, pero en un eje de etiquetas lo busca por el texto de la etiqueta.
const umbralPorEtiqueta = (etiqueta: string): number => etiqueta as unknown as number;

// Carbon no trae el discontinuo ni el grosor por serie como opcion: se aplican sobre los trazos ya dibujados
// (cada `path.line` guarda su serie en `__data__.name`) y se reaplican cuando el grafico se redibuja.
export function aplicarTrazos(raiz: ParentNode, series: SerieDeCurva[]): void {
  const rol = new Map(series.map((s) => [s.nombre, s.rol]));
  raiz.querySelectorAll<SVGPathElement>("path.line").forEach((trazo) => {
    const nombre = (trazo as unknown as { __data__?: { name?: string } }).__data__?.name;
    const r = nombre === undefined ? undefined : rol.get(nombre);
    if (!r) return;
    trazo.style.strokeWidth = String(GROSOR[r]);
    trazo.style.strokeDasharray = TRAZO[r];
    // El punteado de lo gastado se lee como puntos redondos y no como un guion corto parecido al plan.
    trazo.style.strokeLinecap = r === "gastado" ? "round" : "";
  });
}

export function CurvaPlanAvance({ titulo, series, unidad }: Props) {
  const contenedor = useRef<HTMLDivElement>(null);
  const modo = useModoEfectivo();

  useEffect(() => {
    const raiz = contenedor.current;
    if (!raiz) return;
    aplicarTrazos(raiz, series);
    const observador = new MutationObserver(() => aplicarTrazos(raiz, series));
    observador.observe(raiz, { childList: true, subtree: true });
    return () => observador.disconnect();
  }, [series]);

  const columnas = [
    { clave: "periodo", titulo: "Período", ordenable: false },
    ...series.map((s) => ({
      clave: s.nombre,
      titulo: unidad ? `${s.nombre} (${unidad})` : s.nombre,
      numerica: true,
      ordenable: false,
      presentar: formatoMontoEsVe,
    })),
  ];
  const todos = periodos(series);
  const filas = todos.map((periodo, i) => ({
    id: `p${i}`,
    periodo: periodoLegible(periodo),
    ...Object.fromEntries(series.map((s) => [s.nombre, s.puntos.find((p) => p.periodo === periodo)?.valor ?? "—"])),
  }));

  const color = escalaDeColor(modo, slotsPorRol(series));
  const corte = periodoDeCorte(series);
  const hayFuturo = corte !== undefined && todos.indexOf(corte) < todos.length - 1;
  const opciones: LineChartOptions = {
    title: titulo,
    height: "320px",
    axes: {
      bottom: {
        mapsTo: "key",
        scaleType: ESCALA_DE_ETIQUETAS,
        ...(corte !== undefined && hayFuturo
          ? {
              thresholds: [
                {
                  value: umbralPorEtiqueta(periodoLegible(corte)),
                  label: `Corte: ${periodoLegible(corte)}`,
                  fillColor: coloresDeSerie(modo).neutro2,
                },
              ],
            }
          : {}),
      },
      left: { mapsTo: "value", title: unidad ?? "Monto", ticks: { formatter: formatoNumeroEsVe } },
    },
    tooltip: {
      valueFormatter: formatoNumeroEsVe,
      customHTML: (data: unknown, porOmision: string) => {
        const clave = claveDelGlobo(data);
        return clave === null ? porOmision : globoDelPunto(series, clave, unidad, color.scale);
      },
    },
    color,
    curve: "curveMonotoneX",
    points: todos.length <= MAXIMO_DE_PUNTOS ? { enabled: true, radius: 4 } : { enabled: false },
  };

  const rotulos = rotulosDeCurva(series, unidad);
  const resumen = [
    `Series: ${series.map((s) => s.nombre).join(", ")}.`,
    todos.length > 0 ? `De ${periodoLegible(todos[0]!)} a ${periodoLegible(todos[todos.length - 1]!)}.` : "",
    corte !== undefined ? `Lo real llega hasta ${periodoLegible(corte)}.` : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <figure className="silice-curva" aria-label={titulo}>
      <div ref={contenedor} className="silice-curva__grafico" role="group" aria-label={`Gráfico: ${titulo}. ${resumen}`}>
        <Suspense fallback={<EsqueletoPagina etiqueta="Cargando el gráfico" />}>
          <GraficoCarbon tipo="linea" datos={filasDeGrafico(series)} opciones={opciones} />
        </Suspense>
      </div>
      {rotulos.length > 0 && (
        <ul
          aria-label="Valores del inicio, el corte y el final"
          className="cds--type-helper-text-01"
          style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexWrap: "wrap", gap: "4px 24px" }}
        >
          {rotulos.map((r) => (
            <li key={r.etiqueta}>
              <strong>{`${r.etiqueta}, ${r.periodo}: `}</strong>
              {r.partes.join(" · ")}
            </li>
          ))}
        </ul>
      )}
      <figcaption className="cds--type-helper-text-01">
        {(() => {
          const partes = ORDEN_DE_ROLES.filter((r) => series.some((s) => s.rol === r)).map((r) => LEYENDA_DE_ROL[r]);
          return partes.length > 0 ? `${partes.join(" · ")}.` : "";
        })()}
      </figcaption>
      <details className="silice-curva__tabla">
        <summary className="cds--type-body-compact-01">Ver como tabla</summary>
        <TablaDensa etiqueta={`Montos de ${titulo}`} columnas={columnas} filas={filas} />
      </details>
    </figure>
  );
}
