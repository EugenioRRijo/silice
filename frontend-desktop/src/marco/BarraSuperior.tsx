import { ArrowLeft, Search, User } from "@carbon/icons-react";
import { useEffect } from "react";
import type { ReactNode } from "react";
import { Link, useLocation } from "react-router";
import { iniciales } from "../shell/iniciales";
import "../shell/MenuCuenta.scss";
import "./BarraSuperior.scss";
import { rutaDeCuenta } from "./espacios";
import type { EspacioId } from "./espacios";
import type { EspacioOfrecido } from "./oferta";
import { RUTA_DE_INICIO, RUTA_DE_VISTA_GENERAL } from "./secciones";
import { useTema } from "./useTema";

interface Props {
  alAbrirBuscador: () => void;
  nombre: string;
  // El nombre de la carpeta abierta ahora, o null si todavía no se sabe (no se pinta un rótulo vacío).
  carpeta: string | null;
  // Dónde se está dentro de la carpeta (ej. «Inicio / Vista general» u «Obras / Drenaje de la clínica»): texto, no enlaces.
  migaContextual?: string | null;
  // Ventana dedicada a pantalla completa para Auditoria, Precios o Produccion.
  enVentanaDedicada?: boolean;
  espacioActivo?: EspacioId | null;
  espacios?: readonly EspacioOfrecido[];
  // Lo que el marco pone antes de la cuenta (la marca de la demostracion, «Recorrido»).
  extra?: ReactNode;
}

const ETIQUETA_MODO: Record<EspacioId, string> = {
  auditoria: "Auditoría",
  precios: "Precios y catálogo",
  produccion: "Producción",
};

// Un campo donde Ctrl+K ya significa otra cosa (texto largo o contenido editable, tambien «plaintext-only»): ahi no se abre el
// buscador. `closest` incluye al propio destino.
function usaCtrlK(destino: EventTarget | null): boolean {
  return (
    destino instanceof HTMLElement &&
    (destino instanceof HTMLTextAreaElement || destino.closest('[contenteditable]:not([contenteditable="false"])') !== null)
  );
}

// Barra superior del marco (plan F6, T6; diseño visual §4): la marca, que lleva a la ruta índice; la carpeta activa y, fuera
// de la ventana dedicada, el contexto de texto; el buscador (Ctrl+K); y la persona, que es un enlace a la Cuenta. Sin el
// tamaño de letra, que vive solo en la Cuenta (decisión de Eugenio, 2026-11-04). En Auditoría, Precios y Producción
// (ventana dedicada) lleva «Volver a obras» y el selector de las tres herramientas. La monta marco/Marco.
export function BarraSuperior({
  alAbrirBuscador,
  nombre,
  carpeta,
  migaContextual = null,
  enVentanaDedicada = false,
  espacioActivo = null,
  espacios = [],
  extra,
}: Props) {
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
    <header className={`silice-marco-barra${enVentanaDedicada ? " silice-marco-barra--dedicada" : ""}`}>
      <div className="silice-marco-barra__izq">
        {enVentanaDedicada && (
          <Link to={RUTA_DE_VISTA_GENERAL} className="silice-marco-barra__volver">
            <ArrowLeft size={16} aria-hidden="true" />
            <span>Volver a obras</span>
          </Link>
        )}
        <Link to={RUTA_DE_INICIO} className="silice-marco-barra__marca">
          {logo ? (
            <img src={logo} alt="Sílice — Ir al inicio" className="silice-marco-barra__logo" />
          ) : (
            <>
              <span className="silice-marco-barra__sello" aria-hidden="true">
                S
              </span>
              <span className="silice-marco-barra__nombre">Sílice</span>
            </>
          )}
        </Link>
        {/* Auditoría, Precios y Producción trabajan con la carpeta abierta: se dice también en la ventana dedicada. */}
        {carpeta && (
          <span className="silice-marco-barra__carpeta" title={`Carpeta activa: ${carpeta}`}>
            <span className="silice-marco-barra__carpeta-rotulo">{"Carpeta activa: "}</span>
            {carpeta}
          </span>
        )}
        {!enVentanaDedicada && (
          <span className="silice-marco-barra__contexto">
            {migaContextual ? (
              <>
                <span className="silice-marco-barra__barra-sep" aria-hidden="true">
                  /
                </span>
                <span className="silice-marco-barra__contexto-texto">{migaContextual}</span>
              </>
            ) : (
              ""
            )}
          </span>
        )}
      </div>

      {enVentanaDedicada && espacios.length > 0 ? (
        <nav aria-label="Selector de herramientas dedicadas" className="silice-marco-barra__modos">
          {espacios.map((e) => (
            <Link
              key={e.id}
              to={e.ruta}
              aria-current={espacioActivo === e.id ? "page" : undefined}
              className="silice-marco-barra__modo"
            >
              {ETIQUETA_MODO[e.id]}
            </Link>
          ))}
        </nav>
      ) : (
        <button
          type="button"
          className="silice-marco-barra__buscar"
          aria-keyshortcuts="Control+K"
          onClick={alAbrirBuscador}
        >
          <Search size={16} aria-hidden="true" />
          <span className="silice-marco-barra__buscar-texto">Buscar una obra, sección o pantalla… (Ctrl+K)</span>
        </button>
      )}

      <div className="silice-marco-barra__der">
        {enVentanaDedicada && (
          <button
            type="button"
            className="silice-marco-barra__buscar silice-marco-barra__buscar--compacto"
            aria-keyshortcuts="Control+K"
            onClick={alAbrirBuscador}
          >
            <Search size={16} aria-hidden="true" />
            <span className="silice-marco-barra__buscar-texto">Buscar una obra, sección o pantalla… (Ctrl+K)</span>
          </button>
        )}
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
      </div>
    </header>
  );
}
