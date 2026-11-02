import { createContext, createElement, useContext, useEffect, useState, type ReactNode } from "react";
import { pedir } from "../api/cliente";
import { aplicarTema, leerTema, RUTA_DEL_LOGO } from "./tema";

interface TemaCargado {
  logo: string | null;
}

// El tema ya cargado por `ProveedorDelTema` (App): el marco lo lee de aqui y no repite el pedido.
const ContextoDelTema = createContext<TemaCargado | null>(null);

// Pide GET /v1/tema (publico), fija los colores validos en la raiz del documento y devuelve la ruta del logo, o null
// si no hay. Si la API no contesta queda el tema neutro del repositorio. Dentro de un `ProveedorDelTema` no pide
// nada: devuelve lo que el proveedor ya cargo. Fuera de uno (pruebas de una pieza suelta) carga por su cuenta.
export function useTema(): TemaCargado {
  const heredado = useContext(ContextoDelTema);
  const [logo, setLogo] = useState<string | null>(null);

  useEffect(() => {
    if (heredado) return;
    let vigente = true;
    pedir("/v1/tema")
      .then((bruto) => {
        if (!vigente) return;
        const tema = leerTema(bruto);
        aplicarTema(tema, document.documentElement);
        setLogo(tema.tiene_logo ? RUTA_DEL_LOGO : null);
      })
      .catch(() => {
        // Sin tema no hay nada que avisar: la persona ve el marco neutro.
      });
    return () => {
      vigente = false;
    };
  }, [heredado]);

  return heredado ?? { logo };
}

// Carga el tema una vez, por encima de la puerta de sesion: el color de la empresa vale en TODA la aplicacion (entrar,
// bienvenida, recuperar acceso y marco), no solo dentro del marco. GET /v1/tema es publico (no pide sesion).
export function ProveedorDelTema({ children }: { children: ReactNode }) {
  const tema = useTema();
  return createElement(ContextoDelTema.Provider, { value: tema }, children);
}
