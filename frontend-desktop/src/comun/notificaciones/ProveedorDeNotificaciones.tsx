import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { JSX, ReactNode } from "react";
import { useAnunciar } from "../Anunciador";
import {
  contarSinLeer,
  descartarVencidas,
  hayDialogoModalAbierto,
  instanteActual,
  marcarTodasComoLeidas,
  ordenarPorFechaDescendente,
  textoDeAnuncio,
} from "./modelo";
import type { Notificacion, NuevaNotificacion } from "./modelo";

export interface AlmacenDeNotificaciones {
  cargar: () => readonly Notificacion[] | Promise<readonly Notificacion[]>;
  guardar: (notificaciones: readonly Notificacion[]) => void | Promise<void>;
}

export function crearAlmacenEnMemoria(iniciales: readonly Notificacion[] = []): AlmacenDeNotificaciones {
  let copia: Notificacion[] = iniciales.map((n) => ({ ...n }));
  return {
    cargar: () => copia.map((n) => ({ ...n })),
    guardar: (notificaciones) => {
      copia = notificaciones.map((n) => ({ ...n }));
    },
  };
}

export interface ContextoDeNotificacionesValor {
  notificaciones: readonly Notificacion[];
  emergentes: readonly Notificacion[];
  sinLeer: number;
  notificar: (nueva: NuevaNotificacion) => string;
  cerrar: (id: string) => void;
  marcarLeida: (id: string) => void;
  marcarTodasLeidas: () => void;
  panelAbierto: boolean;
  abrirPanel: () => void;
  cerrarPanel: () => void;
  alternarPanel: () => void;
  idPanel: string;
  registrarCampanita: (elemento: HTMLButtonElement | null) => void;
  enfocarCampanita: () => boolean;
  modalAbierto: boolean;
}

export interface PropsDelProveedorDeNotificaciones {
  almacen?: AlmacenDeNotificaciones;
  idPanel?: string;
  ahora?: () => Date;
  children: ReactNode;
}

const ID_PANEL_POR_OMISION = "panel-notif";

function esPromesa<T>(valor: T | Promise<T>): valor is Promise<T> {
  return typeof valor === "object" && valor !== null && "then" in valor && typeof valor.then === "function";
}

function persistirSinFallo(almacen: AlmacenDeNotificaciones, lista: readonly Notificacion[]): void {
  try {
    const resultado = almacen.guardar(lista);
    if (esPromesa(resultado)) {
      void resultado.catch(() => {});
    }
  } catch {
    // Un fallo de almacenamiento no rompe la interfaz.
  }
}

let secuenciaId = 0;
function nuevoId(): string {
  secuenciaId += 1;
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `notif-${secuenciaId}-${crypto.randomUUID()}`;
  }
  return `notif-${secuenciaId}`;
}

const VALOR_FUERA_DE_PROVEEDOR: ContextoDeNotificacionesValor = {
  notificaciones: [],
  emergentes: [],
  sinLeer: 0,
  notificar: () => "",
  cerrar: () => {},
  marcarLeida: () => {},
  marcarTodasLeidas: () => {},
  panelAbierto: false,
  abrirPanel: () => {},
  cerrarPanel: () => {},
  alternarPanel: () => {},
  idPanel: ID_PANEL_POR_OMISION,
  registrarCampanita: () => {},
  enfocarCampanita: () => false,
  modalAbierto: false,
};

const ContextoDeNotificaciones = createContext<ContextoDeNotificacionesValor>(VALOR_FUERA_DE_PROVEEDOR);

interface CargaInicialSincrona {
  vigentes: Notificacion[];
  recortadas: boolean;
  pendienteAsync: Promise<readonly Notificacion[]> | null;
}

function leerInicial(almacen: AlmacenDeNotificaciones, instante: Date): CargaInicialSincrona {
  const respuesta = almacen.cargar();
  if (esPromesa(respuesta)) {
    // El inicializador de useState puede correr dos veces (modo estricto) y una de las promesas queda sin consumir: se
    // marca atendida aquí para que un fallo de carga (sin red, 401) no quede como rechazo sin atrapar. El efecto sigue
    // leyendo esta misma promesa con su propio catch.
    respuesta.catch(() => {});
    return { vigentes: [], recortadas: false, pendienteAsync: respuesta };
  }
  const vigentes = ordenarPorFechaDescendente(descartarVencidas(respuesta, instante));
  return {
    vigentes,
    recortadas: vigentes.length < respuesta.length,
    pendienteAsync: null,
  };
}

export function ProveedorDeNotificaciones({
  almacen,
  idPanel = ID_PANEL_POR_OMISION,
  ahora,
  children,
}: PropsDelProveedorDeNotificaciones): JSX.Element {
  const anunciar = useAnunciar();
  const [almacenEnMemoria] = useState<AlmacenDeNotificaciones>(() => crearAlmacenEnMemoria());
  const almacenEfectivo = almacen ?? almacenEnMemoria;

  const obtenerAhora = useCallback(() => instanteActual(ahora), [ahora]);

  const [cargaInicial] = useState<CargaInicialSincrona>(() =>
    leerInicial(almacenEfectivo, instanteActual(ahora)),
  );
  const [notificaciones, setNotificaciones] = useState<readonly Notificacion[]>(cargaInicial.vigentes);
  const [emergentes, setEmergentes] = useState<readonly Notificacion[]>([]);
  const [panelAbierto, setPanelAbierto] = useState(false);
  const [modalAbierto, setModalAbierto] = useState<boolean>(() => hayDialogoModalAbierto());

  const colaModalRef = useRef<Notificacion[]>([]);
  const refCampanita = useRef<HTMLButtonElement | null>(null);
  const almacenInicialRef = useRef(almacenEfectivo);

  // Carga asíncrona (p. ej. API por persona) y limpieza de las de más de 30 días al arrancar.
  useEffect(() => {
    let cancelado = false;
    const esPrimerAlmacen = almacenInicialRef.current === almacenEfectivo;

    if (esPrimerAlmacen && cargaInicial.pendienteAsync === null) {
      if (cargaInicial.recortadas) {
        persistirSinFallo(almacenEfectivo, cargaInicial.vigentes);
      }
      return () => {
        cancelado = true;
      };
    }

    const promesa =
      esPrimerAlmacen && cargaInicial.pendienteAsync !== null
        ? cargaInicial.pendienteAsync
        : Promise.resolve(almacenEfectivo.cargar());
    almacenInicialRef.current = almacenEfectivo;

    void promesa
      .then((cargadas) => {
        if (cancelado) return;
        const instante = obtenerAhora();
        const vigentes = descartarVencidas(cargadas, instante);
        const habiaVencidas = vigentes.length < cargadas.length;
        setNotificaciones((actuales) => {
          const idsActuales = new Set(actuales.map((n) => n.id));
          const fusion = ordenarPorFechaDescendente([
            ...descartarVencidas(actuales, instante),
            ...vigentes.filter((n) => !idsActuales.has(n.id)),
          ]);
          if (habiaVencidas || actuales.length > 0) {
            persistirSinFallo(almacenEfectivo, fusion);
          }
          return fusion;
        });
      })
      .catch(() => {});

    return () => {
      cancelado = true;
    };
  }, [almacenEfectivo, cargaInicial, obtenerAhora]);

  const anunciarLote = useCallback(
    (lote: readonly Notificacion[]) => {
      const urgentes = lote.filter((n) => n.gravedad === "error").map((n) => textoDeAnuncio(n));
      const corteses = lote.filter((n) => n.gravedad !== "error").map((n) => textoDeAnuncio(n));
      if (corteses.length > 0) {
        anunciar(corteses.join(" "));
      }
      if (urgentes.length > 0) {
        anunciar(urgentes.join(" "), { urgente: true });
      }
    },
    [anunciar],
  );

  // Vigila apertura y cierre de cualquier <dialog> modal para pausar y desencolar al cerrarse.
  useEffect(() => {
    if (typeof document === "undefined" || !document.body) return;

    const sincronizarModal = () => {
      const abiertoAhora = hayDialogoModalAbierto();
      setModalAbierto(abiertoAhora);
      if (!abiertoAhora && colaModalRef.current.length > 0) {
        const encoladas = colaModalRef.current.splice(0);
        setEmergentes((previas) => [...previas, ...encoladas]);
        anunciarLote(encoladas);
      }
    };

    const observador = new MutationObserver(sincronizarModal);
    observador.observe(document.body, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["open", "aria-modal", "role"],
    });
    document.addEventListener("close", sincronizarModal, true);
    document.addEventListener("cancel", sincronizarModal, true);

    return () => {
      observador.disconnect();
      document.removeEventListener("close", sincronizarModal, true);
      document.removeEventListener("cancel", sincronizarModal, true);
    };
  }, [anunciarLote]);

  const notificar = useCallback(
    (nueva: NuevaNotificacion): string => {
      const instante = obtenerAhora();
      const item: Notificacion = {
        id: nueva.id ?? nuevoId(),
        gravedad: nueva.gravedad,
        titulo: nueva.titulo,
        ...(nueva.detalle !== undefined ? { detalle: nueva.detalle } : {}),
        ...(nueva.enlace !== undefined ? { enlace: nueva.enlace } : {}),
        creada: nueva.creada ?? instante.toISOString(),
        leida: nueva.leida ?? false,
      };

      setNotificaciones((previas) => {
        const vigentes = descartarVencidas(previas, instante).filter((n) => n.id !== item.id);
        const actualizadas = ordenarPorFechaDescendente([item, ...vigentes]);
        persistirSinFallo(almacenEfectivo, actualizadas);
        return actualizadas;
      });

      if (hayDialogoModalAbierto()) {
        setModalAbierto(true);
        colaModalRef.current.push(item);
      } else {
        setEmergentes((previas) => [...previas.filter((n) => n.id !== item.id), item]);
        anunciar(textoDeAnuncio(item), { urgente: item.gravedad === "error" });
      }
      return item.id;
    },
    [almacenEfectivo, anunciar, obtenerAhora],
  );

  const cerrar = useCallback((id: string) => {
    colaModalRef.current = colaModalRef.current.filter((n) => n.id !== id);
    setEmergentes((previas) => previas.filter((n) => n.id !== id));
  }, []);

  const marcarLeida = useCallback(
    (id: string) => {
      setNotificaciones((previas) => {
        if (!previas.some((n) => n.id === id && !n.leida)) return previas;
        const actualizadas = previas.map((n) => (n.id === id ? { ...n, leida: true } : n));
        persistirSinFallo(almacenEfectivo, actualizadas);
        return actualizadas;
      });
    },
    [almacenEfectivo],
  );

  const marcarTodasLeidas = useCallback(() => {
    setNotificaciones((previas) => {
      if (contarSinLeer(previas) === 0) return previas;
      const actualizadas = marcarTodasComoLeidas(previas);
      persistirSinFallo(almacenEfectivo, actualizadas);
      return actualizadas;
    });
  }, [almacenEfectivo]);

  const abrirPanel = useCallback(() => setPanelAbierto(true), []);
  const cerrarPanel = useCallback(() => setPanelAbierto(false), []);
  const alternarPanel = useCallback(() => setPanelAbierto((abierto) => !abierto), []);

  const registrarCampanita = useCallback((elemento: HTMLButtonElement | null) => {
    refCampanita.current = elemento;
  }, []);

  const enfocarCampanita = useCallback((): boolean => {
    const boton = refCampanita.current;
    if (boton !== null && boton.isConnected) {
      boton.focus();
      return true;
    }
    return false;
  }, []);

  const sinLeer = useMemo(() => contarSinLeer(notificaciones), [notificaciones]);

  const valor = useMemo<ContextoDeNotificacionesValor>(
    () => ({
      notificaciones,
      emergentes,
      sinLeer,
      notificar,
      cerrar,
      marcarLeida,
      marcarTodasLeidas,
      panelAbierto,
      abrirPanel,
      cerrarPanel,
      alternarPanel,
      idPanel,
      registrarCampanita,
      enfocarCampanita,
      modalAbierto,
    }),
    [
      notificaciones,
      emergentes,
      sinLeer,
      notificar,
      cerrar,
      marcarLeida,
      marcarTodasLeidas,
      panelAbierto,
      abrirPanel,
      cerrarPanel,
      alternarPanel,
      idPanel,
      registrarCampanita,
      enfocarCampanita,
      modalAbierto,
    ],
  );

  return <ContextoDeNotificaciones.Provider value={valor}>{children}</ContextoDeNotificaciones.Provider>;
}

export function useNotificaciones(): ContextoDeNotificacionesValor {
  return useContext(ContextoDeNotificaciones);
}
