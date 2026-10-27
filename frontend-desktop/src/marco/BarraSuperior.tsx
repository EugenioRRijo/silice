import { Search } from "@carbon/icons-react";
import { useEffect } from "react";
import type { ReactNode } from "react";
import { TamanoLetra } from "../comun/TamanoLetra";
import { MenuCuenta } from "../shell/MenuCuenta";
import "./BarraSuperior.scss";
import { Migas, type Miga } from "./Migas";
import { useTema } from "./useTema";

interface Props {
  migas: Miga[];
  alAbrirBuscador: () => void;
  nombre: string;
  alSalir: () => void;
  // Lo que el marco pone antes del tamaño de letra (la marca de la demostración, «Recorrido»).
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

// Barra superior del marco nuevo: marca, migas, buscador (Ctrl+K), tamaño de letra y cuenta. La monta marco/Marco.
export function BarraSuperior({ migas, alAbrirBuscador, nombre, alSalir, extra }: Props) {
  const { logo } = useTema();

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
      {logo ? (
        <img src={logo} alt="Logo de la empresa" className="silice-marco-barra__logo" />
      ) : (
        <span className="silice-marco-barra__nombre">Sílice</span>
      )}
      <Migas migas={migas} />
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
      <TamanoLetra />
      <MenuCuenta nombre={nombre} alSalir={alSalir} />
    </header>
  );
}
