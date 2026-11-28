import { useCallback, useEffect, useState } from "react";

// Preferencia de apariencia (claro, oscuro o como el sistema). Por defecto sigue al sistema y solo guarda una clave en
// localStorage cuando la persona elige «Claro» u «Oscuro»; al volver a «Como el sistema» la clave se elimina. Todo acceso
// a localStorage va en try/catch para no fallar con almacenamiento bloqueado o lleno.

export type ModoDeColor = "claro" | "oscuro" | "sistema";
export type ModoEfectivo = "claro" | "oscuro";

export const CLAVE_MODO_COLOR = "silice-modo";
const CONSULTA_OSCURA = "(prefers-color-scheme: dark)";

const CONTENT_POR_MODO: Record<ModoDeColor, string> = {
  claro: "light",
  oscuro: "dark",
  sistema: "light dark",
};

function normalizarModo(valor: string | null | undefined): ModoDeColor {
  return valor === "claro" || valor === "oscuro" ? valor : "sistema";
}

/** Lee la preferencia guardada en localStorage; si falta, es inválida o falla, devuelve "sistema". */
export function leerModo(): ModoDeColor {
  try {
    return normalizarModo(window.localStorage.getItem(CLAVE_MODO_COLOR));
  } catch {
    return "sistema";
  }
}

/** Guarda "claro" u "oscuro" en localStorage, o elimina la clave al volver a "sistema". */
export function guardarModo(modo: ModoDeColor): void {
  try {
    if (modo === "sistema") {
      window.localStorage.removeItem(CLAVE_MODO_COLOR);
    } else {
      window.localStorage.setItem(CLAVE_MODO_COLOR, modo);
    }
  } catch {
    // Sin almacenamiento la elección vale para esta pantalla y no se recuerda.
  }
}

/** Fija `data-modo` en <html> (o lo quita en "sistema") y actualiza `<meta name="color-scheme">`. */
export function aplicarModo(modo: ModoDeColor): void {
  const raiz = document.documentElement;
  if (modo === "sistema") {
    delete raiz.dataset.modo;
  } else {
    raiz.dataset.modo = modo;
  }
  let meta = document.querySelector('meta[name="color-scheme"]');
  if (!meta) {
    meta = document.createElement("meta");
    meta.setAttribute("name", "color-scheme");
    document.head.appendChild(meta);
  }
  meta.setAttribute("content", CONTENT_POR_MODO[modo]);
}

/** Devuelve el modo activo del sistema operativo según `prefers-color-scheme: dark`. */
export function modoDelSistema(): ModoEfectivo {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return "claro";
  }
  return window.matchMedia(CONSULTA_OSCURA).matches ? "oscuro" : "claro";
}

function modoInicial(): ModoDeColor {
  const aplicado = document.documentElement.dataset.modo;
  if (aplicado === "claro" || aplicado === "oscuro") return aplicado;
  return leerModo();
}

export interface EstadoModoDeColor {
  modo: ModoDeColor;
  delSistema: ModoEfectivo;
  elegir: (nuevo: ModoDeColor) => void;
}

/** Estado sincronizado del modo de color: aplica y guarda la elección, y escucha `storage` y `matchMedia`. */
export function useModoDeColor(): EstadoModoDeColor {
  const [modo, setModo] = useState<ModoDeColor>(modoInicial);
  const [delSistema, setDelSistema] = useState<ModoEfectivo>(modoDelSistema);

  const elegir = useCallback((nuevo: ModoDeColor) => {
    setModo(nuevo);
    aplicarModo(nuevo);
    guardarModo(nuevo);
  }, []);

  useEffect(() => {
    const alCambiarStorage = (evento: StorageEvent) => {
      if (evento.key !== null && evento.key !== CLAVE_MODO_COLOR) return;
      const siguiente = evento.key === null ? leerModo() : normalizarModo(evento.newValue);
      setModo(siguiente);
      aplicarModo(siguiente);
    };
    window.addEventListener("storage", alCambiarStorage);
    return () => window.removeEventListener("storage", alCambiarStorage);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const consulta = window.matchMedia(CONSULTA_OSCURA);
    if (typeof consulta.addEventListener !== "function") return;
    const alCambiarSistema = (evento?: MediaQueryListEvent) => {
      const oscuro = evento?.matches ?? consulta.matches;
      setDelSistema(oscuro ? "oscuro" : "claro");
    };
    consulta.addEventListener("change", alCambiarSistema);
    return () => consulta.removeEventListener("change", alCambiarSistema);
  }, []);

  return { modo, delSistema, elegir };
}
