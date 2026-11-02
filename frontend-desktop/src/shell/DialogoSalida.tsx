import { Button } from "@carbon/react";
import { useEffect, useId, useRef } from "react";
import type { JSX, KeyboardEvent } from "react";
import "./DialogoSalida.scss";
import { PAGINAS, paginaPorId, type PaginaDef } from "./rutas";
import { responderSalida, unirConY, useSalidaPendiente, type SalidaPendiente } from "./salida";
import { useAtraparFoco } from "./useAtraparFoco";

interface Props {
  // Registro de donde salen los titulos de las pantallas sucias (el del armazon; en pruebas, el suyo).
  paginas?: readonly PaginaDef[];
}

// «Cambios sin guardar» (diseno de modulos §4 y §12.5). Dialogo propio, sin el Modal de Carbon (como el de carpetas,
// BCP-5 §4.7): modal, foco inicial en «Quedarme» (la opcion que no pierde nada), Tab atrapado y Esc = «Quedarme».
export function DialogoSalida({ paginas = PAGINAS }: Props): JSX.Element | null {
  const pendiente = useSalidaPendiente();
  if (!pendiente) return null;
  return <Caja key={pendiente.numero} pendiente={pendiente} paginas={paginas} />;
}

function Caja({ pendiente, paginas }: { pendiente: SalidaPendiente; paginas: readonly PaginaDef[] }) {
  const base = useId();
  const caja = useRef<HTMLDivElement>(null);
  const quedarme = useRef<HTMLButtonElement>(null);
  // Lo que tenia el foco al preguntar (el enlace que se eligio): «Quedarme» lo devuelve ahi.
  const previo = useRef<Element | null>(null);
  const atrapar = useAtraparFoco(caja);

  useEffect(() => {
    previo.current = document.activeElement;
    quedarme.current?.focus();
  }, []);

  const nombres = [
    ...pendiente.pantallas.map((id) => paginaPorId(id, paginas)?.titulo ?? paginaPorId(id)?.titulo ?? id),
    ...pendiente.extras,
  ];
  const carpeta = pendiente.motivo === "carpeta";
  const consecuencia =
    pendiente.consecuencia ?? (carpeta ? "Si cambia de carpeta, se perderán." : "Si sale de esta pantalla, se perderán.");

  function quedarse() {
    const anterior = previo.current;
    responderSalida(false);
    // Si lo que tenia el foco ya no esta (un panel de area que se cerro), el foco va al contenido.
    if (anterior instanceof HTMLElement && anterior.isConnected) anterior.focus();
    else document.getElementById("contenido")?.focus();
  }

  function alTeclear(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key === "Escape") {
      // Esc es de este dialogo: ni el sidebar ni nada de detras se entera.
      e.preventDefault();
      e.stopPropagation();
      quedarse();
      return;
    }
    atrapar(e);
  }

  return (
    <div className="silice-salida__fondo">
      <div
        ref={caja}
        role="dialog"
        aria-modal="true"
        aria-labelledby={`${base}-titulo`}
        aria-describedby={`${base}-texto`}
        tabIndex={-1}
        className="silice-salida"
        onKeyDown={alTeclear}
      >
        <h2 id={`${base}-titulo`} className="silice-salida__titulo cds--type-heading-compact-02">
          Cambios sin guardar
        </h2>
        <p id={`${base}-texto`} className="silice-salida__texto cds--type-body-compact-01">
          Tiene cambios sin guardar en {unirConY(nombres)}. {consecuencia}
        </p>
        <div className="silice-salida__acciones">
          <Button ref={quedarme} kind="secondary" onClick={quedarse}>
            Quedarme
          </Button>
          <Button kind="danger" onClick={() => responderSalida(true)}>
            {pendiente.motivo === "salir" ? "Salir y descartar" : "Cambiar y descartar"}
          </Button>
        </div>
      </div>
    </div>
  );
}
