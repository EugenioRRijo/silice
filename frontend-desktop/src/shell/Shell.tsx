import { InlineNotification } from "@carbon/react";
import { Suspense, createElement, lazy, useCallback, useEffect, useMemo, useState } from "react";
import type { ReactElement } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router";
import { ErrorDeApi, pedir } from "../api/cliente";
import type { CasosRespuesta, ProyectoRespuesta, SesionRespuesta } from "../api/tipos";
import { AvisoError } from "../comun/AvisoError";
import { EsqueletoPagina } from "../comun/EsqueletoPagina";
import { EstadoVacio } from "../comun/EstadoVacio";
import { Cabecera } from "./Cabecera";
import { ContextoAplicacion } from "./contexto";
import type { Aplicacion } from "./contexto";
import { LimiteDeError } from "./LimiteDeError";
import { MenuLateral } from "./MenuLateral";
import { PAGINAS, enlaceClasico, estaMigrada, rutaDe, visible } from "./rutas";
import type { PaginaDef } from "./rutas";
import { SelectorCaso, SelectorProyecto } from "./Selectores";

export const MENSAJE_SIN_PERMISO = "Su cuenta no tiene permiso para esta pantalla o acción.";

interface Props {
  sesion: SesionRespuesta;
  alSalir: () => void;
  // La API contesto 401 en medio del trabajo: la sesion vencio.
  alExpirar: () => void;
  // Se puede cambiar solo en las pruebas.
  paginas?: readonly PaginaDef[];
  // Base de la interfaz Streamlit (por ejemplo http://127.0.0.1:8501), si se conoce.
  urlClasica?: string | null;
}

// Un elemento `lazy` por pagina, estable entre renders: React no vuelve a pedir el archivo. Se crea fuera del
// dibujado de los componentes (la regla static-components pide no crear componentes mientras se dibuja).
const elementos = new WeakMap<PaginaDef, ReactElement>();
function elementoDe(pagina: PaginaDef): ReactElement | null {
  const cargar = pagina.cargar;
  if (!cargar) return null;
  let elemento = elementos.get(pagina);
  if (!elemento) {
    elemento = createElement(lazy(cargar));
    elementos.set(pagina, elemento);
  }
  return elemento;
}

function PaginaDeRuta({
  pagina,
  acciones,
  modoEntrega,
  urlClasica,
}: {
  pagina: PaginaDef;
  acciones: readonly string[];
  modoEntrega: boolean;
  urlClasica?: string | null;
}) {
  if (!visible(pagina, acciones, modoEntrega)) {
    return (
      <div className="silice-pagina-aviso">
        <EstadoVacio titulo="Sin permiso" descripcion={MENSAJE_SIN_PERMISO} />
      </div>
    );
  }
  if (!estaMigrada(pagina)) {
    const enlace = enlaceClasico(urlClasica, pagina);
    return (
      <div className="silice-pagina-aviso">
        <EstadoVacio
          titulo={pagina.titulo}
          descripcion="Esta pantalla todavía está en la interfaz clásica de Sílice."
        >
          {enlace && (
            <a href={enlace} target="_blank" rel="noopener noreferrer" className="cds--link">
              Abrir en la interfaz clásica
            </a>
          )}
        </EstadoVacio>
      </div>
    );
  }
  return elementoDe(pagina);
}

function esSinPermiso(e: unknown): boolean {
  return e instanceof ErrorDeApi && e.estado === 403;
}

// Marco de la interfaz: cabecera con caso y proyecto, menu por rol y modo entrega, y la pagina de la ruta.
export function Shell({ sesion, alSalir, alExpirar, paginas = PAGINAS, urlClasica }: Props) {
  const ubicacion = useLocation();
  const [menuAbierto, setMenuAbierto] = useState(false);
  const [casos, setCasos] = useState<CasosRespuesta | null>(null);
  const [cambiandoCaso, setCambiandoCaso] = useState(false);
  const [proyectos, setProyectos] = useState<ProyectoRespuesta[] | null>(null);
  const [proyecto, setProyecto] = useState<string | null>(null);
  const [recarga, setRecarga] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  // Cambia con el caso: las paginas se vuelven a montar y piden sus datos de nuevo.
  const [generacion, setGeneracion] = useState(0);

  const acciones = sesion.acciones;
  const puedeCambiarCaso = acciones.includes("cambiar_caso");
  const casoActual = casos?.actual.ruta_relativa ?? null;

  const fallo = useCallback(
    (razon: unknown) => {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      else setError(razon);
    },
    [alExpirar],
  );

  useEffect(() => {
    let vigente = true;
    pedir<CasosRespuesta>("/v1/casos")
      .then((r) => {
        // Una API que no trae la forma esperada no tumba la pantalla: simplemente no hay selector de caso.
        if (vigente && r?.actual && Array.isArray(r.casos)) setCasos(r);
      })
      .catch((e: unknown) => {
        if (vigente && !esSinPermiso(e)) fallo(e);
      });
    return () => {
      vigente = false;
    };
  }, [fallo]);

  useEffect(() => {
    let vigente = true;
    pedir<ProyectoRespuesta[]>("/v1/proyectos")
      .then((respuesta) => {
        if (!vigente) return;
        const lista = Array.isArray(respuesta) ? respuesta : [];
        setProyectos(lista);
        setProyecto((previo) => (previo !== null && lista.some((p) => p.codigo === previo) ? previo : null));
      })
      .catch((e: unknown) => {
        if (!vigente) return;
        setProyectos(null);
        if (!esSinPermiso(e)) fallo(e);
      });
    return () => {
      vigente = false;
    };
  }, [fallo, casoActual, recarga]);

  const cambiarCaso = useCallback(
    async (nombre: string) => {
      setCambiandoCaso(true);
      setError(null);
      try {
        const respuesta = await pedir<Partial<CasosRespuesta>>("/v1/casos/actual", { metodo: "POST", cuerpo: { nombre } });
        setCasos((previo) => {
          const elegido = respuesta.actual ?? previo?.casos.find((c) => c.nombre === nombre);
          return previo && elegido ? { ...previo, actual: elegido } : previo;
        });
        setProyecto(null);
        setProyectos(null);
        setGeneracion((g) => g + 1);
        setAviso(`Ahora trabaja con el caso «${nombre}». Si se reinicia la API, vuelve al caso por defecto.`);
      } catch (e) {
        fallo(e);
      } finally {
        setCambiandoCaso(false);
      }
    },
    [fallo],
  );

  const recargarProyectos = useCallback(() => setRecarga((n) => n + 1), []);

  const aplicacion = useMemo<Aplicacion>(
    () => ({ sesion, proyecto, caso: casos?.actual ?? null, recargarProyectos, alExpirar }),
    [sesion, proyecto, casos, recargarProyectos, alExpirar],
  );

  const primera = paginas.find((p) => estaMigrada(p) && visible(p, acciones, sesion.modo_entrega));

  const selectores = (
    <>
      {casos && (
        <SelectorCaso casos={casos} puedeCambiar={puedeCambiarCaso} ocupado={cambiandoCaso} alElegir={(n) => void cambiarCaso(n)} />
      )}
      {proyectos && <SelectorProyecto proyectos={proyectos} elegido={proyecto} alElegir={setProyecto} />}
    </>
  );

  return (
    <ContextoAplicacion.Provider value={aplicacion}>
      {/* Con hash por enrutador un enlace #contenido cambiaria la ruta: se manda el foco a mano. */}
      <button type="button" className="silice-saltar cds--type-body-compact-01" onClick={() => document.getElementById("contenido")?.focus()}>
        Saltar al contenido
      </button>
      <Cabecera
        nombre={sesion.nombre}
        alSalir={alSalir}
        selectores={selectores}
        menu={{ abierto: menuAbierto, alternar: () => setMenuAbierto((a) => !a) }}
      />
      <MenuLateral
        paginas={paginas}
        acciones={acciones}
        modoEntrega={sesion.modo_entrega}
        urlClasica={urlClasica}
        abierto={menuAbierto}
        alCerrar={() => setMenuAbierto(false)}
      />
      <main id="contenido" className="silice-contenido" tabIndex={-1}>
        {(error !== null || aviso) && (
          <div className="silice-avisos">
            <AvisoError error={error} titulo="No se pudo completar la acción" alCerrar={() => setError(null)} />
            {aviso && (
              <InlineNotification
                kind="info"
                title="Caso cambiado"
                subtitle={aviso}
                lowContrast
                onClose={() => {
                  setAviso(null);
                  return false;
                }}
              />
            )}
          </div>
        )}
        <LimiteDeError key={`${ubicacion.pathname}|${generacion}`}>
          <Suspense fallback={<EsqueletoPagina />}>
            <Routes>
              <Route
                index
                element={
                  primera ? (
                    <Navigate to={rutaDe(primera)} replace />
                  ) : (
                    <div className="silice-pagina-aviso">
                      <EstadoVacio
                        titulo="No hay pantallas disponibles en esta interfaz"
                        descripcion="Las pantallas que su cuenta puede usar siguen en la interfaz clásica de Sílice."
                      />
                    </div>
                  )
                }
              />
              {paginas.map((pagina) => (
                <Route
                  key={pagina.id}
                  path={rutaDe(pagina)}
                  element={
                    <PaginaDeRuta
                      pagina={pagina}
                      acciones={acciones}
                      modoEntrega={sesion.modo_entrega}
                      urlClasica={urlClasica}
                    />
                  }
                />
              ))}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </LimiteDeError>
      </main>
    </ContextoAplicacion.Provider>
  );
}
