import { WarningAltFilled } from "@carbon/icons-react";
import { Button } from "@carbon/react";
import "./FranjaDelPaso.scss";

interface Props {
  tipo: "falta" | "siguiente";
  texto: string;
  // El único botón principal de la pantalla mientras la franja esté a la vista. Sin acción (la cuenta no puede usar la
  // pantalla de destino) la franja solo informa.
  // `enSegundoPlano`: un diálogo de la pantalla está abierto y su paso lleva el principal (Archivos y planos, Tarea 11 de
  // F4); mientras tanto el botón de la franja pasa a secundario, para que no haya dos principales a la vista.
  accion?: { texto: string; alPulsar: () => void; deshabilitada?: boolean; enSegundoPlano?: boolean };
}

// La franja «Te falta / Siguiente paso» (Tarea 2 del plan F4; especificación §2.3 y §6.4): es el molde de toda sección de
// la obra, así que vive en `comun/`. La usa el Resumen y la usará Presupuesto (Tarea 5). «Te falta» es una precaución
// (fondo y raya de aviso, con el ícono: la palabra ya basta y el color no va solo); «Siguiente paso» solo orienta, sin
// ícono. El botón es la acción de la pantalla: uno solo, el principal.
export function FranjaDelPaso({ tipo, texto, accion }: Props) {
  const falta = tipo === "falta";
  return (
    <section aria-label="Siguiente paso" className={falta ? "silice-franja silice-franja--falta" : "silice-franja"}>
      <p className="silice-franja__texto cds--type-body-compact-01">
        {falta && <WarningAltFilled size={16} aria-hidden="true" className="silice-franja__icono" />}
        <strong>{falta ? "Te falta:" : "Siguiente paso:"}</strong> {texto}
      </p>
      {accion && (
        <Button kind={accion.enSegundoPlano ? "secondary" : "primary"} size="md" disabled={accion.deshabilitada} onClick={accion.alPulsar}>
          {accion.texto}
        </Button>
      )}
    </section>
  );
}
