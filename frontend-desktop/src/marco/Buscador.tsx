import { Search } from "@carbon/icons-react";
import { useEffect, useId, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { useNavigate } from "react-router";
import { useAtraparFoco } from "../shell/useAtraparFoco";
import "./Buscador.scss";
import { resultadosDe } from "./busqueda";
import { obrasAlcanzables, useOferta } from "./oferta";
import { useObras } from "./useObras";

interface Props {
  abierto: boolean;
  alCerrar: () => void;
}

// El botón de la barra superior que abre el buscador: a él vuelve el foco si quien lo abrió ya no está.
const BOTON_DEL_BUSCADOR = '[aria-keyshortcuts="Control+K"]';

function anuncioDe(cantidad: number): string {
  if (cantidad === 0) return "Sin resultados";
  return cantidad === 1 ? "1 resultado" : `${cantidad} resultados`;
}

// Buscador global (Ctrl+K) del marco nuevo: obras, secciones, entradas de Empresa y pantallas sin sitio en el árbol. Es
// un diálogo propio, no el Modal de Carbon (como los demás del armazón: su archivo trae una URL que `npm run dist`
// rechaza, RNF-22), con el patrón WAI-ARIA combobox + listbox: el foco se queda en el campo y la opción activa se
// señala con aria-activedescendant. Todavía no está montado en la aplicación (Tarea 8 del plan del marco).
export function Buscador({ abierto, alCerrar }: Props) {
  return abierto ? <Caja alCerrar={alCerrar} /> : null;
}

function Caja({ alCerrar }: { alCerrar: () => void }) {
  const base = useId();
  const caja = useRef<HTMLDivElement>(null);
  const navegar = useNavigate();
  const atrapar = useAtraparFoco(caja);
  const { puedeCambiarDeCarpeta, oferta } = useOferta();
  const { obras, carpetaActual, estado } = useObras();
  const [texto, setTexto] = useState("");
  const [activo, setActivo] = useState(0);
  // Quien tenía el foco al abrir (el botón de la barra, si se abrió con un clic).
  const previo = useRef<Element | null>(document.activeElement);
  const devolverFoco = useRef(true);
  const entrada = useRef<HTMLInputElement>(null);

  const resultados = resultadosDe(texto, obrasAlcanzables(obras, carpetaActual, puedeCambiarDeCarpeta), oferta);
  const indice = Math.min(activo, Math.max(resultados.length - 1, 0));
  const idDe = (i: number) => `${base}-opcion-${i}`;

  useEffect(() => entrada.current?.focus(), []);

  // Al cerrar sin elegir, el foco vuelve a quien lo tenía (el botón de la barra) o, si ya no está, a ese botón.
  useEffect(() => {
    const anterior = previo.current;
    return () => {
      if (!devolverFoco.current) return;
      const destino = anterior instanceof HTMLElement && anterior.isConnected ? anterior : document.querySelector<HTMLElement>(BOTON_DEL_BUSCADOR);
      destino?.focus();
    };
  }, []);

  function elegir(i: number) {
    const elegido = resultados[i];
    if (!elegido) return;
    // El foco va al contenido de la pantalla elegida, no de vuelta a la barra.
    devolverFoco.current = false;
    navegar(elegido.ruta);
    alCerrar();
    document.getElementById("contenido")?.focus();
  }

  function alTeclear(e: KeyboardEvent<HTMLDivElement>) {
    const n = resultados.length;
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      alCerrar();
    } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (n > 0) setActivo((indice + (e.key === "ArrowDown" ? 1 : n - 1)) % n);
    } else if (e.key === "Enter") {
      e.preventDefault();
      elegir(indice);
    } else atrapar(e);
  }

  return (
    <div className="silice-buscador__fondo" onMouseDown={(e) => e.target === e.currentTarget && alCerrar()}>
      <div
        ref={caja}
        role="dialog"
        aria-modal="true"
        aria-label="Buscar"
        className="silice-buscador"
        onKeyDown={alTeclear}
      >
        <div className="silice-buscador__campo">
          <Search size={20} aria-hidden="true" />
          <input
            ref={entrada}
            type="text"
            role="combobox"
            aria-label="Buscar una obra, sección o pantalla"
            aria-expanded="true"
            aria-controls={`${base}-lista`}
            aria-autocomplete="list"
            aria-activedescendant={resultados.length > 0 ? idDe(indice) : undefined}
            autoComplete="off"
            spellCheck={false}
            placeholder="Buscar una obra, sección o pantalla…"
            value={texto}
            onChange={(e) => {
              setTexto(e.target.value);
              setActivo(0);
            }}
            className="silice-buscador__entrada"
          />
        </div>
        <ul id={`${base}-lista`} role="listbox" aria-label="Resultados" className="silice-buscador__lista">
          {resultados.map((r, i) => (
            <li
              key={`${r.texto}|${r.ruta}`}
              id={idDe(i)}
              role="option"
              aria-selected={i === indice}
              className="silice-buscador__opcion"
              onMouseMove={() => setActivo(i)}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => elegir(i)}
            >
              <span className="silice-buscador__texto">{r.texto}</span>
              <span className="silice-buscador__detalle">{r.detalle}</span>
            </li>
          ))}
        </ul>
        {estado === "error" && (
          <p role="alert" className="silice-buscador__aviso">
            No se pudieron cargar las obras
          </p>
        )}
        <div role="status" aria-live="polite" aria-atomic="true" className="silice-buscador__estado">
          {anuncioDe(resultados.length)}
        </div>
      </div>
    </div>
  );
}
