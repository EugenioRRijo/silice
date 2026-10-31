import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useInRouterContext, useSearchParams } from "react-router";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import { quedaEnLaHoja } from "../../marco/secciones";
import { useAplicacion } from "../../shell/contexto";
import { useFormularioSucio } from "../../shell/sucio";
import { useCarga } from "../inicio/useCarga";
import { ContextoDeDialogos } from "./ContextoDeDialogos";
import { DialogoDeGuardar } from "./DialogoDeGuardar";
import { DialogoDeVersion } from "./DialogoDeVersion";
import { rutaDeVersiones, textoDeCambios, versionesOfrecidas } from "./logica";
import type { Resumen, VersionesRespuesta } from "./logica";
import { usuarioDeSesion } from "./logicaGuardar";
import { RUTA_DE_BORRADORES, borradorExistente } from "./logicaRetomar";
import type { OfertaDeRetomar } from "./logicaRetomar";
import type { AlCrearVersion } from "./OperacionesDePrecios";
import { usePuedeEditarLaHoja } from "./puedeEditar";
import { useBorrador } from "./useBorrador";
import type { EstadoBorrador } from "./useBorrador";
import { useGuardadoDeLaPagina } from "./useGuardadoDeLaPagina";
import { useOfertas } from "./useOfertas";
import { useVersiones } from "./useVersiones";
import "./hoja.scss";

// Por qué existe (Tarea 3 del plan F4): Presupuesto, Archivos y planos (el plano y el cómputo entran en el borrador) y
// Versiones («Abrir», «Guardar versión…») trabajan sobre el MISMO borrador. Antes lo abría la Hoja y lo descartaba al
// desmontarse; aquí vive a nivel de la obra (lo monta EspacioDeObra en esas tres secciones) y la Hoja solo lo consume.
// Es la lógica de `HojaDeProyecto` sin cambios: las versiones, las ofertas de retomar, el borrador, cambiar de versión
// (con su confirmación), guardar y los diálogos de las operaciones sobre versiones, que se pintan aquí, fuera del
// contenido inerte de la sección. Lo usan la Hoja (`PaginaHoja`), la cabecera de la obra (la versión abierta) y, desde las
// Tareas 6 y 11, Versiones y Archivos y planos. Pasa de 250 líneas porque reúne ese estado, que es uno solo.

export type VersionesDeLaObra =
  | { estado: "cargando" }
  | { estado: "listo"; datos: VersionesRespuesta }
  | { estado: "error"; error: unknown };

export interface HojaDeLaObra {
  proyecto: string;
  nombreProyecto: string | null;
  // La lista de versiones: la que se leyó al abrir o la que se volvió a leer tras guardar.
  versiones: VersionesDeLaObra;
  // La versión que se abre: null es el borrador en blanco; undefined, que aún no se sabe (se leen las versiones o se
  // espera la respuesta a la oferta de retomar).
  codigo: string | null | undefined;
  estado: EstadoBorrador;
  hayCambios: boolean;
  // `puedeEditarLaHoja` (Tarea 2b) con la base del borrador abierto: editar_hoja y no solo_lectura.
  puedeEditar: boolean;
  // Los borradores con cambios que el servidor conserva de esta obra (E10) y lo que se hace con ellos.
  ofrecidos: OfertaDeRetomar[];
  retomar: (o: OfertaDeRetomar) => void;
  descartarOfrecidos: () => Promise<void>;
  descartando: boolean;
  falloAlDescartar: unknown;
  // E11: al abrir, el servidor dijo que ya hay un borrador con cambios de esa versión (su id).
  existente: string | null;
  // Abre otra versión; con cambios, pregunta antes («Descartar los cambios»).
  pedirVersion: (codigo: string) => void;
  refrescar: () => Promise<void>;
  aplicar: (r: Resumen) => void;
  reabrirNuevo: () => void;
  descartarCambios: () => Promise<void>;
  // Abre «Guardar versión» (DialogoDeGuardar).
  abrirGuardado: () => void;
  alCrearVersion: AlCrearVersion;
  // El aviso «Versión guardada», que la sección pinta.
  exito: { proyecto: string; texto: string } | null;
  quitarExito: () => void;
  // Hay un diálogo de la Hoja abierto: el contenido de la sección queda `inert`.
  inerte: boolean;
}

export const ContextoDeLaHoja = createContext<HojaDeLaObra | null>(null);

export function useHojaDeLaObra(): HojaDeLaObra {
  const hoja = useContext(ContextoDeLaHoja);
  if (hoja === null) throw new Error("useHojaDeLaObra se usó fuera de ProveedorDeLaHoja.");
  return hoja;
}

function textoDeCambiarVersion(cambios: number): string {
  return `Tiene ${textoDeCambios(cambios)}. Si abre otra versión se pierden: guarde primero o descarte.`;
}

// El proveedor de la obra elegida en la sesión (la de `useAplicacion`). Sin obra no hay borrador que compartir.
export function ProveedorDeLaHoja({ children }: { children: ReactNode }) {
  const { proyecto, nombreProyecto } = useAplicacion();
  if (proyecto === null) return <>{children}</>;
  return (
    <ProveedorDeProyecto proyecto={proyecto} nombreProyecto={nombreProyecto ?? null}>
      {children}
    </ProveedorDeProyecto>
  );
}

function ProveedorDeProyecto({ proyecto, nombreProyecto, children }: { proyecto: string; nombreProyecto: string | null; children: ReactNode }) {
  const { alExpirar, sesion } = useAplicacion();
  const carga = useCarga<VersionesRespuesta>(rutaDeVersiones(proyecto), alExpirar);
  const { ofertas, recargar: recargarOfertas } = useOfertas(proyecto, nombreProyecto, alExpirar);
  const [elegida, setElegida] = useState<{ proyecto: string; codigo: string } | null>(null);
  // El borrador que la persona decidió retomar (en vez de abrir uno nuevo) y el proyecto cuyas ofertas ya no valen.
  const [retomando, setRetomando] = useState<{ proyecto: string; id: string; version: string | null } | null>(null);
  const [sinOfertas, setSinOfertas] = useState<string | null>(null);
  const [descartando, setDescartando] = useState(false);
  const [falloAlDescartar, setFalloAlDescartar] = useState<unknown>(null);
  // La versión que la persona pidió con cambios sin guardar: espera su confirmación.
  const [versionPendiente, setVersionPendiente] = useState<string | null>(null);

  const retomado = retomando?.proyecto === proyecto ? retomando : null;
  const ofrecidos = ofertas.estado === "listo" && retomado === null && sinOfertas !== proyecto ? ofertas.lista : [];

  // Tras guardar se vuelve a leer la lista de versiones sin desmontar nada (valen mientras la carga inicial sea la misma).
  const cargadas = carga.estado === "listo" ? carga.datos : null;
  const { datos, recargarVersiones } = useVersiones(proyecto, cargadas, alExpirar);
  const ofrecidas = datos ? versionesOfrecidas(datos.versiones) : [];
  const delProyecto = elegida?.proyecto === proyecto ? elegida.codigo : null;
  const codigo =
    datos === null || ofertas.estado !== "listo" || ofrecidos.length > 0
      ? undefined
      : retomado !== null
        ? retomado.version
        : ofrecidas.some((v) => v.codigo === delProyecto)
          ? delProyecto
          : (datos.por_omision ?? null);

  const { estado, refrescar, reabrir, aplicar, descartarCambios, descartarActual, cerrarGuardado } = useBorrador(
    proyecto,
    codigo,
    alExpirar,
    retomado?.id ?? null,
  );
  const hayCambios = estado.estado === "listo" && estado.borrador.resumen.cambios > 0;
  // F4 2b: una sola regla para lo que escribe (quien revisa, o un borrador de solo lectura, no edita).
  const puedeEditar = usePuedeEditarLaHoja(estado.estado === "listo" ? estado.borrador.base : null);

  // E11: si al abrir el servidor dice que ya hay un borrador con cambios de esa versión, se ofrece retomarlo.
  const existente = estado.estado === "error" ? borradorExistente(estado.error) : null;
  const [existenteVisto, setExistenteVisto] = useState<string | null>(null);
  if (existente !== null && existente !== existenteVisto) {
    // Ajuste durante el render (react.dev, «You might not need an effect»): se vuelve a leer la lista, que ya lo incluye.
    setExistenteVisto(existente);
    setSinOfertas(null);
    recargarOfertas();
  }

  const elegirVersion = useCallback(
    (nueva: string) => {
      setRetomando(null);
      setElegida({ proyecto, codigo: nueva });
    },
    [proyecto],
  );
  const abrirVersion = elegirVersion;
  const pedirVersion = (nueva: string) => {
    if (nueva === codigo) return;
    if (hayCambios && estado.estado === "listo") setVersionPendiente(nueva);
    else abrirVersion(nueva);
  };
  const olvidarOfertas = useCallback(() => setSinOfertas(proyecto), [proyecto]);
  // Los diálogos de restaurar, cotizar, retirar y convertir los abre una pestaña pero se pintan aquí, fuera del contenido inerte.
  const [anfitrion, setAnfitrion] = useState<HTMLElement | null>(null);
  const [dialogosAbiertos, setDialogosAbiertos] = useState(0);
  const registrarDialogo = useCallback((delta: number) => setDialogosAbiertos((n) => n + delta), []);
  const dialogos = useMemo(
    () => ({ anfitrion, abiertos: dialogosAbiertos, registrar: registrarDialogo }),
    [anfitrion, dialogosAbiertos, registrarDialogo],
  );
  const { guardado, exito, quitarExito, cancelarYDevolverFoco, abrirDesdeElGuardado, alCrearVersion, devolverFocoA } = useGuardadoDeLaPagina({
    proyecto,
    id: estado.estado === "listo" ? estado.borrador.id : null,
    rev: estado.estado === "listo" ? estado.borrador.resumen.rev : 0,
    alExpirar,
    cerrarGuardado,
    recargarVersiones,
    olvidarOfertas,
    elegirVersion,
    pedirVersion,
    hayConfirmacion: versionPendiente !== null || dialogosAbiertos > 0,
  });
  const seguirEditando = useCallback(() => {
    setVersionPendiente(null);
    devolverFocoA("version");
  }, [devolverFocoA]);
  const descartarYAbrir = async () => {
    const nueva = versionPendiente;
    setVersionPendiente(null);
    devolverFocoA("version");
    if (nueva === null) return;
    if (await descartarActual()) abrirVersion(nueva);
  };
  const retomar = (oferta: OfertaDeRetomar) => {
    setFalloAlDescartar(null);
    setRetomando({ proyecto, id: oferta.id, version: oferta.version });
  };
  const descartarOfrecidos = async () => {
    setDescartando(true);
    setFalloAlDescartar(null);
    try {
      await Promise.all(ofrecidos.map((o) => pedir(`${RUTA_DE_BORRADORES}/${o.id}`, { metodo: "DELETE" })));
      setSinOfertas(proyecto);
    } catch (error) {
      if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
      setFalloAlDescartar(error);
    } finally {
      setDescartando(false);
    }
  };
  // «Abrir de nuevo» (el borrador ya no está o ya no sirve): se abre uno nuevo de la versión, sin volver a ofrecer los viejos.
  const reabrirNuevo = () => {
    setRetomando(null);
    setSinOfertas(proyecto);
    reabrir();
  };

  useEffect(() => {
    const alVolver = () => {
      if (document.visibilityState === "visible") refrescar();
    };
    document.addEventListener("visibilitychange", alVolver);
    return () => document.removeEventListener("visibilitychange", alVolver);
  }, [refrescar]);

  // Con cambios sin guardar, el navegador avisa antes de cerrar o recargar la ventana (la clásica no podía).
  useEffect(() => {
    if (!hayCambios) return;
    const avisar = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", avisar);
    return () => window.removeEventListener("beforeunload", avisar);
  }, [hayCambios]);

  // Dentro de una obra, salir con cambios por el marco pregunta («Cambios sin guardar», foco 1), salvo hacia otra sección
  // con Hoja de la misma obra, que comparte este borrador. Fuera de una obra (la Hoja montada sola) no se registra.
  const obra = useContext(ContextoDeLaObra);
  const carpetaDeLaObra = obra?.carpeta ?? null;
  const obraId = obra?.obraId ?? null;
  const conserva = useMemo(
    () => (obraId === null ? null : (destino: string) => quedaEnLaHoja(destino, carpetaDeLaObra, obraId)),
    [carpetaDeLaObra, obraId],
  );
  useFormularioSucio("hoja", conserva !== null && hayCambios, conserva);

  const enRuta = useInRouterContext();
  const versiones: VersionesDeLaObra =
    carga.estado === "cargando"
      ? carga
      : carga.estado === "listo" && datos !== null
        ? { estado: "listo", datos }
        : { estado: "error", error: "error" in carga ? carga.error : null };
  const hoja: HojaDeLaObra = {
    proyecto,
    nombreProyecto,
    versiones,
    codigo,
    estado,
    hayCambios,
    puedeEditar,
    ofrecidos,
    retomar,
    descartarOfrecidos,
    descartando,
    falloAlDescartar,
    existente,
    pedirVersion,
    refrescar,
    aplicar,
    reabrirNuevo,
    descartarCambios,
    abrirGuardado: guardado.abrir,
    alCrearVersion,
    exito,
    quitarExito,
    inerte: versionPendiente !== null || guardado.abierto || dialogosAbiertos > 0,
  };

  return (
    <ContextoDeLaHoja.Provider value={hoja}>
      <ContextoDeDialogos.Provider value={dialogos}>
        {children}
        {enRuta && <VersionDeLaRuta pedirVersion={pedirVersion} />}
        {guardado.abierto && estado.estado === "listo" && (
          <DialogoDeGuardar
            proyecto={estado.borrador.base.proyecto}
            version={estado.borrador.base.version}
            soloLectura={estado.borrador.base.solo_lectura}
            cambiosSinGuardar={estado.borrador.resumen.cambios}
            total={estado.borrador.resumen.total}
            moneda={estado.borrador.resumen.moneda}
            usuario={usuarioDeSesion(sesion)}
            fuente={guardado.fuente}
            alCambiarFuente={guardado.escribir}
            cambios={guardado.cambios}
            enviando={guardado.enviando}
            error={guardado.error}
            alGuardar={(confirmar) => void guardado.guardar(confirmar)}
            alCancelar={cancelarYDevolverFoco}
            alRecargar={() => void refrescar().then(guardado.limpiarError)}
            alAbrirVersion={(v) => void abrirDesdeElGuardado(v)}
            alAbrirDeNuevo={() => {
              cancelarYDevolverFoco();
              reabrirNuevo();
            }}
          />
        )}
        {versionPendiente !== null && estado.estado === "listo" && (
          <DialogoDeVersion
            titulo="Descartar los cambios"
            texto={textoDeCambiarVersion(estado.borrador.resumen.cambios)}
            textoConfirmar="Descartar y abrir"
            textoCancelar="Seguir editando"
            alConfirmar={() => void descartarYAbrir()}
            alCancelar={seguirEditando}
          />
        )}
        {/* Aquí se pintan los diálogos de las operaciones sobre versiones: fuera del contenido, que queda inerte mientras haya uno. */}
        <div ref={setAnfitrion} className="silice-hoja__anfitrion" />
      </ContextoDeDialogos.Provider>
    </ContextoDeLaHoja.Provider>
  );
}

// `?version=<código>` en la ruta (Versiones «Abrir», Tarea 6; Mercado, Tarea 13): se pide esa versión por el camino de
// siempre (con cambios, primero «Descartar los cambios») y se quita el parámetro, para que volver a la ruta no la pida otra
// vez. Solo dentro de un enrutador: las pruebas de la Hoja la montan sola.
function VersionDeLaRuta({ pedirVersion }: { pedirVersion: (codigo: string) => void }) {
  const [parametros, setParametros] = useSearchParams();
  const pedida = parametros.get("version");
  const pedir = useRef(pedirVersion);
  useEffect(() => {
    pedir.current = pedirVersion;
  });
  useEffect(() => {
    if (pedida === null) return;
    pedir.current(pedida);
    setParametros(
      (previos) => {
        const sin = new URLSearchParams(previos);
        sin.delete("version");
        return sin;
      },
      { replace: true },
    );
  }, [pedida, setParametros]);
  return null;
}
