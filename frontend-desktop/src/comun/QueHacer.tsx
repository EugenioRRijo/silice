import { useId, useState } from "react";
import type { JSX } from "react";
import type { GuiaQueHacer } from "./catalogoQueHacer";

// «Qué hacer» de un hallazgo o de una alerta (B2, ficha-b2 §1.6 y D3): un botón que abre, a pedido, qué quiere decir y qué
// conviene revisar. Llega cerrado: la pantalla queda tranquila y la prueba de comprensión de las alertas mide si la persona
// entiende lo que ve, no si lee la guía. Es un disclosure con `aria-expanded` (guía `accessibility`: nada de `title`).
export function QueHacer({ guia }: { guia: GuiaQueHacer }): JSX.Element {
  const [abierto, setAbierto] = useState(false);
  const idCuerpo = useId();
  return (
    <div className="silice-quehacer">
      <button
        type="button"
        className="silice-quehacer__boton"
        aria-expanded={abierto}
        aria-controls={abierto ? idCuerpo : undefined}
        onClick={() => setAbierto((previo) => !previo)}
      >
        Qué hacer <span className="silice-oculto">{`con «${guia.titulo}»`}</span>
      </button>
      {abierto && (
        <div id={idCuerpo} className="silice-quehacer__cuerpo">
          {guia.generico && (
            <p className="silice-quehacer__nota cds--type-label-01">
              Guía general: esta regla todavía no tiene una guía propia.
            </p>
          )}
          <p className="cds--type-body-compact-01">{guia.significa}</p>
          <p className="cds--type-body-compact-01">{guia.que_hacer}</p>
        </div>
      )}
    </div>
  );
}
