import { Close } from "@carbon/icons-react";
import { useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { JSX, KeyboardEvent as ReactKeyboardEvent } from "react";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { EnlaceDeNotificacionVista } from "./EnlaceDeNotificacionVista";
import { useNotificaciones } from "./ProveedorDeNotificaciones";
import { agruparPorDia, gravedadEnPalabra, hayDialogoModalAbierto, horaDeNotificacion } from "./modelo";
import "./PanelDeNotificaciones.scss";

type FiltroDePanel = "todas" | "sin-leer";

// La pantalla de Cuenta › Notificaciones (C11b). Vive aquí porque lo común no importa de las páginas: la página
// `paginas/notificaciones` la vuelve a exportar y el marco la registra con esta misma ruta.
export const RUTA_DE_PREFERENCIAS = "/cuenta/notificaciones";

export interface PropsDelPanelDeNotificaciones {
  ahora?: Date;
  rutaPreferencias?: string;
}

export function PanelDeNotificaciones({
  ahora,
  rutaPreferencias = RUTA_DE_PREFERENCIAS,
}: PropsDelPanelDeNotificaciones = {}): JSX.Element {
  const {
    notificaciones,
    sinLeer,
    marcarLeida,
    marcarTodasLeidas,
    panelAbierto,
    cerrarPanel,
    idPanel,
    enfocarCampanita,
  } = useNotificaciones();

  const [filtro, setFiltro] = useState<FiltroDePanel>("todas");
  const refTitulo = useRef<HTMLHeadingElement | null>(null);
  const abiertoAntesRef = useRef(false);
  const idBaseGrupos = useId();

  useLayoutEffect(() => {
    if (panelAbierto) {
      abiertoAntesRef.current = true;
      refTitulo.current?.focus();
      return;
    }
    if (abiertoAntesRef.current) {
      abiertoAntesRef.current = false;
      enfocarCampanita();
    }
  }, [panelAbierto, enfocarCampanita]);

  useEffect(() => {
    if (!panelAbierto) return;
    const alTeclearDocumento = (evento: KeyboardEvent) => {
      if (evento.key !== "Escape" || evento.defaultPrevented || hayDialogoModalAbierto()) return;
      evento.preventDefault();
      cerrarPanel();
    };
    document.addEventListener("keydown", alTeclearDocumento);
    return () => {
      document.removeEventListener("keydown", alTeclearDocumento);
    };
  }, [panelAbierto, cerrarPanel]);

  const alTeclearEnPanel = (evento: ReactKeyboardEvent<HTMLElement>) => {
    if (evento.key !== "Escape" || evento.defaultPrevented) return;
    evento.preventDefault();
    evento.stopPropagation();
    cerrarPanel();
  };

  const visibles = useMemo(
    () => (filtro === "sin-leer" ? notificaciones.filter((n) => !n.leida) : notificaciones),
    [filtro, notificaciones],
  );

  const grupos = useMemo(() => agruparPorDia(visibles, ahora), [visibles, ahora]);

  return (
    <aside
      id={idPanel}
      aria-label="Notificaciones"
      className="silice-panel-notificaciones"
      hidden={!panelAbierto}
      onKeyDown={alTeclearEnPanel}
    >
      {panelAbierto && (
        <>
          <div className="silice-panel-notificaciones__cabecera">
            <h2 ref={refTitulo} tabIndex={-1}>
              Notificaciones
            </h2>
            <button
              type="button"
              className="silice-panel-notificaciones__marcar"
              onClick={marcarTodasLeidas}
            >
              Marcar todas como leídas
            </button>
            <button
              type="button"
              className="silice-notificacion-cerrar"
              aria-label="Cerrar el panel"
              onClick={cerrarPanel}
            >
              <Close size={16} aria-hidden="true" />
            </button>
          </div>

          <div
            className="silice-panel-notificaciones__filtros"
            role="group"
            aria-label="Mostrar notificaciones"
          >
            <button
              type="button"
              aria-pressed={filtro === "todas"}
              onClick={() => setFiltro("todas")}
            >
              {"Todas "}
              <span className="silice-panel-notificaciones__cifra">
                {formatoEsVe(String(notificaciones.length))}
              </span>
            </button>
            <button
              type="button"
              aria-pressed={filtro === "sin-leer"}
              onClick={() => setFiltro("sin-leer")}
            >
              {"Sin leer "}
              <span className="silice-panel-notificaciones__cifra">
                {formatoEsVe(String(sinLeer))}
              </span>
            </button>
          </div>

          {grupos.length === 0 ? (
            <p className="silice-panel-notificaciones__vacio">
              {filtro === "sin-leer" && notificaciones.length > 0
                ? "No tiene notificaciones sin leer."
                : "No tiene notificaciones recientes."}
            </p>
          ) : (
            grupos.map((grupo, indice) => {
              const idGrupo = `${idBaseGrupos}-g-${indice}`;
              return (
                <section key={grupo.etiqueta} aria-labelledby={idGrupo}>
                  <h3 id={idGrupo} className="silice-panel-notificaciones__grupo-titulo">
                    {grupo.etiqueta}
                  </h3>
                  {grupo.items.map((item) => {
                    const hora = horaDeNotificacion(item.creada);
                    const lineaDetalle = [item.detalle, hora].filter(Boolean).join(" · ");
                    const claseItem = item.leida
                      ? "silice-panel-notificaciones__item"
                      : "silice-panel-notificaciones__item silice-panel-notificaciones__item--sin-leer";
                    return (
                      <article key={item.id} className={claseItem}>
                        <span className="silice-notificacion-gravedad" data-gravedad={item.gravedad}>
                          {gravedadEnPalabra(item.gravedad)}
                        </span>
                        {" · "}
                        <span>{item.titulo}</span>
                        {lineaDetalle !== "" && <p>{lineaDetalle}</p>}
                        {item.enlace !== undefined && (
                          <EnlaceDeNotificacionVista
                            enlace={item.enlace}
                            alSeguir={() => marcarLeida(item.id)}
                          />
                        )}
                      </article>
                    );
                  })}
                </section>
              );
            })
          )}

          <p className="silice-panel-notificaciones__pie">
            Las notificaciones se guardan 30 días.
            {" "}
            <EnlaceDeNotificacionVista
              enlace={{ texto: "Elegir qué notificaciones recibir", ruta: rutaPreferencias }}
            />
          </p>
        </>
      )}
    </aside>
  );
}
