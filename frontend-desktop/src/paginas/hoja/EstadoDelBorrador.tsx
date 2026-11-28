import { Button } from "@carbon/react";
import { useState } from "react";
import type { ReactNode } from "react";
import { MontoExacto } from "../../comun/MontoExacto";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { porcentajeDeAlicuota } from "../control/logica";
import type { Impuestos } from "../control/logica";
import { textoDeCambios } from "./logica";
import type { BorradorAbierto } from "./logica";

// La línea de estado del Presupuesto (decisión de Eugenio, 2026-11-05: cabecera compacta). Una sola región, «Estado del
// borrador», con la versión y los cambios sin guardar, la aprobación de la versión (la pone `FranjaDelPresupuesto`, que es
// quien la lee), el total sin IVA (y con IVA cuando está disponible) y «Descartar» cuando toca.
//
// B1-3 (ficha-b1 §3.2; guía `accessibility`): el total se dice con `MontoExacto`: sin `title` y sin región viva propia (el
// anuncio único lo da `useAnunciar`); el valor exacto está en su Toggletip. «Descartar cambios» (fantasma) y su confirmación
// solo salen si quien monta pasa `alDescartar` y hay cambios; la superficie nueva no lo pasa: lo ofrece «Más acciones».
interface Props {
  borrador: BorradorAbierto;
  // Opcional: la vista por pestañas lo pasa; la superficie nueva lo lleva al menú «Más acciones».
  alDescartar?: () => void;
  // F4 2b: sin permiso de edición (o con un borrador de solo lectura) no se ofrece descartar.
  puedeEditar: boolean;
  // La aprobación de la versión abierta (`AprobacionDeVersion`), entre los cambios y el total. Nada si no hay versión.
  aprobacion?: ReactNode;
  // Impuestos calculados por el servidor; cuando llegan, «Con IVA (16 %) …» va debajo de «Total sin IVA».
  impuestos?: Impuestos;
}

export function EstadoDelBorrador({ borrador, alDescartar, puedeEditar, aprobacion, impuestos }: Props) {
  const { base, resumen } = borrador;
  const [confirmando, setConfirmando] = useState(false);
  const puedeDescartar = alDescartar !== undefined && puedeEditar && resumen.cambios > 0;
  return (
    <section className="silice-hoja__estado" role="region" aria-label="Estado del borrador">
      <p className="silice-hoja__estado-version cds--type-body-compact-01">
        {base.version === null ? "Borrador en blanco" : `Versión ${base.version}`} · {textoDeCambios(resumen.cambios)}
      </p>
      {aprobacion}
      <div className="silice-hoja__total-bloque">
        <div className="silice-hoja__total cds--type-heading-compact-02">
          Total sin IVA <MontoExacto texto={resumen.total.texto} exacto={resumen.total.exacto} unidad={resumen.moneda} />
        </div>
        {impuestos !== undefined && (
          <p className="silice-hoja__total-iva cds--type-body-compact-01 silice-cifra">
            {`Con IVA (${porcentajeDeAlicuota(impuestos.alicuota)} %) ${formatoEsVe(impuestos.total)} ${resumen.moneda}`}
          </p>
        )}
      </div>
      {puedeDescartar && !confirmando && (
        <Button kind="ghost" size="sm" onClick={() => setConfirmando(true)}>
          Descartar cambios
        </Button>
      )}
      {resumen.version_mas_nueva !== null && (
        <p className="silice-hoja__estado-aparte cds--type-helper-text-01">La versión vigente ahora es la {resumen.version_mas_nueva}.</p>
      )}
      {puedeDescartar && confirmando && (
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
