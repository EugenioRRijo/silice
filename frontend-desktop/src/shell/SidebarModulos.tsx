import { useEffect, useId, useRef } from "react";
import type { JSX, KeyboardEvent } from "react";
import { Link } from "react-router";
import "./SidebarModulos.scss";
import { EnlaceSeguro, useClicSeguro } from "./EnlaceSeguro";
import type { EntradaNav } from "./navegacion";
import { PAGINAS, inicioDe, rutaDe, type ModuloDef, type ModuloId, type PaginaDef } from "./rutas";
import { ID_SIDEBAR, cerrarSidebar } from "./sidebar";

interface Props {
  // Modulos que la cuenta ve, en su orden.
  modulos: readonly ModuloDef[];
  actual: ModuloId | null;
  // Las areas del modulo abierto (las mismas de la barra): el sidebar las muestra cuando la barra no cabe.
  entradas: readonly EntradaNav[];
  // Administracion y Acerca de Silice, segun la cuenta: van al pie.
  fuera: readonly PaginaDef[];
  abierto: boolean;
  fijado: boolean;
  // Hay ancho para fijarlo (useFijadoPosible); si no, fijado se comporta como oculto.
  fijadoPosible: boolean;
  // Esc o clic en la capa: el armazon lo cierra y devuelve el foco a «Sílice».
  alCerrar: () => void;
  alFijar: (fijo: boolean) => void;
  // Quien tiene la sesion: la barra cede su nombre con la letra grande y el pie lo dice.
  nombre: string;
  // Registro de pantallas (el del armazon; en pruebas, el suyo): de aqui sale el inicio de cada modulo.
  paginas?: readonly PaginaDef[];
}

// Sidebar de modulos, estado 3 del diseno (2026-10-25-modulos-design.md §4 y §12.4): oculto por omision; abierto, va
// encima del contenido con una capa, bajo la barra, como dialogo modal con el foco atrapado; fijado (y con ancho), es una
// franja que empuja el contenido. Arriba los modulos; debajo, las areas del modulo abierto (solo se ven cuando la barra
// no cabe: lo decide shell.scss); al pie Administracion, Acerca, la sesion y «Fijar»/«Ocultar».
export function SidebarModulos(props: Props): JSX.Element | null {
  const fijadoVisible = props.fijado && props.fijadoPosible;
  const enCapa = props.abierto && !fijadoVisible;
  if (!enCapa && !fijadoVisible) return null;
  // Al pasar de capa a fijado (o al reves) cambia de dialogo a navegacion: se monta de nuevo.
  return <Contenido key={enCapa ? "capa" : "fijado"} {...props} enCapa={enCapa} />;
}

// Lo enfocable que de verdad se ve: las areas pueden estar ocultas por CSS (barra que si cabe).
function enfocables(caja: HTMLElement): HTMLElement[] {
  return Array.from(caja.querySelectorAll<HTMLElement>("a[href], button:not([disabled])")).filter((el) => {
    for (let nodo: HTMLElement | null = el; nodo && nodo !== caja; nodo = nodo.parentElement) {
      if (getComputedStyle(nodo).display === "none") return false;
    }
    return true;
  });
}

function Contenido({
  modulos,
  actual,
  entradas,
  fuera,
  fijadoPosible,
  alCerrar,
  alFijar,
  nombre,
  paginas = PAGINAS,
  enCapa,
}: Props & { enCapa: boolean }) {
  const base = useId();
  const caja = useRef<HTMLDivElement>(null);
  const moduloActual = modulos.find((m) => m.id === actual) ?? null;

  // En capa, el foco entra al modulo actual (o al primero). Fijado no le roba el foco a la pagina.
  useEffect(() => {
    if (!enCapa || !caja.current) return;
    const destino =
      caja.current.querySelector<HTMLElement>('.silice-sidebar__modulo[aria-current="page"]') ?? enfocables(caja.current)[0];
    destino?.focus();
  }, [enCapa]);

  function alTeclear(e: KeyboardEvent<HTMLElement>) {
    if (!enCapa || !caja.current) return;
    if (e.key === "Escape") {
      // Esc es de la capa: la cierra y no llega al oyente del armazon (que la abriria de nuevo).
      e.stopPropagation();
      alCerrar();
      return;
    }
    if (e.key !== "Tab") return;
    const lista = enfocables(caja.current);
    const primero = lista[0];
    const ultimo = lista[lista.length - 1];
    if (!primero || !ultimo) return;
    if (e.shiftKey && document.activeElement === primero) {
      e.preventDefault();
      ultimo.focus();
    } else if (!e.shiftKey && document.activeElement === ultimo) {
      e.preventDefault();
      primero.focus();
    }
  }

  const cuerpo = (
    <>
      <p id={`${base}-modulos`} className="silice-sidebar__rotulo cds--type-label-01">
        Módulos
      </p>
      <ul className="silice-sidebar__modulos" aria-labelledby={`${base}-modulos`}>
        {modulos.map((m) => (
          <li key={m.id}>
            <EnlaceModulo modulo={m} actual={m.id === actual} ruta={rutaDe(inicioDe(m.id, paginas))} />
          </li>
        ))}
      </ul>
      {moduloActual && entradas.length > 0 && (
        <div className="silice-sidebar__areas" role="group" aria-labelledby={`${base}-areas`}>
          <p id={`${base}-areas`} className="silice-sidebar__rotulo cds--type-label-01">
            Áreas de {moduloActual.titulo}
          </p>
          {entradas.map((e) =>
            e.tipo === "enlace" ? (
              // Un area de una sola pantalla es un enlace directo, sin rotulo que repita su nombre (como en la barra).
              <ul key={e.area} className="silice-sidebar__lista">
                <li>
                  <EnlacePantalla pagina={e.pagina} base={base} />
                </li>
              </ul>
            ) : (
              <div key={e.area} className="silice-sidebar__area">
                <p id={`${base}-area-${e.area}`} className="silice-sidebar__rotulo-area cds--type-label-01">
                  {e.titulo}
                </p>
                <ul className="silice-sidebar__lista" aria-labelledby={`${base}-area-${e.area}`}>
                  {e.grupos.flatMap((g) => g.paginas).map((p) => (
                    <li key={p.id}>
                      <EnlacePantalla pagina={p} base={base} />
                    </li>
                  ))}
                </ul>
              </div>
            ),
          )}
        </div>
      )}
      <div className="silice-sidebar__pie">
        {fuera.length > 0 && (
          <ul className="silice-sidebar__fuera">
            {fuera.map((p) => (
              <li key={p.id}>
                <EnlaceSeguro to={rutaDe(p)} className="silice-sidebar__enlace cds--type-body-compact-01" alNavegar={cerrarSidebar}>
                  {p.titulo}
                </EnlaceSeguro>
              </li>
            ))}
          </ul>
        )}
        <p className="silice-sidebar__sesion cds--type-helper-text-01">Sesión de {nombre}</p>
        {enCapa ? (
          fijadoPosible && (
            <button
              type="button"
              className="silice-sidebar__fijar cds--type-body-compact-01"
              onClick={() => alFijar(true)}
            >
              Fijar
            </button>
          )
        ) : (
          <button type="button" className="silice-sidebar__fijar cds--type-body-compact-01" onClick={() => alFijar(false)}>
            Ocultar
          </button>
        )}
      </div>
    </>
  );

  if (enCapa) {
    return (
      <>
        {/* La capa oscurece lo de detras (bajo la barra); un clic en ella cierra el sidebar. No es enfocable: Esc hace lo mismo. */}
        <div className="silice-sidebar__fondo" aria-hidden="true" onClick={alCerrar} />
        <div
          id={ID_SIDEBAR}
          ref={caja}
          role="dialog"
          aria-modal="true"
          aria-label="Módulos de Sílice"
          className="silice-sidebar"
          onKeyDown={alTeclear}
        >
          {cuerpo}
        </div>
      </>
    );
  }
  return (
    <nav id={ID_SIDEBAR} ref={caja} aria-label="Módulos" className="silice-sidebar silice-sidebar--fijado">
      {cuerpo}
    </nav>
  );
}

// El renglon de un modulo: lleva al inicio del modulo; el actual se marca aunque la pantalla abierta sea otra del modulo.
function EnlaceModulo({ modulo, actual, ruta }: { modulo: ModuloDef; actual: boolean; ruta: string }) {
  const id = useId();
  const clic = useClicSeguro(ruta, cerrarSidebar);
  return (
    <Link
      to={ruta}
      className="silice-sidebar__modulo"
      aria-current={actual ? "page" : undefined}
      aria-labelledby={`${id}-n`}
      aria-describedby={`${id}-a`}
      onClick={clic}
    >
      <span id={`${id}-n`} className="silice-sidebar__nombre cds--type-heading-03">
        {modulo.titulo}
      </span>
      <span id={`${id}-a`} className="silice-sidebar__ayuda cds--type-helper-text-01">
        {modulo.enUnaLinea}
      </span>
    </Link>
  );
}

function EnlacePantalla({ pagina, base }: { pagina: PaginaDef; base: string }) {
  const idTitulo = `${base}-${pagina.id}-t`;
  const idAyuda = `${base}-${pagina.id}-a`;
  return (
    <EnlaceSeguro
      to={rutaDe(pagina)}
      className="silice-sidebar__pantalla"
      aria-labelledby={idTitulo}
      aria-describedby={idAyuda}
      alNavegar={cerrarSidebar}
    >
      <span id={idTitulo} className="silice-sidebar__titulo cds--type-body-compact-01">
        {pagina.titulo}
      </span>
      <span id={idAyuda} className="silice-sidebar__ayuda cds--type-helper-text-01">
        {pagina.enUnaLinea}
      </span>
    </EnlaceSeguro>
  );
}
