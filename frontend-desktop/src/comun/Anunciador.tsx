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

export function ProveedorDeAnuncios({ children }: { children: ReactNode }): JSX.Element {
  const [cortes, setCortes] = useState("");
  const [urgente, setUrgente] = useState("");
  const canales = useRef<{ cortes: Canal; urgente: Canal }>({
    cortes: { ultimo: "", reloj: null },
    urgente: { ultimo: "", reloj: null },
  });

  useEffect(() => {
    const actual = canales.current;
    return () => {
      if (actual.cortes.reloj !== null) clearTimeout(actual.cortes.reloj);
      if (actual.urgente.reloj !== null) clearTimeout(actual.urgente.reloj);
    };
  }, []);

  const anunciar = useCallback<FuncionAnunciar>((texto, opciones) => {
    if (opciones?.urgente) {
      emitirEnCanal(canales.current.urgente, setUrgente, texto);
    } else {
      emitirEnCanal(canales.current.cortes, setCortes, texto);
    }
  }, []);

  return (
    <ContextoDeAnuncios.Provider value={anunciar}>
      {children}
      <div className="cds--visually-hidden" role="status" aria-live="polite">
        {cortes}
      </div>
      <div className="cds--visually-hidden" aria-live="assertive" aria-atomic="true">
        {urgente}
      </div>
    </ContextoDeAnuncios.Provider>
  );
}

export function useAnunciar(): FuncionAnunciar {
  return useContext(ContextoDeAnuncios);
}
