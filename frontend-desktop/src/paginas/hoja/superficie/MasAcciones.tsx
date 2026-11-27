import { ChevronDown } from "@carbon/icons-react";
import { Button } from "@carbon/react";
import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import type { FocusEvent, JSX, KeyboardEvent, ReactNode } from "react";
import { Link } from "react-router";
import { Dialogo } from "../../../comun/Dialogo";

// «Más acciones del presupuesto» (B1-3, ficha-b1 §1.6): el menú de lo ocasional (subtotales por frente, Excel, PDF,
// archivos, espacio/plan/ajustes y descartar los cambios) para que la cabecera fija no pase del tope de decisiones a la vista.
//
// Es un menú, no un diálogo: lleva el atributo `popover` (guía `dialog`, Regla 3), no `<dialog>`. Se usa `popover="manual"`
// y no `auto` a propósito: con `auto`, pulsar el botón que lo abre cuenta como «clic fuera», lo cierra y el `onClick` lo
// volvería a abrir. Aquí el cierre lo decide este componente: Esc (y el foco vuelve al botón), clic fuera y salir con Tab.
// Sus opciones (`children`) están siempre montadas aunque el menú esté cerrado: una descarga que falla deja su aviso junto a
// su botón y no se pierde al cerrar. Cada opción decide si cierra; «Descartar» sí, porque abre su confirmación.
//
// «Descartar los cambios» (D7) es destructivo: `Dialogo` con `destructivo` pone el foco inicial en «Cancelar» (guía `dialog`:
// «autofocus on the safe action»). Al cancelar, el foco vuelve al botón del menú, que es lo que sigue en pantalla.
interface Props {
  // Cambios sin guardar del borrador; sin cambios (o sin `alDescartar`) no se ofrece descartar.
  cambios: number;
  alDescartar?: () => void;
  // Abre el panel «Subtotales por frente».
  alVerFrentes?: () => void;
  // Enlace o acción para «Traer un plano o cómputo» (sección Archivos de la obra).
  rutaArchivos?: string;
  alIrAArchivos?: () => void;
  // Enlace a «Espacio, plan y ajustes» (subvista de pestañas).
  rutaPestanas?: string;
  // Las demás opciones del menú (hoy «Descargar Excel» y «PDF»).
  children?: ReactNode;
}

export function MasAcciones({
  cambios,
  alDescartar,
  alVerFrentes,
  rutaArchivos,
  alIrAArchivos,
  rutaPestanas,
  children,
}: Props): JSX.Element {
  const [abierto, setAbierto] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  const raiz = useRef<HTMLDivElement>(null);
  const boton = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLUListElement>(null);
  const devolverFoco = useRef(false);
  const idMenu = useId();

  // El `popover` nativo muestra y oculta el menú en la capa superior. jsdom no lo implementa: ahí manda `hidden`.
  useLayoutEffect(() => {
    const el = menu.current;
    if (el === null) return;
    try {
      if (abierto) el.showPopover?.();
      else el.hidePopover?.();
    } catch {
      // Ya estaba en ese estado: nada que hacer.
    }
  }, [abierto]);

  useEffect(() => {
    if (!abierto) return;
    const alPulsarFuera = (evento: PointerEvent) => {
      if (evento.target instanceof Node && raiz.current?.contains(evento.target) !== true) setAbierto(false);
    };
    document.addEventListener("pointerdown", alPulsarFuera);
    return () => document.removeEventListener("pointerdown", alPulsarFuera);
  }, [abierto]);

  // Al cerrar la confirmación sin descartar, el foco vuelve al botón del menú. Corre después de que `Dialogo` cierra el suyo.
  useEffect(() => {
    if (confirmando || !devolverFoco.current) return;
    devolverFoco.current = false;
    boton.current?.focus();
  }, [confirmando]);

  const alTeclear = (evento: KeyboardEvent) => {
    if (evento.key !== "Escape" || !abierto) return;
    evento.stopPropagation();
    setAbierto(false);
    boton.current?.focus();
  };

  const alSalirElFoco = (evento: FocusEvent) => {
    const destino = evento.relatedTarget;
    if (destino instanceof Node && raiz.current?.contains(destino) === true) return;
    if (destino === null) return;
    setAbierto(false);
  };

  const puedeDescartar = alDescartar !== undefined && cambios > 0;
  const cancelar = () => {
    devolverFoco.current = true;
    setConfirmando(false);
  };

  return (
    <div ref={raiz} className="silice-hoja__mas-acciones" onKeyDown={alTeclear} onBlur={alSalirElFoco}>
      <Button
        ref={boton}
        kind="tertiary"
        size="md"
        renderIcon={ChevronDown}
        aria-label="Más acciones del presupuesto"
        aria-expanded={abierto}
        aria-controls={idMenu}
        onClick={() => setAbierto((v) => !v)}
      >
        Más acciones
      </Button>
      <ul ref={menu} id={idMenu} popover="manual" hidden={!abierto} className="silice-hoja__mas-acciones-menu">
        {alVerFrentes !== undefined && (
          <li>
            <Button
              kind="ghost"
              size="md"
              onClick={() => {
                setAbierto(false);
                // Devuelve el foco al botón antes de abrir el panel para que cerrar el panel lo regrese allí.
                boton.current?.focus();
                alVerFrentes();
              }}
            >
              Subtotales por frente
            </Button>
          </li>
        )}
        {children !== undefined && children !== null && <li>{children}</li>}
        {rutaArchivos !== undefined ? (
          <li>
            <Link className="cds--btn cds--btn--ghost cds--btn--md" to={rutaArchivos} onClick={() => setAbierto(false)}>
              Traer un plano o cómputo
            </Link>
          </li>
        ) : alIrAArchivos !== undefined ? (
          <li>
            <Button
              kind="ghost"
              size="md"
              onClick={() => {
                setAbierto(false);
                alIrAArchivos();
              }}
            >
              Traer un plano o cómputo
            </Button>
          </li>
        ) : null}
        {rutaPestanas !== undefined && (
          <li>
            <Link className="cds--btn cds--btn--ghost cds--btn--md" to={rutaPestanas} onClick={() => setAbierto(false)}>
              Espacio, plan y ajustes
            </Link>
          </li>
        )}
        {puedeDescartar && (
          <li>
            <Button
              kind="danger--ghost"
              size="md"
              onClick={() => {
                setAbierto(false);
                setConfirmando(true);
              }}
            >
              Descartar cambios
            </Button>
          </li>
        )}
      </ul>
      <Dialogo
        abierto={confirmando}
        titulo="Descartar cambios"
        alCerrar={cancelar}
        destructivo
        pie={
          <>
            <Button kind="secondary" size="md" onClick={cancelar}>
              Cancelar
            </Button>
            <Button
              kind="danger"
              size="md"
              onClick={() => {
                setConfirmando(false);
                alDescartar?.();
              }}
            >
              Descartar y abrir de nuevo
            </Button>
          </>
        }
      >
        <p className="cds--type-body-compact-01">
          {cambios === 1
            ? "¿Descartar el cambio sin guardar? No se puede recuperar."
            : `¿Descartar los ${cambios} cambios sin guardar? No se pueden recuperar.`}
        </p>
      </Dialogo>
    </div>
  );
}
