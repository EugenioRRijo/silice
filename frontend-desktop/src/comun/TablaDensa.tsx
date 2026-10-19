import {
  DataTable,
  DataTableSkeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@carbon/react";
import { EstadoVacio } from "./EstadoVacio";
import { Severidad } from "./Severidad";
import { Variacion } from "./Variacion";

export interface ColumnaDensa {
  clave: string;
  titulo: string;
  // Montos y cantidades: a la derecha, cifras tabulares y orden como decimal exacto.
  numerica?: boolean;
  // Por omision todas se ordenan.
  ordenable?: boolean;
  // Como se dibuja la celda: "severidad" = icono y nombre de la severidad; "variacion" = cifra de variacion de
  // costo con la semantica IBCS (flecha, color y texto accesible). Sin esto, el texto tal cual.
  celda?: "severidad" | "variacion";
}

// Los valores son texto tal como los manda la API: la tabla no los redondea ni los reformatea.
export type FilaDensa = { id: string } & Record<string, string>;

interface Props {
  // Nombre accesible de la tabla y del esqueleto.
  etiqueta: string;
  columnas: ColumnaDensa[];
  filas: FilaDensa[];
  cargando?: boolean;
  vacio?: { titulo: string; descripcion?: string };
}

const DECIMAL = /^([+-]?)(\d*)(?:\.(\d*))?$/;

interface Descompuesto {
  negativo: boolean;
  entera: bigint;
  fraccion: string;
}

function descomponer(texto: string): Descompuesto | null {
  const m = DECIMAL.exec(texto.trim());
  if (!m || (m[2] === "" && !m[3])) return null;
  const entera = BigInt(m[2] || "0");
  const fraccion = (m[3] ?? "").replace(/0+$/, "");
  const esCero = entera === 0n && fraccion === "";
  return { negativo: m[1] === "-" && !esCero, entera, fraccion };
}

// Compara dos decimales escritos como texto SIN pasar por float (no se pierde ningun digito). Lo que no es un
// decimal ("", "n/d") queda despues de los numeros. Comparar no es calcular: la interfaz no opera con montos.
export function compararDecimales(a: string, b: string): number {
  const x = descomponer(a);
  const y = descomponer(b);
  if (!x && !y) return a === b ? 0 : a.localeCompare(b, "es");
  if (!x) return 1;
  if (!y) return -1;
  if (x.negativo !== y.negativo) return x.negativo ? -1 : 1;
  const signo = x.negativo ? -1 : 1;
  if (x.entera !== y.entera) return (x.entera < y.entera ? -1 : 1) * signo;
  const largo = Math.max(x.fraccion.length, y.fraccion.length);
  const fx = x.fraccion.padEnd(largo, "0");
  const fy = y.fraccion.padEnd(largo, "0");
  if (fx === fy) return 0;
  return (fx < fy ? -1 : 1) * signo;
}

function dibujar(tipo: "severidad" | "variacion" | undefined, valor: unknown) {
  const texto = String(valor ?? "");
  if (tipo === "severidad" && texto) return <Severidad valor={texto} />;
  if (tipo === "variacion" && texto) return <Variacion valor={texto} />;
  return valor as string;
}

// Tabla de datos de alta densidad (DESIGN.md, Densidad): Carbon DataTable tamano `sm` (32 px).
export function TablaDensa({ etiqueta, columnas, filas, cargando = false, vacio }: Props) {
  if (cargando) {
    return (
      <div role="status" aria-busy="true" aria-label={`Cargando ${etiqueta}`}>
        <DataTableSkeleton
          size="sm"
          columnCount={columnas.length}
          rowCount={6}
          headers={columnas.map((c) => ({ header: c.titulo }))}
          showToolbar={false}
          showHeader={false}
        />
      </div>
    );
  }

  const numericas = new Set(columnas.filter((c) => c.numerica).map((c) => c.clave));
  const sinOrden = new Set(columnas.filter((c) => c.ordenable === false).map((c) => c.clave));
  const especial = new Map(columnas.filter((c) => c.celda).map((c) => [c.clave, c.celda]));
  const cabeceras = columnas.map((c) => ({ key: c.clave, header: c.titulo }));

  return (
    <div className="silice-tabla">
      <DataTable
        rows={filas}
        headers={cabeceras}
        size="sm"
        isSortable
        sortRow={(a, b, { key, sortDirection, sortStates, locale, compare }) => {
          const [x, y] = sortDirection === sortStates.ASC ? [a, b] : [b, a];
          if (numericas.has(key)) return compararDecimales(String(x ?? ""), String(y ?? ""));
          return compare(x, y, locale);
        }}
      >
        {({ rows, headers, getTableProps, getHeaderProps, getRowProps }) => (
          <Table {...getTableProps()} aria-label={etiqueta}>
            <TableHead>
              <TableRow>
                {headers.map((cabecera) => {
                  const { key, ...propiedades } = getHeaderProps({
                    header: cabecera,
                    isSortable: !sinOrden.has(cabecera.key),
                  });
                  return (
                    <TableHeader key={key} {...propiedades} className={numericas.has(cabecera.key) ? "silice-cifra" : undefined}>
                      {cabecera.header}
                    </TableHeader>
                  );
                })}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((fila) => {
                const { key, ...propiedades } = getRowProps({ row: fila });
                return (
                  <TableRow key={key} {...propiedades}>
                    {fila.cells.map((celda) => (
                      <TableCell key={celda.id} className={numericas.has(celda.info.header) ? "silice-cifra" : undefined}>
                        {dibujar(especial.get(celda.info.header), celda.value)}
                      </TableCell>
                    ))}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </DataTable>
      {filas.length === 0 && (
        <EstadoVacio
          titulo={vacio?.titulo ?? "No hay datos para mostrar"}
          descripcion={vacio?.descripcion}
        />
      )}
    </div>
  );
}
