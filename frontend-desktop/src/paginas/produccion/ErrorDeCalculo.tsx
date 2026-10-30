import { InlineNotification } from "@carbon/react";
import type { JSX, Ref } from "react";
import { desgloseDeTasas, mensajeDePlanta } from "./logicaPlanta";

interface Props {
  error: unknown;
  titulo: string;
  // La caja que recibe el foco cuando el aviso aparece (un elemento estable, no el botón que se desactivó).
  caja?: Ref<HTMLDivElement>;
}

// El rechazo de un cálculo. Si faltan tasas BCV, el servidor nombra cada costo con su fecha: aquí sale uno por renglón.
// Cualquier otro mensaje va entero, en español; nunca un número de estado ni el cuerpo de una validación.
export function ErrorDeCalculo({ error, titulo, caja }: Props): JSX.Element | null {
  if (error === null || error === undefined) return null;
  const mensaje = mensajeDePlanta(error);
  const tasas = desgloseDeTasas(mensaje);
  return (
    <div ref={caja} tabIndex={-1}>
      <InlineNotification
        kind="error"
        role="alert"
        title={titulo}
        lowContrast
        hideCloseButton
        subtitle={tasas ? tasas.encabezado : mensaje}
      >
        {tasas && (
          <>
            <ul className="planta-faltan">
              {tasas.faltan.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
            <span>{tasas.cierre}</span>
          </>
        )}
      </InlineNotification>
    </div>
  );
}
