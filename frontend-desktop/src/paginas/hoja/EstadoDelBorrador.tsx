import { Button } from "@carbon/react";
import { useState } from "react";
import type { ReactNode } from "react";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { textoDeCambios } from "./logica";
import type { BorradorAbierto } from "./logica";

// La línea de estado del Presupuesto (decisión de Eugenio, 2026-11-05: cabecera compacta). Una sola región, «Estado del
// borrador», con la versión y los cambios sin guardar, la aprobación de la versión (la pone `FranjaDelPresupuesto`, que es
// quien la lee) y el total. Ya no lleva título propio: la región conserva el nombre para quien lee con lector de pantalla.
// «Descartar cambios» (fantasma) y su confirmación solo salen cuando hay cambios; «Guardar versión…» es del paso de la franja.
interface Props {
  borrador: BorradorAbierto;
  alDescartar: () => void;
  // F4 2b: sin permiso de edición (o con un borrador de solo lectura) no se ofrece descartar.
  puedeEditar: boolean;
  // La aprobación de la versión abierta (`AprobacionDeVersion`), entre los cambios y el total. Nada si no hay versión.
  aprobacion?: ReactNode;
}

export function EstadoDelBorrador({ borrador, alDescartar, puedeEditar, aprobacion }: Props) {
  const { base, resumen } = borrador;
  const [confirmando, setConfirmando] = useState(false);
  return (
    <section className="silice-hoja__estado" role="region" aria-label="Estado del borrador">
      <p className="silice-hoja__estado-version cds--type-body-compact-01">
        {base.version === null ? "Borrador en blanco" : `Versión ${base.version}`} · {textoDeCambios(resumen.cambios)}
      </p>
      {aprobacion}
      <p className="silice-hoja__total cds--type-heading-compact-02" aria-live="polite" title={formatoEsVe(resumen.total.exacto)}>
        Total {formatoEsVe(resumen.total.texto)} {resumen.moneda}
        <span className="cds--visually-hidden"> Valor exacto {formatoEsVe(resumen.total.exacto)}</span>
      </p>
      {puedeEditar && resumen.cambios > 0 && !confirmando && (
        <Button kind="ghost" size="sm" onClick={() => setConfirmando(true)}>
          Descartar cambios
        </Button>
      )}
      {resumen.version_mas_nueva !== null && (
        <p className="silice-hoja__estado-aparte cds--type-helper-text-01">La versión vigente ahora es la {resumen.version_mas_nueva}.</p>
      )}
      {resumen.cambios > 0 && confirmando && (
        <div className="silice-hoja__confirmar silice-hoja__estado-aparte" role="group" aria-label="Descartar cambios">
          <p className="cds--type-body-compact-01">
            {resumen.cambios === 1
              ? "¿Descartar el cambio sin guardar? No se puede recuperar."
              : `¿Descartar los ${resumen.cambios} cambios sin guardar? No se pueden recuperar.`}
          </p>
          <Button kind="danger--tertiary" size="sm" onClick={alDescartar}>
            Descartar y abrir de nuevo
          </Button>
          <Button kind="secondary" size="sm" onClick={() => setConfirmando(false)}>
            Seguir editando
          </Button>
        </div>
      )}
    </section>
  );
}
