import { Button, SkeletonText, Table, TableBody, TableCell, TableHead, TableRow } from "@carbon/react";
import { Link } from "react-router";
import type { Etapa, MonedaDeLaCartera, ObraDeLaCartera, ResumenTodasRespuesta } from "../../api/tipos";
import { AvisoError } from "../../comun/AvisoError";
import { InlineNotification, TableHeader } from "../../comun/carbonEs";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { valorParaDibujar } from "../../comun/paletaGraficos";
import { QueEsEsto } from "../../comun/QueEsEsto";
import type { Carga } from "../../comun/useCarga";
import { centesimasEsVe, formatoEsVe } from "../../indicadores/formatoEsVe";
import { EtapaDeObra } from "../../marco/EtapaDeObra";
import { rutaOPendientes } from "../../marco/espacios";
import { claveDeObra } from "../pendientes/logica";
import { ResumenDeGravedad } from "./LoQueBloquea";
import { TEXTOS } from "./textos";

const ETAPAS: readonly Etapa[] = ["en_elaboracion", "en_aprobacion", "aprobada", "en_ejecucion", "atrasada"];
const esEtapa = (etapa: string): etapa is Etapa => (ETAPAS as readonly string[]).includes(etapa);

// El color de cada etapa en la barra segmentada: fijo por etapa mediante tokens de inicio.scss; «atrasada» usa el token
// de gravedad de error y va siempre acompañada de su palabra en la leyenda y en la tabla.
const COLOR_DE_ETAPA: Record<Etapa, string> = {
  en_elaboracion: "var(--silice-grafico-etapa-en-elaboracion)",
  en_aprobacion: "var(--silice-grafico-etapa-en-aprobacion)",
  aprobada: "var(--silice-grafico-etapa-aprobada)",
  en_ejecucion: "var(--silice-grafico-etapa-en-ejecucion)",
  atrasada: "var(--silice-gravedad-error)",
};
const COLOR_DE_OTRA_ETAPA = "var(--silice-grafico-etapa-otra)";

export interface SegmentoEtapa {
  id: string;
  label: string;
  obras: number;
  valorTexto: string;
  color: string;
}

export function segmentosPorEtapa(obras: readonly ObraDeLaCartera[]): SegmentoEtapa[] {
  const conteo = new Map<string, { texto: string; obras: number }>();
  for (const o of obras) {
    const actual = conteo.get(o.etapa);
    if (actual) actual.obras += 1;
    else conteo.set(o.etapa, { texto: o.etapa_texto, obras: 1 });
  }
  const orden = [...ETAPAS, ...[...conteo.keys()].filter((e) => !esEtapa(e))];
  return orden.flatMap((etapa): SegmentoEtapa[] => {
    const e = conteo.get(etapa);
    if (e === undefined) return [];
    return [
      {
        id: etapa,
        label: e.texto,
        obras: e.obras,
        valorTexto: formatoEsVe(String(e.obras)),
        color: esEtapa(etapa) ? COLOR_DE_ETAPA[etapa] : COLOR_DE_OTRA_ETAPA,
      },
    ];
  });
}

// Marcas redondas para el eje horizontal de presupuesto (solo para situar las líneas de referencia y el ancho visual).
export function escalaHorizontal(maximo: number): { tope: number; marcas: number[] } {
  if (!Number.isFinite(maximo) || maximo <= 0) return { tope: 0, marcas: [0] };
  const crudo = maximo / 3;
  const magnitud = 10 ** Math.floor(Math.log10(crudo));
  const pasos = [1, 2, 2.5, 5, 10];
  const factor = pasos.find((p) => p * magnitud >= crudo) ?? 10;
  const paso = factor * magnitud;
  const cantidad = Math.max(1, Math.ceil(maximo / paso));
  const marcas: number[] = [];
  for (let i = 0; i <= cantidad; i++) marcas.push(Math.round(i * paso * 100) / 100);
  return { tope: marcas[marcas.length - 1] ?? maximo, marcas };
}

// Solo para la geometría de las barras (valorParaDibujar): lo que se lee sigue siendo el texto del servidor.
function numeroFinito(valor: string | null): number | null {
  if (valor === null) return null;
  const n = valorParaDibujar(valor);
  return Number.isFinite(n) ? n : null;
}

function porcentajeAcotado(porcentaje: string | null): number | null {
  const n = numeroFinito(porcentaje);
  if (n === null) return null;
  return Math.min(100, Math.max(0, n));
}

function ordenarPorPresupuesto(obras: readonly ObraDeLaCartera[]): ObraDeLaCartera[] {
  return [...obras].sort((a, b) => {
    const ta = numeroFinito(a.total);
    const tb = numeroFinito(b.total);
    if (ta === null && tb === null) return 0;
    if (ta === null) return 1;
    if (tb === null) return -1;
    return tb - ta;
  });
}

interface Props {
  carga: Carga<ResumenTodasRespuesta>;
  carpetas: ReadonlyMap<string, string>;
  problemasPorObra?: ReadonlyMap<string, { bloquea: number; aviso: number }>;
  puedeCrear: boolean;
  alCrear?: () => void;
}

function AvanceEnCelda({ real, plan }: { real: string | null; plan: string | null }) {
  if (real === null || plan === null) {
    return <span className="silice-inicio__sin-avance cds--type-body-compact-01">{TEXTOS.avance.sinAvance}</span>;
  }
  const pctReal = porcentajeAcotado(real);
  const pctPlan = porcentajeAcotado(plan);
  return (
    <div className="silice-inicio__avance">
      <span className="cds--type-body-compact-01 silice-cifra">{TEXTOS.avance.real(formatoEsVe(real), formatoEsVe(plan))}</span>
      {pctReal !== null && pctPlan !== null && (
        <span className="fiori-kpi__barra" aria-hidden="true">
          <span className="fiori-kpi__barra-real" style={{ inlineSize: `${pctReal}%` }} />
          <span className="fiori-kpi__barra-meta" style={{ inlineSize: `${pctPlan}%` }} />
        </span>
      )}
    </div>
  );
}

function Vacio({ puedeCrear, alCrear }: Pick<Props, "puedeCrear" | "alCrear">) {
  if (!puedeCrear) {
    return <EstadoVacio titulo={TEXTOS.cartera.vacio.soloRevisa.titulo} descripcion={TEXTOS.cartera.vacio.soloRevisa.descripcion} />;
  }
  const { titulo, descripcion, boton } = TEXTOS.cartera.vacio.puedeCrear;
  return (
    <EstadoVacio titulo={titulo} descripcion={descripcion}>
      <div>
        <Button kind="primary" size="sm" onClick={alCrear}>
          {boton}
        </Button>
      </div>
    </EstadoVacio>
  );
}

function GraficoDeMoneda({
  fila,
  obras,
  mostrarSubtitulo,
  carpetas,
  problemasPorObra,
}: {
  fila: MonedaDeLaCartera;
  obras: readonly ObraDeLaCartera[];
  mostrarSubtitulo: boolean;
  carpetas: ReadonlyMap<string, string>;
  problemasPorObra: ReadonlyMap<string, { bloquea: number; aviso: number }>;
}) {
  const ordenadas = ordenarPorPresupuesto(obras);
  const maximo = Math.max(0, ...ordenadas.map((o) => numeroFinito(o.total) ?? 0));
  const { tope, marcas } = escalaHorizontal(maximo);

  const resumenAria = [
    `${TEXTOS.cartera.moneda(fila.moneda)}: ${centesimasEsVe(fila.total)} ${fila.moneda}.`,
    ...ordenadas.map((o) => {
      const pres = o.total === null ? TEXTOS.avance.sinVersion : `${centesimasEsVe(o.total)} ${o.moneda}`;
      const av = o.avance_real === null ? TEXTOS.avance.sinAvance : `${formatoEsVe(o.avance_real)} %`;
      return `${o.nombre}: ${pres}, ${av}.`;
    }),
  ].join(" ");

  const problemasTotales = ordenadas.reduce(
    (acc, o) => {
      const p = problemasPorObra.get(claveDeObra(o.carpeta, o.obra_id));
      if (p) {
        acc.bloquea += p.bloquea;
        acc.aviso += p.aviso;
      }
      return acc;
    },
    { bloquea: 0, aviso: 0 },
  );

  return (
    <section className="silice-cartera-moneda" aria-label={TEXTOS.cartera.moneda(fila.moneda)}>
      {mostrarSubtitulo && (
        <h3 className="silice-cartera-moneda__titulo">{TEXTOS.cartera.tituloDeMoneda(fila.moneda, fila.total)}</h3>
      )}

      <div className="silice-cartera-grafico" role="img" aria-label={resumenAria}>
        <div className="silice-cartera-grafico__filas">
          {ordenadas.map((o) => {
            const clave = claveDeObra(o.carpeta, o.obra_id);
            const carpeta = carpetas.get(clave);
            const monto = numeroFinito(o.total);
            const pctPresupuesto = tope > 0 && monto !== null && monto > 0 ? Math.min(100, (monto / tope) * 100) : 0;
            const pctAvance = porcentajeAcotado(o.avance_real);
            const pctEjecutado = pctAvance !== null ? (pctPresupuesto * pctAvance) / 100 : 0;
            const textoPresupuesto = o.total === null ? TEXTOS.avance.sinVersion : `${centesimasEsVe(o.total)} ${o.moneda}`;
            const textoEjecutado =
              o.avance_real === null ? TEXTOS.avance.sinAvance : TEXTOS.avance.ejecutadoPct(formatoEsVe(o.avance_real));

            return (
              <div key={clave} className="silice-cartera-grafico__fila">
                <div className="silice-cartera-grafico__obra">
                  <span className="silice-cartera-grafico__obra-nombre">{o.nombre}</span>
                  {carpeta !== undefined && <span className="silice-inicio__carpeta"> · {carpeta}</span>}
                </div>
                <div className="silice-cartera-grafico__zona-barras">
                  <div className="silice-cartera-grafico__cuadricula" aria-hidden="true">
                    {marcas.map((marca) => {
                      const pos = tope > 0 ? (marca / tope) * 100 : 0;
                      return (
                        <span
                          key={marca}
                          className={`silice-cartera-grafico__linea${marca === 0 ? " silice-cartera-grafico__linea--base" : ""}`}
                          style={{ insetInlineStart: `${pos}%` }}
                        />
                      );
                    })}
                  </div>
                  <div className="silice-cartera-grafico__par">
                    <div className="silice-cartera-grafico__carril">
                      <span
                        className="silice-cartera-grafico__barra silice-cartera-grafico__barra--presupuesto"
                        style={{ inlineSize: `${pctPresupuesto}%` }}
                      />
                      <span
                        className="silice-cartera-grafico__cifra silice-cartera-grafico__cifra--sec"
                        style={{ insetInlineStart: `${pctPresupuesto}%` }}
                      >
                        {textoPresupuesto}
                      </span>
                    </div>
                    <div className="silice-cartera-grafico__carril">
                      <span
                        className="silice-cartera-grafico__barra silice-cartera-grafico__barra--ejecutado"
                        style={{ inlineSize: `${pctEjecutado}%` }}
                      />
                      <span
                        className="silice-cartera-grafico__cifra silice-cartera-grafico__cifra--fuerte"
                        style={{ insetInlineStart: `${pctEjecutado}%` }}
                      >
                        {textoEjecutado}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}

          {tope > 0 && (
            <div className="silice-cartera-grafico__eje-fila" aria-hidden="true">
              <div className="silice-cartera-grafico__obra" />
              <div className="silice-cartera-grafico__zona-barras">
                <div className="silice-cartera-grafico__marcas">
                  {marcas.map((marca) => (
                    <span
                      key={marca}
                      className="silice-cartera-grafico__marca"
                      style={{ insetInlineStart: `${(marca / tope) * 100}%` }}
                    >
                      {formatoEsVe(String(marca))}
                    </span>
                  ))}
                </div>
                <span className="silice-cartera-grafico__unidad">{TEXTOS.cartera.ejeMoneda(fila.moneda)}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="silice-inicio__leyenda">
        <span className="silice-inicio__leyenda-item">
          <i className="silice-inicio__muestra silice-inicio__muestra--presupuesto" aria-hidden="true" />
          {TEXTOS.cartera.leyendaPresupuesto}
        </span>
        <span className="silice-inicio__leyenda-item">
          <i className="silice-inicio__muestra silice-inicio__muestra--ejecutado" aria-hidden="true" />
          {TEXTOS.cartera.leyendaEjecutado}
        </span>
      </div>

      <details className="silice-inicio__vertabla">
        <summary>{TEXTOS.cartera.verComoTabla}</summary>
        <div
          role="region"
          aria-label={TEXTOS.cartera.desplazar(fila.moneda)}
          tabIndex={0}
          className="silice-tabla silice-inicio__obras silice-inicio__tabla-detalle"
        >
          <Table size="sm" aria-label={TEXTOS.cartera.tabla(fila.moneda)}>
            <TableHead>
              <TableRow>
                <TableHeader>{TEXTOS.avance.obra}</TableHeader>
                <TableHeader>{TEXTOS.avance.estado}</TableHeader>
                <TableHeader className="silice-cifra">{TEXTOS.avance.presupuesto(fila.moneda)}</TableHeader>
                <TableHeader>{TEXTOS.avance.avance}</TableHeader>
                <TableHeader>{TEXTOS.avance.problemas}</TableHeader>
              </TableRow>
            </TableHead>
            <TableBody>
              {ordenadas.map((o) => {
                const clave = claveDeObra(o.carpeta, o.obra_id);
                const carpeta = carpetas.get(clave);
                const problemas = problemasPorObra.get(clave) ?? { bloquea: 0, aviso: 0 };
                return (
                  <TableRow key={clave}>
                    <TableCell>
                      <Link className="cds--link" to={rutaOPendientes("obras", { carpeta: o.carpeta, obraId: o.obra_id })}>
                        {o.nombre}
                      </Link>
                      {carpeta !== undefined && <span className="silice-inicio__carpeta"> · {carpeta}</span>}
                    </TableCell>
                    <TableCell data-etiqueta={TEXTOS.avance.estado}>
                      {esEtapa(o.etapa) ? <EtapaDeObra etapa={o.etapa} texto={o.etapa_texto} /> : o.etapa_texto}
                    </TableCell>
                    <TableCell className="silice-cifra silice-inicio__sinquiebre" data-etiqueta={TEXTOS.avance.total}>
                      {o.total === null ? TEXTOS.avance.sinVersion : `${centesimasEsVe(o.total)} ${o.moneda}`}
                    </TableCell>
                    <TableCell data-etiqueta={TEXTOS.avance.avance}>
                      <AvanceEnCelda real={o.avance_real} plan={o.avance_plan} />
                    </TableCell>
                    <TableCell data-etiqueta={TEXTOS.avance.problemas}>
                      <ResumenDeGravedad bloquea={problemas.bloquea} aviso={problemas.aviso} />
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
            <tfoot>
              <tr>
                <td>{TEXTOS.cartera.pieCartera}</td>
                <td>{TEXTOS.enEjecucion(fila.en_ejecucion)}</td>
                <td className="silice-cifra silice-inicio__sinquiebre">{`${centesimasEsVe(fila.total)} ${fila.moneda}`}</td>
                <td>{`${formatoEsVe(String(fila.obras))} ${fila.obras === 1 ? "obra" : "obras"}`}</td>
                <td>
                  <ResumenDeGravedad bloquea={problemasTotales.bloquea} aviso={problemasTotales.aviso} />
                </td>
              </tr>
            </tfoot>
          </Table>
        </div>
      </details>
    </section>
  );
}

function BloqueAvanceDeLaCartera({
  obras,
  carpetas,
}: {
  obras: readonly ObraDeLaCartera[];
  carpetas: ReadonlyMap<string, string>;
}) {
  const segmentos = segmentosPorEtapa(obras);
  const totalObras = obras.length;
  const conSeguimiento = obras.filter((o) => o.avance_real !== null && o.avance_plan !== null);
  const etiquetaBarra = `${TEXTOS.avance.etapasAria}: ${segmentos.map((s) => `${s.label} ${s.valorTexto}`).join(", ")}`;

  return (
    <section className="silice-inicio__seccion silice-inicio__seccion--compacta" aria-labelledby="inicio-avance">
      <h2 id="inicio-avance" className="silice-inicio__subtitulo-seccion cds--type-heading-compact-02">
        {TEXTOS.avance.titulo}
      </h2>

      <div className="silice-avance-segmentos" role="img" aria-label={etiquetaBarra}>
        {segmentos.map((seg) => (
          <span
            key={seg.id}
            data-etapa={seg.id}
            className="silice-avance-segmentos__parte"
            style={{
              flexGrow: seg.obras,
              inlineSize: `${(seg.obras / Math.max(1, totalObras)) * 100}%`,
              backgroundColor: seg.color,
            }}
          />
        ))}
      </div>

      <ul className="silice-inicio__leyenda silice-inicio__leyenda--lista" aria-label="Detalle por etapa">
        {segmentos.map((seg) => (
          <li key={seg.id} className="silice-inicio__leyenda-item">
            <i className="silice-inicio__muestra" style={{ backgroundColor: seg.color }} aria-hidden="true" />
            <span>{`${seg.label}: ${seg.valorTexto}`}</span>
          </li>
        ))}
      </ul>

      {conSeguimiento.length > 0 && (
        <ul className="silice-avance-medidores" aria-label="Avance real frente al planificado">
          {conSeguimiento.map((o) => {
            const clave = claveDeObra(o.carpeta, o.obra_id);
            const real = porcentajeAcotado(o.avance_real) ?? 0;
            const plan = porcentajeAcotado(o.avance_plan) ?? 0;
            return (
              <li key={clave} className="silice-avance-medidores__fila">
                <div className="silice-avance-medidores__cabecera">
                  <span className="silice-avance-medidores__obra">{o.nombre}</span>
                  <span className="silice-cifra silice-avance-medidores__cifra">
                    {TEXTOS.avance.real(formatoEsVe(o.avance_real!), formatoEsVe(o.avance_plan!))}
                  </span>
                </div>
                <div className="silice-inicio__prog" aria-hidden="true">
                  <span className="silice-inicio__prog-real" style={{ inlineSize: `${real}%` }} />
                  <span className="silice-inicio__prog-plan" style={{ insetInlineStart: `${plan}%` }} />
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <details className="silice-inicio__vertabla">
        <summary>{TEXTOS.avance.verComoTabla}</summary>
        <div
          role="region"
          aria-label={TEXTOS.avance.desplazar}
          tabIndex={0}
          className="silice-tabla silice-inicio__obras silice-inicio__tabla-detalle"
        >
          <Table size="sm" aria-label={TEXTOS.avance.tabla}>
            <TableHead>
              <TableRow>
                <TableHeader>{TEXTOS.avance.obra}</TableHeader>
                <TableHeader>{TEXTOS.avance.estado}</TableHeader>
                <TableHeader className="silice-cifra">{TEXTOS.avance.total}</TableHeader>
                <TableHeader>{TEXTOS.avance.avance}</TableHeader>
              </TableRow>
            </TableHead>
            <TableBody>
              {obras.map((o) => {
                const clave = claveDeObra(o.carpeta, o.obra_id);
                const carpeta = carpetas.get(clave);
                return (
                  <TableRow key={clave}>
                    <TableCell>
                      <Link className="cds--link" to={rutaOPendientes("obras", { carpeta: o.carpeta, obraId: o.obra_id })}>
                        {o.nombre}
                      </Link>
                      {carpeta !== undefined && <span className="silice-inicio__carpeta"> · {carpeta}</span>}
                    </TableCell>
                    <TableCell data-etiqueta={TEXTOS.avance.estado}>
                      {esEtapa(o.etapa) ? <EtapaDeObra etapa={o.etapa} texto={o.etapa_texto} /> : o.etapa_texto}
                    </TableCell>
                    <TableCell className="silice-cifra silice-inicio__sinquiebre" data-etiqueta={TEXTOS.avance.total}>
                      {o.total === null ? TEXTOS.avance.sinVersion : `${centesimasEsVe(o.total)} ${o.moneda}`}
                    </TableCell>
                    <TableCell data-etiqueta={TEXTOS.avance.avance}>
                      <AvanceEnCelda real={o.avance_real} plan={o.avance_plan} />
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </details>

      <p className="silice-inicio__explicacion">{TEXTOS.avance.queMuestra}</p>
    </section>
  );
}

// Gráfico principal de la cartera («La cartera de obras») y bloque secundario compacto («Avance de la cartera»).
// Lee `GET /v1/obras/resumen/todas` sin mezclar monedas ni recalcular montos.
export function CarteraYAvance({
  carga,
  carpetas,
  problemasPorObra = new Map(),
  puedeCrear,
  alCrear,
}: Props) {
  if (carga.estado === "sin_permiso") return null;

  const obras = carga.estado === "listo" ? carga.datos.obras : [];
  const porMoneda = carga.estado === "listo" ? carga.datos.por_moneda : [];

  return (
    <>
      <section className="silice-inicio__seccion" aria-labelledby="inicio-cartera">
        <div className="silice-inicio__cabecera-seccion">
          <h2 id="inicio-cartera" className="silice-inicio__titulo-seccion cds--type-heading-compact-02">
            {TEXTOS.cartera.titulo}
          </h2>
          {carga.estado === "listo" && porMoneda.length > 0 && (
            <QueEsEsto titulo={TEXTOS.cartera.ayudaTitulo}>
              <p className="cds--type-body-compact-01">{TEXTOS.cartera.ayuda}</p>
            </QueEsEsto>
          )}
        </div>

        {carga.estado === "cargando" && (
          <div role="status" aria-busy="true" aria-label={TEXTOS.cartera.cargando}>
            <SkeletonText paragraph lineCount={3} />
          </div>
        )}
        {carga.estado === "error" && <AvisoError error={carga.error} titulo={TEXTOS.cartera.error} />}
        {carga.estado === "no_disponible" && (
          <EstadoVacio titulo={TEXTOS.cartera.noDisponible} descripcion={TEXTOS.cartera.noDisponibleQueHacer} />
        )}
        {carga.estado === "listo" && (
          <>
            {carga.datos.carpetas_omitidas > 0 && (
              <InlineNotification
                kind="warning"
                title={TEXTOS.cartera.omitidas(carga.datos.carpetas_omitidas)}
                lowContrast
                hideCloseButton
              />
            )}
            {porMoneda.length === 0 && obras.length === 0 ? (
              <Vacio puedeCrear={puedeCrear} alCrear={alCrear} />
            ) : (
              <>
                <div className="silice-cartera-rejilla">
                  {porMoneda.map((fila) => (
                    <GraficoDeMoneda
                      key={fila.moneda}
                      fila={fila}
                      obras={obras.filter((o) => o.moneda === fila.moneda)}
                      mostrarSubtitulo={porMoneda.length > 1}
                      carpetas={carpetas}
                      problemasPorObra={problemasPorObra}
                    />
                  ))}
                </div>
                <p className="silice-inicio__explicacion">{TEXTOS.cartera.queMuestra}</p>
              </>
            )}
          </>
        )}
      </section>

      {obras.length > 0 && <BloqueAvanceDeLaCartera obras={obras} carpetas={carpetas} />}
    </>
  );
}
