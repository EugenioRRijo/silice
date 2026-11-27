import { InlineNotification } from "../comun/carbonEs";
import { Suspense, createElement, lazy, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent, ReactElement, ReactNode } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate, useNavigationType } from "react-router";
import { recordarObra } from "../api/carpetaYObra";
import { ErrorDeApi, pedir } from "../api/cliente";
import type { SesionRespuesta } from "../api/tipos";
import { AvisoError } from "../comun/AvisoError";
import { EsqueletoPagina } from "../comun/EsqueletoPagina";
import { useTituloDelDocumento } from "../comun/tituloDelDocumento";
import { olvidarImportaciones } from "../paginas/archivos/useImportacion";
import { Bandeja } from "../paginas/pendientes/Bandeja";
import { hojasConCambios } from "../shell/carpetas/hojasConCambios";
import { useCarpetaDeTrabajo } from "../shell/carpetas/useCarpetaDeTrabajo";
import { BotonRecorrido, ColumnaRecorrido } from "../shell/ColumnaRecorrido";
import { ContextoAplicacion } from "../shell/contexto";
import type { Aplicacion, MonedaPendiente } from "../shell/contexto";
import { DialogoSalida } from "../shell/DialogoSalida";
import { LimiteDeError } from "../shell/LimiteDeError";
import { MarcaDemostracion } from "../shell/MarcaDemostracion";
import { terminarRecorrido, useColumnaOculta, useRecorrido } from "../shell/recorrido";
import { PAGINAS, paginaPorId, rutaDe, usable } from "../shell/rutas";
import type { PaginaDef } from "../shell/rutas";
import { esClicSimple } from "../shell/navegarSeguro";
import { cancelarSalida, confirmarSalida } from "../shell/salida";
import { formulariosSucios, olvidarFormularios } from "../shell/sucio";
import type { AlmacenDelVisor } from "../visor/almacen";
import type { CrearHojaVisor } from "../visor/hojaVisor";
import { AvisoApagada, AvisoSinPermiso } from "./avisos";
import { BarraLateral } from "./BarraLateral";
import { BarraSuperior } from "./BarraSuperior";
import { Buscador } from "./Buscador";
import { EspacioDeCuenta } from "./EspacioDeCuenta";
import { EspacioDeHerramientas, RaizDelEspacio } from "./EspacioDeHerramientas";
import { EspacioDeInicio, RaizDeInicio } from "./EspacioDeInicio";
import { EspacioDeObra } from "./EspacioDeObra";
import { ESPACIOS, SECCIONES_DE_CUENTA, esEspacio, espacioDeLaPagina, rutaDeCuenta, subvistaDeLaPagina } from "./espacios";
import type { EspacioId } from "./espacios";
import { enfocarElTitulo, nombrarLaVentana } from "./focoAlTitulo";
import { almacenDeLaApi } from "../comun/notificaciones/almacenDeLaApi";
import { PanelDeNotificaciones } from "../comun/notificaciones/PanelDeNotificaciones";
import { ProveedorDeNotificaciones } from "../comun/notificaciones/ProveedorDeNotificaciones";
import { RegionDeNotificaciones } from "../comun/notificaciones/RegionDeNotificaciones";
import { BarraDeEstado } from "./BarraDeEstado";
import "./marco.scss";
import { ModeTransitionOverlay } from "./ModeTransitionOverlay";
import type { EstacionMayor } from "./ModeTransitionOverlay";
import { ofertaDe } from "./oferta";
import { carpetaDelDestino, ubicar } from "./ubicar";
import { abrirNuevaObra, cerrarNuevaObra } from "./nuevaObra";
import type { VigilanteDeObra } from "./otraPestana";
import { PATRON_DE_OBRA, RUTA_DE_INICIO, RUTA_DE_PENDIENTES, RUTA_DE_VISTA_GENERAL, SECCIONES_DE_OBRA, rutaDeObra } from "./secciones";
import type { SeccionId } from "./secciones";
import { useModulos } from "./useModulos";
import { ContextoObras, useCargaDeObras } from "./useObras";
import { ContextoPendientes, useCargaDePendientes } from "./usePendientes";
import { ContextoLayoutDelMarco, guardarBarraColapsada, leerBarraColapsada } from "./useWorkspaceLayout";

const CARPETA_CAMBIADA = "Carpeta cambiada";

export interface PropsDelMarco {
  sesion: SesionRespuesta;
  alSalir: () => void;
  // La API contestó 401 en medio del trabajo: la sesión venció.
  alExpirar: () => void;
  // Cuenta › Contraseña: cambia la propia (la sesión la da `useSesion`, que relee la ficha nueva).
  alCambiarContrasena?: (actual: string, nueva: string) => Promise<void>;
  // Solo en pruebas: el registro de pantallas, el visor de hojas y el vigilante de pestañas.
  paginas?: readonly PaginaDef[];
  // Lo abierto en «Libro de la empresa», guardado por encima de la puerta de sesión (UC-26).
  almacen?: AlmacenDelVisor;
  crearHoja?: CrearHojaVisor;
  vigilante?: VigilanteDeObra;
}

// Un elemento `lazy` por pantalla, estable entre dibujos: React no vuelve a pedir el archivo.
const elementos = new WeakMap<PaginaDef, ReactElement>();
function elementoDe(pagina: PaginaDef): ReactElement {
  let elemento = elementos.get(pagina);
  if (!elemento) {
    elemento = createElement(lazy(pagina.cargar));
    elementos.set(pagina, elemento);
  }
  return elemento;
}

interface Aviso {
  titulo: string;
  texto: string;
}

// La obra elegida en la sesión (la de la carpeta abierta), «cargando» mientras llegan las obras, o null.
type ObraDeLaSesion = { carpeta: string | null; obraId: number } | "cargando" | null;

// Marco de la interfaz (plan del rediseño del marco, Tarea 8): barra superior con la marca, la carpeta activa, el buscador y
// la persona (F6, T6), barra lateral con Pendientes, las obras y «Costos y producción», y el contenido de la ruta. Monta lo que seguía vigente del armazón anterior: el
// límite de error, «Cambios sin guardar», la marca de la demostración, los avisos, el recorrido guiado y la sesión
// vencida. Pasa de 250 líneas porque reúne el estado que comparten todas las pantallas (sesión, carpeta, obra elegida,
// moneda pendiente) con las rutas; las piezas con lógica propia viven aparte (ubicar.ts, EspacioDeObra, useObraDeLaRuta).
export function Marco({ sesion, alSalir: alSalirDeApp, alExpirar: alExpirarDeApp, alCambiarContrasena, paginas = PAGINAS, almacen, crearHoja, vigilante }: PropsDelMarco) {
  const ubicacion = useLocation();
  const navegar = useNavigate();
  const { acciones, modo_entrega: modoEntrega } = sesion;
  const puedeEditarHoja = acciones.includes("editar_hoja");
  const [proyecto, setProyecto] = useState<string | null>(() => sesion.eleccion?.proyecto ?? null);
  const [error, setError] = useState<unknown>(null);
  const [aviso, setAviso] = useState<Aviso | null>(() =>
    sesion.eleccion?.aviso ? { titulo: CARPETA_CAMBIADA, texto: sesion.eleccion.aviso } : null,
  );
  const [monedaPendiente, setMonedaPendiente] = useState<MonedaPendiente | null>(null);
  const [declarandoMoneda, setDeclarandoMoneda] = useState(false);
  // La carpeta abierta ahora (sin .db): la moneda pendiente es de SU carpeta y nunca se declara en otra.
  const carpetaAbierta = useRef<string | null>(null);
  // Cambia con la carpeta: las pantallas se vuelven a montar y piden sus datos de nuevo.
  const [generacion, setGeneracion] = useState(0);
  const [buscadorAbierto, setBuscadorAbierto] = useState(false);
  // Lo que la instalación apagó (plan vial, Tarea 19): no se ofrece ni se abre.
  const { apagados: modulosApagados, leidos: modulosLeidos, recargar: recargarModulos } = useModulos();

  // Un recorrido en curso, la pregunta de salida abierta, los formularios sucios y el diálogo «Nueva obra» no
  // sobreviven a la sesión.
  const olvidarLaSesion = useCallback(() => {
    terminarRecorrido();
    olvidarImportaciones();
    cancelarSalida();
    olvidarFormularios();
    cerrarNuevaObra();
  }, []);
  const alSalir = useCallback(() => {
    olvidarLaSesion();
    alSalirDeApp();
  }, [olvidarLaSesion, alSalirDeApp]);
  const alExpirar = useCallback(() => {
    olvidarLaSesion();
    alExpirarDeApp();
  }, [olvidarLaSesion, alExpirarDeApp]);
  useEffect(() => () => olvidarLaSesion(), [olvidarLaSesion]);
  // Las obras de todas las carpetas: las leen la barra lateral y el buscador sin volver a pedirlas.
  const obras = useCargaDeObras(acciones, alExpirar);
  const { recargar: recargarObras } = obras;
  // Los pendientes de todas las obras: los leen la bandeja y la barra lateral sin volver a pedirlos.
  const pendientes = useCargaDePendientes(acciones, alExpirar);
  const { recargar: recargarPendientes } = pendientes;

  const fallo = useCallback(
    (razon: unknown) => {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      else setError(razon);
    },
    [alExpirar],
  );

  // Una sola recarga de la lista por obra mientras la carpeta de la lista no coincide con la de la obra: si la lista vuelve
  // sin ella (no debería), no se insiste. Se reinicia al cambiar de carpeta y al coincidir, para que entrar otra vez en la
  // misma obra de otra carpeta (tras pasar por la empresa) vuelva a poner al día la lista.
  const recargadaPara = useRef<string | null>(null);

  // Al volver desde `/obra/demostracion.db/...` navegamos a `/`: si `alCambiarCarpeta` subiera `generacion` antes de
  // que React Router aplique la transición, `LimiteDeError` volvería a montar `EspacioDeObra` en esa ruta y
  // `useObraDeLaRuta` reabriría `demostracion.db` (F1).
  const saliendoDeObraDemo = useRef(false);

  // Abrir otra carpeta desde una pantalla (Cuenta › Carpetas, «Probar con datos de demostración», un envío por aprobar
  // de otra carpeta): se olvida la obra elegida, las pantallas se vuelven a montar y se avisa.
  const alCambiarCarpeta = useCallback(
    (carpeta: string) => {
      carpetaAbierta.current = carpeta;
      recargadaPara.current = null;
      setError(null);
      setMonedaPendiente(null);
      setProyecto(null);
      recargarObras();
      // Los contadores de la barra son de la carpeta abierta: se piden de nuevo (la carga de Inicio solo repite al entrar en él).
      recargarPendientes();
      if (!saliendoDeObraDemo.current) setGeneracion((g) => g + 1);
      saliendoDeObraDemo.current = false;
      setAviso({ titulo: CARPETA_CAMBIADA, texto: `Ahora trabaja con la carpeta «${carpeta}».` });
    },
    [recargarObras, recargarPendientes],
  );
  const obrasDeLaCarpeta = useMemo(
    () =>
      obras.obras
        .filter((o) => o.carpeta === obras.carpetaActual)
        .map((o) => ({ codigo: String(o.obra_id), nombre: o.obra })),
    [obras.obras, obras.carpetaActual],
  );
  const { casos, abrir: abrirCarpeta, volverALaEmpresa, recargar: recargarCasos } = useCarpetaDeTrabajo({
    puedeVerBorradores: puedeEditarHoja,
    obras: obrasDeLaCarpeta,
    alExpirar,
    alFallar: fallo,
    alCambiar: alCambiarCarpeta,
  });
  useEffect(() => {
    if (casos) carpetaAbierta.current = casos.actual.nombre.replace(/\.db$/, "");
  }, [casos]);

  const elegirObra = useCallback(
    (codigo: string | null) => {
      setProyecto(codigo);
      recordarObra(codigo).catch((e: unknown) => {
        if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      });
    },
    [alExpirar],
  );

  // Al entrar en una obra (useObraDeLaRuta ya la fijó en el servidor) queda elegida. Si estaba en otra carpeta, el marco
  // pone al día la carpeta; si es de otra carpeta o no la conoce (recién creada), también la lista de obras.
  const carpetaActual = obras.carpetaActual;
  const listaDeObras = obras.obras;
  const alEntrarEnObra = useCallback(
    (carpeta: string | null, obraId: number) => {
      setProyecto(String(obraId));
      const clave = `${carpeta ?? ""}|${obraId}`;
      const conocida = listaDeObras.some((o) => o.carpeta === carpeta && o.obra_id === obraId);
      if (carpeta === carpetaActual && conocida) recargadaPara.current = null;
      if (carpeta !== carpetaActual) recargarCasos();
      if ((carpeta !== carpetaActual || !conocida) && recargadaPara.current !== clave) {
        recargadaPara.current = clave;
        recargarObras();
      }
    },
    [carpetaActual, listaDeObras, recargarCasos, recargarObras],
  );

  const declararMoneda = useCallback(
    async (carpeta: string, moneda: string): Promise<boolean> => {
      if (carpetaAbierta.current !== carpeta) {
        setMonedaPendiente(null);
        return false;
      }
      setDeclarandoMoneda(true);
      try {
        await pedir("/v1/carpeta/moneda", { metodo: "PUT", cuerpo: { moneda } });
        if (carpetaAbierta.current === carpeta) setMonedaPendiente(null);
        return true;
      } catch (e) {
        if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
        else if (carpetaAbierta.current === carpeta) setMonedaPendiente({ carpeta, moneda, error: e });
        return false;
      } finally {
        setDeclarandoMoneda(false);
      }
    },
    [alExpirar],
  );

  // El aviso es de la pantalla en que se dio: al navegar a otra se cierra. Se ajusta durante el dibujo, sin efecto.
  // Salvo el de un cambio de carpeta que la persona pidió para ir a una herramienta (`abrirDePendiente`) o al volver
  // de una obra de demostración: ese aviso dice dónde está trabajando ahora y sobrevive a esa navegación (incluida la
  // redirección de `/` a la Vista general).
  const [rutaQueConservaElAviso, setRutaQueConservaElAviso] = useState<string | null>(null);

  // «Volver a la carpeta de la empresa» desde la marca de la demostración.
  const volver = useCallback(() => {
    const enObraDeDemo =
      carpetaDelDestino(ubicacion.pathname) === "demostracion.db" ||
      ubicacion.pathname === "/obra/demostracion.db" ||
      ubicacion.pathname.startsWith("/obra/demostracion.db/");
    saliendoDeObraDemo.current = enObraDeDemo;
    volverALaEmpresa()
      .then((cambio) => {
        saliendoDeObraDemo.current = false;
        if (!cambio) return;
        if (enObraDeDemo) {
          setRutaQueConservaElAviso(RUTA_DE_INICIO);
          navegar(RUTA_DE_INICIO);
        }
        document.getElementById("contenido")?.focus();
      })
      .catch((razon) => {
        saliendoDeObraDemo.current = false;
        fallo(razon);
      });
  }, [volverALaEmpresa, fallo, ubicacion.pathname, navegar]);

  const [rutaDelAviso, setRutaDelAviso] = useState(ubicacion.pathname);
  if (rutaDelAviso !== ubicacion.pathname) {
    setRutaDelAviso(ubicacion.pathname);
    const conservaEnInicio =
      rutaQueConservaElAviso === RUTA_DE_INICIO &&
      (ubicacion.pathname === RUTA_DE_INICIO || ubicacion.pathname === RUTA_DE_VISTA_GENERAL);
    if (aviso && !conservaEnInicio && rutaQueConservaElAviso !== ubicacion.pathname) setAviso(null);
    if (
      rutaQueConservaElAviso !== null &&
      !(rutaQueConservaElAviso === RUTA_DE_INICIO && ubicacion.pathname === RUTA_DE_INICIO)
    ) {
      setRutaQueConservaElAviso(null);
    }
  }
  // Cada vez que cambia la ruta, lo que quedó a medias de un pendiente (abrir su carpeta) ya no es lo que la persona pidió.
  const turnoDePendiente = useRef(0);
  useEffect(() => {
    turnoDePendiente.current += 1;
  }, [ubicacion.pathname]);

  // Salir de donde se está por el marco (barra lateral, buscador) sin perder trabajo (foco 5 del plan): con
  // formularios sucios se pregunta; si la obra de destino está en otra carpeta, también por los borradores de la Hoja,
  // que el cambio de carpeta olvida en el servidor. Atrás y adelante del navegador no se interceptan (diseño de módulos).
  const irSeguro = useCallback(
    async (destino: string) => {
      const carpeta = carpetaDelDestino(destino);
      const cambiaDeCarpeta = carpeta !== undefined && carpeta !== carpetaActual;
      try {
        const borradores = cambiaDeCarpeta && puedeEditarHoja ? await hojasConCambios(obrasDeLaCarpeta) : [];
        if (await confirmarSalida(cambiaDeCarpeta ? "carpeta" : "salir", borradores, null, destino)) navegar(destino);
      } catch (e) {
        fallo(e);
      }
    },
    [carpetaActual, puedeEditarHoja, obrasDeLaCarpeta, navegar, fallo],
  );
  // «Ver el catálogo» de un pendiente de otra carpeta: la herramienta trabaja con la carpeta abierta, así que se abre antes
  // la del pendiente (con la misma pregunta y aviso de siempre) y solo si se abrió se va a la herramienta.
  const abrirDePendiente = useCallback(
    async (destino: string, antes?: { carpeta: string | null }) => {
      const turno = ++turnoDePendiente.current;
      if (antes !== undefined) {
        try {
          if (!(await (antes.carpeta === null ? volverALaEmpresa() : abrirCarpeta(antes.carpeta)))) return;
        } catch (e) {
          fallo(e);
          return;
        }
        // La persona fue a otra parte mientras se abría la carpeta (o pidió otro paso): ese destino ya no es el suyo.
        if (turno !== turnoDePendiente.current) return;
        setRutaQueConservaElAviso(destino.split("?")[0] ?? destino);
      }
      await irSeguro(destino);
    },
    [volverALaEmpresa, abrirCarpeta, irSeguro, fallo],
  );
  const contenido = useRef<HTMLElement>(null);
  const alClicAntes = (e: MouseEvent<HTMLDivElement>) => {
    if (!esClicSimple(e)) return;
    // Los diálogos (MarcoDeDialogo) se pintan en un portal, pero sus clics suben por el árbol de React hasta aquí. No hace
    // falta excluirlos: `closest` recorre el DOM, donde el portal cuelga del cuerpo del documento y no de este marco, y
    // ningún diálogo lleva enlaces `a[href]`; sus botones no son enlaces. Si alguno los lleva, hay que excluir `.silice-dialogo`.
    const enlace = (e.target as Element).closest("a[href]");
    if (!enlace) return;
    const href = enlace.getAttribute("href") ?? "";
    const destino = href.startsWith("#") ? href.slice(1) : href;
    if (!destino.startsWith("/") || destino === `${ubicacion.pathname}${ubicacion.search}`) return;
    const carpeta = carpetaDelDestino(destino);
    const cambiaDeCarpeta = carpeta !== undefined && carpeta !== carpetaActual;
    // Los enlaces del contenido: las pantallas preguntan por su cuenta por lo suyo (useNavegarSeguro, confirmarSalida), pero
    // nadie pregunta por los borradores de la Hoja cuando el enlace abre una obra de otra carpeta (la Vista general): ese
    // cambio los olvida en el servidor. Se intercepta solo entonces, y `irSeguro` pregunta una sola vez por todo.
    const deLaPantalla = contenido.current?.contains(enlace) === true;
    if (deLaPantalla ? !cambiaDeCarpeta : formulariosSucios(destino).length === 0 && !cambiaDeCarpeta) return;
    e.preventDefault();
    void irSeguro(destino);
  };

  const { titulo } = ubicar(ubicacion.pathname, obras.obras, paginas);
  useFocoAlTitulo(ubicacion.pathname, ubicacion.key, !titulo);
  useTituloDelDocumento(titulo);

  // La carpeta abierta, con el título que da el servidor («Carpeta de la empresa» la de la empresa); mientras no llega, el
  // nombre de su archivo sin la extensión. Sin nada que decir (cuenta sin lectura de obras y sin lista de carpetas), null.
  const carpetaActiva = obras.tituloActual || casos?.actual.nombre.replace(/\.db$/, "") || null;
  // C11: las notificaciones de esta persona se guardan en el servidor 30 días (f7520d3b); un almacén por sesión.
  const almacenDeNotificaciones = useMemo(() => almacenDeLaApi(), []);
  const nombreProyecto = obras.obras.find((o) => o.carpeta === carpetaActual && String(o.obra_id) === proyecto)?.obra ?? null;
  const aplicacion = useMemo<Aplicacion>(
    () => ({
      sesion,
      proyecto,
      nombreProyecto,
      caso: casos?.actual ?? null,
      // `undefined` mientras no se sabe: las pantallas que dependen de un módulo encendido esperan (`useModulos`).
      modulosApagados: modulosLeidos ? modulosApagados : undefined,
      recargarModulos,
      recargarProyectos: recargarObras,
      elegirObra,
      abrirNuevaObra,
      abrirCarpeta,
      monedaPendiente,
      declararMoneda,
      declarandoMoneda,
      alExpirar,
      cambiarContrasena: alCambiarContrasena,
      almacenDelLibro: almacen,
      crearHojaVisor: crearHoja,
    }),
    [sesion, proyecto, nombreProyecto, casos, modulosApagados, modulosLeidos, recargarModulos, recargarObras, elegirObra, abrirCarpeta, monedaPendiente, declararMoneda, declarandoMoneda, alExpirar, alCambiarContrasena, almacen, crearHoja],
  );

  let obraDeLaSesion: ObraDeLaSesion = null;
  if (obras.estado === "cargando" && obras.obras.length === 0) obraDeLaSesion = "cargando";
  else {
    const o = obras.obras.find((x) => x.carpeta === carpetaActual && String(x.obra_id) === proyecto);
    if (o) obraDeLaSesion = { carpeta: o.carpeta, obraId: o.obra_id };
  }

  const pantalla = (pagina: PaginaDef | undefined): ReactNode => (
    <PantallaDeRuta pagina={pagina} acciones={acciones} modoEntrega={modoEntrega} apagados={modulosApagados} />
  );
  // Con la columna del recorrido a la vista, el contenido le cede su ancho (ColumnaRecorrido.scss).
  const recorrido = useRecorrido();
  const columnaOculta = useColumnaOculta();
  const conRecorrido = recorrido !== null && !columnaOculta;

  // Los 3 espacios de la empresa (Auditoria, Precios, Produccion). Desde el lote C4 (2026-11-26) no tienen ventana aparte: la barra
  // lateral se ve también dentro de ellos (es la que lleva de un espacio a otro y a cada obra); `enVentanaDedicada` solo sirve
  // para que la barra de arriba no repita el contexto, que ya dice el espacio.
  const primerSegmento = ubicacion.pathname.split("/")[1] ?? "";
  const espacioActivo: EspacioId | null = esEspacio(primerSegmento) ? primerSegmento : null;
  const enVentanaDedicada = espacioActivo !== null;
  const oferta = useMemo(() => ofertaDe(acciones, modoEntrega, modulosApagados), [acciones, modoEntrega, modulosApagados]);

  // Barra lateral colapsable (256px <-> 48px) con persistencia local y atajo Ctrl+B.
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(() => leerBarraColapsada());
  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      guardarBarraColapsada(next);
      return next;
    });
  }, []);

  useEffect(() => {
    function alTeclearCtrlB(e: KeyboardEvent) {
      if (!(e.ctrlKey || e.metaKey) || e.key.toLowerCase() !== "b") return;
      const destino = e.target as HTMLElement | null;
      if (
        destino instanceof HTMLInputElement ||
        destino instanceof HTMLTextAreaElement ||
        destino instanceof HTMLSelectElement ||
        destino?.isContentEditable
      ) {
        return;
      }
      e.preventDefault();
      toggleSidebar();
    }
    window.addEventListener("keydown", alTeclearCtrlB);
    return () => window.removeEventListener("keydown", alTeclearCtrlB);
  }, [toggleSidebar]);

  // Transicion rapida al cambiar entre estaciones mayores (Obras <-> Auditoria / Precios / Produccion).
  const estacionActual: EstacionMayor = espacioActivo ?? "obras";
  const [estacionPrevia, setEstacionPrevia] = useState<EstacionMayor>(estacionActual);
  const [transicion, setTransicion] = useState<EstacionMayor | null>(null);
  if (estacionPrevia !== estacionActual) {
    setEstacionPrevia(estacionActual);
    setTransicion(estacionActual);
  }
  const alTerminarTransicion = useCallback(() => setTransicion(null), []);

  // Breadcrumb contextual limpio en la barra superior (sustituye el chip tecnico de carpeta).
  const obraActualRuta = obraDeLaRuta(ubicacion.pathname);
  const migaContextual = useMemo(() => {
    if (enVentanaDedicada) return null;
    if (ubicacion.pathname === RUTA_DE_PENDIENTES) return "Inicio / Pendientes";
    if (ubicacion.pathname === RUTA_DE_VISTA_GENERAL || ubicacion.pathname === RUTA_DE_INICIO) return "Inicio / Vista general";
    if (ubicacion.pathname === "/cuenta" || ubicacion.pathname.startsWith("/cuenta/")) return "Perfil y configuración";
    if (obraActualRuta !== null) {
      const nombreObra = obras.obras.find(
        (o) => o.carpeta === obraActualRuta.carpeta && o.obra_id === obraActualRuta.obraId,
      )?.obra;
      return nombreObra ? `Obras / ${nombreObra}` : "Obras";
    }
    return null;
  }, [enVentanaDedicada, ubicacion.pathname, obraActualRuta, obras.obras]);

  const layoutDelMarco = useMemo(
    () => ({ sidebarCollapsed, toggleSidebar }),
    [sidebarCollapsed, toggleSidebar],
  );
  const contenidoExpandido = sidebarCollapsed;

  return (
    <ContextoAplicacion.Provider value={aplicacion}>
      <ContextoPendientes.Provider value={pendientes}>
        <ContextoObras.Provider value={obras}>
          <ContextoLayoutDelMarco.Provider value={layoutDelMarco}>
            <ProveedorDeNotificaciones almacen={almacenDeNotificaciones}>
            <div className={`silice-marco${conRecorrido ? " silice-con-recorrido" : ""}`} onClickCapture={alClicAntes}>
              {/* Con hash por enrutador un enlace #contenido cambiaría la ruta: se manda el foco a mano. */}
              <button type="button" className="silice-saltar cds--type-body-compact-01" onClick={() => contenido.current?.focus()}>
                Saltar al contenido
              </button>
              <BarraSuperior
                alAbrirBuscador={() => setBuscadorAbierto(true)}
                nombre={sesion.nombre}
                carpeta={carpetaActiva}
                migaContextual={migaContextual}
                enVentanaDedicada={enVentanaDedicada}
                espacioActivo={espacioActivo}
                espacios={oferta.espacios}
                extra={
                  <>
                    <MarcaDemostracion activa={casos?.es_demostracion === true} puedeVolver={acciones.includes("abrir_carpeta")} alVolver={volver} />
                    <BotonRecorrido />
                  </>
                }
              />
              <div className="silice-marco__cuerpo">
                <BarraLateral obraAbierta={obraActualRuta} />
                <main
                  id="contenido"
                  ref={contenido}
                  className={`silice-contenido${contenidoExpandido ? " silice-contenido--expandido" : ""}`}
                  tabIndex={-1}
                >
                {(error !== null || aviso) && (
                  <div className="silice-avisos">
                    <AvisoError error={error} titulo="No se pudo completar la acción" alCerrar={() => setError(null)} />
                    {aviso && (
                      <InlineNotification
                        kind="info"
                        title={aviso.titulo}
                        subtitle={aviso.texto}
                        lowContrast
                        onClose={() => {
                          setAviso(null);
                          return false;
                        }}
                      />
                    )}
                  </div>
                )}
                <LimiteDeError key={`${claveDelContenido(ubicacion.pathname)}|${generacion}`} reinicio={ubicacion.pathname}>
                  <Suspense fallback={<EsqueletoPagina />}>
                    <Routes>
                      {/* Inicio (F6, T8): la app abre en la Vista general. `/pendientes`, el nombre de antes de F6, se retiró en F8. */}
                      <Route index element={<ALaVistaGeneral />} />
                      <Route path="/inicio" element={<RaizDeInicio />} />
                      <Route
                        path="/inicio/:vista"
                        element={
                          <EspacioDeInicio
                            general={pantalla(paginaPorId("inicio", paginas))}
                            pendientes={<Bandeja alAbrir={abrirDePendiente} obras={obras.obras} carpetaActual={obras.estado === "lista" ? obras.carpetaActual : undefined} />}
                          />
                        }
                      />
                      <Route
                        path={PATRON_DE_OBRA}
                        element={
                          <EspacioDeObra
                            obras={obras.obras}
                            casos={casos}
                            alEntrar={alEntrarEnObra}
                            pantalla={(id) => pantalla(paginaPorId(id, paginas))}
                            vigilante={vigilante}
                          />
                        }
                      />
                      {/* La Cuenta (F6, T6): `/cuenta` abre «Configuración». */}
                      <Route path="/cuenta" element={<RaizDeLaCuenta />} />
                      <Route
                        path="/cuenta/:seccion"
                        element={<EspacioDeCuenta sesion={sesion} pantalla={(id) => pantalla(paginaPorId(id, paginas))} alSalir={alSalir} />}
                      />
                      {/* Producción, Auditoría y Precios (F6, T4): `/<espacio>` abre su primera herramienta usable (contrato 1). */}
                      {ESPACIOS_DEL_MARCO.flatMap((espacio) => [
                        <Route
                          key={`${espacio}-raiz`}
                          path={`/${espacio}`}
                          element={<RaizDelEspacio espacio={espacio} acciones={acciones} modoEntrega={modoEntrega} apagados={modulosApagados} />}
                        />,
                        <Route
                          key={espacio}
                          path={`/${espacio}/:herramienta`}
                          element={
                            <EspacioDeHerramientas
                              espacio={espacio}
                              pantalla={(id) => pantalla(paginaPorId(id, paginas))}
                              acciones={acciones}
                              modoEntrega={modoEntrega}
                              apagados={modulosApagados}
                            />
                          }
                        />,
                      ])}
                      {/* Las direcciones cortas (`/hoja`, `/reajuste`…): la ruta canónica de una pantalla sin obra (`rutaCanonica`). */}
                      {paginas
                        .filter((p) => tieneDireccionCorta(p.id))
                        .map((p) => (
                          <Route
                            key={p.id}
                            path={rutaDe(p)}
                            element={<DireccionCorta pagina={p} obraDeLaSesion={obraDeLaSesion} pantalla={pantalla} />}
                          />
                        ))}
                      <Route path="*" element={<ALaVistaGeneral />} />
                    </Routes>
                  </Suspense>
                </LimiteDeError>
              </main>
            </div>
              {/* C11: barra de estado con la campanita, la pila de notificaciones nuevas y el panel a la derecha. */}
              <BarraDeEstado carpeta={carpetaActiva} />
              <RegionDeNotificaciones />
              <PanelDeNotificaciones />
              <ColumnaRecorrido paginas={paginas} acciones={acciones} modoEntrega={modoEntrega} />
              <Buscador abierto={buscadorAbierto} alCerrar={() => setBuscadorAbierto(false)} alElegir={(ruta) => void irSeguro(ruta)} />
              {/* Después de los diálogos: «Cambios sin guardar» puede abrirse encima de «Nueva obra». */}
              <DialogoSalida paginas={paginas} />
              <ModeTransitionOverlay destino={transicion} alTerminar={alTerminarTransicion} />
            </div>
            </ProveedorDeNotificaciones>
          </ContextoLayoutDelMarco.Provider>
        </ContextoObras.Provider>
      </ContextoPendientes.Provider>
    </ContextoAplicacion.Provider>
  );
}

// La pantalla con su permiso: la que la cuenta no puede usar dice por qué (la API también la rechazaría).
function PantallaDeRuta({ pagina, acciones, modoEntrega, apagados }: { pagina: PaginaDef | undefined; acciones: readonly string[]; modoEntrega: boolean; apagados: readonly string[] }) {
  if (!pagina) return <APendientes />;
  // Una pantalla de una especialidad apagada lo dice (a quien sí podría usarla); las demás, «Sin permiso».
  if (!usable(pagina, acciones, modoEntrega, apagados) && usable(pagina, acciones, modoEntrega)) return <AvisoApagada />;
  if (!usable(pagina, acciones, modoEntrega)) return <AvisoSinPermiso />;
  return elementoDe(pagina);
}

const ESPACIOS_DEL_MARCO = Object.keys(ESPACIOS) as EspacioId[];

// Las redirecciones al inicio conservan la consulta (contrato de rutas §1), como las demás de este archivo.
function ALaVistaGeneral() {
  const { search } = useLocation();
  return <Navigate to={`${RUTA_DE_VISTA_GENERAL}${search}`} replace />;
}

// Lleva a la bandeja en Inicio: lo que se monta cuando una pantalla no está en el registro.
function APendientes() {
  const { search } = useLocation();
  return <Navigate to={`${RUTA_DE_PENDIENTES}${search}`} replace />;
}

// `#/cuenta` abre la primera sección, «Configuración», que es de toda cuenta; la consulta se conserva.
function RaizDeLaCuenta() {
  const { search } = useLocation();
  return <Navigate to={`${rutaDeCuenta("preferencias")}${search}`} replace />;
}

// La sección o la subvista de la obra donde vive una pantalla, o undefined si no es de la obra.
function destinoEnLaObra(paginaId: string): { id: SeccionId; subvista: string | undefined } | undefined {
  const seccion = SECCIONES_DE_OBRA.find((s) => s.pagina === paginaId);
  if (seccion) return { id: seccion.id, subvista: undefined };
  const deSubvista = subvistaDeLaPagina(paginaId);
  return deSubvista ? { id: deSubvista.seccion, subvista: deSubvista.subvista.id } : undefined;
}

// Si la pantalla tiene dirección corta (`#/<id>`): la tienen las de la obra y las que no viven en ningún espacio, en la
// Cuenta ni en Inicio, como dice `rutaCanonica` (hoy ninguna del registro; sí las de las pruebas). Las de Producción,
// Auditoría, Precios y la Cuenta la perdieron en F8 (`/produccion` y `/auditoria` son la raíz de su espacio).
function tieneDireccionCorta(paginaId: string): boolean {
  if (paginaId === "inicio" || esEspacio(paginaId)) return false;
  return espacioDeLaPagina(paginaId) === undefined && !SECCIONES_DE_CUENTA.some((c) => c.pagina === paginaId);
}

// La dirección corta de una pantalla (contrato 2.4): es su ruta canónica sin obra (`rutaCanonica`), la que usan el buscador
// y los recorridos guiados. La de una sección o una subvista de la obra (`#/hoja`, `#/tablero`, `#/reajuste`…) lleva a esa
// sección o subvista de la obra elegida en la sesión (o a Pendientes si no hay ninguna, salvo que traiga una consulta, como
// `#/aprobar?envio=12`: entonces se abre donde estaba, para no perder lo que pide); la consulta se conserva siempre que se
// redirige. La de una pantalla que no es de la obra la abre ahí mismo. Las demás direcciones de antes de F6 (Pendientes,
// las herramientas de los espacios, Administración, Acerca de y `#/empresa/…`) se retiraron en F8 (contrato 2.4, enmienda
// 2026-11-06): como toda dirección que no existe, llevan a la Vista general.
function DireccionCorta({ pagina, obraDeLaSesion, pantalla }: { pagina: PaginaDef; obraDeLaSesion: ObraDeLaSesion; pantalla: (p: PaginaDef | undefined) => ReactNode }) {
  const { search } = useLocation();
  const destino = destinoEnLaObra(pagina.id);
  if (!destino) return pantalla(pagina);
  if (obraDeLaSesion === "cargando") return <EsqueletoPagina />;
  if (obraDeLaSesion) {
    return <Navigate to={`${rutaDeObra(obraDeLaSesion.carpeta, obraDeLaSesion.obraId, destino.id, destino.subvista)}${search}`} replace />;
  }
  return search ? pantalla(pagina) : <Navigate to={RUTA_DE_PENDIENTES} replace />;
}

// Lo que vuelve a montar el contenido al navegar: cada pantalla, salvo las secciones de una misma obra, que comparten el
// espacio de la obra (su ficha, la obra fijada en la sesión y el borrador de la Hoja, Tarea 3 del plan F4). Dentro de la
// obra, EspacioDeObra reinicia su propio límite de error con cada sección.
function claveDelContenido(pathname: string): string {
  // Lo mismo en un espacio de herramientas o en la Cuenta: la cabecera y la barra no se vuelven a montar al cambiar de
  // herramienta o de sección.
  const [, primero, segundo, ...resto] = pathname.split("/");
  if (primero !== undefined && esEspacio(primero) && segundo !== undefined && resto.length === 0) return `espacio|${primero}`;
  if (primero === "cuenta" && segundo !== undefined && resto.length === 0) return "cuenta";
  // Inicio (F6, T8): lo mismo entre la Vista general y Pendientes.
  if (primero === "inicio" && segundo !== undefined && resto.length === 0) return "espacio|inicio";
  const obra = obraDeLaRuta(pathname);
  return obra === null ? pathname : `obra|${obra.carpeta ?? ""}|${obra.obraId}`;
}

// La obra de la ruta, para marcarla en la barra lateral.
function obraDeLaRuta(pathname: string): { carpeta: string | null; obraId: number } | null {
  const carpeta = carpetaDelDestino(pathname);
  if (carpeta === undefined) return null;
  return { carpeta, obraId: Number(pathname.split("/")[3]) };
}

// Al cambiar de espacio (la clave del contenido: de la Vista general a una obra, de una obra a otra, a la Cuenta o a un
// espacio de herramientas), el foco pasa al h1 de la nueva aunque lo tenga el enlace pulsado: el lector de pantalla la
// anuncia. Dentro del mismo espacio (otra sección de la obra, otra subvista u otra herramienta) el foco se queda en el
// enlace de la barra, y solo va al h1 si se perdió (decisión de F6, T5). La primera carga y sus redirecciones (`replace`)
// no lo fuerzan (focoAlTitulo.ts espera el h1, que se carga a demanda); pero si la redirección sigue a un cambio de espacio
// (la marca «Sílice» va a «/», que redirige a la Vista general) el cambio se completa: `forzarPendiente` lo recuerda hasta
// que el foco llega al h1. El título de la ventana lo da `ubicar`; el h1 solo la nombra si el marco no sabe nombrar la ruta.
function useFocoAlTitulo(pathname: string, clave: string, sinTitulo: boolean) {
  const rutaPrevia = useRef(pathname);
  const clavePrevia = useRef(clave);
  const espacio = claveDelContenido(pathname);
  const espacioPrevio = useRef(espacio);
  const forzarPendiente = useRef(false);
  const sinTituloAhora = useRef(sinTitulo);
  const tipo = useNavigationType();
  // Antes del efecto de abajo (se ejecutan en orden): el foco lee lo último que dijo `ubicar`.
  useEffect(() => {
    sinTituloAhora.current = sinTitulo;
  }, [sinTitulo]);
  useEffect(() => {
    const mismaRuta = rutaPrevia.current === pathname;
    if (mismaRuta && clavePrevia.current === clave) return;
    rutaPrevia.current = pathname;
    clavePrevia.current = clave;
    const cambiaDeEspacio = espacioPrevio.current !== espacio;
    espacioPrevio.current = espacio;
    const redirige = !mismaRuta && tipo === "REPLACE";
    if (!redirige) forzarPendiente.current = cambiaDeEspacio;
    else if (!forzarPendiente.current) return;
    return enfocarElTitulo({
      forzar: forzarPendiente.current,
      alEnfocar: (h1) => {
        forzarPendiente.current = false;
        if (sinTituloAhora.current) nombrarLaVentana(h1.textContent?.trim() ?? "");
      },
    });
  }, [pathname, clave, tipo, espacio]);
}
