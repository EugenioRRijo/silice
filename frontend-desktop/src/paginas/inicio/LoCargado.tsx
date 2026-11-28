import { ErrorFilled, WarningAltFilled } from "@carbon/icons-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import type { CarpetaRespuesta } from "../../api/tipos";
import { AvisoError } from "../../comun/AvisoError";
import type { Carga } from "../../comun/useCarga";
import { SinDato } from "../../comun/VisualMeters";
import { fechaEsVe, formatoEsVe } from "../../indicadores/formatoEsVe";
import type { ExistenciaRespuesta } from "./PanelArenera";
import { TEXTOS } from "./textos";
import { resultadoEnUnaLinea } from "./UltimasAuditorias";
import type { AuditoriaGuardadaRespuesta } from "./UltimasAuditorias";

export interface PartidaResumenRespuesta {
  codigo: string;
}

export interface InsumoResumenRespuesta {
  codigo: string;
  precio_vigente: string | null;
}

interface EnlacesDeLoCargado {
  auditoria: string | null;
  precios: string | null;
  catalogo: string | null;
  produccion: string | null;
}

interface Props {
  auditorias: Carga<AuditoriaGuardadaRespuesta[]>;
  carpeta: Carga<CarpetaRespuesta>;
  partidas: Carga<PartidaResumenRespuesta[]>;
  insumos: Carga<InsumoResumenRespuesta[]>;
  arenera: Carga<ExistenciaRespuesta[]>;
  enlaces: EnlacesDeLoCargado;
}

function Tarjeta({
  etiqueta,
  cifra,
  detalle,
  enlace,
  children,
}: {
  etiqueta: string;
  cifra?: ReactNode;
  detalle?: ReactNode;
  enlace?: { texto: string; ruta: string } | null;
  children?: ReactNode;
}) {
  return (
    <article className="silice-inicio__tarjeta" aria-label={etiqueta}>
      <span className="silice-inicio__tarjeta-etiqueta">{etiqueta}</span>
      {children ?? (
        <>
          <span className="silice-inicio__tarjeta-cifra">{cifra}</span>
          {detalle !== undefined && <span className="silice-inicio__tarjeta-detalle">{detalle}</span>}
        </>
      )}
      {enlace && (
        <Link className="cds--link silice-inicio__tarjeta-enlace" to={enlace.ruta}>
          {enlace.texto}
        </Link>
      )}
    </article>
  );
}

function TarjetaSegunCarga<T>({
  etiqueta,
  carga,
  tituloError,
  enlace,
  pintar,
}: {
  etiqueta: string;
  carga: Carga<T>;
  tituloError: string;
  enlace: { texto: string; ruta: string } | null;
  pintar: (datos: T) => { cifra: ReactNode; detalle: ReactNode };
}) {
  if (carga.estado === "sin_permiso") return null;
  if (carga.estado === "cargando") {
    return (
      <Tarjeta etiqueta={etiqueta} enlace={enlace}>
        <span className="silice-inicio__tarjeta-detalle" role="status">
          Cargando…
        </span>
      </Tarjeta>
    );
  }
  if (carga.estado === "error") {
    return (
      <Tarjeta etiqueta={etiqueta} enlace={enlace}>
        <AvisoError error={carga.error} titulo={tituloError} />
      </Tarjeta>
    );
  }
  if (carga.estado === "no_disponible") {
    return <Tarjeta etiqueta={etiqueta} cifra={<SinDato />} detalle="No disponible en esta instalación" enlace={enlace} />;
  }
  const { cifra, detalle } = pintar(carga.datos);
  return <Tarjeta etiqueta={etiqueta} cifra={cifra} detalle={detalle} enlace={enlace} />;
}

function detalleDeLibros(datos: readonly AuditoriaGuardadaRespuesta[]): { cifra: string; detalle: string } {
  const cuenta = datos.length >= 100 ? `${formatoEsVe(String(datos.length))}+` : formatoEsVe(String(datos.length));
  if (datos.length === 0) return { cifra: "0", detalle: TEXTOS.cargado.libros.sinDatos };
  const ultima = datos[0]!;
  const dia = fechaEsVe(ultima.fecha.slice(0, 10));
  return {
    cifra: cuenta,
    detalle: `Último el ${dia} (${ultima.archivo}) · ${resultadoEnUnaLinea(ultima.errores, ultima.advertencias)}`,
  };
}

function detalleDeLista(datos: CarpetaRespuesta): { cifra: string; detalle: string } {
  if (datos.lista === null) {
    return {
      cifra: TEXTOS.cargado.lista.sinLista,
      detalle: datos.aviso ?? TEXTOS.cargado.lista.sinDatos,
    };
  }
  const partes = [`Vigencia: ${fechaEsVe(datos.lista.fecha)}`, `Moneda ${datos.lista.moneda}`];
  if (datos.aviso) partes.push(datos.aviso);
  return {
    cifra: datos.lista.nombre,
    detalle: partes.join(" · "),
  };
}

function detalleDePartidas(datos: readonly PartidaResumenRespuesta[]): { cifra: string; detalle: string } {
  const total = formatoEsVe(String(datos.length));
  if (datos.length === 0) return { cifra: "0", detalle: TEXTOS.cargado.partidas.sinDatos };
  return {
    cifra: total,
    detalle: datos.length === 1 ? "1 partida guardada para armar" : `${total} partidas guardadas para armar`,
  };
}

function detalleDeInsumos(datos: readonly InsumoResumenRespuesta[]): { cifra: string; detalle: string } {
  const total = formatoEsVe(String(datos.length));
  if (datos.length === 0) return { cifra: "0", detalle: TEXTOS.cargado.insumos.sinDatos };
  const sinPrecio = datos.filter((i) => i.precio_vigente === null).length;
  if (sinPrecio === 0) return { cifra: total, detalle: TEXTOS.cargado.insumos.todosVigentes };
  return {
    cifra: total,
    detalle: sinPrecio === 1 ? "1 insumo sin precio vigente" : `${formatoEsVe(String(sinPrecio))} insumos sin precio vigente`,
  };
}

function detalleDeProduccion(datos: readonly ExistenciaRespuesta[]): { cifra: string; detalle: ReactNode } {
  const total = formatoEsVe(String(datos.length));
  if (datos.length === 0) return { cifra: "0", detalle: TEXTOS.cargado.produccion.sinMateriales };
  const base = datos.length === 1 ? "1 material registrado" : `${total} materiales registrados`;
  const negativas = datos.filter((f) => f.negativa).length;
  const pocos = datos.filter((f) => !f.negativa && f.queda_poco).length;
  if (negativas === 0 && pocos === 0) return { cifra: total, detalle: `${base} · ${TEXTOS.cargado.produccion.todoBien}` };
  return {
    cifra: total,
    detalle: (
      <>
        {base}
        {negativas > 0 && (
          <>
            {" · "}
            <span className="silice-inicio__gravedad silice-inicio__gravedad--error">
              <ErrorFilled size={16} aria-hidden="true" />
              {negativas === 1
                ? "Error · 1 con existencia negativa"
                : `Error · ${formatoEsVe(String(negativas))} con existencia negativa`}
            </span>
          </>
        )}
        {pocos > 0 && (
          <>
            {" · "}
            <span className="silice-inicio__gravedad silice-inicio__gravedad--adv">
              <WarningAltFilled size={16} aria-hidden="true" />
              {pocos === 1 ? "Advertencia · 1 queda poco" : `Advertencia · ${formatoEsVe(String(pocos))} quedan poco`}
            </span>
          </>
        )}
      </>
    ),
  };
}

// Tarjetas de «Lo que hay cargado» (especificación 00-inicio-resumen.html): solo con los recursos que la aplicación ya
// consulta según los permisos de la cuenta. Cada tarjeta falla por su cuenta sin tumbar a las demás.
export function LoCargado({ auditorias, carpeta, partidas, insumos, arenera, enlaces }: Props) {
  const todasSinPermiso = [auditorias, carpeta, partidas, insumos, arenera].every((c) => c.estado === "sin_permiso");
  if (todasSinPermiso) return null;

  return (
    <section className="silice-inicio__seccion" aria-labelledby="inicio-cargado">
      <h2 id="inicio-cargado" className="silice-inicio__subtitulo-seccion cds--type-heading-compact-02">
        {TEXTOS.cargado.titulo}
      </h2>
      <div className="silice-inicio__tarjetas">
        <TarjetaSegunCarga
          etiqueta={TEXTOS.cargado.libros.etiqueta}
          carga={auditorias}
          tituloError={TEXTOS.cargado.libros.error}
          enlace={enlaces.auditoria ? { texto: TEXTOS.cargado.libros.ir, ruta: enlaces.auditoria } : null}
          pintar={detalleDeLibros}
        />
        <TarjetaSegunCarga
          etiqueta={TEXTOS.cargado.lista.etiqueta}
          carga={carpeta}
          tituloError={TEXTOS.cargado.lista.error}
          enlace={enlaces.precios ? { texto: TEXTOS.cargado.lista.ir, ruta: enlaces.precios } : null}
          pintar={detalleDeLista}
        />
        <TarjetaSegunCarga
          etiqueta={TEXTOS.cargado.partidas.etiqueta}
          carga={partidas}
          tituloError={TEXTOS.cargado.partidas.error}
          enlace={enlaces.catalogo ? { texto: TEXTOS.cargado.partidas.ir, ruta: enlaces.catalogo } : null}
          pintar={detalleDePartidas}
        />
        <TarjetaSegunCarga
          etiqueta={TEXTOS.cargado.insumos.etiqueta}
          carga={insumos}
          tituloError={TEXTOS.cargado.insumos.error}
          enlace={enlaces.catalogo ? { texto: TEXTOS.cargado.insumos.ir, ruta: enlaces.catalogo } : null}
          pintar={detalleDeInsumos}
        />
        <TarjetaSegunCarga
          etiqueta={TEXTOS.cargado.produccion.etiqueta}
          carga={arenera}
          tituloError={TEXTOS.cargado.produccion.error}
          enlace={enlaces.produccion ? { texto: TEXTOS.cargado.produccion.ir, ruta: enlaces.produccion } : null}
          pintar={detalleDeProduccion}
        />
      </div>
    </section>
  );
}
