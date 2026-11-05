import { InlineNotification } from "../comun/carbonEs";
import { Suspense, createElement, lazy, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent, ReactElement, ReactNode } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate, useNavigationType, useParams } from "react-router";
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
import { EspacioDeObra } from "./EspacioDeObra";
import { ESPACIOS, SECCIONES_DE_CUENTA, esEspacio, espacioDeLaPagina, rutaDeCuenta, rutaDeHerramienta, subvistaDeLaPagina } from "./espacios";
import type { EspacioId } from "./espacios";
import { enfocarElTitulo } from "./focoAlTitulo";
import "./marco.scss";
import { carpetaDelDestino, ubicar } from "./ubicar";
import { abrirNuevaObra, cerrarNuevaObra } from "./nuevaObra";
import type { VigilanteDeObra } from "./otraPestana";
import { PATRON_DE_OBRA, RUTA_DE_PENDIENTES, SECCIONES_DE_OBRA, rutaDeObra } from "./secciones";
import { useModulos } from "./useModulos";
import { useObras } from "./useObras";
import { ContextoPendientes, useCargaDePendientes } from "./usePendientes";

const CARPETA_CAMBIADA = "Carpeta cambiada";

export interface PropsDelMarco {
  sesion: SesionRespuesta;
  alSalir: () => void;
  // La API contestó 401 en medio del trabajo: la sesión venció.
  alExpirar: () => void;
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
export function Marco({ sesion, alSalir: alSalirDeApp, alExpirar: alExpirarDeApp, paginas = PAGINAS, almacen, crearHoja, vigilante }: PropsDelMarco) {
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
  const obras = useObras(acciones);
  const { recargar: recargarObras } = obras;
  // Lo que la instalación apagó (plan vial, Tarea 19): no se ofrece ni se abre.
  const { apagados: modulosApagados, recargar: recargarModulos } = useModulos();

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
  // Los pendientes de todas las obras: los leen la bandeja y la barra lateral sin volver a pedirlos.
  const pendientes = useCargaDePendientes(acciones, alExpirar);

  const fallo = useCallback(
    (razon: unknown) => {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      else setError(razon);
    },
    [alExpirar],
  );

  // Abrir otra carpeta desde una pantalla (Cuenta › Carpetas, «Probar con datos de demostración», un envío por aprobar
  // de otra carpeta): se olvida la obra elegida, las pantallas se vuelven a montar y se avisa.
  const alCambiarCarpeta = useCallback(
    (carpeta: string) => {
      carpetaAbierta.current = carpeta;
      setError(null);
      setMonedaPendiente(null);
      setProyecto(null);
      recargarObras();
      setGeneracion((g) => g + 1);
      setAviso({ titulo: CARPETA_CAMBIADA, texto: `Ahora trabaja con la carpeta «${carpeta}».` });
    },
    [recargarObras],
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
  // Una sola recarga por obra: si la lista vuelve sin ella (no debería), no se insiste.
  const recargadaPara = useRef<string | null>(null);
  const alEntrarEnObra = useCallback(
    (carpeta: string | null, obraId: number) => {
      setProyecto(String(obraId));
      const clave = `${carpeta ?? ""}|${obraId}`;
      const conocida = listaDeObras.some((o) => o.carpeta === carpeta && o.obra_id === obraId);
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

  // «Volver a la carpeta de la empresa» desde la marca de la demostración.
  const volver = useCallback(() => {
    volverALaEmpresa()
      .then((cambio) => {
        if (cambio) document.getElementById("contenido")?.focus();
      })
      .catch(fallo);
  }, [volverALaEmpresa, fallo]);

  // El aviso es de la pantalla en que se dio: al navegar a otra se cierra. Se ajusta durante el dibujo, sin efecto.
  const [rutaDelAviso, setRutaDelAviso] = useState(ubicacion.pathname);
  if (rutaDelAviso !== ubicacion.pathname) {
    setRutaDelAviso(ubicacion.pathname);
    if (aviso) setAviso(null);
  }

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
  const contenido = useRef<HTMLElement>(null);
  const alClicAntes = (e: MouseEvent<HTMLDivElement>) => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    // Los diálogos (MarcoDeDialogo) se pintan en un portal, pero sus clics suben por el árbol de React hasta aquí. No hace
    // falta excluirlos: `closest` recorre el DOM, donde el portal cuelga del cuerpo del documento y no de este marco, y
    // ningún diálogo lleva enlaces `a[href]`; sus botones no son enlaces. Si alguno los lleva, hay que excluir `.silice-dialogo`.
    const enlace = (e.target as Element).closest("a[href]");
    // Las pantallas preguntan por su cuenta (useNavegarSeguro, confirmarSalida).
    if (!enlace || contenido.current?.contains(enlace)) return;
    const href = enlace.getAttribute("href") ?? "";
    const destino = href.startsWith("#") ? href.slice(1) : href;
    if (!destino.startsWith("/") || destino === `${ubicacion.pathname}${ubicacion.search}`) return;
    const carpeta = carpetaDelDestino(destino);
    if (formulariosSucios(destino).length === 0 && (carpeta === undefined || carpeta === carpetaActual)) return;
    e.preventDefault();
    void irSeguro(destino);
  };

  useFocoAlTitulo(ubicacion.pathname, ubicacion.key);
  const { titulo } = ubicar(ubicacion.pathname, obras.obras, paginas);
  useTituloDelDocumento(titulo);

  // La carpeta abierta, con el título que da el servidor («Carpeta de la empresa» la de la empresa); mientras no llega, el
  // nombre de su archivo sin la extensión. Sin nada que decir (cuenta sin lectura de obras y sin lista de carpetas), null.
  const carpetaActiva = obras.tituloActual || casos?.actual.nombre.replace(/\.db$/, "") || null;
  const nombreProyecto = obras.obras.find((o) => o.carpeta === carpetaActual && String(o.obra_id) === proyecto)?.obra ?? null;
  const aplicacion = useMemo<Aplicacion>(
    () => ({
      sesion,
      proyecto,
      nombreProyecto,
      caso: casos?.actual ?? null,
      modulosApagados,
      recargarModulos,
      recargarProyectos: recargarObras,
      elegirObra,
      abrirNuevaObra,
      abrirCarpeta,
      monedaPendiente,
      declararMoneda,
      declarandoMoneda,
      alExpirar,
      almacenDelLibro: almacen,
      crearHojaVisor: crearHoja,
    }),
    [sesion, proyecto, nombreProyecto, casos, modulosApagados, recargarModulos, recargarObras, elegirObra, abrirCarpeta, monedaPendiente, declararMoneda, declarandoMoneda, alExpirar, almacen, crearHoja],
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

  return (
    <ContextoAplicacion.Provider value={aplicacion}>
      <ContextoPendientes.Provider value={pendientes}>
        <div className={`silice-marco${conRecorrido ? " silice-con-recorrido" : ""}`} onClickCapture={alClicAntes}>
          {/* Con hash por enrutador un enlace #contenido cambiaría la ruta: se manda el foco a mano. */}
          <button type="button" className="silice-saltar cds--type-body-compact-01" onClick={() => contenido.current?.focus()}>
            Saltar al contenido
          </button>
          <BarraSuperior
            alAbrirBuscador={() => setBuscadorAbierto(true)}
            nombre={sesion.nombre}
            carpeta={carpetaActiva}
            extra={
              <>
                <MarcaDemostracion activa={casos?.es_demostracion === true} puedeVolver={acciones.includes("cambiar_caso")} alVolver={volver} />
                <BotonRecorrido />
              </>
            }
          />
          <div className="silice-marco__cuerpo">
            <BarraLateral obraAbierta={obraDeLaRuta(ubicacion.pathname)} />
            <main id="contenido" ref={contenido} className="silice-contenido" tabIndex={-1}>
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
                    <Route index element={<Navigate to={RUTA_DE_PENDIENTES} replace />} />
                    <Route path={RUTA_DE_PENDIENTES} element={<Bandeja alAbrir={(ruta) => void irSeguro(ruta)} obras={obras.obras} />} />
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
                    {/* La Cuenta (F6, T6): `/cuenta` abre «Pantalla y tamaño de letra»; las direcciones viejas de Empresa llevan allí. */}
                    <Route path="/cuenta" element={<RaizDeLaCuenta />} />
                    <Route
                      path="/cuenta/:seccion"
                      element={<EspacioDeCuenta sesion={sesion} pantalla={(id) => pantalla(paginaPorId(id, paginas))} alSalir={alSalir} />}
                    />
                    <Route path="/empresa/:entrada" element={<EntradaDeEmpresa />} />
                    {/* Producción, Auditoría y Precios (F6, T4): `/<espacio>` abre su primera herramienta usable. Van antes de
                        las direcciones viejas porque `/auditoria` y `/produccion` también eran el id de una pantalla. */}
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
                    {paginas
                      .filter((p) => !esEspacio(p.id))
                      .map((p) => (
                        <Route
                          key={p.id}
                          path={rutaDe(p)}
                          element={<RutaVieja pagina={p} obraDeLaSesion={obraDeLaSesion} pantalla={pantalla} />}
                        />
                      ))}
                    <Route path="*" element={<Navigate to={RUTA_DE_PENDIENTES} replace />} />
                  </Routes>
                </Suspense>
              </LimiteDeError>
            </main>
          </div>
          <ColumnaRecorrido paginas={paginas} acciones={acciones} modoEntrega={modoEntrega} />
          <Buscador abierto={buscadorAbierto} alCerrar={() => setBuscadorAbierto(false)} alElegir={(ruta) => void irSeguro(ruta)} />
          {/* Después de los diálogos: «Cambios sin guardar» puede abrirse encima de «Nueva obra». */}
          <DialogoSalida paginas={paginas} />
        </div>
      </ContextoPendientes.Provider>
    </ContextoAplicacion.Provider>
  );
}

// La pantalla con su permiso: la que la cuenta no puede usar dice por qué (la API también la rechazaría).
function PantallaDeRuta({ pagina, acciones, modoEntrega, apagados }: { pagina: PaginaDef | undefined; acciones: readonly string[]; modoEntrega: boolean; apagados: readonly string[] }) {
  if (!pagina) return <Navigate to={RUTA_DE_PENDIENTES} replace />;
  // Una pantalla de una especialidad apagada lo dice (a quien sí podría usarla); las demás, «Sin permiso».
  if (!usable(pagina, acciones, modoEntrega, apagados) && usable(pagina, acciones, modoEntrega)) return <AvisoApagada />;
  if (!usable(pagina, acciones, modoEntrega)) return <AvisoSinPermiso />;
  return elementoDe(pagina);
}

const ESPACIOS_DEL_MARCO = Object.keys(ESPACIOS) as EspacioId[];

// Las entradas de Empresa que F6 sacó de la barra lateral y movió de sitio (contrato de rutas 2.4): `#/empresa/precios` abría el
// Catálogo, `#/empresa/auditoria` la subida del Excel y `#/empresa/produccion` las existencias (T4); `#/empresa/personas`
// abría Administración y `#/empresa/ayuda` «Acerca de» (T6, ahora en la Cuenta). Ya no hay pantalla en `#/empresa/...`.
const ENTRADAS_MOVIDAS: Readonly<Record<string, string>> = {
  precios: rutaDeHerramienta("precios", "catalogo"),
  auditoria: rutaDeHerramienta("auditoria", "subir"),
  produccion: rutaDeHerramienta("produccion", "existencias"),
  personas: rutaDeCuenta("cuentas"),
  ayuda: rutaDeCuenta("ayuda"),
};

// `#/empresa/<entrada>`: va a donde vive hoy la pantalla, con replace y conservando la consulta; una entrada que no existe
// lleva a Pendientes.
function EntradaDeEmpresa() {
  const { entrada: id } = useParams();
  const { search } = useLocation();
  const destino = id !== undefined && Object.hasOwn(ENTRADAS_MOVIDAS, id) ? ENTRADAS_MOVIDAS[id] : undefined;
  return <Navigate to={destino === undefined ? RUTA_DE_PENDIENTES : `${destino}${search}`} replace />;
}

// `#/cuenta` abre la primera sección, «Pantalla y tamaño de letra», que es de toda cuenta; la consulta se conserva.
function RaizDeLaCuenta() {
  const { search } = useLocation();
  return <Navigate to={`${rutaDeCuenta("preferencias")}${search}`} replace />;
}

// Las direcciones de antes (`#/<pantalla>`): la de una herramienta de Producción, Auditoría o Precios va a
// `#/<espacio>/<segmento>`; Administración y Acerca de van a su sección de la Cuenta; la de una sección o de una subvista
// de la obra (`/tablero`, `/componer`, `/reajuste`…, contrato 2.4), a esa sección o subvista de la obra elegida en la sesión
// (o a Pendientes si no hay ninguna, salvo que traiga una consulta, como `#/aprobar?envio=12`: entonces se abre donde
// estaba, para no perder lo que pide). La consulta se conserva siempre que se redirige.
function RutaVieja({ pagina, obraDeLaSesion, pantalla }: { pagina: PaginaDef; obraDeLaSesion: ObraDeLaSesion; pantalla: (p: PaginaDef | undefined) => ReactNode }) {
  const { search } = useLocation();
  const deEspacio = espacioDeLaPagina(pagina.id);
  if (deEspacio) return <Navigate to={`${rutaDeHerramienta(deEspacio.espacio, deEspacio.herramienta.id)}${search}`} replace />;
  const deCuenta = SECCIONES_DE_CUENTA.find((c) => c.pagina === pagina.id);
  if (deCuenta) return <Navigate to={`${rutaDeCuenta(deCuenta.id)}${search}`} replace />;
  const seccion = SECCIONES_DE_OBRA.find((s) => s.pagina === pagina.id);
  const deSubvista = subvistaDeLaPagina(pagina.id);
  const destino = seccion ? { id: seccion.id, subvista: undefined } : deSubvista ? { id: deSubvista.seccion, subvista: deSubvista.subvista.id } : undefined;
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
  const obra = obraDeLaRuta(pathname);
  return obra === null ? pathname : `obra|${obra.carpeta ?? ""}|${obra.obraId}`;
}

// La obra de la ruta, para marcarla en la barra lateral.
function obraDeLaRuta(pathname: string): { carpeta: string | null; obraId: number } | null {
  const carpeta = carpetaDelDestino(pathname);
  if (carpeta === undefined) return null;
  return { carpeta, obraId: Number(pathname.split("/")[3]) };
}

// Al cambiar de pantalla, si el foco se perdió (lo tenía un control de la anterior), pasa al h1 de la nueva: el lector
// de pantalla la anuncia y el siguiente Tab parte de ahí. Si lo tiene otro control, no se toca; la primera carga y las
// redirecciones (`replace` a otra ruta) tampoco (focoAlTitulo.ts espera el h1 de la pantalla, que se carga a demanda).
function useFocoAlTitulo(pathname: string, clave: string) {
  const rutaPrevia = useRef(pathname);
  const clavePrevia = useRef(clave);
  const tipo = useNavigationType();
  useEffect(() => {
    const mismaRuta = rutaPrevia.current === pathname;
    if (mismaRuta && clavePrevia.current === clave) return;
    rutaPrevia.current = pathname;
    clavePrevia.current = clave;
    if (!mismaRuta && tipo === "REPLACE") return;
    return enfocarElTitulo();
  }, [pathname, clave, tipo]);
}
