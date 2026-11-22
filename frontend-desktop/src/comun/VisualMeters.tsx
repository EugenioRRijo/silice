import { useEffect, useState } from "react";
import { formatoEsVe } from "../indicadores/formatoEsVe";
import "./VisualMeters.scss";

function prefiereMenosMovimiento(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return true;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

// Progreso suave (cubic-out) 0 -> 1 al montar o cambiar clave; instantaneo con prefers-reduced-motion o jsdom.
function useLoadProgress(durationMs = 680, triggerKey?: string | number): number {
  const reducido = prefiereMenosMovimiento() || typeof requestAnimationFrame !== "function";
  const [animProgress, setAnimProgress] = useState(() => (reducido ? 1 : 0));

  useEffect(() => {
    if (reducido) return;
    let rafId = 0;
    const start = performance.now();

    const tick = (now: number) => {
      const t = Math.max(0, Math.min(1, (now - start) / durationMs));
      const eased = 1 - Math.pow(1 - t, 3);
      setAnimProgress(eased);
      if (t < 1) rafId = requestAnimationFrame(tick);
    };

    rafId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafId);
  }, [durationMs, triggerKey, reducido]);

  return reducido ? 1 : animProgress;
}

function formatearDecimal(valor: number, decimales = 2): string {
  if (!Number.isFinite(valor)) return "0";
  return formatoEsVe(valor.toFixed(decimales));
}

/* 1. Indicador circular animado (RadialGauge) */
export interface RadialGaugeProps {
  value: number;
  label: string;
  sublabel?: string;
  tone?: "gold" | "emerald" | "crimson" | "charcoal";
  size?: number;
}

export function RadialGauge({ value, label, sublabel, tone = "gold", size = 96 }: RadialGaugeProps) {
  const clamped = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
  const progress = useLoadProgress(720, `${label}-${clamped}`);
  const animatedValue = clamped * progress;

  const strokeWidth = size >= 96 ? 10 : 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (animatedValue / 100) * circumference;

  const strokeColor =
    tone === "emerald" ? "#168a4c" : tone === "crimson" ? "#b91c1c" : tone === "charcoal" ? "#222427" : "#e5b21a";
  const trackColor = tone === "emerald" ? "#dcfce7" : tone === "crimson" ? "#fee2e2" : "#eae8e1";

  return (
    <div className="silice-radial">
      <div className="silice-radial__aro" style={{ inlineSize: size, blockSize: size }}>
        <svg width={size} height={size} className="silice-radial__svg" role="img" aria-label={`${label}: ${formatearDecimal(clamped, 1)} %`}>
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={trackColor} strokeWidth={strokeWidth} />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={strokeColor}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
          />
        </svg>
        <div className="silice-radial__centro" aria-hidden="true">
          <span className="silice-radial__cifra">{`${formatearDecimal(animatedValue, 1)} %`}</span>
        </div>
      </div>
      <div className="silice-radial__texto">
        <p className="silice-radial__etiqueta">{label}</p>
        {sublabel && <p className="silice-radial__sub">{sublabel}</p>}
      </div>
    </div>
  );
}

/* 2. Grafico circular interactivo con leyenda dividida por lineas finas (AnimatedDonutChart) */
export interface DonutSegment {
  label: string;
  value: number;
  valueText?: string;
  color: string;
  subtext?: string;
}

export function AnimatedDonutChart({
  segments,
  centerLabel,
  centerValue,
  unit = "",
  size = 176,
}: {
  segments: DonutSegment[];
  centerLabel: string;
  centerValue: string;
  unit?: string;
  size?: number;
}) {
  const positivos = segments.filter((s) => Number.isFinite(s.value) && s.value > 0);
  const total = positivos.reduce((acc, s) => acc + s.value, 0) || 1;
  const progress = useLoadProgress(800, `${centerValue}-${positivos.length}`);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const strokeWidth = 22;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  const arcs = segments.reduce<
    (DonutSegment & { val: number; pct: number; startOffset: number; fraction: number })[]
  >((acc, seg) => {
    const val = Number.isFinite(seg.value) && seg.value > 0 ? seg.value : 0;
    const fraction = val / total;
    const prev = acc.at(-1);
    const startOffset = prev ? prev.startOffset + prev.fraction : 0;
    acc.push({ ...seg, val, pct: fraction * 100, startOffset, fraction });
    return acc;
  }, []);

  const activeSeg = hoveredIdx !== null ? arcs[hoveredIdx] : null;

  return (
    <div className="silice-donut">
      <div className="silice-donut__aro" style={{ inlineSize: size, blockSize: size }}>
        <svg width={size} height={size} className="silice-donut__svg" role="img" aria-label={`Gráfico circular: ${centerLabel}`}>
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#efece5" strokeWidth={strokeWidth} />
          {arcs.map((arc, idx) => {
            if (arc.val <= 0) return null;
            const visibleLen = Math.max(0, arc.fraction * circumference * progress - 2);
            const dashArray = `${visibleLen} ${circumference}`;
            const dashOffset = -(arc.startOffset * circumference * progress);
            const hovered = hoveredIdx === idx;
            return (
              <circle
                key={arc.label}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke={arc.color}
                strokeWidth={hovered ? strokeWidth + 4 : strokeWidth}
                strokeDasharray={dashArray}
                strokeDashoffset={dashOffset}
                className="silice-donut__segmento"
                onMouseEnter={() => setHoveredIdx(idx)}
                onMouseLeave={() => setHoveredIdx(null)}
              />
            );
          })}
        </svg>
        <div className="silice-donut__centro" aria-hidden="true">
          <span className="silice-donut__centro-titulo">{activeSeg ? activeSeg.label : centerLabel}</span>
          <span className="silice-donut__centro-valor">
            {activeSeg ? `${formatearDecimal(activeSeg.pct, 1)} %` : centerValue}
          </span>
          {activeSeg ? (
            <span className="silice-donut__centro-unidad">
              {activeSeg.valueText ?? `${formatearDecimal(activeSeg.val, unit ? 2 : 0)}${unit ? ` ${unit}` : ""}`}
            </span>
          ) : (
            unit && <span className="silice-donut__centro-unidad">{unit}</span>
          )}
        </div>
      </div>

      <ul className="silice-donut__leyenda" aria-label={`Detalle de ${centerLabel}`}>
        {arcs.map((arc, idx) => (
          <li
            key={arc.label}
            className={`silice-donut__item${hoveredIdx === idx ? " silice-donut__item--activo" : ""}`}
            onMouseEnter={() => setHoveredIdx(idx)}
            onMouseLeave={() => setHoveredIdx(null)}
          >
            <div className="silice-donut__item-izq">
              <span className="silice-donut__muestra" style={{ backgroundColor: arc.color }} aria-hidden="true" />
              <div className="silice-donut__item-texto">
                <span className="silice-donut__item-nombre">{arc.label}</span>
                {arc.subtext && <span className="silice-donut__item-sub">{arc.subtext}</span>}
              </div>
            </div>
            <div className="silice-donut__item-der">
              <span className="silice-donut__item-valor">
                {arc.valueText ?? `${formatearDecimal(arc.val, unit ? 2 : 0)}${unit ? ` ${unit}` : ""}`}
              </span>
              <span className="silice-donut__item-pct">{`${formatearDecimal(arc.pct, 1)} %`}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* 3. Grafico de barras animado (vertical u horizontal, linea base en cero) */
export interface BarDatum {
  id: string;
  label: string;
  sublabel?: string;
  value: number;
  secondaryValue?: number;
  valueLabel: string;
  secondaryLabel?: string;
  color?: string;
  secondaryColor?: string;
}

export function AnimatedBarChart({
  items,
  maxValue,
  orientation = "vertical",
  primaryLegend,
  secondaryLegend,
  height = 200,
}: {
  items: BarDatum[];
  maxValue?: number;
  orientation?: "vertical" | "horizontal";
  primaryLegend?: string;
  secondaryLegend?: string;
  height?: number;
}) {
  const progress = useLoadProgress(760, `${orientation}-${items.map((i) => i.value).join("-")}`);
  const computedMax = maxValue ?? Math.max(1, ...items.flatMap((i) => [Math.max(0, i.value), Math.max(0, i.secondaryValue ?? 0)]));

  if (orientation === "horizontal") {
    return (
      <div className="silice-barras-h">
        {items.map((item) => {
          const pct = Math.min(100, Math.max(item.value > 0 ? 3 : 0, (item.value / computedMax) * 100)) * progress;
          const secPct =
            item.secondaryValue !== undefined
              ? Math.min(100, Math.max(item.secondaryValue > 0 ? 2 : 0, (item.secondaryValue / computedMax) * 100)) * progress
              : null;
          return (
            <div key={item.id} className="silice-barras-h__fila">
              <div className="silice-barras-h__cabecera">
                <div className="silice-barras-h__nombre">
                  <strong>{item.label}</strong>
                  {item.sublabel && <span className="silice-barras-h__sub">{item.sublabel}</span>}
                </div>
                <span className="silice-barras-h__valor">{item.valueLabel}</span>
              </div>
              <div className="silice-barras-h__pista">
                <div className="silice-barras-h__relleno" style={{ inlineSize: `${pct}%`, backgroundColor: item.color ?? "#222427" }} />
              </div>
              {secPct !== null && (
                <div className="silice-barras-h__pista silice-barras-h__pista--sec">
                  <div
                    className="silice-barras-h__relleno"
                    style={{ inlineSize: `${secPct}%`, backgroundColor: item.secondaryColor ?? "#e5b21a" }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  const primarySwatch = items.find((i) => i.color)?.color ?? "#222427";
  const secondarySwatch = items.find((i) => i.secondaryColor)?.secondaryColor ?? "#e5b21a";
  const maxBarPx = Math.max(48, height - 28);

  return (
    <div className="silice-barras-v">
      {(primaryLegend || secondaryLegend) && (
        <div className="silice-barras-v__leyenda">
          {primaryLegend && (
            <span className="silice-barras-v__leyenda-item">
              <span className="silice-barras-v__muestra" style={{ backgroundColor: primarySwatch }} aria-hidden="true" />
              {primaryLegend}
            </span>
          )}
          {secondaryLegend && (
            <span className="silice-barras-v__leyenda-item">
              <span className="silice-barras-v__muestra" style={{ backgroundColor: secondarySwatch }} aria-hidden="true" />
              {secondaryLegend}
            </span>
          )}
        </div>
      )}

      <div className="silice-barras-v__lienzo">
        <div className="silice-barras-v__area" style={{ blockSize: height }}>
          <div className="silice-barras-v__rejilla" aria-hidden="true">
            {[100, 75, 50, 25, 0].map((tick) => {
              const bottomPx = (tick / 100) * maxBarPx;
              return (
                <div key={tick} className="silice-barras-v__linea" style={{ insetBlockEnd: `${bottomPx}px` }}>
                  <span className="silice-barras-v__tick">
                    {maxValue === 100 ? `${tick} %` : formatearDecimal((computedMax * tick) / 100, 0)}
                  </span>
                  <div className={`silice-barras-v__trazo${tick === 0 ? " silice-barras-v__trazo--base" : ""}`} />
                </div>
              );
            })}
          </div>

          <div className="silice-barras-v__columnas">
            {items.map((item) => {
              const primaryH = Math.max(item.value > 0 ? 4 : 0, (Math.max(0, item.value) / computedMax) * maxBarPx * progress);
              const secondaryH =
                item.secondaryValue !== undefined
                  ? Math.max(item.secondaryValue > 0 ? 4 : 0, (Math.max(0, item.secondaryValue) / computedMax) * maxBarPx * progress)
                  : null;
              return (
                <div key={item.id} className="silice-barras-v__grupo">
                  <div className="silice-barras-v__par">
                    <div className="silice-barras-v__col">
                      <span className="silice-barras-v__cifra">{item.valueLabel}</span>
                      <div
                        className="silice-barras-v__barra"
                        style={{ blockSize: `${primaryH}px`, backgroundColor: item.color ?? "#222427" }}
                      />
                    </div>
                    {secondaryH !== null && (
                      <div className="silice-barras-v__col">
                        <span className="silice-barras-v__cifra silice-barras-v__cifra--sec">{item.secondaryLabel ?? ""}</span>
                        <div
                          className="silice-barras-v__barra"
                          style={{ blockSize: `${secondaryH}px`, backgroundColor: item.secondaryColor ?? "#e5b21a" }}
                        />
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="silice-barras-v__eje-x">
          {items.map((item) => (
            <div key={`${item.id}-x`} className="silice-barras-v__rotulo">
              <span className="silice-barras-v__rotulo-principal" title={item.label}>
                {item.label}
              </span>
              {item.sublabel && (
                <span className="silice-barras-v__rotulo-sub" title={item.sublabel}>
                  {item.sublabel}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* 4. Medidor de rango de riesgo (Base / P50 / P80 / P95 opcional) */
export function RiskRangeMeter({
  base,
  p50,
  p80,
  p95,
  currency,
  baseText,
  p50Text,
  p80Text,
  p95Text,
}: {
  base: number;
  p50: number;
  p80: number;
  p95?: number;
  currency: string;
  baseText?: string;
  p50Text?: string;
  p80Text?: string;
  p95Text?: string;
}) {
  const maxVal = Math.max(p95 ?? 0, p80, p50, base * 1.05, 1);
  const progress = useLoadProgress(720, `${base}-${p80}-${p95 ?? 0}`);
  const pct = (v: number) => Math.min(100, Math.max(6, (Math.max(0, v) / maxVal) * 100)) * progress;
  const delta = (v: number) => {
    if (base <= 0) return "0,0 %";
    const diff = ((v - base) / base) * 100;
    const signo = diff > 0 ? "+" : "";
    return `${signo}${formatearDecimal(diff, 1)} %`;
  };

  const filas = [
    {
      label: "Presupuesto base vigente",
      value: base,
      text: baseText ?? `${formatearDecimal(base)} ${currency}`,
      color: "#222427",
      delta: "0,0 %",
    },
    {
      label: "Escenario probable (P50)",
      value: p50,
      text: p50Text ?? `${formatearDecimal(p50)} ${currency}`,
      color: "#5b6270",
      delta: delta(p50),
    },
    {
      label: "Exposición recomendada (P80)",
      value: p80,
      text: p80Text ?? `${formatearDecimal(p80)} ${currency}`,
      color: "#e5b21a",
      delta: delta(p80),
    },
    ...(p95 !== undefined
      ? [
          {
            label: "Estrés extremo (P95)",
            value: p95,
            text: p95Text ?? `${formatearDecimal(p95)} ${currency}`,
            color: "#b91c1c",
            delta: delta(p95),
          },
        ]
      : []),
  ];

  return (
    <div className="silice-riesgo-medidor" role="group" aria-label="Rango de exposición de costos">
      {filas.map((r) => (
        <div key={r.label} className="silice-riesgo-medidor__fila">
          <div className="silice-riesgo-medidor__cabecera">
            <span className="silice-riesgo-medidor__nombre">{r.label}</span>
            <span className="silice-riesgo-medidor__valor">
              {r.text} <span className="silice-riesgo-medidor__delta">({r.delta})</span>
            </span>
          </div>
          <div className="silice-riesgo-medidor__pista">
            <div className="silice-riesgo-medidor__barra" style={{ inlineSize: `${pct(r.value)}%`, backgroundColor: r.color }} />
          </div>
        </div>
      ))}
    </div>
  );
}

