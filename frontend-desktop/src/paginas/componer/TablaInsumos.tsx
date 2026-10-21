import {
  Button,
  Select,
  SelectItem,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@carbon/react";
import { CampoTexto } from "../../comun/CampoTexto";
import { COLUMNAS, TITULOS } from "./tablas";
import type { Fila, TipoTabla } from "./tablas";

interface Props {
  tipo: TipoTabla;
  filas: Fila[];
  // Opciones de modalidad que manda la API (solo mano de obra).
  modalidades: string[];
  alCambiar: (indice: number, clave: string, valor: string) => void;
  alAgregar: () => void;
  alBorrar: (indice: number) => void;
}

// Una tabla de insumos editable (UC-10, pasos 2 a 4). Carbon `sm`: celdas de texto; los montos se teclean y se
// muestran como texto, alineados a la derecha, y nunca se convierten en el navegador.
export function TablaInsumos({ tipo, filas, modalidades, alCambiar, alAgregar, alBorrar }: Props) {
  const titulo = TITULOS[tipo];
  const columnas = COLUMNAS[tipo];
  return (
    <section className="silice-componer__tabla" aria-label={titulo}>
      <h3 className="cds--type-heading-compact-02">{titulo}</h3>
      <div className="silice-tabla">
        <Table size="sm" aria-label={`Insumos: ${titulo}`}>
          <TableHead>
            <TableRow>
              {columnas.map((c) => (
                <TableHeader key={c.clave} className={c.numerica ? "silice-cifra" : undefined}>
                  {c.titulo}
                </TableHeader>
              ))}
              <TableHeader aria-label="Acciones" />
            </TableRow>
          </TableHead>
          <TableBody>
            {filas.map((fila, i) => (
              <TableRow key={i}>
                {columnas.map((c) => {
                  const nombre = `${c.titulo}, fila ${i + 1}`;
                  return (
                    <TableCell key={c.clave} className={c.numerica ? "silice-cifra" : undefined}>
                      {c.clave === "modalidad" ? (
                        <Select
                          id={`${tipo}-${i}-${c.clave}`}
                          size="sm"
                          labelText={nombre}
                          hideLabel
                          value={fila[c.clave] ?? ""}
                          onChange={(e) => alCambiar(i, c.clave, e.target.value)}
                        >
                          <SelectItem value="" text="" />
                          {modalidades.map((m) => (
                            <SelectItem key={m} value={m} text={m} />
                          ))}
                        </Select>
                      ) : (
                        <CampoTexto
                          id={`${tipo}-${i}-${c.clave}`}
                          size="sm"
                          labelText={nombre}
                          hideLabel
                          value={fila[c.clave] ?? ""}
                          onChange={(e) => alCambiar(i, c.clave, e.target.value)}
                        />
                      )}
                    </TableCell>
                  );
                })}
                <TableCell>
                  <Button
                    kind="ghost"
                    size="sm"
                    aria-label={`Borrar fila ${i + 1} de ${titulo}`}
                    onClick={() => alBorrar(i)}
                  >
                    Borrar
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <Button kind="tertiary" size="sm" aria-label={`Agregar fila a ${titulo}`} onClick={alAgregar}>
        Agregar fila
      </Button>
    </section>
  );
}
