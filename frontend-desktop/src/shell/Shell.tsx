import { InlineNotification } from "@carbon/react";
import { Suspense, createElement, lazy, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
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
import { DialogoSalida } from "./DialogoSalida";
import { LimiteDeError } from "./LimiteDeError";
import { MenuCuenta } from "./MenuCuenta";
import { moduloAlEntrar, moduloDeRuta, navegacion } from "./navegacion";
import { PanelCarpetaProyecto, nombreDeCarpeta } from "./PanelCarpetaProyecto";
import { olvidarImportaciones } from "../paginas/hoja/useImportacion";
import { guardarPreferencias } from "./preferencias";
import { terminarRecorrido, useColumnaOculta, useRecorrido } from "./recorrido";
import { cancelarSalida } from "./salida";
import {
  ID_BOTON_SILICE,
  ID_SIDEBAR,
  abrirSidebar,
  alternarSidebar,
  cerrarSidebar,
  esEscParaElSidebar,
  fijarSidebar,
  iniciarSidebar,
  useSidebar,
} from "./sidebar";
import { SidebarModulos } from "./SidebarModulos";
import { olvidarFormularios } from "./sucio";
import { useFijadoPosible } from "./useFijadoPosible";
import { MODULOS, PAGINAS, fueraDeModulos, inicioDe, modulosVisibles, rutaDe, visible } from "./rutas";
import type { ModuloId, PaginaDef } from "./rutas";
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
  paginas,
}: {
  pagina: PaginaDef;
  acciones: readonly string[];
  modoEntrega: boolean;
  paginas: readonly PaginaDef[];
}) {
  if (!visible(pagina, acciones, modoEntrega, paginas)) {
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

// Marco de la interfaz: barra superior («Sílice», el modulo abierto y sus areas por rol y modo entrega, carpeta y
// proyecto, recorrido, letra y cuenta), el sidebar de modulos, la columna del recorrido guiado, la pagina de la ruta y
// la confirmacion al salir con trabajo sin guardar.
export function Shell({ sesion, alSalir: alSalirDeApp, alExpirar: alExpirarDeApp, paginas = PAGINAS, almacen, crearHoja }: Props) {
  const ubicacion = useLocation();
  const [casos, setCasos] = useState<CasosRespuesta | null>(null);
  const [cambiandoCaso, setCambiandoCaso] = useState(false);
  const [proyectos, setProyectos] = useState<ProyectoRespuesta[] | null>(null);
  const [proyecto, setProyecto] = useState<string | null>(null);
  const [recarga, setRecarga] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  // Cambia con el caso: las paginas se vuelven a montar y piden sus datos de nuevo.
  const [generacion, setGeneracion] = useState(0);

  // Un recorrido en curso no sobrevive a la sesion: al salir o vencer se cierra (vive fuera del arbol de React). Lo mismo
  // la pregunta de salida abierta y los formularios sucios (lo que no se guardo se pierde con la sesion).
  const alSalir = useCallback(() => {
    terminarRecorrido();
    olvidarImportaciones();
    cancelarSalida();
    olvidarFormularios();
    alSalirDeApp();
  }, [alSalirDeApp]);
  const alExpirar = useCallback(() => {
    terminarRecorrido();
    olvidarImportaciones();
    cancelarSalida();
    olvidarFormularios();
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

  // Sidebar de modulos (MOD-2): oculto al entrar, con el fijado que recuerda la cuenta. Antes de pintar (sin parpadeo del
  // fijado); al desmontarse (salir de la sesion) vuelve a oculto y se olvida lo pendiente.
  const fijadoDeLaCuenta = sesion.preferencias?.sidebar_fijado ?? false;
  useLayoutEffect(() => {
    iniciarSidebar(fijadoDeLaCuenta);
  }, [fijadoDeLaCuenta]);
  useEffect(
    () => () => {
      iniciarSidebar(false);
      cancelarSalida();
      olvidarFormularios();
    },
    [],
  );
  const { abierto: sidebarAbierto, fijado: sidebarFijado } = useSidebar();
  const fijadoPosible = useFijadoPosible();
  // Fijado solo con ancho para ello; si no, se comporta como oculto (y al abrirse va en capa).
  const fijadoVisible = sidebarFijado && fijadoPosible;
  const enCapa = sidebarAbierto && !fijadoVisible;
  // Abierto en capa con fijado sin ancho y la ventana se ensancha: pasa a franja; la capa se da por cerrada para que al
  // estrecharse no reaparezca sola ni robe el foco.
  useEffect(() => {
    if (fijadoVisible && sidebarAbierto) cerrarSidebar();
  }, [fijadoVisible, sidebarAbierto]);

  const enfocarSilice = useCallback(() => document.getElementById(ID_BOTON_SILICE)?.focus(), []);
  const cerrarModulos = useCallback(() => {
    cerrarSidebar();
    enfocarSilice();
  }, [enfocarSilice]);

  // Esc (choque 9 del plan): un solo oyente en el documento, en la fase de burbuja, asi lo que tiene su propio Esc (un
  // panel de area, la cuenta, la carpeta, un dialogo) lo atiende antes y detiene la propagacion. En capa, Esc cierra el
  // sidebar y el foco vuelve a «Sílice» (dentro del sidebar lo atiende el propio sidebar); con todo cerrado lo abre si
  // el Esc no es de nadie (esEscParaElSidebar); fijado y a la vista no hace nada (decision 4 de Eugenio).
  useEffect(() => {
    const alTeclear = (e: KeyboardEvent) => {
      if (e.key !== "Escape" || e.defaultPrevented) return;
      if (enCapa) {
        // Otro dialogo modal encima (p. ej. «Cambios sin guardar») se queda con su Esc.
        const otroModal = Array.from(document.querySelectorAll('[aria-modal="true"]')).some((m) => m.id !== ID_SIDEBAR);
        if (!otroModal) cerrarModulos();
        return;
      }
      if (fijadoVisible || !esEscParaElSidebar(e)) return;
      abrirSidebar();
    };
    document.addEventListener("keydown", alTeclear);
    return () => document.removeEventListener("keydown", alTeclear);
  }, [enCapa, fijadoVisible, cerrarModulos]);

  const acciones = sesion.acciones;
  const modoEntrega = sesion.modo_entrega;

  // Modulo abierto (plan de modulos, MOD-1). Sale de la pantalla; fuera de los modulos (Administracion, Acerca), en una
  // ruta sin pantalla o en una pantalla de un modulo que la cuenta no ve, queda el ultimo usado. Al entrar, el ultimo
  // es el que la cuenta recuerda (si aun lo ve) o el de su rol.
  const visibles = useMemo(() => modulosVisibles(acciones, modoEntrega, paginas), [acciones, modoEntrega, paginas]);
  const [ultimo, setUltimo] = useState<ModuloId | null>(() =>
    moduloAlEntrar(sesion.preferencias?.modulo ?? null, acciones, modoEntrega, paginas),
  );
  const deLaPantalla = moduloDeRuta(ubicacion.pathname, null, paginas);
  const modulo = deLaPantalla !== null && visibles.some((m) => m.id === deLaPantalla) ? deLaPantalla : ultimo;
  // Se ajusta durante el render, sin efecto (como el aviso de carpeta, mas abajo).
  if (modulo !== ultimo) setUltimo(modulo);

  // El modulo de la pantalla se recuerda por cuenta cuando cambia (PUT /v1/sesion/preferencias). Solo el que viene de
  // una pantalla: entrar en Acerca con el modulo de entrada no es «usar» ese modulo. Un 401 es la sesion vencida; otro
  // error no molesta a la persona (lo peor es entrar la proxima vez en otro modulo).
  const guardado = useRef<ModuloId | null>(sesion.preferencias?.modulo ?? null);
  useEffect(() => {
    if (modulo === null || modulo !== deLaPantalla || modulo === guardado.current) return;
    guardado.current = modulo;
    void guardarPreferencias({ modulo }, alExpirar);
  }, [modulo, deLaPantalla, alExpirar]);

  // «Sílice»: oculto, abre en capa (el sidebar lleva el foco al modulo actual); en capa, cierra; fijado y a la vista,
  // lleva el foco al modulo actual (no lo oculta: eso es «Ocultar», al pie del sidebar).
  const alPulsarSilice = useCallback(() => {
    if (!fijadoVisible) {
      alternarSidebar();
      return;
    }
    cerrarSidebar();
    const lado = document.getElementById(ID_SIDEBAR);
    (lado?.querySelector<HTMLElement>('.silice-sidebar__modulo[aria-current="page"]') ?? lado?.querySelector<HTMLElement>("a"))?.focus();
  }, [fijadoVisible]);

  // «Fijar» y «Ocultar»: se recuerda por cuenta. El boton que se pulso desaparece (el sidebar pasa de capa a franja, o
  // se va): el foco va a «Ocultar» o a «Sílice» cuando React ya repinto.
  const alFijar = useCallback(
    (fijo: boolean) => {
      fijarSidebar(fijo);
      void guardarPreferencias({ sidebar_fijado: fijo }, alExpirar);
      requestAnimationFrame(() => {
        if (fijo) document.querySelector<HTMLElement>(`#${ID_SIDEBAR} .silice-sidebar__fijar`)?.focus();
        else enfocarSilice();
      });
    },
    [alExpirar, enfocarSilice],
  );

  const entradas = useMemo(
    () => (modulo === null ? [] : navegacion(modulo, acciones, modoEntrega, paginas)),
    [modulo, acciones, modoEntrega, paginas],
  );
  // Administracion y Acerca de Silice, al pie del sidebar (las que la cuenta puede usar).
  const fuera = useMemo(() => fueraDeModulos(acciones, modoEntrega, paginas), [acciones, modoEntrega, paginas]);
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

  // El aviso de carpeta cambiada es de la pantalla en que se cambio: al navegar a otra se cierra (D6 del recorrido
  // funcional). Se ajusta durante el render, sin efecto.
  const [rutaDelAviso, setRutaDelAviso] = useState(ubicacion.pathname);
  if (rutaDelAviso !== ubicacion.pathname) {
    setRutaDelAviso(ubicacion.pathname);
    if (aviso) setAviso(null);
  }

  const recargarProyectos = useCallback(() => setRecarga((n) => n + 1), []);

  const aplicacion = useMemo<Aplicacion>(
    () => ({
      sesion,
      proyecto,
      nombreProyecto: proyectos?.find((p) => p.codigo === proyecto)?.nombre ?? null,
      caso: casos?.actual ?? null,
      recargarProyectos,
      alExpirar,
      modulo,
      almacenDelLibro: almacen,
      crearHojaVisor: crearHoja,
    }),
    [sesion, proyecto, proyectos, casos, recargarProyectos, alExpirar, modulo, almacen, crearHoja],
  );

  // A donde llevan «/», «/inicio» y una ruta inexistente: el inicio del ultimo modulo usado (o del de entrada); sin
  // ningun modulo visible, la primera pantalla de fuera de los modulos (Administracion o Acerca).
  const moduloDeEntrada = moduloAlEntrar(ultimo, acciones, modoEntrega, paginas);
  const destino =
    moduloDeEntrada !== null ? inicioDe(moduloDeEntrada, paginas) : fueraDeModulos(acciones, modoEntrega, paginas)[0];
  const redirigir = destino ? (
    <Navigate to={rutaDe(destino)} replace />
  ) : (
    <div className="silice-pagina-aviso">
      <EstadoVacio titulo="No hay pantallas disponibles en esta interfaz" descripcion="Su cuenta no puede usar ninguna pantalla." />
    </div>
  );

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
      <div
        className={`silice-marco${conRecorrido ? " silice-con-recorrido" : ""}${fijadoVisible ? " silice-marco--fijado" : ""}`}
        data-modulo={modulo ?? undefined}
      >
        {/* Con hash por enrutador un enlace #contenido cambiaria la ruta: se manda el foco a mano. */}
        <button type="button" className="silice-saltar cds--type-body-compact-01" onClick={() => document.getElementById("contenido")?.focus()}>
          Saltar al contenido
        </button>
        <BarraSuperior
          modulo={MODULOS.find((m) => m.id === modulo) ?? null}
          entradas={entradas}
          derecha={derecha}
          sidebar={{ abierto: enCapa, visible: enCapa || fijadoVisible, alternar: alPulsarSilice }}
        />
        <SidebarModulos
          modulos={visibles}
          actual={modulo}
          entradas={entradas}
          fuera={fuera}
          abierto={sidebarAbierto}
          fijado={sidebarFijado}
          fijadoPosible={fijadoPosible}
          alCerrar={cerrarModulos}
          alFijar={alFijar}
          nombre={sesion.nombre}
          paginas={paginas}
        />
        {/* Antes del contenido: por debajo del umbral de la letra pasa a franja bajo la barra (ColumnaRecorrido.scss). */}
        <ColumnaRecorrido paginas={paginas} acciones={acciones} modoEntrega={modoEntrega} />
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
                <Route index element={redirigir} />
                {/* El antiguo Inicio: hoy cada modulo tiene el suyo. */}
                <Route path="/inicio" element={redirigir} />
                {paginas.map((pagina) => (
                  <Route
                    key={pagina.id}
                    path={rutaDe(pagina)}
                    element={
                      <PaginaDeRuta pagina={pagina} acciones={acciones} modoEntrega={modoEntrega} paginas={paginas} />
                    }
                  />
                ))}
                <Route path="*" element={redirigir} />
              </Routes>
            </Suspense>
          </LimiteDeError>
        </main>
        <DialogoSalida paginas={paginas} />
      </div>
    </ContextoAplicacion.Provider>
  );
}
