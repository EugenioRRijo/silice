import { lazy, Suspense, useEffect, useRef } from "react";
import { formatoMontoEsVe } from "../indicadores/formatoEsVe";
import { EsqueletoPagina } from "./EsqueletoPagina";
import { colorPorSerie, formatoNumeroEsVe } from "./paletaGraficos";
import { TablaDensa } from "./TablaDensa";

const GraficoCarbon = lazy(() => import("./GraficoCarbon"));

// Curva comun plan / avance / pronostico (tablero y control de obra). El rol decide como se dibuja y no depende solo
// del color: el plan va en trazo continuo fino, lo real en continuo grueso y el pronostico discontinuo.
export type RolDeSerie = "plan" | "real" | "pronostico";

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

export const TRAZO_DE_PRONOSTICO = "6 4";
export const GROSOR: Record<RolDeSerie, number> = { plan: 1.5, real: 3, pronostico: 2 };

const TEXTO_DE_ROL: Record<RolDeSerie, string> = {
  plan: "plan",
  real: "real",
  pronostico: "pronostico (discontinuo)",
};

// La API nombra los periodos del control «Dia N» (convencion de la regla R7): se leen «Día N».
export function periodoLegible(periodo: string): string {
  return periodo.replace(/^Dia (?=[0-9])/, "Día ");
}

export function filasDeGrafico(series: SerieDeCurva[]): { group: string; key: string; value: number }[] {
  return series.flatMap((s) =>
    s.puntos.map((p) => ({ group: s.nombre, key: periodoLegible(p.periodo), value: Number(p.valor) })),
  );
}

// Los periodos en el orden en que aparecen (la primera serie que los trae manda).
export function periodos(series: SerieDeCurva[]): string[] {
  const vistos: string[] = [];
  for (const s of series) for (const p of s.puntos) if (!vistos.includes(p.periodo)) vistos.push(p.periodo);
  return vistos;
}

// Carbon no trae el discontinuo ni el grosor por serie como opcion: se aplican sobre los trazos ya dibujados
// (cada `path.line` guarda su serie en `__data__.name`) y se reaplican cuando el grafico se redibuja.
export function aplicarTrazos(raiz: ParentNode, series: SerieDeCurva[]): void {
  const rol = new Map(series.map((s) => [s.nombre, s.rol]));
  raiz.querySelectorAll<SVGPathElement>("path.line").forEach((trazo) => {
    const nombre = (trazo as unknown as { __data__?: { name?: string } }).__data__?.name;
    const r = nombre === undefined ? undefined : rol.get(nombre);
    if (!r) return;
    trazo.style.strokeWidth = String(GROSOR[r]);
    trazo.style.strokeDasharray = r === "pronostico" ? TRAZO_DE_PRONOSTICO : "none";
  });
}

export function CurvaPlanAvance({ titulo, series, unidad }: Props) {
  const contenedor = useRef<HTMLDivElement>(null);

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
  const filas = periodos(series).map((periodo, i) => ({
    id: `p${i}`,
    periodo: periodoLegible(periodo),
    ...Object.fromEntries(series.map((s) => [s.nombre, s.puntos.find((p) => p.periodo === periodo)?.valor ?? "—"])),
  }));

  return (
    <figure className="silice-curva" aria-label={titulo}>
      <div ref={contenedor} className="silice-curva__grafico">
        <Suspense fallback={<EsqueletoPagina etiqueta="Cargando el grafico" />}>
          <GraficoCarbon
            tipo="linea"
            datos={filasDeGrafico(series)}
            opciones={{
              title: titulo,
              height: "320px",
              axes: {
                bottom: { mapsTo: "key", scaleType: "labels" },
                left: { mapsTo: "value", title: unidad ?? "Monto", ticks: { formatter: formatoNumeroEsVe } },
              },
              tooltip: { valueFormatter: formatoNumeroEsVe },
              color: colorPorSerie(series),
              curve: "curveMonotoneX",
              points: { enabled: false },
              toolbar: { enabled: false },
            }}
          />
        </Suspense>
      </div>
      <figcaption className="cds--type-helper-text-01">
        {series.map((s) => `${s.nombre}: ${TEXTO_DE_ROL[s.rol]}`).join(" · ")}
      </figcaption>
      <details className="silice-curva__tabla">
        <summary className="cds--type-body-compact-01">Ver los montos por período</summary>
        <TablaDensa etiqueta={`Montos de ${titulo}`} columnas={columnas} filas={filas} />
      </details>
    </figure>
  );
}
