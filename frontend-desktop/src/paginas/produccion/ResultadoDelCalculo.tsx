import type { BarChartOptions, ChartTabularData } from "@carbon/charts-react";
import { lazy, Suspense } from "react";
import type { JSX, ReactNode, Ref } from "react";
import type { CalculoDeCosto } from "../../api/produccionPlanta";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import {
  ESCALA_DE_ETIQUETAS,
  escalaDeColor,
  formatoNumeroEsVe,
  slotsPorGrupo,
  useModoEfectivo,
  valorParaDibujar,
} from "../../comun/paletaGraficos";
import { compararDecimales, TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { ConstanciasDelCalculo } from "./ConstanciasDelCalculo";
import { fechaEsVe, mostrarMonto, nombreDelMes } from "./logica";
import { fuenteDelPrecio, resumenDeCalculo } from "./logicaPlanta";
import "./graficosProduccion.scss";

const GraficoCarbon = lazy(() => import("../../comun/GraficoCarbon"));

const CATALOGO_TIPOS = ["Agregado", "Mezcla"] as const;

export interface DetalleGloboProduccion {
  encabezado: string;
  cifra: string;
  nota: string;
  trazo?: string;
}

export interface ConfigBarrasProduccion {
  titulo: string;
  tituloEje: string;
  altura?: string;
  color: { scale: Record<string, string> };
  detalleDeClave: (clave: string) => DetalleGloboProduccion | null;
}

function escaparGlobo(texto: string): string {
  return texto
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

// Lienzo común de barras verticales para las vistas de Producción: una sola escala vertical en es-VE, barras de hasta
// 24 px, paleta por entidad y globo escapado.
export function LienzoBarrasProduccion({
  datos,
  config,
}: {
  datos: ChartTabularData;
  config: ConfigBarrasProduccion;
}): JSX.Element {
  const opciones: BarChartOptions = {
    title: config.titulo,
    height: config.altura ?? "220px",
    bars: { maxWidth: 24 },
    axes: {
      bottom: { mapsTo: "key", scaleType: ESCALA_DE_ETIQUETAS },
      left: {
        mapsTo: "value",
        title: config.tituloEje,
        ticks: { formatter: formatoNumeroEsVe },
      },
    },
    color: config.color,
    tooltip: {
      valueFormatter: formatoNumeroEsVe,
      customHTML: (data: unknown, porOmision: string) => {
        const primero: unknown = Array.isArray(data) ? data[0] : data;
        const clave =
          typeof primero === "object" &&
          primero !== null &&
          "key" in primero &&
          typeof primero.key === "string"
            ? primero.key
            : null;
        const detalle = clave === null ? null : config.detalleDeClave(clave);
        if (!detalle) return porOmision;
        const llave = detalle.trazo
          ? `<span style="display:inline-block;inline-size:0.75rem;border-block-start:2px solid ${escaparGlobo(detalle.trazo)}"></span>`
          : "";
        return (
          `<div style="padding:0.5rem 0.75rem">` +
          `<p style="margin:0 0 0.25rem;font-weight:600">${escaparGlobo(detalle.encabezado)}</p>` +
          `<div style="display:flex;gap:0.5rem;align-items:center">${llave}<strong>${escaparGlobo(detalle.cifra)}</strong><span>${escaparGlobo(detalle.nota)}</span></div>` +
          `</div>`
        );
      },
    },
  };

  return (
    <div
      className="prod-grafica__lienzo"
      role="group"
      aria-label={`Gráfico: ${config.titulo}`}
    >
      <Suspense fallback={<EsqueletoPagina etiqueta="Cargando el gráfico" />}>
        <GraficoCarbon tipo="barras" datos={datos} opciones={opciones} />
      </Suspense>
    </div>
  );
}

interface Props {
  calculo: CalculoDeCosto;
  region: Ref<HTMLElement>;
  // Lo que va debajo de la tabla (la publicación, si la cuenta puede).
  children?: ReactNode;
}

function lecturaDeProductos(calculo: CalculoDeCosto): string {
  const mayor = calculo.productos.reduce((acc, actual) =>
    compararDecimales(actual.por_tonelada, acc.por_tonelada) > 0 ? actual : acc,
  );
  const montoMayor = `${mostrarMonto(mayor.presentado)} ${calculo.moneda}/t`;
  if (calculo.productos.length === 1) {
    return `${mayor.codigo} queda en ${montoMayor} (sin redondear: ${formatoEsVe(mayor.por_tonelada)} ${calculo.moneda}/t)`;
  }
  return `el mayor costo unitario corresponde a ${mayor.codigo} con ${montoMayor}; los agregados reparten la cantera y las mezclas suman su receta y la planta`;
}

// El cálculo tal como lo guardó el servidor: costo por tonelada de cada producto (presentado con dos decimales y el
// valor exacto aparte, en su propia columna), los totales de cada centro y la fuente con que quedará el precio. Nada
// de esto se calcula aquí: solo se escribe con coma decimal y punto de miles.
export function ResultadoDelCalculo({
  calculo,
  region,
  children,
}: Props): JSX.Element {
  const modo = useModoEfectivo();
  const resumen = resumenDeCalculo(calculo.instantanea);
  const columnas: ColumnaDensa[] = [
    { clave: "codigo", titulo: "Producto" },
    { clave: "tipo", titulo: "Tipo" },
    {
      clave: "presentado",
      titulo: `Costo por tonelada (redondeado, ${calculo.moneda})`,
      numerica: true,
      presentar: mostrarMonto,
    },
    {
      clave: "exacto",
      titulo: `Costo exacto (sin redondear, ${calculo.moneda})`,
      numerica: true,
      presentar: formatoEsVe,
    },
  ];
  const filas: FilaDensa[] = calculo.productos.map((p) => ({
    id: p.codigo,
    codigo: p.codigo,
    tipo: resumen.agregados.includes(p.codigo) ? "Agregado" : "Mezcla",
    presentado: p.presentado,
    exacto: p.por_tonelada,
  }));

  const tiposPresentes = CATALOGO_TIPOS.filter((t) =>
    filas.some((f) => f["tipo"] === t),
  );
  const color = escalaDeColor(
    modo,
    slotsPorGrupo(tiposPresentes, CATALOGO_TIPOS),
  );
  const tituloGrafico = `Costo por tonelada por producto (${calculo.moneda}/t)`;

  return (
    <section
      ref={region}
      tabIndex={-1}
      aria-label="Resultado del cálculo"
      className="planta-resultado"
    >
      <h2 className="cds--type-heading-compact-02">Cálculo n.º {calculo.id}</h2>
      <p className="cds--type-body-compact-01">
        Período {nombreDelMes(calculo.periodo)}, en {calculo.moneda}. Calculado
        por {calculo.usuario}
        {calculo.registrado
          ? ` el ${fechaEsVe(calculo.registrado.slice(0, 10))}`
          : ""}
        . Fuente:{" "}
        <span className="silice-cifra">
          {fuenteDelPrecio(calculo.periodo, calculo.id)}
        </span>
      </p>
      {filas.length > 0 ? (
        <figure className="prod-grafica" aria-label={tituloGrafico}>
          <LienzoBarrasProduccion
            datos={calculo.productos.map((p) => ({
              group: resumen.agregados.includes(p.codigo)
                ? "Agregado"
                : "Mezcla",
              key: p.codigo,
              value: valorParaDibujar(p.presentado),
            }))}
            config={{
              titulo: tituloGrafico,
              tituloEje: `Costo (${calculo.moneda}/t)`,
              altura: "240px",
              color,
              detalleDeClave: (codigo) => {
                const prod = calculo.productos.find((p) => p.codigo === codigo);
                if (!prod) return null;
                const tipo = resumen.agregados.includes(prod.codigo)
                  ? "Agregado"
                  : "Mezcla";
                return {
                  encabezado: `${prod.codigo} · ${tipo}`,
                  cifra: `${mostrarMonto(prod.presentado)} ${calculo.moneda}/t`,
                  nota: `Exacto: ${formatoEsVe(prod.por_tonelada)} ${calculo.moneda}/t`,
                  trazo: color.scale[tipo],
                };
              },
            }}
          />
          <ul
            className="prod-grafica__rotulos cds--type-helper-text-01"
            aria-label="Costo en el extremo de cada barra"
          >
            {calculo.productos.map((p) => {
              const tipo = resumen.agregados.includes(p.codigo)
                ? "Agregado"
                : "Mezcla";
              return (
                <li key={p.codigo} className="prod-grafica__rotulo">
                  <span
                    className="prod-grafica__muestra"
                    style={{ backgroundColor: color.scale[tipo] }}
                    aria-hidden="true"
                  />
                  <span>
                    <strong>{p.codigo}</strong>
                    {` (${tipo}): ${mostrarMonto(p.presentado)} ${calculo.moneda}/t`}
                  </span>
                </li>
              );
            })}
          </ul>
          <p className="prod-grafica__lectura cds--type-body-compact-01">
            {`Qué muestra: el costo propio por tonelada de cada producto en ${nombreDelMes(calculo.periodo)}, expresado en ${calculo.moneda}. Qué leer: ${lecturaDeProductos(calculo)}.`}
          </p>
          <details className="prod-grafica__tabla">
            <summary className="cds--type-body-compact-01">
              Ver como tabla
            </summary>
            <TablaDensa
              etiqueta={`Costo por tonelada de ${nombreDelMes(calculo.periodo)}`}
              columnas={columnas}
              filas={filas}
            />
          </details>
        </figure>
      ) : (
        <p className="cds--type-body-compact-01">
          Este cálculo no tiene costos por tonelada: todo pasa al mes siguiente.
        </p>
      )}
      <ul
        className="planta-lista cds--type-body-compact-01"
        aria-label="Totales del período"
      >
        {resumen.totalCantera !== null && (
          <li>
            Total de la cantera: {mostrarMonto(resumen.totalCantera)}{" "}
            {calculo.moneda}
          </li>
        )}
        {resumen.totalPlanta !== null && (
          <li>
            Total de la planta: {mostrarMonto(resumen.totalPlanta)}{" "}
            {calculo.moneda}
          </li>
        )}
      </ul>
      <ConstanciasDelCalculo calculo={calculo} />
      {calculo.publicado && (
        <p className="cds--type-body-compact-01">
          Ya se publicó en la lista n.º {calculo.publicado.lista_id} (carpeta «
          {calculo.publicado.caso}») el{" "}
          {fechaEsVe(calculo.publicado.registrado.slice(0, 10))}. Un cálculo se
          publica una sola vez; para otro precio, recalcule.
        </p>
      )}
      <p className="planta-nota cds--type-body-compact-01">
        Código de verificación del cálculo (SHA-256, comprueba que no cambió):{" "}
        <span className="silice-cifra">{calculo.huella}</span>. Recalcular crea
        otro cálculo; el anterior queda intacto.
      </p>
      {children}
    </section>
  );
}
