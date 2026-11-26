import type { BarChartOptions, DonutChartOptions } from "@carbon/charts-react";
import { lazy, Suspense, useContext } from "react";
import { AvisoError } from "../../comun/AvisoError";
import { CurvaPlanAvance } from "../../comun/CurvaPlanAvance";
import { EnlaceComoBoton } from "../../comun/EnlaceComoBoton";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { TablaDensa } from "../../comun/TablaDensa";
import { RadialGauge } from "../../comun/VisualMeters";
import {
  ESCALA_DE_ETIQUETAS,
  formatoNumeroEsVe,
  fusionarOpciones,
  opcionesBase,
  slotsPorGrupo,
  useModoEfectivo,
} from "../../comun/paletaGraficos";
import { fechaEsVe, formatoEsVe, formatoMontoEsVe } from "../../indicadores/formatoEsVe";
import { rutaOPendientes } from "../../marco/espacios";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import { useAplicacion } from "../../shell/contexto";
import { useCarga } from "../../comun/useCarga";
import {
  anillosDePorcentaje,
  centroDelAnillo,
  datosDeDesglose,
  detalleDeTarjeta,
  datosDePareto,
  datosDeVersiones,
  etiquetaDePeso,
  rutaDelTablero,
  seriesDeCurva,
} from "./logica";
import type { Tarjeta, TableroRespuesta } from "./logica";
import "./tablero.scss";

const GraficoCarbon = lazy(() => import("../../comun/GraficoCarbon"));

// Una tarjeta de dinero con su exacto lo lleva en el `title` y para el lector de pantalla (VB-21); las demas, el
// texto de la API en el `title`.
function Tarjetas({ tarjetas, moneda, destacarPrimera = false }: { tarjetas: Tarjeta[]; moneda: string; destacarPrimera?: boolean }) {
  return (
    <dl className="silice-tablero__tarjetas">
      {tarjetas.map((t, i) => (
        <div key={t.rotulo} className="silice-tablero__tarjeta">
          <dt className="cds--type-label-01">{t.rotulo}</dt>
          <dd
            className={destacarPrimera && i === 0 ? "cds--type-heading-04" : "cds--type-heading-03"}
            title={t.exacto ? `Valor exacto: ${formatoEsVe(t.exacto)} ${moneda}`.trim() : formatoMontoEsVe(t.valor)}
          >
            {formatoMontoEsVe(t.valor)}
            {t.exacto && (
              <span className="cds--visually-hidden">{`. Valor exacto: ${formatoEsVe(t.exacto)} ${moneda}`.trimEnd()}</span>
            )}
          </dd>
          {t.detalle && <dd className="cds--type-helper-text-01">{detalleDeTarjeta(t)}</dd>}
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
  etiqueta,
  centro,
}: {
  titulo: string;
  tipo: "anillo" | "barras";
  datos: { group: string; value: number }[];
  eje?: { abajo: string; izquierda: string };
  // Solo el anillo: la etiqueta de cada porcion y el numero del centro, ya en es-VE desde la API (VB-21).
  etiqueta?: (d: { data: { group: string } }) => string;
  centro?: string | null;
}) {
  const modo = useModoEfectivo();
  const grupos = datos.map((d) => d.group);
  // Sin barra de herramientas (su button va dentro de un div role="button", axe: nested-interactive, y sus rotulos estan en
  // ingles: cada grafico ya tiene su tabla con los montos exactos), tema segun el modo y cifras en es-VE: todo eso viene de
  // `opcionesBase`; aqui solo va lo propio de cada grafico.
  if (tipo === "anillo") {
    const opciones = fusionarOpciones<DonutChartOptions>(
      opcionesBase(modo, { colores: slotsPorGrupo(grupos), series: grupos.length, ejes: false }),
      {
        title: titulo,
        height: "300px",
        resizable: true,
        ...(etiqueta ? { pie: { labels: { formatter: etiqueta } } } : {}),
        donut: { center: { label: "Total", numberFormatter: centro ? () => centro : formatoNumeroEsVe } },
      },
    );
    return (
      <Suspense fallback={<EsqueletoPagina etiqueta="Cargando el gráfico" />}>
        <GraficoCarbon tipo="anillo" datos={datos} opciones={opciones} />
      </Suspense>
    );
  }
  // Una sola serie en barras: todas del mismo color (la longitud ya dice el valor) y sin leyenda.
  const opciones = fusionarOpciones<BarChartOptions>(
    opcionesBase(modo, { colores: Object.fromEntries(grupos.map((g) => [g, "serie1" as const])), series: 1 }),
    {
      title: titulo,
      height: "300px",
      resizable: true,
      axes: {
        left: { mapsTo: "group", scaleType: ESCALA_DE_ETIQUETAS, title: eje?.izquierda },
        bottom: { mapsTo: "value", title: eje?.abajo, ticks: { formatter: formatoNumeroEsVe } },
      },
    },
  );
  return (
    <Suspense fallback={<EsqueletoPagina etiqueta="Cargando el gráfico" />}>
      <GraficoCarbon tipo="barras" datos={datos} opciones={opciones} />
    </Suspense>
  );
}

function Contenido({ datos }: { datos: TableroRespuesta }) {
  const obra = useContext(ContextoDeLaObra);
  const obraAbierta = obra ? { carpeta: obra.carpeta, obraId: obra.obraId } : undefined;
  const moneda = datos.moneda ?? "";
  if (datos.version === null) {
    return (
      <EstadoVacio
        titulo="Esta obra aún no tiene presupuesto guardado"
        descripcion="Guarde una versión del presupuesto de la obra para ver aquí su resumen, su curva y su Pareto."
      />
    );
  }
  return (
    <>
      <p className="silice-tablero__nota cds--type-body-compact-01">
        {`Versión ${datos.version} del ${fechaEsVe(datos.fecha ?? "")} · ${formatoEsVe(String(datos.renglones))} ${datos.renglones === 1 ? "renglón" : "renglones"} · ${moneda}`}
      </p>
      <Tarjetas tarjetas={datos.tarjetas} moneda={moneda} destacarPrimera />

      <section className="silice-tablero__bloque" aria-labelledby="tablero-control">
        <h2 id="tablero-control" className="cds--type-heading-compact-02">
          Control de la obra
        </h2>
        {datos.control?.disponible ? (
          <>
            <p className="silice-tablero__nota cds--type-body-compact-01">
              En plazo (SPI) y costo (CPI), 1,00 o más es favorable; menos de 1,00 indica atraso o sobrecosto.
            </p>
            {anillosDePorcentaje(datos.control.anillos).length > 0 && (
              <div className="silice-tablero__anillos">
                {anillosDePorcentaje(datos.control.anillos).map((a) => (
                  <div key={a.rotulo} className="silice-tablero__anillo">
                    {/* La fracción solo dibuja el arco; lo que se lee es el texto del servidor («62.5 %»), en es-VE. La
                        variación (`favorable` de la API) la dice el anillo con ícono y palabra, no solo con el color. */}
                    <RadialGauge
                      label={a.rotulo}
                      fraccion={Number(a.fraccion)}
                      texto={formatoMontoEsVe(a.texto)}
                      variacion={a.favorable === true ? "favorable" : a.favorable === false ? "desfavorable" : null}
                      referencia={a.referencia}
                      size={92}
                    />
                  </div>
                ))}
              </div>
            )}
            <Tarjetas tarjetas={datos.control.tarjetas} moneda={moneda} />
          </>
        ) : (
          <EstadoVacio titulo="Aún no hay control de obra" descripcion={datos.control?.motivo}>
            <EnlaceComoBoton to={rutaOPendientes("control", obraAbierta)} kind="secondary">
              Abrir el control de obra
            </EnlaceComoBoton>
          </EstadoVacio>
        )}
      </section>

      {datos.curvas && datos.curvas.series.length > 0 && (
        <section className="silice-tablero__bloque" aria-labelledby="tablero-curva">
          <h2 id="tablero-curva" className="cds--type-heading-compact-02">
            Curva de la obra
          </h2>
          <CurvaPlanAvance titulo={datos.curvas.titulo} series={seriesDeCurva(datos.curvas)} unidad={moneda} />
        </section>
      )}

      {datos.desglose.length > 0 && (
        <section className="silice-tablero__bloque" aria-labelledby="tablero-desglose">
          <h2 id="tablero-desglose" className="cds--type-heading-compact-02">
            Desglose del contrato
          </h2>
          <Grafico
            titulo="Desglose del contrato"
            tipo="anillo"
            datos={datosDeDesglose(datos.desglose)}
            etiqueta={etiquetaDePeso(datos.desglose)}
            centro={centroDelAnillo(datos.tarjetas)}
          />
          <TablaDensa
            etiqueta="Desglose del contrato"
            columnas={[
              { clave: "rubro", titulo: "Rubro" },
              { clave: "monto", titulo: `Monto (${moneda})`, numerica: true, presentar: formatoMontoEsVe },
              { clave: "peso", titulo: "Peso", numerica: true, presentar: formatoMontoEsVe },
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
          <p className="silice-tablero__nota cds--type-body-compact-01">
            Partidas que concentran la mayor parte del costo, de mayor a menor.
          </p>
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
              { clave: "peso", titulo: "% del total", numerica: true, presentar: formatoMontoEsVe },
              { clave: "acumulado", titulo: "% acumulado", numerica: true, presentar: formatoMontoEsVe },
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
          {datos.versiones.length >= 2 && (
            <Grafico
              titulo="Total por versión"
              tipo="barras"
              datos={datosDeVersiones(datos.versiones)}
              eje={{ abajo: `Total (${moneda})`, izquierda: "Versión" }}
            />
          )}
          <TablaDensa
            etiqueta="Versiones del presupuesto"
            columnas={[
              { clave: "version", titulo: "Versión" },
              // VD-5: la fecha sin su forma ISO en el title (`presentar` la pondria); el title es de las cifras
              { clave: "fecha", titulo: "Fecha", celda: (f) => fechaEsVe(f.fecha ?? "") },
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
  if (carga.estado === "sin_permiso") {
    return (
      <EstadoVacio
        titulo="Su cuenta no puede ver el tablero"
        descripcion="Ver el tablero pide el papel «arma presupuestos» o «revisa paquetes»: pídaselo a quien administra Sílice."
      />
    );
  }
  if (carga.estado === "no_disponible") {
    return <EstadoVacio titulo="Esa obra no está en esta carpeta" descripcion="Elija otra obra en la lista «Obras» de la barra lateral." />;
  }
  return <AvisoError error={carga.error} titulo="No se pudo cargar el tablero" />;
}

// Tablero del proyecto: el proyecto es el de la cabecera. Solo lectura (`leer_proyecto`); no escribe nada.
export default function PaginaTablero() {
  const { proyecto } = useAplicacion();
  return (
    <div className="silice-tablero silice-pagina">
      <h1 className="cds--type-heading-04">Tablero de la obra</h1>
      <p className="silice-tablero__nota cds--type-body-compact-01">
        Resumen visual de cuánto cuesta la obra, qué partidas pesan más y cómo avanza
      </p>
      {proyecto === null ? (
        <EstadoVacio titulo="Elija una obra" descripcion="Elija una obra en «Obras» de la barra lateral, o búsquela con Ctrl+K." />
      ) : (
        <Cargado proyecto={proyecto} />
      )}
    </div>
  );
}
