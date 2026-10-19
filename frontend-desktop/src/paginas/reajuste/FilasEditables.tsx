import { Button, TextInput } from "@carbon/react";
import { Add, TrashCan } from "@carbon/icons-react";
import { filasVacias } from "./logica";
import type { Fila } from "./logica";

export interface ColumnaEditable {
  clave: string;
  titulo: string;
  // Texto de ayuda dentro del campo vacio (por ejemplo el formato de una fecha).
  ayuda?: string;
  // Solo se lee: el nombre de un componente no se escribe.
  fija?: boolean;
}

interface Props {
  // Nombre de la tabla: va en el aria-label y en el nombre de cada campo.
  etiqueta: string;
  columnas: ColumnaEditable[];
  filas: Fila[];
  alCambiar: (filas: Fila[]) => void;
  // Con `fijas` no se agregan ni se quitan filas (los tres componentes).
  fijas?: boolean;
}

// Tabla de campos de texto: cada celda es un campo con nombre accesible «<columna>, <tabla> fila <n>». Los valores
// se mandan a la API tal como se escriben (RB-2): aqui no se interpreta nada.
export function FilasEditables({ etiqueta, columnas, filas, alCambiar, fijas = false }: Props) {
  const cambiar = (indice: number, clave: string, valor: string) =>
    alCambiar(filas.map((fila, i) => (i === indice ? { ...fila, [clave]: valor } : fila)));
  const quitar = (indice: number) => {
    const resto = filas.filter((_, i) => i !== indice);
    alCambiar(resto.length > 0 ? resto : filasVacias(columnas.map((c) => c.clave), 1));
  };

  return (
    <div className="silice-filas">
      <table className="silice-filas__tabla" aria-label={etiqueta}>
        <thead>
          <tr>
            {columnas.map((c) => (
              <th key={c.clave} className="cds--type-label-01">
                {c.titulo}
              </th>
            ))}
            {!fijas && <th aria-hidden="true" />}
          </tr>
        </thead>
        <tbody>
          {filas.map((fila, i) => (
            <tr key={i}>
              {columnas.map((c) => (
                <td key={c.clave}>
                  <TextInput
                    id={`${etiqueta}-${c.clave}-${i}`}
                    labelText={`${c.titulo}, ${etiqueta} fila ${i + 1}`}
                    hideLabel
                    size="sm"
                    value={fila[c.clave] ?? ""}
                    placeholder={c.ayuda}
                    readOnly={c.fija}
                    onChange={(e) => cambiar(i, c.clave, e.target.value)}
                  />
                </td>
              ))}
              {!fijas && (
                <td>
                  <Button
                    kind="ghost"
                    size="sm"
                    hasIconOnly
                    renderIcon={TrashCan}
                    iconDescription={`Quitar ${etiqueta} fila ${i + 1}`}
                    onClick={() => quitar(i)}
                  />
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      {!fijas && (
        <Button
          kind="tertiary"
          size="sm"
          renderIcon={Add}
          onClick={() => alCambiar([...filas, ...filasVacias(columnas.map((c) => c.clave), 1)])}
        >
          {`Agregar fila a ${etiqueta}`}
        </Button>
      )}
    </div>
  );
}
