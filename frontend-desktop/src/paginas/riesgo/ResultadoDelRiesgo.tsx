import type { JSX, Ref } from "react";
import type { ComprobacionDeLaObra, ProyeccionDeLaObra } from "../../api/riesgo";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa } from "../../comun/TablaDensa";
import { formatoEsVe, fechaEsVe } from "../../indicadores/formatoEsVe";
import { MAS_EMPUJAN, monto } from "./logica";

interface Props<T> {
  datos: T;
  region: Ref<HTMLElement>;
}

// La proyección como la manda el servidor: P50, P80, la reserva que cubre el P80 y los insumos que más la empujan. Nada
// se calcula aquí; los montos exactos se leen en centésimas con coma decimal y punto de miles.
export function ResultadoDeLaProyeccion({ datos, region }: Props<ProyeccionDeLaObra>): JSX.Element {
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
        {`${formatoEsVe(String(datos.trayectorias))} trayectorias con semilla ${datos.semilla}, sobre ${datos.meses_usados} meses completos de historia.`}
      </p>
      <dl className="riesgo-cifras">
        <dt>Total base</dt>
        <dd className="silice-cifra">{m(datos.total_base)}</dd>
        <dt>P50</dt>
        <dd className="silice-cifra">{m(datos.p50)}</dd>
        <dt>P80</dt>
        <dd className="silice-cifra">{m(datos.p80)}</dd>
        <dt>Reserva para cubrir el P80</dt>
        <dd className="silice-cifra">{m(datos.reserva)}</dd>
      </dl>
      {filas.length > 0 ? (
        <TablaDensa etiqueta="Los tres insumos que más empujan" columnas={columnas} filas={filas} />
      ) : (
        <p className="riesgo-nota cds--type-body-compact-01">Ningún insumo se movió con la historia usada.</p>
      )}
      <details className="cds--type-body-compact-01">
        <summary>Supuestos de la proyección</summary>
        <ul>
          {datos.supuestos.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
      </details>
    </section>
  );
}

// La comprobación hacia atrás: cuántas veces lo que pasó quedó dentro del P80 de lo proyectado en cada corte. Los
// plazos de los cortes se solapan: la cobertura es un indicador, no una probabilidad.
export function ResultadoDeLaComprobacion({ datos, region }: Props<ComprobacionDeLaObra>): JSX.Element {
  return (
    <section ref={region} tabIndex={-1} aria-label="Comprobación hacia atrás" className="riesgo-resultado">
      <h2 className="cds--type-heading-compact-02">Comprobación hacia atrás</h2>
      <dl className="riesgo-cifras">
        <dt>Cobertura</dt>
        <dd className="silice-cifra">{`${formatoEsVe(datos.cobertura_pct)} %`}</dd>
        <dt>Cortes dentro del P80</dt>
        <dd className="silice-cifra">{`${formatoEsVe(String(datos.dentro))} de ${formatoEsVe(String(datos.n_cortes))}`}</dd>
        <dt>Número de cortes</dt>
        <dd className="silice-cifra">{formatoEsVe(String(datos.n_cortes))}</dd>
      </dl>
      <p className="riesgo-nota cds--type-body-compact-01">
        {`Cada corte proyecta ${datos.meses} meses solo con la historia anterior, con ${formatoEsVe(String(datos.trayectorias_por_corte))} trayectorias, y lo compara con lo que pasó. Los plazos se solapan: la cobertura es un indicador, no una probabilidad.`}
      </p>
    </section>
  );
}
