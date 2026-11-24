import { SkeletonText, Table, TableBody, TableCell, TableHead, TableRow, Button } from "@carbon/react";
import { Link } from "react-router";
import type { Etapa, ObraDeLaCartera, ResumenTodasRespuesta } from "../../api/tipos";
import { AvisoError } from "../../comun/AvisoError";
import { InlineNotification, TableHeader } from "../../comun/carbonEs";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { QueEsEsto } from "../../comun/QueEsEsto";
import { AnimatedBarChart, AnimatedDonutChart } from "../../comun/VisualMeters";
import type { BarDatum, DonutSegment } from "../../comun/VisualMeters";
import { centesimasEsVe, formatoEsVe } from "../../indicadores/formatoEsVe";
import { FranjaDeCifras } from "../../indicadores/FranjaDeCifras";
import { EtapaDeObra } from "../../marco/EtapaDeObra";
import { rutaOPendientes } from "../../marco/espacios";
import { claveDeObra } from "../pendientes/logica";
import type { Carga } from "../../comun/useCarga";
import { TEXTOS } from "./textos";

// Las palabras de la etapa las da el servidor (`etapa_texto`, la misma tabla del Resumen de la obra); aquí solo se decide
// el ícono. Una etapa que esta pantalla no conoce se escribe sin ícono.
const ETAPAS: readonly Etapa[] = ["en_elaboracion", "en_aprobacion", "aprobada", "en_ejecucion", "atrasada"];
const esEtapa = (etapa: string): etapa is Etapa => (ETAPAS as readonly string[]).includes(etapa);

// El color de cada etapa en el anillo por estado: fijo por etapa (no por su lugar ni su tamaño). Son tokens del gráfico
// (`--silice-grafico-etapa-*`, en inicio.scss, con sus valores y el porqué), no colores en el componente.
// Excepción anotada: «atrasada» no lleva un color de serie sino la severidad de error (`--silice-sev-error`), el mismo
// de su ícono en la tabla (`EtapaDeObra`), para que la obra atrasada se lea igual en los dos lugares.
// La paleta queda para la dirección de diseño (los grises 50, 70 y 100 se parecen entre sí); mientras tanto la leyenda
// dice cada estado con su nombre y su cifra, así que el color no es lo único que los distingue.
const COLOR_DE_ETAPA: Record<Etapa, string> = {
  en_elaboracion: "var(--silice-grafico-etapa-en-elaboracion)",
  en_aprobacion: "var(--silice-grafico-etapa-en-aprobacion)",
  aprobada: "var(--silice-grafico-etapa-aprobada)",
  en_ejecucion: "var(--silice-grafico-etapa-en-ejecucion)",
  atrasada: "var(--silice-sev-error)",
};
// Una etapa que esta pantalla no conoce, al final.
const COLOR_DE_OTRA_ETAPA = "var(--silice-grafico-etapa-otra)";

// Las barras del avance: solo las obras con real y plan, con las cifras de la API en es-VE (el número solo dibuja).
const MAXIMO_DE_BARRAS = 6;
function barrasDeAvance(obras: readonly ObraDeLaCartera[]): BarDatum[] {
  return obras.flatMap((o): BarDatum[] => {
    if (o.avance_real === null || o.avance_plan === null) return [];
    return [
      {
        id: claveDeObra(o.carpeta, o.obra_id),
        label: o.nombre,
        real: Number(o.avance_real),
        plan: Number(o.avance_plan),
        realText: `${formatoEsVe(o.avance_real)} %`,
        planText: `${formatoEsVe(o.avance_plan)} %`,
      },
    ];
  }).slice(0, MAXIMO_DE_BARRAS);
}

// El anillo por estado: cuántas obras de la lista hay en cada etapa (un conteo de filas; la API no manda porcentajes por
// estado y la pantalla no los calcula), en el orden de la obra y con el texto de la etapa que da el servidor.
function partesPorEtapa(obras: readonly ObraDeLaCartera[]): DonutSegment[] {
  const conteo = new Map<string, { texto: string; obras: number }>();
  for (const o of obras) {
    const actual = conteo.get(o.etapa);
    if (actual) actual.obras += 1;
    else conteo.set(o.etapa, { texto: o.etapa_texto, obras: 1 });
  }
  const orden = [...ETAPAS, ...[...conteo.keys()].filter((e) => !esEtapa(e))];
  return orden.flatMap((etapa): DonutSegment[] => {
    const e = conteo.get(etapa);
    if (e === undefined) return [];
    return [
      {
        id: etapa,
        label: e.texto,
        value: e.obras,
        valueText: formatoEsVe(String(e.obras)),
        color: esEtapa(etapa) ? COLOR_DE_ETAPA[etapa] : COLOR_DE_OTRA_ETAPA,
      },
    ];
  });
}

interface Props {
  carga: Carga<ResumenTodasRespuesta>;
  // La carpeta de las obras que se llaman igual en carpetas distintas, por `claveDeObra` (la misma regla de la bandeja).
  carpetas: ReadonlyMap<string, string>;
  puedeCrear: boolean;
  alCrear?: () => void;
}

// El ancho de la barra de avance: el porcentaje del servidor («62.5») entre 0 y 100. Solo dibuja; la cifra que se lee es el
// texto del servidor. Un valor que no es un número no dibuja nada.
function anchoDeBarra(porcentaje: string): string | null {
  const n = Number(porcentaje);
  if (!Number.isFinite(n)) return null;
  return `${Math.min(100, Math.max(0, n))}%`;
}

// Real con relleno sólido y plan con contorno (IBCS), con sus cifras al lado: el color nunca va solo.
function Avance({ real, plan }: { real: string | null; plan: string | null }) {
  if (real === null || plan === null) return <span className="silice-inicio__sin-avance cds--type-body-compact-01">{TEXTOS.avance.sinAvance}</span>;
  const anchoReal = anchoDeBarra(real);
  const anchoPlan = anchoDeBarra(plan);
  return (
    <div className="silice-inicio__avance">
      <span className="cds--type-body-compact-01 silice-cifra">{TEXTOS.avance.real(formatoEsVe(real), formatoEsVe(plan))}</span>
      {anchoReal !== null && anchoPlan !== null && (
        <span className="fiori-kpi__barra" aria-hidden="true">
          <span className="fiori-kpi__barra-real" style={{ inlineSize: anchoReal }} />
          <span className="fiori-kpi__barra-meta" style={{ inlineSize: anchoPlan }} />
        </span>
      )}
    </div>
  );
}

function FilaDeObra({ obra, carpeta }: { obra: ObraDeLaCartera; carpeta: string | undefined }) {
  return (
    <TableRow>
      <TableCell>
        <Link className="cds--link" to={rutaOPendientes("obras", { carpeta: obra.carpeta, obraId: obra.obra_id })}>
          {obra.nombre}
        </Link>
        {carpeta !== undefined && <span className="silice-inicio__carpeta"> · {carpeta}</span>}
      </TableCell>
      <TableCell data-etiqueta={TEXTOS.avance.estado}>
        {esEtapa(obra.etapa) ? <EtapaDeObra etapa={obra.etapa} texto={obra.etapa_texto} /> : obra.etapa_texto}
      </TableCell>
      <TableCell className="silice-cifra silice-inicio__sinquiebre" data-etiqueta={TEXTOS.avance.total}>
        {obra.total === null ? TEXTOS.avance.sinVersion : `${centesimasEsVe(obra.total)} ${obra.moneda}`}
      </TableCell>
      <TableCell data-etiqueta={TEXTOS.avance.avance}>
        <Avance real={obra.avance_real} plan={obra.avance_plan} />
      </TableCell>
    </TableRow>
  );
}

function Cartera({ datos }: { datos: ResumenTodasRespuesta }) {
  // Una tarjeta por moneda presente, tal como viene: nunca se suman ni se promedian entre sí, ni se pinta una vacía.
  return (
    <div className="silice-cartera-rejilla">
      {datos.por_moneda.map((fila) => (
        <section key={fila.moneda} className="silice-cartera-moneda" aria-label={TEXTOS.cartera.moneda(fila.moneda)}>
          <p className="silice-cartera-moneda__titulo cds--type-body-compact-01">{TEXTOS.cartera.tituloDeMoneda(fila.moneda)}</p>
          <FranjaDeCifras
            etiqueta={TEXTOS.cartera.cifras(fila.moneda)}
            cifras={[
              { id: "total", titulo: TEXTOS.cartera.total, valor: `${centesimasEsVe(fila.total)} ${fila.moneda}` },
              { id: "obras", titulo: TEXTOS.cartera.obras, valor: formatoEsVe(String(fila.obras)) },
              { id: "ejecucion", titulo: TEXTOS.cartera.enEjecucion, valor: formatoEsVe(String(fila.en_ejecucion)) },
            ]}
          />
        </section>
      ))}
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

// El segundo y el tercer bloque de la Vista general (diseño visual B.2): la cartera por moneda (cada cifra, tal como la dio
// el servidor `GET /v1/obras/resumen/todas`; Bs y USD nunca se suman) y el avance ejecutado contra el plan, obra por obra. Sin
// obras, los dos bloques se unen en un solo estado vacío; sin `leer_proyecto` (carga `sin_permiso`) no se pinta ninguno. Un
// fallo de la lectura se dice aquí y no toca a los demás bloques de la pantalla.
export function CarteraYAvance({ carga, carpetas, puedeCrear, alCrear }: Props) {
  if (carga.estado === "sin_permiso") return null;
  const cuerpo = () => {
    switch (carga.estado) {
      case "cargando":
        return (
          <div role="status" aria-busy="true" aria-label={TEXTOS.cartera.cargando}>
            <SkeletonText paragraph lineCount={3} />
          </div>
        );
      case "error":
        return <AvisoError error={carga.error} titulo={TEXTOS.cartera.error} />;
      case "no_disponible":
        return <EstadoVacio titulo={TEXTOS.cartera.noDisponible} descripcion={TEXTOS.cartera.noDisponibleQueHacer} />;
      case "listo":
        return (
          <>
            {carga.datos.carpetas_omitidas > 0 && (
              <InlineNotification kind="warning" title={TEXTOS.cartera.omitidas(carga.datos.carpetas_omitidas)} lowContrast hideCloseButton />
            )}
            {carga.datos.por_moneda.length === 0 && carga.datos.obras.length === 0 ? (
              <Vacio puedeCrear={puedeCrear} alCrear={alCrear} />
            ) : (
              <Cartera datos={carga.datos} />
            )}
          </>
        );
    }
  };
  const obras = carga.estado === "listo" ? carga.datos.obras : [];
  const barrasAvance = barrasDeAvance(obras);

  return (
    <>
      <section className="silice-inicio__bloque" aria-labelledby="inicio-cartera">
        <h2 id="inicio-cartera" className="cds--type-heading-compact-02">
          {TEXTOS.cartera.titulo}
        </h2>
        {carga.estado === "listo" && carga.datos.por_moneda.length > 0 && (
          <QueEsEsto titulo={TEXTOS.cartera.ayudaTitulo}>
            <p className="cds--type-body-compact-01">{TEXTOS.cartera.ayuda}</p>
          </QueEsEsto>
        )}
        {cuerpo()}
      </section>
      {obras.length > 0 && (
        <section className="silice-inicio__visuales" aria-label="Indicadores visuales de cartera">
          {barrasAvance.length > 0 && (
            <div className="silice-panel silice-panel--padded silice-inicio__grafico-card">
              <h3 className="cds--type-heading-compact-02">Avance real frente al plan</h3>
              <p className="silice-panel__subtitulo">Si el avance real queda por debajo del plan, la obra lleva atraso</p>
              <AnimatedBarChart items={barrasAvance} realLegend="Avance real (%)" planLegend="Plan acumulado (%)" height={190} />
            </div>
          )}
          <div className="silice-panel silice-panel--padded silice-inicio__grafico-card">
            <h3 className="cds--type-heading-compact-02">Distribución de obras por estado</h3>
            <p className="silice-panel__subtitulo">Cuántas obras hay en cada estado</p>
            <AnimatedDonutChart
              segments={partesPorEtapa(obras)}
              centerLabel="Obras"
              centerValue={formatoEsVe(String(obras.length))}
              size={168}
            />
          </div>
        </section>
      )}
      {obras.length > 0 && (
        <section className="silice-inicio__bloque" aria-labelledby="inicio-obras">
          <h2 id="inicio-obras" className="cds--type-heading-compact-02">
            {TEXTOS.avance.titulo}
          </h2>
          {/* La caja es la región que se desplaza si algo no cupiera: enfocable por teclado y con nombre. Con letra grande las
              filas se apilan antes (inicio.scss), así que la columna de avance no queda fuera de la vista. */}
          <div role="region" aria-label={TEXTOS.avance.desplazar} tabIndex={0} className="silice-tabla silice-inicio__obras">
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
                {obras.map((o) => (
                  <FilaDeObra key={claveDeObra(o.carpeta, o.obra_id)} obra={o} carpeta={carpetas.get(claveDeObra(o.carpeta, o.obra_id))} />
                ))}
              </TableBody>
            </Table>
          </div>
        </section>
      )}
    </>
  );
}
