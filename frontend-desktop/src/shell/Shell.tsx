import { InlineNotification } from "@carbon/react";
import { Suspense, createElement, lazy, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactElement } from "react";
import { Navigate, Route, Routes, useLocation, useNavigationType } from "react-router";
import { ErrorDeApi, pedir } from "../api/cliente";
import type { CasosRespuesta, ProyectoRespuesta, SesionRespuesta } from "../api/tipos";
import { AvisoError } from "../comun/AvisoError";
import { EsqueletoPagina } from "../comun/EsqueletoPagina";
import { EstadoVacio } from "../comun/EstadoVacio";
import { TamanoLetra } from "../comun/TamanoLetra";
import { useTituloDelDocumento } from "../comun/tituloDelDocumento";
import { BarraSuperior } from "./BarraSuperior";
import { BotonRecorrido, ColumnaRecorrido } from "./ColumnaRecorrido";
import { ContextoAplicacion } from "./contexto";
import type { Aplicacion } from "./contexto";
import { LimiteDeError } from "./LimiteDeError";
import { MenuCuenta } from "./MenuCuenta";
import { MenuEnCapa } from "./MenuEnCapa";
import { navegacion } from "./navegacion";
import { PanelCarpetaProyecto, nombreDeCarpeta } from "./PanelCarpetaProyecto";
import { olvidarImportaciones } from "../paginas/hoja/useImportacion";
import { terminarRecorrido, useColumnaOculta, useRecorrido } from "./recorrido";
import { PAGINAS, rutaDe, visible } from "./rutas";
import type { PaginaDef } from "./rutas";
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
}: {
  pagina: PaginaDef;
  acciones: readonly string[];
  modoEntrega: boolean;
}) {
  if (!visible(pagina, acciones, modoEntrega)) {
    return (
      <div className="silice-pagina-aviso">
        <EstadoVacio titulo="Sin permiso" descripcion={MENSAJE_SIN_PERMISO} />
      </div>
    );
  }
  return elementoDe(pagina);
}

function esSinPermiso(e: unknown): boolean {
  return e instanceof ErrorDeApi && e.estado === 403;
}

// Marco de la interfaz: barra superior (areas por rol y modo entrega, carpeta y proyecto, recorrido, letra y cuenta), su
// capa para cuando no cabe, la columna del recorrido guiado y la pagina de la ruta.
export function Shell({ sesion, alSalir: alSalirDeApp, alExpirar: alExpirarDeApp, paginas = PAGINAS, almacen, crearHoja }: Props) {
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
  // cuenta», que desaparece con ella, o un enlace del panel de un area, que se cierra al elegir), pasa al h1 de la nueva:
  // el lector de pantalla la anuncia y el siguiente Tab parte de ahi. Si lo tiene otro control (un enlace directo de la
  // barra), no se toca. La primera carga tampoco: ahi el primer Tab debe ser «Saltar al contenido». La pagina se carga a
  // demanda: se espera su h1 unos cuadros.
  // Las redirecciones del indice («/») y de la ruta inexistente son `replace` a OTRA ruta: son la carga inicial, no un
  // cambio de pagina de la persona (ronda 1 del arbitro). Los enlaces, `navigate` y atras/adelante son PUSH o POP.
  // Elegir en un panel la pantalla ya abierta es un `replace` a la MISMA ruta (cambia solo la clave): el panel se cierra
  // con el enlace que tenia el foco, y el foco tambien va al h1.
  const rutaPrevia = useRef(ubicacion.pathname);
  const clavePrevia = useRef(ubicacion.key);
  const tipoNavegacion = useNavigationType();
  useEffect(() => {
    const mismaRuta = rutaPrevia.current === ubicacion.pathname;
    if (mismaRuta && clavePrevia.current === ubicacion.key) return;
    rutaPrevia.current = ubicacion.pathname;
    clavePrevia.current = ubicacion.key;
    if (!mismaRuta && tipoNavegacion === "REPLACE") return;
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
  }, [ubicacion.pathname, ubicacion.key, tipoNavegacion]);

  // Esc cierra el menu abierto como capa y devuelve el foco a su boton (VB-14). Se escucha en la fase de captura: la capa
  // detiene la propagacion de su propio Esc (para no cerrar nada mas) y este oyente no se enteraria.
  useEffect(() => {
    if (!menuAbierto) return;
    const alTeclear = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      setMenuAbierto(false);
      // El boton cambia de nombre al cerrarse; se le manda el foco cuando React ya lo repinto.
      requestAnimationFrame(() => document.querySelector<HTMLElement>(".cds--header__menu-toggle")?.focus());
    };
    document.addEventListener("keydown", alTeclear, true);
    return () => document.removeEventListener("keydown", alTeclear, true);
  }, [menuAbierto]);

  const acciones = sesion.acciones;
  const entradas = useMemo(() => navegacion(acciones, sesion.modo_entrega, paginas), [acciones, sesion.modo_entrega, paginas]);
  // Con la columna del recorrido a la vista, el contenido le cede su ancho (ColumnaRecorrido.scss).
  const recorrido = useRecorrido();
  const columnaOculta = useColumnaOculta();
  const conRecorrido = recorrido !== null && !columnaOculta;
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
        setAviso(`Ahora trabaja con la carpeta de trabajo «${nombreDeCarpeta(nombre)}». Si se reinicia la API, vuelve a la carpeta por defecto.`);
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

  const primera = paginas.find((p) => visible(p, acciones, sesion.modo_entrega));

  // Lado derecho de la barra, en este orden: carpeta y proyecto, recorrido (solo con la columna plegada), letra y cuenta.
  const derecha = (
    <>
      <PanelCarpetaProyecto
        casos={casos}
        proyectos={proyectos}
        elegido={proyecto}
        puedeCambiar={puedeCambiarCaso}
        ocupado={cambiandoCaso}
        alElegirCaso={(n) => void cambiarCaso(n)}
        alElegirProyecto={setProyecto}
      />
      <BotonRecorrido />
      <TamanoLetra />
      <MenuCuenta nombre={sesion.nombre} alSalir={alSalir} />
    </>
  );

  return (
    <ContextoAplicacion.Provider value={aplicacion}>
      <div className={conRecorrido ? "silice-marco silice-con-recorrido" : "silice-marco"}>
        {/* Con hash por enrutador un enlace #contenido cambiaria la ruta: se manda el foco a mano. */}
        <button type="button" className="silice-saltar cds--type-body-compact-01" onClick={() => document.getElementById("contenido")?.focus()}>
          Saltar al contenido
        </button>
        <BarraSuperior
          entradas={entradas}
          derecha={derecha}
          menu={{ abierto: menuAbierto, alternar: () => setMenuAbierto((a) => !a) }}
        />
        <MenuEnCapa entradas={entradas} abierto={menuAbierto} alCerrar={() => setMenuAbierto(false)} nombre={sesion.nombre} />
        {/* Antes del contenido: por debajo del umbral de la letra pasa a franja bajo la barra (ColumnaRecorrido.scss). */}
        <ColumnaRecorrido paginas={paginas} acciones={acciones} modoEntrega={sesion.modo_entrega} />
        <main id="contenido" className="silice-contenido" tabIndex={-1}>
          {(error !== null || aviso) && (
            <div className="silice-avisos">
              <AvisoError error={error} titulo="No se pudo completar la acción" alCerrar={() => setError(null)} />
              {aviso && (
                <InlineNotification
                  kind="info"
                  title="Carpeta de trabajo cambiada"
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
                          descripcion="Su cuenta no puede usar ninguna pantalla."
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
                      />
                    }
                  />
                ))}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </LimiteDeError>
        </main>
      </div>
    </ContextoAplicacion.Provider>
  );
}
