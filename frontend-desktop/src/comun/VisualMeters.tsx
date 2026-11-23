import { CheckmarkOutline, WarningAlt } from "@carbon/icons-react";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import type { KeyboardEvent } from "react";
import { TEXTO_SEMANTICA } from "../indicadores/ibcs";
import "./VisualMeters.scss";

// Los medidores del rediseño del 2026-11-21 (anillo, anillo por partes, barras y rango). Contrato de los cuatro:
// - El número solo dibuja (la fracción o el valor que manda la API). La cifra que se lee es el texto que les dan, ya en es-VE
//   (quien llama lo arma con `formatoEsVe` y compañía, sin pasar por Number): ningún medidor calcula, redondea ni formatea
//   una cifra (DESIGN.md, «La pantalla no calcula nada»).
// - Sin dato escriben «—» con «sin dato» para la lectora, nunca «0».
// - Crecen al cargar (Eugenio, 2026-11-22: las animaciones del rediseño se quedan) y con `prefers-reduced-motion: reduce`
//   se pintan ya en su valor final, sin pedir cuadros de animación. La preferencia se escucha: si cambia con la pantalla
//   abierta, el medidor salta a su valor; si se vuelve a permitir el movimiento, crece otra vez desde cero.
// - Los colores salen de la hoja de estilos (tokens), no van en línea; el anillo por partes recibe el color de cada parte
//   de quien lo llama, fijo por entidad.

const MENOS_MOVIMIENTO = "(prefers-reduced-motion: reduce)";
const hayMatchMedia = () => typeof window !== "undefined" && typeof window.matchMedia === "function";

// Sin matchMedia (jsdom, un navegador viejo) se asume movimiento reducido: el medidor se pinta en su valor.
function prefiereMenosMovimiento(): boolean {
  return hayMatchMedia() ? window.matchMedia(MENOS_MOVIMIENTO).matches : true;
}

function alCambiarElMovimiento(avisar: () => void): () => void {
  if (!hayMatchMedia()) return () => {};
  const consulta = window.matchMedia(MENOS_MOVIMIENTO);
  if (typeof consulta.addEventListener !== "function") return () => {};
  consulta.addEventListener("change", avisar);
  return () => consulta.removeEventListener("change", avisar);
}

function usePrefiereMenosMovimiento(): boolean {
  return useSyncExternalStore(alCambiarElMovimiento, prefiereMenosMovimiento, () => true);
}

// Progreso suave (cubic-out) de 0 a 1 al montar o al cambiar la clave; 1 de una vez con movimiento reducido.
function useLoadProgress(durationMs: number, triggerKey: string): number {
  const reducido = usePrefiereMenosMovimiento() || typeof requestAnimationFrame !== "function";
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

const SIN_DATO = "sin dato";

const finito = (n: number | null | undefined): n is number => typeof n === "number" && Number.isFinite(n);
const tieneTexto = (t: string | null | undefined): t is string => typeof t === "string" && t.trim() !== "";
// El texto para un nombre accesible: el dado o «sin dato».
const leible = (t: string | null | undefined): string => (tieneTexto(t) ? t : SIN_DATO);

// «—» a la vista y «sin dato» para la lectora: nunca un cero que no dio el servidor.
export function SinDato() {
  return (
    <span className="silice-sin-dato">
      <span aria-hidden="true">—</span>
      <span className="cds--visually-hidden">{SIN_DATO}</span>
    </span>
  );
}

function Cifra({ texto }: { texto: string | null | undefined }) {
  return tieneTexto(texto) ? <>{texto}</> : <SinDato />;
}

/* 1. Anillo de un porcentaje (RadialGauge) */
export interface RadialGaugeProps {
  label: string;
  // Solo dibuja: la fracción de la API (0.625 es 62,5 % de la vuelta), recortada entre 0 y 1. Sin número no hay arco.
  fraccion: number | null;
  // Lo que se lee en el centro, una sola vez: el texto del servidor ya en es-VE («62,5 %»).
  texto: string | null;
  // La variación IBCS que manda la API (`favorable` del anillo). Sin ella el arco va en la tinta (lo real); con ella, en el
  // verde o el rojo, y nunca solo en el color: al lado del anillo van su ícono y su palabra.
  variacion?: "favorable" | "desfavorable" | null;
  // Línea opcional de referencia visible (ej. «Plan a la fecha: 70 %» o «Meta: ≥ 1,00»).
  referencia?: string | null;
  size?: number;
}

const TONO_DE_LA_VARIACION = { favorable: "emerald", desfavorable: "crimson" } as const;

export function RadialGauge({ label, fraccion, texto, variacion = null, referencia = null, size = 96 }: RadialGaugeProps) {
  const tone = variacion === null ? "charcoal" : TONO_DE_LA_VARIACION[variacion];
  const IconoDeVariacion = variacion === "favorable" ? CheckmarkOutline : WarningAlt;
  const destino = finito(fraccion) ? Math.max(0, Math.min(1, fraccion)) : 0;
  const progress = useLoadProgress(720, `${label}-${destino}`);

  const strokeWidth = size >= 96 ? 10 : 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - destino * progress);

  return (
    <div className="silice-radial">
      <div className="silice-radial__aro" style={{ inlineSize: size, blockSize: size }}>
        <svg width={size} height={size} className="silice-radial__svg" role="img" aria-label={`${label}: ${leible(texto)}`}>
          <circle className="silice-radial__pista" cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={strokeWidth} />
          <circle
            className={`silice-radial__arco silice-radial__arco--${tone}`}
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
          />
        </svg>
        <div className="silice-radial__centro" aria-hidden="true">
          <span className="silice-radial__cifra">
            <Cifra texto={texto} />
          </span>
        </div>
      </div>
      <div className="silice-radial__texto">
        <p className="silice-radial__etiqueta">{label}</p>
        {variacion !== null && (
          <p className={`silice-radial__variacion silice-radial__variacion--${variacion}`}>
            <IconoDeVariacion size={16} aria-hidden="true" />
            <span>{TEXTO_SEMANTICA[variacion]}</span>
          </p>
        )}
        {tieneTexto(referencia) && <p className="cds--type-helper-text-01">{referencia}</p>}
      </div>
    </div>
  );
}

/* 2. Anillo por partes con su leyenda (AnimatedDonutChart) */
export interface DonutSegment {
  // Fija la parte (y su color) aunque cambie el orden o el tamaño.
  id: string;
  label: string;
  // Solo dibuja: el tamaño de la parte. Sin número, o cero, no se dibuja (la leyenda la sigue diciendo).
  value: number;
  // Lo que se lee de la parte, ya en es-VE.
  valueText: string | null;
  // El porcentaje de la parte, solo si lo manda la API (ya en es-VE); el anillo no lo calcula.
  pctText?: string | null;
  // Un color del gráfico o un token (`var(--…)`), fijo por entidad.
  color: string;
}

export function AnimatedDonutChart({
  segments,
  centerLabel,
  centerValue,
  size = 176,
}: {
  segments: DonutSegment[];
  centerLabel: string;
  // Lo que se lee en el centro sin nada resaltado, ya en es-VE.
  centerValue: string | null;
  size?: number;
}) {
  const progress = useLoadProgress(800, segments.map((s) => `${s.id}:${s.value}`).join("|"));
  // Lo resaltado: el ratón manda sobre el foco y el foco sobre lo fijado con Enter.
  const [sobre, setSobre] = useState<number | null>(null);
  const [enfocado, setEnfocado] = useState<number | null>(null);
  const [fijado, setFijado] = useState<number | null>(null);
  // La única parada de Tab de la leyenda (tabindex itinerante): la última enfocada.
  const [parada, setParada] = useState(0);
  const botones = useRef<(HTMLButtonElement | null)[]>([]);

  const strokeWidth = 22;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  const tamanos = segments.map((s) => (finito(s.value) && s.value > 0 ? s.value : 0));
  const total = tamanos.reduce((acc, v) => acc + v, 0);
  const dibujadas = tamanos.filter((v) => v > 0).length;
  // 2 px de la superficie entre partes vecinas; una sola parte cierra la vuelta.
  const hueco = dibujadas > 1 ? 2 : 0;
  const arcos = tamanos.reduce<{ inicio: number; fraccion: number }[]>((acc, v) => {
    const prev = acc.at(-1);
    acc.push({ inicio: prev ? prev.inicio + prev.fraccion : 0, fraccion: total > 0 ? v / total : 0 });
    return acc;
  }, []);

  const indiceActivo = sobre ?? enfocado ?? fijado;
  const activo = indiceActivo !== null ? segments[indiceActivo] : undefined;
  const paradaValida = Math.min(fijado ?? parada, Math.max(0, segments.length - 1));

  const alTeclear = (idx: number) => (e: KeyboardEvent<HTMLButtonElement>) => {
    const ultimo = segments.length - 1;
    const destino: Record<string, number> = {
      ArrowDown: idx === ultimo ? 0 : idx + 1,
      ArrowRight: idx === ultimo ? 0 : idx + 1,
      ArrowUp: idx === 0 ? ultimo : idx - 1,
      ArrowLeft: idx === 0 ? ultimo : idx - 1,
      Home: 0,
      End: ultimo,
    };
    if (e.key === "Escape") {
      setFijado(null);
      return;
    }
    const siguiente = destino[e.key];
    if (siguiente === undefined) return;
    e.preventDefault();
    botones.current[siguiente]?.focus();
  };

  return (
    <div className="silice-donut">
      <div className="silice-donut__aro" style={{ inlineSize: size, blockSize: size }}>
        <svg width={size} height={size} className="silice-donut__svg" role="img" aria-label={`${centerLabel}: ${leible(centerValue)}`}>
          <circle className="silice-donut__pista" cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={strokeWidth} />
          {segments.map((seg, idx) => {
            const arco = arcos[idx]!;
            if (arco.fraccion <= 0) return null;
            const visible = Math.max(0, arco.fraccion * circumference * progress - hueco);
            const resaltada = indiceActivo === idx;
            return (
              <circle
                key={seg.id}
                data-id={seg.id}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                style={{ stroke: seg.color }}
                strokeWidth={resaltada ? strokeWidth + 4 : strokeWidth}
                strokeDasharray={`${visible} ${circumference}`}
                strokeDashoffset={-(arco.inicio * circumference * progress)}
                className={`silice-donut__segmento${resaltada ? " silice-donut__segmento--activo" : ""}`}
                // La lectora y el teclado van por la leyenda (un botón por parte); el arco solo responde al ratón.
                aria-hidden="true"
                onMouseEnter={() => setSobre(idx)}
                onMouseLeave={() => setSobre(null)}
              />
            );
          })}
        </svg>
        <div className="silice-donut__centro" aria-hidden="true">
          <span className="silice-donut__centro-titulo">{activo ? activo.label : centerLabel}</span>
          <span className="silice-donut__centro-valor">
            <Cifra texto={activo ? activo.valueText : centerValue} />
          </span>
          {activo && tieneTexto(activo.pctText) && <span className="silice-donut__centro-unidad">{activo.pctText}</span>}
        </div>
      </div>

      {/* Cada parte es un botón de la leyenda: el foco (Tab una vez y luego flechas, Inicio y Fin) la resalta en el anillo y
          en el centro; Enter o Espacio la deja fijada (aria-pressed) y Esc la suelta. El nombre dice la parte y su cifra. */}
      <ul className="silice-donut__leyenda" aria-label={`Detalle de ${centerLabel}`}>
        {segments.map((seg, idx) => (
          <li key={seg.id} className="silice-donut__fila">
            <button
              type="button"
              ref={(b) => {
                botones.current[idx] = b;
              }}
              className={`silice-donut__item${indiceActivo === idx ? " silice-donut__item--activo" : ""}`}
              tabIndex={idx === paradaValida ? 0 : -1}
              aria-pressed={fijado === idx}
              aria-label={[seg.label, leible(seg.valueText), ...(tieneTexto(seg.pctText) ? [seg.pctText] : [])].join(" ")}
              onFocus={() => {
                setEnfocado(idx);
                setParada(idx);
              }}
              onBlur={() => setEnfocado(null)}
              onClick={() => setFijado((f) => (f === idx ? null : idx))}
              onKeyDown={alTeclear(idx)}
              onMouseEnter={() => setSobre(idx)}
              onMouseLeave={() => setSobre(null)}
            >
              <span className="silice-donut__item-izq">
                <span className="silice-donut__muestra" style={{ backgroundColor: seg.color }} aria-hidden="true" />
                <span className="silice-donut__item-nombre">{seg.label}</span>
              </span>
              <span className="silice-donut__item-der">
                <span className="silice-donut__item-valor">
                  <Cifra texto={seg.valueText} />
                </span>
                {tieneTexto(seg.pctText) && <span className="silice-donut__item-pct">{seg.pctText}</span>}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* 3. Barras de avance real contra el plan, de 0 a 100 % (IBCS: real relleno, plan en contorno) */
export interface BarDatum {
  id: string;
  // El nombre completo: si no cabe, la hoja de estilos lo recorta y el `title` lo dice entero.
  label: string;
  // Solo dibujan: el porcentaje de la API (62.5 es 62,5 %).
  real: number | null;
  plan?: number | null;
  // Lo que se lee sobre cada barra, ya en es-VE.
  realText: string | null;
  planText?: string | null;
}

const MARCAS_DE_LA_ESCALA = [100, 75, 50, 25, 0] as const;

export function AnimatedBarChart({
  items,
  realLegend,
  planLegend,
  height = 200,
}: {
  items: BarDatum[];
  realLegend: string;
  planLegend?: string;
  height?: number;
}) {
  const progress = useLoadProgress(760, items.map((i) => `${i.id}:${i.real}:${i.plan}`).join("|"));
  const maxBarPx = Math.max(48, height - 28);
  // Una barra con valor mide al menos 4 px para que se vea; la animación la lleva de 0 a su alto.
  const alto = (v: number | null | undefined) =>
    finito(v) && v > 0 ? Math.max(4, (Math.min(100, v) / 100) * maxBarPx) * progress : 0;
  const conPlan = items.some((i) => i.plan !== undefined);

  return (
    <div className="silice-barras-v">
      <div className="silice-barras-v__leyenda">
        <span className="silice-barras-v__leyenda-item">
          <span className="silice-barras-v__muestra silice-barras-v__muestra--real" aria-hidden="true" />
          {realLegend}
        </span>
        {conPlan && planLegend && (
          <span className="silice-barras-v__leyenda-item">
            <span className="silice-barras-v__muestra silice-barras-v__muestra--plan" aria-hidden="true" />
            {planLegend}
          </span>
        )}
      </div>

      <div className="silice-barras-v__lienzo">
        <div className="silice-barras-v__area" style={{ blockSize: height }}>
          <div className="silice-barras-v__rejilla" aria-hidden="true">
            {MARCAS_DE_LA_ESCALA.map((tick) => (
              <div key={tick} className="silice-barras-v__linea" style={{ insetBlockEnd: `${(tick / 100) * maxBarPx}px` }}>
                <span className="silice-barras-v__tick">{`${tick} %`}</span>
                <div className={`silice-barras-v__trazo${tick === 0 ? " silice-barras-v__trazo--base" : ""}`} />
              </div>
            ))}
          </div>

          <div className="silice-barras-v__columnas">
            {items.map((item) => {
              const hReal = alto(item.real);
              const hPlan = alto(item.plan);
              return (
                <div key={item.id} className="silice-barras-v__grupo">
                  <div className="silice-barras-v__par">
                    <div className="silice-barras-v__col">
                      <span className="silice-barras-v__cifra">
                        <Cifra texto={item.realText} />
                      </span>
                      <div className="silice-barras-v__barra silice-barras-v__barra--real" style={{ blockSize: `${hReal}px` }} />
                    </div>
                    {item.plan !== undefined && (
                      <div className="silice-barras-v__col">
                        <span className="silice-barras-v__cifra silice-barras-v__cifra--sec">
                          <Cifra texto={item.planText} />
                        </span>
                        <div
                          className="silice-barras-v__barra silice-barras-v__barra--plan"
                          style={{ blockSize: `${hPlan}px`, ...(hPlan === 0 ? { borderWidth: 0 } : {}) }}
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
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* 4. Rango de un costo proyectado (RiskRangeMeter): cada escenario contra lo previsto (IBCS) */
export interface PuntoDelRango {
  rotulo: string;
  // Solo dibuja: el monto de la API.
  valor: number | null;
  // Lo que se lee, ya en es-VE («1.302,46 USD»).
  texto: string | null;
  // «plan»: lo previsto (el presupuesto base), una marca en contorno. «pronostico»: un escenario (P50, P80), una barra
  // achurada que va de la base al escenario.
  tipo: "plan" | "pronostico";
}

// La escala va de la menor a la mayor cifra (no desde cero: contra cero, base, P50 y P80 medirían casi lo mismo). La base
// cruza cada pista con una línea, para comparar cada escenario contra ella; un escenario por debajo va de él a la base.
// El porcentaje del ancho solo dibuja: no se escribe ninguna variación.
export function RiskRangeMeter({ puntos, etiqueta = "Rango de exposición de costos" }: { puntos: PuntoDelRango[]; etiqueta?: string }) {
  const progress = useLoadProgress(720, puntos.map((p) => `${p.rotulo}:${p.valor}`).join("|"));
  const valores = puntos.map((p) => p.valor).filter(finito);
  const menor = valores.length > 0 ? Math.min(...valores) : 0;
  const rango = valores.length > 0 ? Math.max(...valores) - menor : 0;
  const posicion = (v: number) => (rango > 0 ? ((v - menor) / rango) * 100 : 0);
  const base = puntos.find((p) => p.tipo === "plan" && finito(p.valor))?.valor ?? null;
  const enBase = base !== null ? posicion(base) : 0;
  // Una marca en `x` % sin salirse de la pista: se corre hacia dentro lo mismo que avanza.
  const sobre = (x: number) => ({ insetInlineStart: `${x}%`, translate: `-${x}%` });

  return (
    <div className="silice-riesgo-medidor" role="group" aria-label={etiqueta}>
      <p className="silice-riesgo-medidor__nota">
        Cada barra muestra cuánto sube el escenario frente al presupuesto base (la escala no parte de cero).
      </p>
      {puntos.map((p) => {
        const hasta = finito(p.valor) ? posicion(p.valor) : null;
        const ancho = hasta === null ? 0 : Math.abs(hasta - enBase) * progress;
        const desde = hasta !== null && hasta < enBase ? enBase - ancho : enBase;
        return (
          <div key={p.rotulo} className="silice-riesgo-medidor__fila">
            <div className="silice-riesgo-medidor__cabecera">
              <span className="silice-riesgo-medidor__nombre">{p.rotulo}</span>
              <span className="silice-riesgo-medidor__valor">
                <Cifra texto={p.texto} />
              </span>
            </div>
            <div className="silice-riesgo-medidor__pista">
              {p.tipo === "plan"
                ? hasta !== null && <div className="silice-riesgo-medidor__marca" style={sobre(hasta)} />
                : hasta !== null && (
                    <div
                      className="silice-riesgo-medidor__barra silice-riesgo-medidor__barra--pronostico"
                      style={{ insetInlineStart: `${desde}%`, inlineSize: `${ancho}%` }}
                    />
                  )}
              {base !== null && <div className="silice-riesgo-medidor__base" style={sobre(enBase)} aria-hidden="true" />}
            </div>
          </div>
        );
      })}
    </div>
  );
}
