import { lazy, Suspense } from "react";
import { AvisoError } from "../../comun/AvisoError";
import { CurvaPlanAvance } from "../../comun/CurvaPlanAvance";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { TablaDensa } from "../../comun/TablaDensa";
import { PALETA_GRAFICOS, colorPorGrupo, formatoNumeroEsVe } from "../../comun/paletaGraficos";
import { formatoMontoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { useCarga } from "../inicio/useCarga";
import {
  datosDeDesglose,
  datosDePareto,
  datosDeVersiones,
  rutaDelTablero,
  seriesDeCurva,
} from "./logica";
import type { Tarjeta, TableroRespuesta } from "./logica";
import "./tablero.scss";

const GraficoCarbon = lazy(() => import("../../comun/GraficoCarbon"));

function Tarjetas({ tarjetas }: { tarjetas: Tarjeta[] }) {
  return (
    <dl className="silice-tablero__tarjetas">
      {tarjetas.map((t) => (
        <div key={t.rotulo} className="silice-tablero__tarjeta">
          <dt className="cds--type-label-01">{t.rotulo}</dt>
          <dd className="cds--type-heading-04" title={t.valor}>
            {formatoMontoEsVe(t.valor)}
          </dd>
          {t.detalle && <dd className="cds--type-helper-text-01">{t.detalle}</dd>}
        </div>
      ))}
    </dl>
  );
}

function Grafico({
  titulo,
  tipo,
  datos,
  eje,
}: {
  titulo: string;
  tipo: "anillo" | "barras";
  datos: { group: string; value: number }[];
  eje?: { abajo: string; izquierda: string };
}) {
  const opciones =
    tipo === "anillo"
      ? {
          title: titulo,
          height: "300px",
          resizable: true,
          donut: { center: { label: "Total", numberFormatter: formatoNumeroEsVe } },
          tooltip: { valueFormatter: formatoNumeroEsVe },
          color: colorPorGrupo(datos.map((d) => d.group)),
        }
      : {
          title: titulo,
          height: "300px",
          resizable: true,
          axes: {
            left: { mapsTo: "group", scaleType: "labels", title: eje?.izquierda },
            bottom: { mapsTo: "value", title: eje?.abajo, ticks: { formatter: formatoNumeroEsVe } },
          },
          legend: { enabled: false },
          tooltip: { valueFormatter: formatoNumeroEsVe },
          color: { scale: Object.fromEntries(datos.map((d) => [d.group, PALETA_GRAFICOS[0]])) },
        };
  return (
    <Suspense fallback={<EsqueletoPagina etiqueta="Cargando el gráfico" />}>
      <GraficoCarbon tipo={tipo} datos={datos} opciones={opciones} />
    </Suspense>
  );
}

function Contenido({ datos }: { datos: TableroRespuesta }) {
  const moneda = datos.moneda ?? "";
  if (datos.version === null) {
    return (
      <EstadoVacio
        titulo="Este proyecto aún no tiene presupuesto guardado"
        descripcion="Elabore un presupuesto y guárdelo para ver aquí su resumen, su curva y su Pareto."
      />
    );
  }
  return (
    <>
      <p className="silice-tablero__nota cds--type-body-compact-01">
        {`Versión ${datos.version} del ${datos.fecha} · ${datos.renglones} renglones · ${moneda}`}
      </p>
      <Tarjetas tarjetas={datos.tarjetas} />

      <section className="silice-tablero__bloque" aria-labelledby="tablero-control">
        <h2 id="tablero-control" className="cds--type-heading-compact-02">
          Control de la obra
        </h2>
        {datos.control?.disponible ? (
          <>
            <Tarjetas tarjetas={datos.control.tarjetas} />
          </>
        ) : (
          <EstadoVacio titulo="Aún no hay control de obra" descripcion={datos.control?.motivo} />
        )}
      </section>

      {datos.curvas && datos.curvas.series.length > 0 && (
        <section className="silice-tablero__bloque" aria-labelledby="tablero-curva">
          <h2 id="tablero-curva" className="cds--type-heading-compact-02">
            Curva del proyecto
          </h2>
          <CurvaPlanAvance titulo={datos.curvas.titulo} series={seriesDeCurva(datos.curvas)} unidad={moneda} />
        </section>
      )}

      {datos.desglose.length > 0 && (
        <section className="silice-tablero__bloque" aria-labelledby="tablero-desglose">
          <h2 id="tablero-desglose" className="cds--type-heading-compact-02">
            Desglose del contrato
          </h2>
          <Grafico titulo="Desglose del contrato" tipo="anillo" datos={datosDeDesglose(datos.desglose)} />
          <TablaDensa
            etiqueta="Desglose del contrato"
            columnas={[
              { clave: "rubro", titulo: "Rubro" },
              { clave: "monto", titulo: `Monto (${moneda})`, numerica: true, presentar: formatoMontoEsVe },
              { clave: "peso", titulo: "Peso", numerica: true },
            ]}
            filas={datos.desglose.map((r) => ({ id: r.rubro, rubro: r.rubro, monto: r.monto, peso: r.peso }))}
          />
        </section>
      )}

      {datos.pareto.length > 0 && (
        <section className="silice-tablero__bloque" aria-labelledby="tablero-pareto">
          <h2 id="tablero-pareto" className="cds--type-heading-compact-02">
            Partidas que más pesan (Pareto)
          </h2>
          <Grafico
            titulo="Partidas que más pesan"
            tipo="barras"
            datos={datosDePareto(datos.pareto)}
            eje={{ abajo: `Total (${moneda})`, izquierda: "Partida" }}
          />
          <TablaDensa
            etiqueta="Partidas que más pesan"
            columnas={[
              { clave: "partida", titulo: "Partida" },
              { clave: "descripcion", titulo: "Descripción" },
              { clave: "total", titulo: `Total (${moneda})`, numerica: true, presentar: formatoMontoEsVe },
              { clave: "peso", titulo: "Peso", numerica: true },
              { clave: "acumulado", titulo: "Acumulado", numerica: true },
            ]}
            filas={datos.pareto.map((f) => ({
              id: f.partida,
              partida: f.partida,
              descripcion: f.descripcion,
              total: f.total,
              peso: f.peso,
              acumulado: f.acumulado,
            }))}
          />
        </section>
      )}

      {datos.versiones.length > 0 && (
        <section className="silice-tablero__bloque" aria-labelledby="tablero-versiones">
          <h2 id="tablero-versiones" className="cds--type-heading-compact-02">
            Versiones del presupuesto
          </h2>
          <Grafico
            titulo="Total por versión"
            tipo="barras"
            datos={datosDeVersiones(datos.versiones)}
            eje={{ abajo: `Total (${moneda})`, izquierda: "Versión" }}
          />
          <TablaDensa
            etiqueta="Versiones del presupuesto"
            columnas={[
              { clave: "version", titulo: "Versión" },
              { clave: "fecha", titulo: "Fecha" },
              { clave: "motivo", titulo: "Motivo" },
              { clave: "costo_directo", titulo: "Costo directo", numerica: true, presentar: formatoMontoEsVe },
              { clave: "total", titulo: "Total", numerica: true, presentar: formatoMontoEsVe },
              { clave: "vigente", titulo: "Vigente" },
            ]}
            filas={datos.versiones.map((v) => ({
              id: v.version,
              version: v.version,
              fecha: v.fecha,
              motivo: v.motivo,
              costo_directo: v.costo_directo,
              total: v.total,
              vigente: v.vigente ? "sí" : "no",
            }))}
          />
        </section>
      )}
    </>
  );
}

function Cargado({ proyecto }: { proyecto: string }) {
  const { alExpirar } = useAplicacion();
  const carga = useCarga<TableroRespuesta>(rutaDelTablero(proyecto), alExpirar);
  if (carga.estado === "cargando") return <EsqueletoPagina etiqueta="Cargando el tablero" />;
  if (carga.estado === "listo") return <Contenido datos={carga.datos} />;
  if (carga.estado === "sin_permiso") return <EstadoVacio titulo="Su cuenta no puede ver el tablero" />;
  if (carga.estado === "no_disponible") {
    return <EstadoVacio titulo="Ese proyecto no existe en este caso" descripcion="Elija otro en la cabecera." />;
  }
  return <AvisoError error={carga.error} titulo="No se pudo cargar el tablero" />;
}

// Tablero del proyecto: el proyecto es el de la cabecera. Solo lectura (`leer_proyecto`); no escribe nada.
export default function PaginaTablero() {
  const { proyecto } = useAplicacion();
  return (
    <div className="silice-tablero silice-pagina">
      <h1 className="cds--type-heading-04">Tablero del proyecto</h1>
      {proyecto === null ? (
        <EstadoVacio titulo="Elija un proyecto" descripcion="El tablero muestra el proyecto elegido en la cabecera." />
      ) : (
        <Cargado proyecto={proyecto} />
      )}
    </div>
  );
}
