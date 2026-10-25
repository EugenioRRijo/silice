import "./MenuEnCapa.scss";
import { HeaderSideNavItems, SideNav, SideNavItems, SideNavLink } from "@carbon/react";
import type { KeyboardEvent } from "react";
import { NavLink } from "react-router";
import type { EntradaNav } from "./navegacion";
import { rutaDe, type PaginaDef } from "./rutas";

interface Props {
  entradas: readonly EntradaNav[];
  abierto: boolean;
  alCerrar: () => void;
  // Quien tiene la sesion: en la capa la cabecera no da para su nombre y el menu lo dice al pie.
  nombre?: string;
}

// tabIndex 0 a proposito: Carbon lo pone en -1 si el menu no esta "expandido"; cerrado, el propio SideNav lo marca inert.
function Enlace({ pagina, alCerrar }: { pagina: PaginaDef; alCerrar: () => void }) {
  const idAyuda = `capa-ayuda-${pagina.id}`;
  return (
    <SideNavLink as={NavLink} to={rutaDe(pagina)} onClick={alCerrar} tabIndex={0} aria-describedby={idAyuda}>
      <span className="silice-capa__enlace">
        <span className="silice-capa__nombre">{pagina.titulo}</span>
        <span id={idAyuda} className="silice-capa__ayuda cds--type-helper-text-01">
          {pagina.enUnaLinea}
        </span>
      </span>
    </SideNavLink>
  );
}

interface GrupoVista {
  subtitulo: string | null;
  paginas: readonly PaginaDef[];
}

function Area({ id, rotulo, grupos, alCerrar }: { id: string; rotulo: string; grupos: readonly GrupoVista[]; alCerrar: () => void }) {
  const idRotulo = `capa-rotulo-${id}`;
  return (
    <li className="silice-capa__grupo">
      <div id={idRotulo} className="silice-capa__rotulo cds--type-label-01">
        {rotulo}
      </div>
      {grupos.map((g, i) => {
        const idSub = `capa-sub-${id}-${i}`;
        return (
          <div key={i}>
            {g.subtitulo && (
              <div id={idSub} className="silice-capa__subtitulo cds--type-helper-text-01">
                {g.subtitulo}
              </div>
            )}
            <ul aria-labelledby={g.subtitulo ? idSub : idRotulo} className="silice-capa__lista">
              {g.paginas.map((p) => (
                <Enlace key={p.id} pagina={p} alCerrar={alCerrar} />
              ))}
            </ul>
          </div>
        );
      })}
    </li>
  );
}

// Menu en capa (Carbon SideNav) para cuando la barra superior no cabe: ancho estrecho o letra grande. Las mismas entradas
// de la barra, cada area como un grupo con su rotulo de texto (no encabezados: el unico h1 es el de la pagina).
export function MenuEnCapa({ entradas, abierto, alCerrar, nombre }: Props) {
  function alTeclear(e: KeyboardEvent<HTMLElement>) {
    if (e.key === "Escape") {
      e.stopPropagation();
      alCerrar();
    }
  }
  return (
    <SideNav
      aria-label="Menú principal (capa)"
      className="silice-capa"
      expanded={abierto}
      isPersistent={false}
      onSideNavBlur={alCerrar}
      onOverlayClick={alCerrar}
      onKeyDown={alTeclear}
    >
      <SideNavItems>
        <HeaderSideNavItems>
          {entradas.map((e) =>
            e.tipo === "enlace" ? (
              // Un area de una sola pantalla es un enlace directo (diseno §5.1): sin rotulo que repita su nombre.
              <li key={e.area} className="silice-capa__grupo">
                <ul className="silice-capa__lista">
                  <Enlace pagina={e.pagina} alCerrar={alCerrar} />
                </ul>
              </li>
            ) : (
              <Area
                key={e.area}
                id={e.area}
                rotulo={e.titulo}
                grupos={e.grupos.map((g) => ({ subtitulo: g.titulo, paginas: g.paginas }))}
                alCerrar={alCerrar}
              />
            ),
          )}
        </HeaderSideNavItems>
        {nombre && <li className="silice-capa__sesion cds--type-helper-text-01">Sesión de {nombre}</li>}
      </SideNavItems>
    </SideNav>
  );
}
