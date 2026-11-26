import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { JSX, ReactNode } from "react";

// Centraliza en un solo lugar las dos regiones vivas (cortés y urgente) para los anuncios no visibles de la aplicación.

interface OpcionesDeAnuncio {
  urgente?: boolean;
}

type FuncionAnunciar = (texto: string, opciones?: OpcionesDeAnuncio) => void;

interface Canal {
  ultimo: string;
  reloj: ReturnType<typeof setTimeout> | null;
}

function emitirEnCanal(canal: Canal, fijar: (valor: string) => void, texto: string): void {
  if (canal.reloj !== null) {
    clearTimeout(canal.reloj);
    canal.reloj = null;
  }
  if (texto !== "" && canal.ultimo === texto) {
    canal.ultimo = "";
    fijar("");
    canal.reloj = setTimeout(() => {
      canal.reloj = null;
      canal.ultimo = texto;
      fijar(texto);
    }, 0);
    return;
  }
  canal.ultimo = texto;
  fijar(texto);
}

const sinProveedor: FuncionAnunciar = () => {};

const ContextoDeAnuncios = createContext<FuncionAnunciar>(sinProveedor);

// Un destino es un par de regiones vivas distinto de la raíz, por ejemplo el del `<dialog>` modal abierto: con
// `showModal()` el resto de la página queda inerte y lo que se escriba en sus regiones no se lee.
export interface DestinoDeAnuncios {
  fijarCortes: (texto: string) => void;
  fijarUrgente: (texto: string) => void;
}

export type RegistrarDestino = (destino: DestinoDeAnuncios) => () => void;

const ContextoDeDestinos = createContext<RegistrarDestino | null>(null);

interface CanalesDeDestino {
  cortes: Canal;
  urgente: Canal;
}

interface EntradaDeDestino {
  destino: DestinoDeAnuncios;
  canales: CanalesDeDestino;
}

function nuevosCanales(): CanalesDeDestino {
  return { cortes: { ultimo: "", reloj: null }, urgente: { ultimo: "", reloj: null } };
}

function limpiarRelojes(canales: CanalesDeDestino): void {
  if (canales.cortes.reloj !== null) clearTimeout(canales.cortes.reloj);
  if (canales.urgente.reloj !== null) clearTimeout(canales.urgente.reloj);
  canales.cortes.reloj = null;
  canales.urgente.reloj = null;
}

export function ProveedorDeAnuncios({ children }: { children: ReactNode }): JSX.Element {
  const [cortes, setCortes] = useState("");
  const [urgente, setUrgente] = useState("");
  const canales = useRef<CanalesDeDestino>(nuevosCanales());
  // Pila de destinos: se escribe en el más alto; sin destinos, en la raíz.
  const pila = useRef<EntradaDeDestino[]>([]);

  useEffect(() => {
    const raiz = canales.current;
    const entradas = pila.current;
    return () => {
      limpiarRelojes(raiz);
      for (const entrada of entradas) limpiarRelojes(entrada.canales);
    };
  }, []);

  const registrarDestino = useCallback<RegistrarDestino>((destino) => {
    const entrada: EntradaDeDestino = { destino, canales: nuevosCanales() };
    pila.current.push(entrada);
    return () => {
      limpiarRelojes(entrada.canales);
      const posicion = pila.current.indexOf(entrada);
      if (posicion >= 0) pila.current.splice(posicion, 1);
    };
  }, []);

  const anunciar = useCallback<FuncionAnunciar>((texto, opciones) => {
    const entrada = pila.current[pila.current.length - 1];
    const destinoCanales = entrada?.canales ?? canales.current;
    const fijarCortes = entrada?.destino.fijarCortes ?? setCortes;
    const fijarUrgente = entrada?.destino.fijarUrgente ?? setUrgente;
    if (opciones?.urgente) {
      emitirEnCanal(destinoCanales.urgente, fijarUrgente, texto);
    } else {
      emitirEnCanal(destinoCanales.cortes, fijarCortes, texto);
    }
  }, []);

  return (
    <ContextoDeAnuncios.Provider value={anunciar}>
      <ContextoDeDestinos.Provider value={registrarDestino}>
        {children}
        <div className="cds--visually-hidden" role="status" aria-live="polite">
          {cortes}
        </div>
        <div className="cds--visually-hidden" aria-live="assertive" aria-atomic="true">
          {urgente}
        </div>
      </ContextoDeDestinos.Provider>
    </ContextoDeAnuncios.Provider>
  );
}

export function useAnunciar(): FuncionAnunciar {
  return useContext(ContextoDeAnuncios);
}

// Para quien monta sus propias regiones vivas (hoy, `Dialogo`). `null` si no hay `ProveedorDeAnuncios` encima.
export function useRegistroDeDestinos(): RegistrarDestino | null {
  return useContext(ContextoDeDestinos);
}
