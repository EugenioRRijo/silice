import type { JSX, ReactNode, Ref } from "react";
import type { ComprobacionDeLaObra, ProyeccionDeLaObra } from "../../api/riesgo";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa } from "../../comun/TablaDensa";
import { RiskRangeMeter } from "../../comun/VisualMeters";
import { formatoEsVe, fechaEsVe } from "../../indicadores/formatoEsVe";
import { MAS_EMPUJAN, monto } from "./logica";

interface Props<T> {
  datos: T;
  region: Ref<HTMLElement>;
  // Lo que va al pie del resultado (la descarga del informe).
  children?: ReactNode;
}

interface PropsDeLaProyeccion extends Props<ProyeccionDeLaObra> {
  // Si la proyección se pidió con alguna serie elegida (el mapa enviado no iba vacío).
  conSeries: boolean;
}

// Sin ningún insumo que empuje. En USD un insumo sin serie queda fijo (en Bs sigue a la tasa): sin ninguna serie elegida
// se dice dónde elegirla (prueba en vivo del 2026-11-18, la demo salía plana sin explicarlo); con series elegidas, que no
// variaron (si hubieran bajado, la contribución traería montos negativos y se verían en la tabla).
const QUIETO = "Ningún insumo se movió con la historia usada.";
const QUIETO_EN_USD =
  "En una obra en USD solo se mueven los insumos que siguen una serie: elíjala en «Serie que mueve cada insumo».";
const QUIETO_CON_SERIES =
  "Ningún insumo se movió con la historia usada: las series elegidas no variaron en los meses de historia usados.";

function textoQuieto(moneda: string, conSeries: boolean): string {
  if (moneda !== "USD") return QUIETO;
  return conSeries ? QUIETO_CON_SERIES : `${QUIETO} ${QUIETO_EN_USD}`;
}

function columnasDelRango(m: (exacto: string) => string): ColumnaDensa[] {
  return [
    { clave: "cifra", titulo: "Cifra", ordenable: false },
    { clave: "monto", titulo: "Monto", numerica: true, ordenable: false, presentar: m },
  ];
}

function filasDelRango(datos: ProyeccionDeLaObra) {
  return [
    { id: "base", cifra: "Presupuesto base vigente", monto: datos.total_base },
    { id: "p50", cifra: "Costo probable (P50)", monto: datos.p50 },
    { id: "p80", cifra: "Costo conservador (P80)", monto: datos.p80 },
    { id: "reserva", cifra: "Reserva recomendada para cubrir el P80", monto: datos.reserva },
  ];
}

// La proyección como la manda el servidor: P50, P80, la reserva que cubre el P80 y los insumos que más la empujan. Nada
// se calcula aquí; los montos exactos se leen en centésimas con coma decimal y punto de miles.
export function ResultadoDeLaProyeccion({ datos, region, conSeries, children }: PropsDeLaProyeccion): JSX.Element {
  const m = (exacto: string) => monto(exacto, datos.moneda);
  const columnas: ColumnaDensa[] = [
    { clave: "insumo", titulo: "Insumo", ordenable: false },
    { clave: "monto", titulo: "Cuánto sube el total", numerica: true, ordenable: false, presentar: m },
  ];
  const filas = datos.contribucion.slice(0, MAS_EMPUJAN).map((c) => ({ id: c.insumo, insumo: c.insumo, monto: c.monto }));
  const desde = datos.inicio_de === "linea_base" ? "de la línea base" : "declarado";
  return (
    <section ref={region} tabIndex={-1} aria-label="Resultado de la proyección" className="riesgo-resultado">
      <h2 className="cds--type-heading-compact-02">Proyección</h2>
      <p className="riesgo-nota cds--type-body-compact-01">
        {`Inicio ${desde}: ${fechaEsVe(datos.inicio)}, ${formatoEsVe(String(datos.meses))} meses. `}
        {`${formatoEsVe(String(datos.trayectorias))} simulaciones con semilla ${datos.semilla}, sobre ${datos.meses_usados} meses completos de historia.`}
      </p>
      <dl className="riesgo-cifras">
        <dt>Total base</dt>
        <dd className="silice-cifra">{m(datos.total_base)}</dd>
        <dt>Costo probable (P50: no se supera en la mitad de las simulaciones)</dt>
        <dd className="silice-cifra">{m(datos.p50)}</dd>
        <dt>Costo conservador (P80: no se supera en 8 de cada 10 simulaciones)</dt>
        <dd className="silice-cifra">{m(datos.p80)}</dd>
        <dt>Reserva recomendada para cubrir el P80</dt>
        <dd className="silice-cifra">{m(datos.reserva)}</dd>
      </dl>
      {/* El mismo P50 y P80 de arriba, dibujados: el número solo da el largo de la barra y lo que se lee es el monto de la API
          en centésimas. Sin variación contra la base: la API no la manda y la pantalla no la calcula. */}
      <RiskRangeMeter
        puntos={[
          { rotulo: "Presupuesto base vigente", valor: Number(datos.total_base), texto: m(datos.total_base), tipo: "plan" },
          { rotulo: "Costo probable (P50)", valor: Number(datos.p50), texto: m(datos.p50), tipo: "pronostico" },
          { rotulo: "Costo conservador (P80)", valor: Number(datos.p80), texto: m(datos.p80), tipo: "pronostico" },
        ]}
      />
      {/* El mismo medidor como tabla (el gráfico no es la única manera de leer las cifras). La API manda P50 y P80, no P10 ni
          P90: la pantalla no los inventa. */}
      <details className="cds--type-body-compact-01">
        <summary>Ver como tabla</summary>
        <TablaDensa etiqueta="Rango de la proyección en cifras" columnas={columnasDelRango(m)} filas={filasDelRango(datos)} />
      </details>
      {filas.length > 0 ? (
        <TablaDensa etiqueta="Los tres insumos que más empujan" columnas={columnas} filas={filas} />
      ) : (
        <p className="riesgo-nota cds--type-body-compact-01">{textoQuieto(datos.moneda, conSeries)}</p>
      )}
      <details className="cds--type-body-compact-01">
        <summary>Supuestos de la proyección</summary>
        <ul>
          {datos.supuestos.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
      </details>
      {children}
    </section>
  );
}

// La prueba con meses pasados: cuántas veces lo que pasó quedó dentro del P80 de lo proyectado en cada corte. Los
// plazos de los cortes se solapan: la cobertura es un indicador, no una probabilidad.
export function ResultadoDeLaComprobacion({ datos, region }: Props<ComprobacionDeLaObra>): JSX.Element {
  return (
    <section ref={region} tabIndex={-1} aria-label="Prueba con meses pasados" className="riesgo-resultado">
      <h2 className="cds--type-heading-compact-02">Prueba con meses pasados</h2>
      <dl className="riesgo-cifras">
        <dt>Cobertura (% de meses cubiertos)</dt>
        <dd className="silice-cifra">{`${formatoEsVe(datos.cobertura_pct)} %`}</dd>
        <dt>Meses cubiertos por el P80</dt>
        <dd className="silice-cifra">{`${formatoEsVe(String(datos.dentro))} de ${formatoEsVe(String(datos.n_cortes))}`}</dd>
        <dt>Meses probados</dt>
        <dd className="silice-cifra">{formatoEsVe(String(datos.n_cortes))}</dd>
      </dl>
      <p className="riesgo-nota cds--type-body-compact-01">
        {`Cada mes probado proyecta ${datos.meses} meses solo con la historia anterior, con ${formatoEsVe(String(datos.trayectorias_por_corte))} simulaciones, y la compara con lo que pasó. Cerca de 80 % o más indica que la proyección habría cubierto bien las subidas pasadas (es una referencia histórica, no una garantía).`}
      </p>
    </section>
  );
}
