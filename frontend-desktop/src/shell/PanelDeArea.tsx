import { useEffect, useId, useLayoutEffect, useRef } from "react";
import type { KeyboardEvent } from "react";
import { EnlaceSeguro } from "./EnlaceSeguro";
import type { GrupoNav } from "./navegacion";
import { rutaDe } from "./rutas";

interface Props {
  // Id de la region: lo usa el `aria-controls` del boton del area.
  id: string;
  // Nombre del area: nombre accesible de la region.
  titulo: string;
  grupos: readonly GrupoNav[];
  // Se llama al elegir una pantalla (la barra cierra el panel); con trabajo sin guardar, solo si la persona sale.
  alElegir: () => void;
}

// Margen minimo entre el panel y el borde de la ventana.
const MARGEN_PX = 8;

// Panel de un area de la barra superior: patron «disclosure» de navegacion (enlaces seguros: preguntan antes de perder
// trabajo), no un menu. Cada pantalla lleva su
// titulo (nombre accesible) y su linea de ayuda (descripcion accesible). Al abrirse, el foco va a la primera entrada; las
// flechas, Inicio y Fin recorren las entradas y se detienen en la primera y la ultima, sin vuelta, como en la APG (Tab
// tambien, en el orden natural).
export function PanelDeArea({ id, titulo, grupos, alElegir }: Props) {
  const base = useId();
  const caja = useRef<HTMLDivElement>(null);

  // Alineado bajo su boton, pero sin salirse de la ventana: si el borde derecho sobra, el panel se corre a la izquierda.
  // Se mide con `clientWidth` (el ancho util, sin la barra de desplazamiento; `100vw` la incluye) y se vuelve a medir al
  // redimensionar la ventana.
  useLayoutEffect(() => {
    const el = caja.current;
    if (!el) return;
    function encajar() {
      if (!el) return;
      const ancho = document.documentElement.clientWidth;
      el.style.maxInlineSize = `min(40rem, ${ancho - 2 * MARGEN_PX}px)`;
      el.style.insetInlineStart = "";
      const exceso = el.getBoundingClientRect().right - (ancho - MARGEN_PX);
      if (exceso > 0) el.style.insetInlineStart = `${-exceso}px`;
    }
    encajar();
    window.addEventListener("resize", encajar);
    return () => window.removeEventListener("resize", encajar);
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
      e.key === "Home" ? 0 : e.key === "End" ? n - 1 : e.key === "ArrowDown" ? Math.min(i + 1, n - 1) : Math.max(i - 1, 0);
    enlaces[siguiente].focus();
  }

  return (
    // tabIndex -1: un clic en una zona no enfocable del panel (subtitulo, relleno, hueco entre columnas) le da el foco a la
    // region en vez de al body, asi el foco no sale de la navegacion y el panel no se cierra. No entra en el orden de Tab.
    <div
      id={id}
      ref={caja}
      role="region"
      aria-label={titulo}
      tabIndex={-1}
      className="silice-panel-area"
      onKeyDown={alTeclear}
    >
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
                    <EnlaceSeguro
                      to={rutaDe(p)}
                      className="silice-panel-area__enlace"
                      aria-labelledby={idTitulo}
                      aria-describedby={idAyuda}
                      alNavegar={alElegir}
                    >
                      <span id={idTitulo} className="silice-panel-area__titulo cds--type-body-compact-01">
                        {p.titulo}
                      </span>
                      <span id={idAyuda} className="silice-panel-area__ayuda cds--type-helper-text-01">
                        {p.enUnaLinea}
                      </span>
                    </EnlaceSeguro>
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
