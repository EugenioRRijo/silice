
import type { KeyboardEvent } from "react";
import { LARGO_DE_CELDA } from "./logica";
import { CampoTexto } from "../../comun/CampoTexto";

interface Props {
  id: string;
  // El nombre accesible: «{columna}, {tabla} fila {n}» en una tabla, el rótulo en un formulario.
  etiqueta: string;
  // En una tabla el nombre va oculto (lo da la cabecera); en un formulario se ve.
  etiquetaVisible?: boolean;
  valor: string;
  invalido?: boolean;
  // El texto que acompaña a la celda inválida (el color nunca va solo).
  textoInvalido?: string;
  // Id del elemento con el mensaje completo del error.
  descripcionId?: string;
  alCambiar: (valor: string) => void;
  // Esc: devuelve el campo a lo último que aceptó el servidor.
  alRestaurar: () => void;
  // ↑/↓/Enter pasan a la misma columna de la fila vecina; sin esta función no se interceptan.
  alMover?: (paso: 1 | -1) => void;
}

// Un campo de texto de una sección editable: el valor es siempre el texto que escribió la persona (nada se convierte) y el
// servidor lo valida con los mensajes de la clásica.
export function CampoDeCelda({
  id,
  etiqueta,
  etiquetaVisible = false,
  valor,
  invalido = false,
  textoInvalido = "Valor no válido",
  descripcionId,
  alCambiar,
  alRestaurar,
  alMover,
}: Props) {
  const alTeclear = (e: KeyboardEvent<HTMLInputElement>) => {
    if (alMover !== undefined && (e.key === "ArrowDown" || e.key === "Enter")) {
      e.preventDefault();
      alMover(1);
    } else if (alMover !== undefined && e.key === "ArrowUp") {
      e.preventDefault();
      alMover(-1);
    } else if (e.key === "Escape") {
      e.preventDefault();
      alRestaurar();
    }
  };
  return (
    <CampoTexto
      id={id}
      labelText={etiqueta}
      hideLabel={!etiquetaVisible}
      size="sm"
      value={valor}
      maxLength={LARGO_DE_CELDA}
      autoComplete="off"
      invalid={invalido}
      invalidText={textoInvalido}
      {...(invalido && descripcionId !== undefined ? { "aria-describedby": descripcionId } : {})}
      onChange={(e) => alCambiar(e.target.value)}
      onKeyDown={alTeclear}
    />
  );
}
