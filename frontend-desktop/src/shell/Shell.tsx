import { InlineNotification } from "@carbon/react";
import { Suspense, createElement, lazy, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactElement } from "react";
import { Navigate, Route, Routes, useLocation, useNavigationType } from "react-router";
import { ErrorDeApi, pedir } from "../api/cliente";
import type { CasosRespuesta, ProyectoRespuesta, SesionRespuesta } from "../api/tipos";
import { AvisoError } from "../comun/AvisoError";
import { EsqueletoPagina } from "../comun/EsqueletoPagina";
import { EstadoVacio } from "../comun/EstadoVacio";
import { useTituloDelDocumento } from "../comun/tituloDelDocumento";
import { Cabecera } from "./Cabecera";
import { ContextoAplicacion } from "./contexto";
import type { Aplicacion } from "./contexto";
import { LimiteDeError } from "./LimiteDeError";
import { MenuLateral } from "./MenuLateral";
import { olvidarImportaciones } from "../paginas/hoja/useImportacion";
import { terminarRecorrido } from "./recorrido";
import { PAGINAS, enlaceClasico, estaMigrada, rutaDe, visible } from "./rutas";
import type { PaginaDef } from "./rutas";
import { SelectorCaso, SelectorProyecto } from "./Selectores";
import type { AlmacenDelVisor } from "../visor/almacen";
import type { CrearHojaVisor } from "../visor/hojaVisor";

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
  // Lo abierto en «Libro de la empresa», guardado por encima de la puerta de sesion (UC-26).
  almacen?: AlmacenDelVisor;
  // Solo en pruebas: el visor de hojas (por omision, Univer).
  crearHoja?: CrearHojaVisor;
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
export function Shell({ sesion, alSalir: alSalirDeApp, alExpirar: alExpirarDeApp, paginas = PAGINAS, urlClasica, almacen, crearHoja }: Props) {
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

  // Un recorrido en curso no sobrevive a la sesion: al salir o vencer se cierra (vive fuera del arbol de React).
  const alSalir = useCallback(() => {
    terminarRecorrido();
    olvidarImportaciones();
    alSalirDeApp();
  }, [alSalirDeApp]);
  const alExpirar = useCallback(() => {
    terminarRecorrido();
    olvidarImportaciones();
    alExpirarDeApp();
  }, [alExpirarDeApp]);

  useTituloDelDocumento(paginas.find((p) => rutaDe(p) === ubicacion.pathname)?.titulo ?? null);

  // VD-7: si al cambiar de pagina el foco se perdio (lo tenia un control de la pagina anterior, p. ej. «Auditar por mi
  // cuenta», que desaparece con ella), pasa al h1 de la nueva: el lector de pantalla la anuncia y el siguiente Tab
  // parte de ahi. Si lo tiene otro control (un enlace del menu), no se toca. La primera carga tampoco: ahi el primer
  // Tab debe ser «Saltar al contenido». La pagina se carga a demanda: se espera su h1 unos cuadros.
  // Las redirecciones del indice («/») y de la ruta inexistente son `replace`: son la carga inicial, no un cambio de
  // pagina de la persona (ronda 1 del arbitro). Los enlaces, `navigate` y atras/adelante son PUSH o POP.
  const rutaPrevia = useRef(ubicacion.pathname);
  const tipoNavegacion = useNavigationType();
  useEffect(() => {
    if (rutaPrevia.current === ubicacion.pathname) return;
    rutaPrevia.current = ubicacion.pathname;
    if (tipoNavegacion === "REPLACE") return;
    let cuadro = 0;
    let intento = 0;
    const buscar = () => {
      const activo = document.activeElement;
      if (activo && activo !== document.body) return;
      // Sin el h1 del esqueleto: lo sustituye el de la pagina real y el foco quedaria en <body>.
      const titulo = document.querySelector<HTMLElement>("#contenido h1:not([data-esqueleto])");
      if (titulo) {
        titulo.tabIndex = -1;
        titulo.focus({ preventScroll: true });
        return;
      }
      if (++intento < 240) cuadro = requestAnimationFrame(buscar);
    };
    cuadro = requestAnimationFrame(buscar);
    return () => cancelAnimationFrame(cuadro);
  }, [ubicacion.pathname, tipoNavegacion]);

  // Esc cierra el menu abierto como capa y devuelve el foco a su boton (VB-14).
  useEffect(() => {
    if (!menuAbierto) return;
    const alTeclear = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      setMenuAbierto(false);
      // El boton cambia de nombre al cerrarse; se le manda el foco cuando React ya lo repinto.
      requestAnimationFrame(() => document.querySelector<HTMLElement>(".cds--header__menu-toggle")?.focus());
    };
    document.addEventListener("keydown", alTeclear);
    return () => document.removeEventListener("keydown", alTeclear);
  }, [menuAbierto]);

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

  // Sin `leer_proyecto` la API contesta 403: no se pide (VB-9).
  const puedeLeerProyectos = acciones.includes("leer_proyecto");
  useEffect(() => {
    if (!puedeLeerProyectos) return;
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
  }, [fallo, casoActual, recarga, puedeLeerProyectos]);

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
    () => ({
      sesion,
      proyecto,
      nombreProyecto: proyectos?.find((p) => p.codigo === proyecto)?.nombre ?? null,
      caso: casos?.actual ?? null,
      recargarProyectos,
      alExpirar,
      almacenDelLibro: almacen,
      crearHojaVisor: crearHoja,
    }),
    [sesion, proyecto, proyectos, casos, recargarProyectos, alExpirar, almacen, crearHoja],
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
        nombre={sesion.nombre}
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
