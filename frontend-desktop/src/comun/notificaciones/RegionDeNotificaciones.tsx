import { Close } from "@carbon/icons-react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { FocusEvent, JSX } from "react";
import { EnlaceDeNotificacionVista } from "./EnlaceDeNotificacionVista";
import { useNotificaciones } from "./ProveedorDeNotificaciones";
import { duracionDeNotificacion, gravedadEnPalabra } from "./modelo";
import type { Notificacion } from "./modelo";
import "./RegionDeNotificaciones.scss";

interface PropsDeTarjeta {
  notificacion: Notificacion;
  modalAbierto: boolean;
  alCerrarPorTiempo: (id: string) => void;
  alCerrarManual: (id: string, teniaFoco: boolean) => void;
  alSeguirEnlace: (id: string) => void;
  registrarBotonCerrar: (id: string, boton: HTMLButtonElement | null) => void;
}

function TarjetaDeNotificacion({
  notificacion,
  modalAbierto,
  alCerrarPorTiempo,
  alCerrarManual,
  alSeguirEnlace,
  registrarBotonCerrar,
}: PropsDeTarjeta): JSX.Element {
  const duracion = duracionDeNotificacion(notificacion.gravedad);
  const [conCursor, setConCursor] = useState(false);
  const [conFoco, setConFoco] = useState(false);
  const pausado = conCursor || conFoco || modalAbierto;

  const restanteRef = useRef<number | null>(duracion);
  const inicioTramoRef = useRef<number | null>(null);
  const tarjetaRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (duracion === null || pausado) return;

    const demora = restanteRef.current ?? duracion;
    inicioTramoRef.current = Date.now();
    const reloj = setTimeout(() => {
      restanteRef.current = 0;
      inicioTramoRef.current = null;
      alCerrarPorTiempo(notificacion.id);
    }, demora);

    return () => {
      clearTimeout(reloj);
      if (inicioTramoRef.current !== null && restanteRef.current !== null) {
        const transcurrido = Math.max(0, Date.now() - inicioTramoRef.current);
        restanteRef.current = Math.max(1, restanteRef.current - transcurrido);
        inicioTramoRef.current = null;
      }
    };
  }, [duracion, pausado, notificacion.id, alCerrarPorTiempo]);

  const alSalirFoco = (evento: FocusEvent<HTMLElement>) => {
    if (!evento.currentTarget.contains(evento.relatedTarget as Node | null)) {
      setConFoco(false);
    }
  };

  const refCerrar = useCallback(
    (boton: HTMLButtonElement | null) => {
      registrarBotonCerrar(notificacion.id, boton);
    },
    [notificacion.id, registrarBotonCerrar],
  );

  return (
    <article
      ref={tarjetaRef}
      className="silice-notificacion-tarjeta"
      onMouseEnter={() => setConCursor(true)}
      onMouseLeave={() => setConCursor(false)}
      onFocus={() => setConFoco(true)}
      onBlur={alSalirFoco}
    >
      <div className="silice-notificacion-tarjeta__cabecera">
        <span className="silice-notificacion-gravedad" data-gravedad={notificacion.gravedad}>
          {gravedadEnPalabra(notificacion.gravedad)}
        </span>
        <span className="silice-notificacion-tarjeta__titulo">{notificacion.titulo}</span>
        <button
          ref={refCerrar}
          type="button"
          className="silice-notificacion-cerrar"
          aria-label={`Cerrar: ${notificacion.titulo}`}
          onClick={() => {
            const activo = document.activeElement;
            const teniaFoco = activo !== null && Boolean(tarjetaRef.current?.contains(activo));
            alCerrarManual(notificacion.id, teniaFoco);
          }}
        >
          <Close size={16} aria-hidden="true" />
        </button>
      </div>
      {notificacion.detalle !== undefined && notificacion.detalle !== "" && (
        <p className="silice-notificacion-tarjeta__detalle">{notificacion.detalle}</p>
      )}
      {notificacion.enlace !== undefined && (
        <EnlaceDeNotificacionVista
          enlace={notificacion.enlace}
          className="silice-notificacion-tarjeta__enlace"
          alSeguir={() => alSeguirEnlace(notificacion.id)}
        />
      )}
    </article>
  );
}

// Región fija abajo a la derecha («Notificaciones nuevas»), sin región viva propia (usa Anunciador) y sin robar el foco.
export function RegionDeNotificaciones(): JSX.Element {
  const { emergentes, cerrar, marcarLeida, enfocarCampanita, modalAbierto } = useNotificaciones();
  const botonesCerrarRef = useRef<Map<string, HTMLButtonElement>>(new Map());
  const focoPrevioExternoRef = useRef<HTMLElement | null>(null);
  const regionRef = useRef<HTMLDivElement | null>(null);

  const registrarBotonCerrar = useCallback((id: string, boton: HTMLButtonElement | null) => {
    if (boton === null) botonesCerrarRef.current.delete(id);
    else botonesCerrarRef.current.set(id, boton);
  }, []);

  const alEntrarFocoRegion = (evento: FocusEvent<HTMLDivElement>) => {
    const origen = evento.relatedTarget;
    if (origen instanceof HTMLElement && !regionRef.current?.contains(origen)) {
      focoPrevioExternoRef.current = origen;
    }
  };

  const alCerrarManual = useCallback(
    (id: string, teniaFoco: boolean) => {
      const indice = emergentes.findIndex((n) => n.id === id);
      const siguiente =
        indice >= 0 ? (emergentes[indice + 1] ?? emergentes[indice - 1] ?? null) : null;
      cerrar(id);
      if (!teniaFoco) return;
      if (siguiente !== null) {
        const botonSiguiente = botonesCerrarRef.current.get(siguiente.id);
        if (botonSiguiente !== undefined && botonSiguiente.isConnected) {
          botonSiguiente.focus();
          return;
        }
      }
      const externo = focoPrevioExternoRef.current;
      if (externo !== null && externo.isConnected) {
        externo.focus();
        return;
      }
      enfocarCampanita();
    },
    [cerrar, emergentes, enfocarCampanita],
  );

  return (
    <div
      ref={regionRef}
      role="region"
      aria-label="Notificaciones nuevas"
      className="silice-notificaciones-region"
      onFocus={alEntrarFocoRegion}
    >
      {emergentes.map((notificacion) => (
        <TarjetaDeNotificacion
          key={notificacion.id}
          notificacion={notificacion}
          modalAbierto={modalAbierto}
          alCerrarPorTiempo={cerrar}
          alCerrarManual={alCerrarManual}
          alSeguirEnlace={marcarLeida}
          registrarBotonCerrar={registrarBotonCerrar}
        />
      ))}
    </div>
  );
}
