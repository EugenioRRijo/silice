import type { BarChartOptions } from "@carbon/charts-react";
import { lazy, Suspense, useMemo, useState } from "react";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import {
  coloresDeSerie,
  ESCALA_DE_ETIQUETAS,
  escalaDeColor,
  formatoNumeroEsVe,
  slotsPorGrupo,
  useModoEfectivo,
  valorParaDibujar,
} from "../../comun/paletaGraficos";
import { compararDecimales, TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa } from "../../comun/TablaDensa";
import { formatoEsVe, formatoMontoEsVe } from "../../indicadores/formatoEsVe";
import { filasComparacion } from "./logica";
import type { EscenarioRespuesta, EscenariosRespuesta } from "./tipos";

const GraficoCarbon = lazy(() => import("../../comun/GraficoCarbon"));

const CERO_DECIMAL = /^-?0+(?:\.0+)?$/;

function escaparHtml(texto: string): string {
  return texto
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function conMoneda(monto: string, moneda: string): string {
  return formatoMontoEsVe(moneda ? `${monto} ${moneda}` : monto);
}

function diferenciaFirmada(variacion: string, moneda: string): string {
  const limpio = variacion.trim();
  if (CERO_DECIMAL.test(limpio)) return conMoneda("0.00", moneda);
  const prefijo = limpio.startsWith("-") || limpio.startsWith("+") ? "" : "+";
  return conMoneda(`${prefijo}${limpio}`, moneda);
}

function porcentajeFirmado(pct: string): string {
  const limpio = pct.trim();
  if (CERO_DECIMAL.test(limpio)) return `${formatoEsVe("0.00")} %`;
  const prefijo = limpio.startsWith("-") || limpio.startsWith("+") ? "" : "+";
  return `${prefijo}${formatoEsVe(limpio)} %`;
}

function magnitudSinSigno(decimal: string): string {
  const limpio = decimal.trim();
  return limpio.startsWith("-") || limpio.startsWith("+")
    ? limpio.slice(1)
    : limpio;
}

function etiquetasUnicas(escenarios: readonly EscenarioRespuesta[]): string[] {
  const conteo = new Map<string, number>();
  for (const e of escenarios)
    conteo.set(e.nombre, (conteo.get(e.nombre) ?? 0) + 1);
  return escenarios.map((e, i) =>
    (conteo.get(e.nombre) ?? 0) > 1 ? `${e.nombre} (${i + 1})` : e.nombre,
  );
}

function resumenImpacto(
  escenarios: readonly EscenarioRespuesta[],
  moneda: string,
): string {
  if (escenarios.length === 0) return "no hay escenarios comparados";
  if (escenarios.length === 1) {
    const unico = escenarios[0]!;
    if (CERO_DECIMAL.test(unico.variacion.trim())) {
      return `«${unico.nombre}» conserva el mismo total del base (${conMoneda(unico.total, moneda)})`;
    }
    return `«${unico.nombre}» cambia el total en ${diferenciaFirmada(unico.variacion, moneda)} (${porcentajeFirmado(unico.variacion_pct)})`;
  }
  const mayor = escenarios.reduce((acc, actual) =>
    compararDecimales(
      magnitudSinSigno(actual.variacion),
      magnitudSinSigno(acc.variacion),
    ) > 0
      ? actual
      : acc,
  );
  if (CERO_DECIMAL.test(mayor.variacion.trim()))
    return "ningún escenario altera el monto del presupuesto base";
  return `el mayor cambio lo produce «${mayor.nombre}» con ${diferenciaFirmada(mayor.variacion, moneda)} (${porcentajeFirmado(mayor.variacion_pct)})`;
}

function columnasTablaGrafico(moneda: string): ColumnaDensa[] {
  const sufijo = moneda ? ` (${moneda})` : "";
  return [
    { clave: "escenario", titulo: "Escenario", ordenable: false },
    {
      clave: "total",
      titulo: `Total${sufijo}`,
      numerica: true,
      ordenable: false,
      presentar: formatoMontoEsVe,
    },
    {
      clave: "variacion",
      titulo: `Diferencia${sufijo}`,
      numerica: true,
      ordenable: false,
      presentar: (v) => diferenciaFirmada(v, ""),
    },
    {
      clave: "variacion_pct",
      titulo: "En %",
      numerica: true,
      ordenable: false,
      presentar: porcentajeFirmado,
    },
  ];
}

function claveDeGlobo(entrada: unknown): string | null {
  const item: unknown = Array.isArray(entrada) ? entrada[0] : entrada;
  return typeof item === "object" &&
    item !== null &&
    "key" in item &&
    typeof item.key === "string"
    ? item.key
    : null;
}

export function GraficoEscenarios({
  resultado,
  moneda,
}: {
  resultado: EscenariosRespuesta;
  moneda: string;
}) {
  const modo = useModoEfectivo();
  const etiquetas = useMemo(
    () => etiquetasUnicas(resultado.escenarios),
    [resultado.escenarios],
  );

  const [estadoCatalogo, setEstadoCatalogo] = useState<{
    base: string;
    nombres: string[];
  }>({
    base: resultado.codigo_base,
    nombres: etiquetas,
  });
  if (estadoCatalogo.base !== resultado.codigo_base) {
    setEstadoCatalogo({ base: resultado.codigo_base, nombres: etiquetas });
  } else {
    const nuevos = etiquetas.filter((n) => !estadoCatalogo.nombres.includes(n));
    if (nuevos.length > 0)
      setEstadoCatalogo({
        base: resultado.codigo_base,
        nombres: [...estadoCatalogo.nombres, ...nuevos],
      });
  }

  const catalogo = useMemo(() => {
    const base =
      estadoCatalogo.base === resultado.codigo_base
        ? [...estadoCatalogo.nombres]
        : [];
    for (const n of etiquetas) if (!base.includes(n)) base.push(n);
    return base;
  }, [estadoCatalogo, resultado.codigo_base, etiquetas]);

  const tituloGrafico = moneda
    ? `Diferencia frente al presupuesto base (${moneda})`
    : "Diferencia frente al presupuesto base";
  const color = escalaDeColor(modo, slotsPorGrupo(etiquetas, catalogo));
  const datos = resultado.escenarios.map((e, i) => ({
    group: etiquetas[i]!,
    key: etiquetas[i]!,
    value: valorParaDibujar(e.variacion),
  }));

  const opciones: BarChartOptions = {
    title: tituloGrafico,
    height: "260px",
    bars: { maxWidth: 24 },
    axes: {
      bottom: { mapsTo: "key", scaleType: ESCALA_DE_ETIQUETAS },
      left: {
        mapsTo: "value",
        title: moneda ? `Diferencia (${moneda})` : "Diferencia",
        includeZero: true,
        ticks: { formatter: formatoNumeroEsVe },
        thresholds: [
          {
            value: 0,
            label: `Base (${resultado.codigo_base}): ${conMoneda(resultado.total_base, moneda)}`,
            fillColor: coloresDeSerie(modo).neutro2,
          },
        ],
      },
    },
    color,
    tooltip: {
      valueFormatter: formatoNumeroEsVe,
      customHTML: (data: unknown, porOmision: string) => {
        const clave = claveDeGlobo(data);
        if (clave === null) return porOmision;
        const idx = etiquetas.indexOf(clave);
        const esc = idx >= 0 ? resultado.escenarios[idx] : undefined;
        if (!esc) return porOmision;
        const trazo = color.scale[clave];
        const llave = trazo
          ? `<span style="display:inline-block;inline-size:0.75rem;border-block-start:2px solid ${escaparHtml(trazo)}"></span>`
          : "";
        return (
          `<div style="padding:0.5rem 0.75rem">` +
          `<p style="margin:0 0 0.25rem;font-weight:600">${escaparHtml(clave)}</p>` +
          `<div style="display:flex;gap:0.5rem;align-items:center">${llave}<strong>${escaparHtml(diferenciaFirmada(esc.variacion, moneda))}</strong><span>(${escaparHtml(porcentajeFirmado(esc.variacion_pct))})</span></div>` +
          `<p style="margin:0.25rem 0 0">Total del escenario: ${escaparHtml(conMoneda(esc.total, moneda))}</p>` +
          `</div>`
        );
      },
    },
  };

  const baseTexto = conMoneda(resultado.total_base, moneda);

  return (
    <figure className="silice-escenarios__grafica" aria-label={tituloGrafico}>
      <div
        className="silice-escenarios__lienzo"
        role="group"
        aria-label={`Gráfico: ${tituloGrafico}. Base ${resultado.codigo_base}: ${baseTexto}.`}
      >
        <Suspense fallback={<EsqueletoPagina etiqueta="Cargando el gráfico" />}>
          <GraficoCarbon tipo="barras" datos={datos} opciones={opciones} />
        </Suspense>
      </div>
      <ul
        className="silice-escenarios__rotulos cds--type-helper-text-01"
        aria-label="Diferencia en el extremo de cada escenario"
      >
        {resultado.escenarios.map((e, i) => {
          const etiqueta = etiquetas[i]!;
          return (
            <li key={`${etiqueta}-${i}`} className="silice-escenarios__rotulo">
              <span
                className="silice-escenarios__muestra"
                style={{ backgroundColor: color.scale[etiqueta] }}
                aria-hidden="true"
              />
              <span>
                <strong>{`${etiqueta}: `}</strong>
                {`${diferenciaFirmada(e.variacion, moneda)} (${porcentajeFirmado(e.variacion_pct)})`}
              </span>
            </li>
          );
        })}
      </ul>
      <p className="silice-escenarios__lectura cds--type-body-compact-01">
        {`Qué muestra: cuánto cambia el total de la obra en cada escenario frente al presupuesto base ${resultado.codigo_base} (${baseTexto}), que permanece sin cambios. Qué leer: las barras sobre cero encarecen la obra y las barras bajo cero la abaratan; ${resumenImpacto(resultado.escenarios, moneda)}.`}
      </p>
      <details className="silice-escenarios__vertabla">
        <summary className="cds--type-body-compact-01">Ver como tabla</summary>
        <TablaDensa
          etiqueta={`Datos de ${tituloGrafico}`}
          columnas={columnasTablaGrafico(moneda)}
          filas={filasComparacion(resultado)}
        />
      </details>
    </figure>
  );
}
