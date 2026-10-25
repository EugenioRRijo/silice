import { useEffect, useId, useLayoutEffect, useRef } from "react";
import type { KeyboardEvent } from "react";
import { NavLink } from "react-router";
import type { GrupoNav } from "./navegacion";
import { rutaDe } from "./rutas";

interface Props {
  // Id de la region: lo usa el `aria-controls` del boton del area.
  id: string;
  // Nombre del area: nombre accesible de la region.
  titulo: string;
  grupos: readonly GrupoNav[];
  // Se llama al elegir una pantalla (la barra cierra el panel).
  alElegir: () => void;
}

// Margen minimo entre el panel y el borde de la ventana.
const MARGEN_PX = 8;

// Panel de un area de la barra superior: patron «disclosure» de navegacion (enlaces), no un menu. Cada pantalla lleva su
// titulo (nombre accesible) y su linea de ayuda (descripcion accesible). Al abrirse, el foco va a la primera entrada; las
// flechas, Inicio y Fin recorren las entradas (Tab tambien, en el orden natural).
export function PanelDeArea({ id, titulo, grupos, alElegir }: Props) {
  const base = useId();
  const caja = useRef<HTMLDivElement>(null);

  // Alineado bajo su boton, pero sin salirse de la ventana: si el borde derecho sobra, el panel se corre a la izquierda.
  useLayoutEffect(() => {
    const el = caja.current;
    if (!el) return;
    const exceso = el.getBoundingClientRect().right - (document.documentElement.clientWidth - MARGEN_PX);
    if (exceso > 0) el.style.insetInlineStart = `${-exceso}px`;
  }, []);

  useEffect(() => {
    caja.current?.querySelector<HTMLAnchorElement>("a")?.focus();
  }, []);

  function alTeclear(e: KeyboardEvent<HTMLDivElement>) {
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) return;
    const enlaces = Array.from(caja.current?.querySelectorAll<HTMLAnchorElement>("a") ?? []);
    if (enlaces.length === 0) return;
    e.preventDefault();
    const i = enlaces.indexOf(document.activeElement as HTMLAnchorElement);
    const n = enlaces.length;
    const siguiente =
      e.key === "Home" ? 0 : e.key === "End" ? n - 1 : e.key === "ArrowDown" ? (i + 1) % n : (i - 1 + n) % n;
    enlaces[siguiente].focus();
  }

  return (
    <div id={id} ref={caja} role="region" aria-label={titulo} className="silice-panel-area" onKeyDown={alTeclear}>
      {grupos.map((g, ig) => {
        const idGrupo = `${base}-g${ig}`;
        return (
          <div key={g.titulo ?? ig} className="silice-panel-area__grupo">
            {g.titulo && (
              <p id={idGrupo} className="silice-panel-area__subtitulo cds--type-label-01">
                {g.titulo}
              </p>
            )}
            <ul className="silice-panel-area__lista" aria-labelledby={g.titulo ? idGrupo : undefined}>
              {g.paginas.map((p) => {
                const idTitulo = `${base}-${p.id}-t`;
                const idAyuda = `${base}-${p.id}-a`;
                return (
                  <li key={p.id}>
                    <NavLink
                      to={rutaDe(p)}
                      className="silice-panel-area__enlace"
                      aria-labelledby={idTitulo}
                      aria-describedby={idAyuda}
                      onClick={alElegir}
                    >
                      <span id={idTitulo} className="silice-panel-area__titulo cds--type-body-compact-01">
                        {p.titulo}
                      </span>
                      <span id={idAyuda} className="silice-panel-area__ayuda cds--type-helper-text-01">
                        {p.enUnaLinea}
                      </span>
                    </NavLink>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </div>
  );
}
