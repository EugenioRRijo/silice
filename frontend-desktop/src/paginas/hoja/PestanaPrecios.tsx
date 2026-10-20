import { Button, InlineLoading, InlineNotification } from "@carbon/react";
import type { CSSProperties, ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { useAplicacion } from "../../shell/contexto";
import { Cifra } from "./Cifra";
import { EstadoDeFila } from "./EstadoDeFila";
import { TablaPaginada } from "./TablaPaginada";
import { VistaCarga } from "./VistaCarga";
import { fechaCorta, partirColumnasDePrecios, rutaDeAtipicos, rutaDePrecios } from "./logica";
import type { AtipicosRespuesta, CeldaPrecio, ColumnaPrecio, PreciosRespuesta } from "./logica";

interface Props {
  proyecto: string;
  // null = borrador en blanco: no hay versión guardada de la que ver los precios.
  version: string | null;
  alAusente: () => void;
}

const SIN_VERSION = "Abra una versión guardada para ver el origen de sus precios.";
const ROTULO_ATIPICOS = "Buscar variaciones atípicas de precio";
const SIN_DATO = "Sin dato";
const ESTADO_CORRECTO = "OK";

// DESIGN.md: el atípico (RF-100) va en morado. La severidad sigue diciendo «Advertencia» con su ícono; solo su color
// toma el token de los atípicos, nunca el color solo.
const MORADO_ATIPICO = { "--silice-sev-advertencia": "var(--silice-atipico)" } as CSSProperties;

// Una celda tal como la manda la API: texto, `{texto, exacto}` (un monto) o null. La tasa se lee con su exacto (puede
// tener más de dos decimales) y las fechas ISO como día/mes/año. La interfaz no calcula ni redondea.
function valorDeCelda(columna: ColumnaPrecio, celda: CeldaPrecio | undefined): ReactNode {
  if (celda === null || celda === undefined || celda === "") return null;
  if (typeof celda === "string") return columna.rotulo.startsWith("Fecha") ? fechaCorta(celda) : celda;
  if (columna.rotulo === "Tasa") return <Cifra monto={{ texto: celda.exacto, exacto: celda.exacto }} />;
  return <Cifra monto={celda} unidad={columna.rotulo === "Erosión %" ? "%" : undefined} />;
}

function EstadoDelPrecio({ texto }: { texto: string }) {
  return <EstadoDeFila estado={{ severidad: texto === ESTADO_CORRECTO ? null : "ADVERTENCIA", texto }} />;
}

function textoDe(celda: CeldaPrecio | undefined): string {
  if (celda === null || celda === undefined) return "";
  return typeof celda === "string" ? celda : celda.texto;
}

function Detalle({
  columnas,
  fila,
  codigo,
}: {
  columnas: ColumnaPrecio[];
  fila: Record<string, CeldaPrecio>;
  codigo: string;
}) {
  return (
    <section className="silice-hoja__seccion" aria-labelledby={`detalle-${codigo}`}>
      <h3 id={`detalle-${codigo}`} className="cds--type-heading-compact-01">
        Detalle de {codigo}
      </h3>
      <dl className="silice-hoja__metricas">
        {columnas.map((c) => (
          <div key={c.clave}>
            <dt className="cds--type-helper-text-01">{c.rotulo}</dt>
            <dd className="cds--type-body-compact-01">{valorDeCelda(c, fila[c.clave]) ?? SIN_DATO}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function TablaDePrecios({ vista }: { vista: PreciosRespuesta }) {
  const [abierto, setAbierto] = useState<string | null>(null);
  const hayIndice = vista.filas.some((f) => f.erosion_indice !== null && f.erosion_indice !== undefined);
  const { principales, detalle } = partirColumnasDePrecios(vista.columnas, hayIndice);
  const porId = new Map(vista.filas.map((f, i) => [`precio-${i}`, f]));
  const abierta = vista.filas.find((f) => textoDe(f.codigo) === abierto);
  return (
    <>
      <TablaPaginada
        etiqueta="Precios"
        desplazable
        columnas={[
          ...principales.map((c) => ({
            clave: c.clave,
            titulo: c.rotulo,
            numerica: c.numerica,
            ordenable: false,
            celda: (f: { id: string }) => {
              const celda = porId.get(f.id)?.[c.clave];
              if (c.rotulo === "Estado") return <EstadoDelPrecio texto={textoDe(celda)} />;
              return valorDeCelda(c, celda);
            },
          })),
          {
            clave: "detalle",
            titulo: "Detalle",
            ordenable: false,
            celda: (f) => {
              const codigo = textoDe(porId.get(f.id)?.codigo);
              const expandido = abierto === codigo;
              return (
                <Button
                  kind="ghost"
                  size="sm"
                  aria-label={`Detalle de ${codigo}`}
                  aria-expanded={expandido}
                  onClick={() => setAbierto(expandido ? null : codigo)}
                >
                  Detalle
                </Button>
              );
            },
          },
        ]}
        filas={vista.filas.map((_, i) => ({ id: `precio-${i}` }))}
      />
      {abierta && abierto !== null && <Detalle columnas={detalle} fila={abierta} codigo={abierto} />}
    </>
  );
}

type Busqueda =
  | { tipo: "ninguna" }
  | { tipo: "buscando" }
  | { tipo: "listo"; atipicos: AtipicosRespuesta }
  | { tipo: "error"; error: unknown };

// RF-100: el botón «Buscar variaciones atípicas de precio» de la clásica, sobre los insumos de la versión. Solo lee y
// solo cuando se pulsa; cada variación es una advertencia que no impide nada.
function BuscarAtipicos({ proyecto, version }: { proyecto: string; version: string }) {
  const { alExpirar } = useAplicacion();
  const [busqueda, setBusqueda] = useState<Busqueda>({ tipo: "ninguna" });
  const vigente = useRef(true);

  useEffect(() => {
    vigente.current = true;
    return () => {
      vigente.current = false;
    };
  }, []);

  const buscar = () => {
    setBusqueda({ tipo: "buscando" });
    pedir<AtipicosRespuesta>(rutaDeAtipicos(proyecto, version)).then(
      (atipicos) => {
        if (vigente.current) setBusqueda({ tipo: "listo", atipicos });
      },
      (error: unknown) => {
        if (!vigente.current) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setBusqueda({ tipo: "error", error });
      },
    );
  };

  return (
    <section className="silice-hoja__seccion">
      <div>
        <Button kind="tertiary" size="md" onClick={buscar} disabled={busqueda.tipo === "buscando"}>
          {ROTULO_ATIPICOS}
        </Button>
        {busqueda.tipo === "buscando" && <InlineLoading description="Buscando variaciones atípicas..." status="active" />}
      </div>
      <div aria-live="polite" aria-atomic="true">
        {busqueda.tipo === "error" && <AvisoError error={busqueda.error} titulo="No se buscaron las variaciones atípicas" />}
        {busqueda.tipo === "listo" && (
          <>
            {busqueda.atipicos.avisos.map((aviso, i) => (
              <InlineNotification
                key={i}
                kind={aviso.nivel}
                role="status"
                title={aviso.nivel === "success" ? "Sin variaciones atípicas" : "Aviso"}
                subtitle={aviso.texto}
                lowContrast
                hideCloseButton
              />
            ))}
            {busqueda.atipicos.variaciones.length > 0 && (
              <div className="silice-hoja__atipicos" style={MORADO_ATIPICO}>
                <TablaPaginada
                  etiqueta="Variaciones atípicas de precio"
                  columnas={[
                    { clave: "insumo", titulo: "Insumo", ordenable: false },
                    {
                      clave: "porcentaje",
                      titulo: "Variación",
                      numerica: true,
                      ordenable: false,
                      celda: (f) => <Cifra monto={{ texto: f.porcentaje!, exacto: f.porcentaje_exacto! }} unidad="%" />,
                    },
                    { clave: "desde", titulo: "Desde", ordenable: false, presentar: fechaCorta },
                    { clave: "hasta", titulo: "Hasta", ordenable: false, presentar: fechaCorta },
                    { clave: "severidad", titulo: "Severidad", ordenable: false, celda: "severidad" },
                  ]}
                  filas={busqueda.atipicos.variaciones.map((v, i) => ({
                    id: `atipico-${i}`,
                    insumo: v.insumo,
                    porcentaje: v.porcentaje,
                    porcentaje_exacto: v.porcentaje_exacto,
                    desde: v.desde,
                    hasta: v.hasta,
                    severidad: v.severidad,
                  }))}
                />
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}

// Pestaña «Precios»: el origen del precio de cada insumo de la versión GUARDADA (no del borrador), evaluado a la fecha
// del servidor. Cotizar y retirar una cotización llegan en la rebanada 3d.
export function PestanaPrecios({ proyecto, version, alAusente }: Props) {
  if (version === null) return <p className="cds--type-body-compact-01">{SIN_VERSION}</p>;
  return (
    <VistaCarga<PreciosRespuesta> ruta={rutaDePrecios(proyecto, version)} etiqueta="Precios" alAusente={alAusente}>
      {(vista) => (
        <div className="silice-hoja__pestana">
          <p className="cds--type-body-compact-01">
            Lista, referencia, fecha, moneda y tasa de cada insumo, su origen y cuánto valor perdió hasta hoy (erosión). Una
            cotización (con su proveedor, número y fecha) vale solo para este proyecto y prevalece sobre la lista global
            hasta que se retire.
          </p>
          <p className="cds--type-helper-text-01">
            Se muestra la versión guardada, no los cambios sin guardar. Evaluada al {fechaCorta(vista.fecha_evaluacion)}.
          </p>
          <TablaDePrecios vista={vista} />
          <BuscarAtipicos proyecto={proyecto} version={version} />
        </div>
      )}
    </VistaCarga>
  );
}
