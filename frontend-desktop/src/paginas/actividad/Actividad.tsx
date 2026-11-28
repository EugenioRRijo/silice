import { Button, SkeletonText } from "@carbon/react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, KeyboardEvent } from "react";
import { AvisoError } from "../../comun/AvisoError";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { TablaDensa } from "../../comun/TablaDensa";
import { useCarga } from "../../comun/useCarga";
import { cantidadEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import {
  NIVELES,
  TIPOS,
  accionesEnTexto,
  cifrasEnLista,
  conMayuscula,
  eventosDelDia,
  fechaVe,
  filtrarEventos,
  moverFoco,
  nivelesPorCuantiles,
  nombreDeCelda,
  rotulosDeMeses,
  semanas,
} from "./logica";
import type { ActividadRespuesta, TipoDeEvento } from "./logica";
import "./actividad.scss";

const PISTA = "Pase el cursor por un día, o muévase con las flechas, para ver lo que se hizo.";

function Calendario({ datos }: { datos: ActividadRespuesta }) {
  const contenedor = useRef<HTMLDivElement>(null);
  const columnas = useMemo(() => semanas(datos.desde, datos.hasta), [datos.desde, datos.hasta]);
  const rotulos = useMemo(() => rotulosDeMeses(columnas), [columnas]);
  const cuantosPorDia = useMemo(() => new Map(datos.dias.map((d) => [d.fecha, d.cuantos])), [datos.dias]);
  const nivelDe = useMemo(() => nivelesPorCuantiles(datos.dias), [datos.dias]);
  // El único día que recibe el foco con Tab es el último con actividad (o el último del período); las flechas mueven el resto.
  const inicial = datos.dias.length > 0 ? datos.dias[datos.dias.length - 1]!.fecha : datos.hasta;
  const [enfocada, setEnfocada] = useState(inicial);
  const [detalle, setDetalle] = useState<string | null>(null);

  function alTeclear(e: KeyboardEvent<HTMLButtonElement>, fecha: string) {
    const destino = moverFoco(fecha, e.key, datos.desde, datos.hasta);
    if (destino === fecha) return;
    e.preventDefault();
    setEnfocada(destino);
    contenedor.current?.querySelector<HTMLButtonElement>(`[data-fecha="${destino}"]`)?.focus();
  }

  // Si aun con las celdas al mínimo no cabe un año, la caja se abre en la semana más reciente (como el calendario de GitHub).
  useEffect(() => {
    const caja = contenedor.current;
    if (caja) caja.scrollLeft = caja.scrollWidth;
  }, [columnas.length]);

  const delDia = detalle === null ? [] : eventosDelDia(datos.eventos, detalle);
  return (
    <>
      <div
        className="silice-actividad__calendario"
        ref={contenedor}
        style={{ "--silice-actividad-columnas": columnas.length } as CSSProperties}
      >
        <div className="silice-actividad__meses" style={{ gridTemplateColumns: `repeat(${columnas.length}, var(--silice-actividad-celda))` }} aria-hidden="true">
          {rotulos.map((r) => (
            <span key={r.semana} className="silice-actividad__mes cds--type-label-01" style={{ gridColumn: r.semana + 1 }}>
              {r.mes}
            </span>
          ))}
        </div>
        <div role="group" aria-label="Calendario de actividad: un cuadro por día" className="silice-actividad__semanas">
          {columnas.map((semana, i) => (
            <div key={i} className="silice-actividad__semana">
              {semana.map((fecha, j) =>
                fecha === null ? (
                  <span key={j} className="silice-actividad__hueco" aria-hidden="true" />
                ) : (
                  <button
                    key={fecha}
                    type="button"
                    data-fecha={fecha}
                    data-nivel={nivelDe(cuantosPorDia.get(fecha) ?? 0)}
                    className="silice-actividad__dia"
                    aria-label={nombreDeCelda(fecha, cuantosPorDia.get(fecha) ?? 0)}
                    tabIndex={fecha === enfocada ? 0 : -1}
                    onFocus={() => {
                      setEnfocada(fecha);
                      setDetalle(fecha);
                    }}
                    onMouseEnter={() => setDetalle(fecha)}
                    onClick={() => setDetalle(fecha)}
                    onKeyDown={(e) => alTeclear(e, fecha)}
                  />
                ),
              )}
            </div>
          ))}
        </div>
      </div>
      <div className="silice-actividad__detalle cds--type-body-compact-01" role="status" aria-live="polite">
        {detalle === null ? (
          <p>{PISTA}</p>
        ) : (
          <>
            <p>
              <strong>{fechaVe(detalle)}</strong>
              {`: ${accionesEnTexto(cuantosPorDia.get(detalle) ?? 0)}`}
            </p>
            {delDia.length > 0 && (
              <ul>
                {delDia.map((e, i) => (
                  <li key={i}>{conMayuscula(e.texto)}</li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>
      <div className="silice-actividad__leyenda cds--type-label-01" aria-hidden="true">
        <span>Menos</span>
        {NIVELES.map((n) => (
          <span key={n} className="silice-actividad__dia silice-actividad__dia--leyenda" data-nivel={n} />
        ))}
        <span>Más</span>
      </div>
    </>
  );
}

function ListaReciente({ datos }: { datos: ActividadRespuesta }) {
  const [tipo, setTipo] = useState<TipoDeEvento | null>(null);
  const visibles = filtrarEventos(datos.eventos, tipo);
  return (
    <>
      <div role="group" aria-label="Filtrar por tipo de acción" className="silice-actividad__filtros">
        <Button size="sm" kind={tipo === null ? "primary" : "tertiary"} aria-pressed={tipo === null} onClick={() => setTipo(null)}>
          Todo
        </Button>
        {TIPOS.map((t) => (
          <Button key={t.tipo} size="sm" kind={tipo === t.tipo ? "primary" : "tertiary"} aria-pressed={tipo === t.tipo} onClick={() => setTipo(t.tipo)}>
            {t.etiqueta}
          </Button>
        ))}
      </div>
      {visibles.length === 0 ? (
        <EstadoVacio
          titulo="Sin actividad"
          descripcion={tipo === null ? "En este período no hay nada que mostrar." : "No hay acciones de este tipo en el período."}
        />
      ) : (
        <ul className="silice-actividad__lista cds--type-body-compact-01">
          {visibles.map((e, i) => (
            <li key={`${e.fecha}-${i}`}>
              <span className="silice-codigo silice-actividad__cuando">{fechaVe(e.fecha)}</span>
              <span>{conMayuscula(e.texto)}</span>
            </li>
          ))}
        </ul>
      )}
      {datos.recortado && (
        <p className="silice-actividad__nota cds--type-helper-text-01">
          {`Se muestran las ${cantidadEsVe(String(datos.eventos.length))} acciones más recientes; las cifras de arriba cuentan todas.`}
        </p>
      )}
    </>
  );
}

function Contenido({ datos }: { datos: ActividadRespuesta }) {
  const [comoTabla, setComoTabla] = useState(false);
  return (
    <div className="silice-actividad">
      <section aria-labelledby="actividad-resumen" className="silice-actividad__bloque">
        <h2 id="actividad-resumen" className="cds--type-heading-compact-02">
          Resumen del período
        </h2>
        <p className="cds--type-body-compact-01">{`Del ${fechaVe(datos.desde)} al ${fechaVe(datos.hasta)}.`}</p>
        <dl className="silice-actividad__cifras">
          {cifrasEnLista(datos.cifras).map((c) => (
            <div key={c.tipo} className="silice-actividad__cifra">
              <dt className="cds--type-label-01">{c.etiqueta}</dt>
              <dd className="silice-codigo cds--type-heading-04">{cantidadEsVe(String(c.cuantos))}</dd>
            </div>
          ))}
        </dl>
      </section>
      <section aria-labelledby="actividad-calendario" className="silice-actividad__bloque">
        <h2 id="actividad-calendario" className="cds--type-heading-compact-02">
          Calendario de actividad
        </h2>
        <Calendario datos={datos} />
        <div>
          <Button size="sm" kind="ghost" aria-pressed={comoTabla} onClick={() => setComoTabla((v) => !v)}>
            Ver como tabla
          </Button>
        </div>
        {comoTabla && (
          <TablaDensa
            etiqueta="Actividad por día"
            columnas={[
              { clave: "fecha", titulo: "Fecha", celda: (f) => fechaVe(f["fecha"] ?? "") },
              { clave: "cuantos", titulo: "Acciones", numerica: true },
            ]}
            filas={datos.dias.map((d) => ({ id: d.fecha, fecha: d.fecha, cuantos: String(d.cuantos) }))}
            vacio={{ titulo: "Sin actividad en el período" }}
          />
        )}
      </section>
      <section aria-labelledby="actividad-reciente" className="silice-actividad__bloque">
        <h2 id="actividad-reciente" className="cds--type-heading-compact-02">
          Actividad reciente
        </h2>
        <ListaReciente datos={datos} />
      </section>
    </div>
  );
}

// La actividad de una cuenta, como la de GitHub: el calendario del último año, las cifras y lo último que hizo. Solo lee
// (`GET /v1/actividad`); el título de la pantalla lo pone quien la monta. Quien no puede ver esta cuenta recibe el motivo
// de la API tal cual.
export default function Actividad({ usuario }: { usuario: string }) {
  const { alExpirar } = useAplicacion();
  const carga = useCarga<ActividadRespuesta>(`/v1/actividad?usuario=${encodeURIComponent(usuario)}`, alExpirar);
  if (carga.estado === "cargando") {
    return (
      <div role="status" aria-busy="true" aria-label="Cargando la actividad">
        <SkeletonText paragraph lineCount={4} />
      </div>
    );
  }
  if (carga.estado !== "listo") return <AvisoError error={carga.error} titulo="No se puede mostrar esta actividad" />;
  return <Contenido key={usuario} datos={carga.datos} />;
}
