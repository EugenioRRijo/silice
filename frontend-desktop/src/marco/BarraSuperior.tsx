import { Add, Search, User } from "@carbon/icons-react";
import { Button } from "@carbon/react";
import { useEffect } from "react";
import type { ReactNode } from "react";
import { Link, useLocation } from "react-router";
import { iniciales } from "../shell/iniciales";
import "../shell/MenuCuenta.scss";
import "./BarraSuperior.scss";
import { rutaDeCuenta } from "./espacios";
import type { EspacioId } from "./espacios";
import { abrirNuevaObra } from "./nuevaObra";
import type { EspacioOfrecido } from "./oferta";
import { RUTA_DE_INICIO } from "./secciones";
import { useTema } from "./useTema";

interface Props {
  alAbrirBuscador: () => void;
  nombre: string;
  // El nombre de la carpeta abierta ahora, o null si todavía no se sabe (no se pinta un rótulo vacío).
  carpeta: string | null;
  // Dónde se está dentro de la carpeta (ej. «Inicio / Vista general» u «Obras / Drenaje de la clínica»): texto, no enlaces.
  migaContextual?: string | null;
  // Ventana dedicada a pantalla completa para Auditoria, Precios o Produccion: sin el contexto de texto (lo dice el espacio).
  enVentanaDedicada?: boolean;
  // Los pasa el marco, pero la barra de arriba ya no los pinta (los espacios viven en la barra lateral).
  espacioActivo?: EspacioId | null;
  espacios?: readonly EspacioOfrecido[];
  // Lo que el marco pone antes de la cuenta (la marca de la demostracion, «Recorrido»).
  extra?: ReactNode;
}

// Un campo donde Ctrl+K ya significa otra cosa (texto largo o contenido editable, tambien «plaintext-only»): ahi no se abre el
// buscador. `closest` incluye al propio destino.
function usaCtrlK(destino: EventTarget | null): boolean {
  return (
    destino instanceof HTMLElement &&
    (destino instanceof HTMLTextAreaElement || destino.closest('[contenteditable]:not([contenteditable="false"])') !== null)
  );
}

// «Nueva obra» es kind="tertiary" (el amarillo lo da silice-boton-nueva-obra): el botón principal de la pantalla es otro (hay pruebas que cuentan .cds--btn--primary).
// Barra de arriba, franja global fina (plan F6, T6; lote C3 de la reestructuración, cara «Papel y resaltador»): la marca,
// que lleva a la ruta índice; la carpeta activa y, fuera de la ventana dedicada, el contexto de texto; «Nueva obra»; el
// buscador (Ctrl+K); y la persona, que es un enlace a la Cuenta. Sin el tamaño de letra, que vive solo en la Cuenta
// (decisión de Eugenio, 2026-11-04). Los espacios de la empresa viven en la barra lateral: `espacioActivo` y `espacios` los
// sigue pasando el marco, pero esta barra ya no los pinta (tampoco «Volver a obras» ni el selector de la cara anterior).
// La monta marco/Marco.
export function BarraSuperior({
  alAbrirBuscador,
  nombre,
  carpeta,
  migaContextual = null,
  enVentanaDedicada = false,
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

      <div className="silice-marco-barra__der">
        {/* La ranura recibe lo que sobra de la barra y mide su propio ancho: si caben «Nueva obra» y el texto completo del
            buscador, el buscador lo muestra; si no, queda en su ícono (consulta de contenedor en BarraSuperior.scss).
            Nunca corta el texto. «Nueva obra» va dentro para que las dos piezas queden pegadas a la derecha. */}
        <div className="silice-marco-barra__buscar-ranura">
          <Button
            type="button"
            kind="tertiary"
            size="sm"
            renderIcon={Add}
            className="silice-boton-nueva-obra"
            onClick={abrirNuevaObra}
          >
            Nueva obra
          </Button>
          <button
            type="button"
            className="silice-marco-barra__buscar"
            aria-keyshortcuts="Control+K"
            onClick={alAbrirBuscador}
          >
            <Search size={16} aria-hidden="true" />
            <span className="silice-marco-barra__buscar-texto">Buscar una obra, sección o pantalla… (Ctrl+K)</span>
          </button>
        </div>
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
