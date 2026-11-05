import { Search, User } from "@carbon/icons-react";
import { useEffect } from "react";
import type { ReactNode } from "react";
import { Link, useLocation } from "react-router";
import { iniciales } from "../shell/iniciales";
import "../shell/MenuCuenta.scss";
import "./BarraSuperior.scss";
import { rutaDeCuenta } from "./espacios";
import { RUTA_DE_INICIO } from "./secciones";
import { useTema } from "./useTema";

interface Props {
  alAbrirBuscador: () => void;
  nombre: string;
  // El nombre de la carpeta abierta ahora, o null si todavía no se sabe (no se pinta un rótulo vacío).
  carpeta: string | null;
  // Lo que el marco pone antes de la cuenta (la marca de la demostración, «Recorrido»).
  extra?: ReactNode;
}

// Un campo donde Ctrl+K ya significa otra cosa (texto largo o contenido editable, también «plaintext-only»): ahi no se abre el
// buscador. `closest` incluye al propio destino.
function usaCtrlK(destino: EventTarget | null): boolean {
  return (
    destino instanceof HTMLElement &&
    (destino instanceof HTMLTextAreaElement || destino.closest('[contenteditable]:not([contenteditable="false"])') !== null)
  );
}

// Barra superior del marco (plan F6, T6; diseño visual §4): la marca, que lleva a la ruta índice; la carpeta activa; el
// buscador (Ctrl+K); y la persona, que es un enlace a la Cuenta. Sin migas (cada espacio dice dónde se está) y sin el
// tamaño de letra, que vive solo en la Cuenta (decisión de Eugenio, 2026-11-04). La monta marco/Marco.
export function BarraSuperior({ alAbrirBuscador, nombre, carpeta, extra }: Props) {
  const { logo } = useTema();
  const { pathname } = useLocation();
  const enLaCuenta = pathname === "/cuenta" || pathname.startsWith("/cuenta/");
  const letras = iniciales(nombre);

  useEffect(() => {
    function alTeclear(e: KeyboardEvent) {
      if (!(e.ctrlKey || e.metaKey) || e.key.toLowerCase() !== "k" || usaCtrlK(e.target)) return;
      e.preventDefault();
      alAbrirBuscador();
    }
    document.addEventListener("keydown", alTeclear);
    return () => document.removeEventListener("keydown", alTeclear);
  }, [alAbrirBuscador]);

  return (
    <header className="silice-marco-barra">
      <Link to={RUTA_DE_INICIO} className="silice-marco-barra__marca">
        {logo ? (
          <img src={logo} alt="Sílice — Ir al inicio" className="silice-marco-barra__logo" />
        ) : (
          <span className="silice-marco-barra__nombre">Sílice</span>
        )}
      </Link>
      {/* Ocupa siempre el hueco flexible (vacía si no se sabe la carpeta) para que el buscador y la cuenta queden a la derecha. */}
      <span className="silice-marco-barra__carpeta">{carpeta ? `Carpeta activa: ${carpeta}` : ""}</span>
      <button
        type="button"
        className="silice-marco-barra__buscar"
        aria-keyshortcuts="Control+K"
        onClick={alAbrirBuscador}
      >
        <Search size={16} aria-hidden="true" />
        <span className="silice-marco-barra__buscar-texto">Buscar una obra, sección o pantalla… (Ctrl+K)</span>
      </button>
      {extra}
      <div className="silice-cuenta">
        <Link
          to={rutaDeCuenta("preferencias")}
          className="cds--header__action silice-cuenta__boton"
          aria-current={enLaCuenta ? "page" : undefined}
          aria-label={`Cuenta de ${nombre}`}
          title={nombre}
        >
          {letras ? (
            <span className="silice-cuenta__iniciales cds--type-label-01" aria-hidden="true">
              {letras}
            </span>
          ) : (
            <User size={16} className="silice-cuenta__persona" aria-hidden="true" />
          )}
          <span className="silice-cuenta__nombre cds--type-body-compact-01">{nombre}</span>
        </Link>
      </div>
    </header>
  );
}
