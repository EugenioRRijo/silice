import { CheckmarkOutline } from "@carbon/icons-react";
import { Button, Pagination, Select, SelectItem, Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TextInput } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { EstadoDeFila } from "./EstadoDeFila";
import {
  FILAS_POR_PAGINA,
  LARGO_DE_CELDA,
  LIMITE_DE_FILAS,
  LIMITE_SIN_PAGINAR,
  PREFIJO_DE_ESTADO,
  filaEnBlanco,
  nuevaClaveDeFila,
  puedeAgregarFila,
  rotuloDeOrigen,
  textoDeFilas,
} from "./logica";
import type { EstadoFila, FilaEditable, TablaEspacio } from "./logica";

// A qué celda ir desde fuera (por ejemplo desde «Ir a la fila 2»); `vez` sube para repetir el mismo destino.
export interface IrA {
  fila: number; // desde 1
  columna: string | null;
  vez: number;
}

interface Props {
  tabla: TablaEspacio;
  filas: FilaEditable[];
  estado: Record<string, EstadoFila>;
  // La celda que el servidor rechazó (fila desde 1; sin columna conocida, la primera de la fila).
  invalida: { fila: number; columna: string | null } | null;
  // Id del elemento con el mensaje completo del error; las celdas inválidas lo tienen como descripción accesible.
  idDelError: string;
  irA: IrA | null;
  alCambiarFilas: (filas: FilaEditable[]) => void;
  // Lo último que aceptó el servidor para una celda (Esc devuelve la celda a eso).
  valorAceptado: (filaClave: number, columna: string) => string;
}

type PorEnfocar = { clave: number; columna: string } | "agregar";

function idDeCelda(tabla: string, clave: number, columna: string): string {
  return `hoja-${tabla}-${clave}-${columna}`;
}

// El texto de «Sin evaluar» es para filas que el servidor aún no conoce (nuevas o con otro código).
function EstadoDeLaFila({ tabla, fila, estado }: { tabla: TablaEspacio; fila: FilaEditable; estado: Record<string, EstadoFila> }) {
  const prefijo = PREFIJO_DE_ESTADO[tabla.clave];
  const origen = prefijo && fila.valores.id ? `${prefijo}:${fila.valores.id}` : "";
  const propio = origen === "" ? undefined : estado[origen];
  if (propio === undefined) {
    return (
      <span className="silice-hoja__estado-fila" title="Aún no se evalúa: se evalúa al aceptar el servidor la edición.">
        <CheckmarkOutline size={16} aria-hidden="true" className="silice-hoja__sin-evaluar" />
        <span>Sin evaluar</span>
      </span>
    );
  }
  return <EstadoDeFila estado={propio} claves={[origen]} rotulo={rotuloDeOrigen(origen)} />;
}

// Una de las tablas del espacio, editable: cada celda es un campo con nombre accesible, las listas cerradas son select
// (se guarda el valor interno, se ve el rótulo), y la persona agrega y quita filas. No calcula nada: los textos salen
// tal cual los escribió la persona y el servidor los valida (diseño §7.3).
export function TablaEditable({ tabla, filas, estado, invalida, idDelError, irA, alCambiarFilas, valorAceptado }: Props) {
  const [pagina, setPagina] = useState(1);
  // La celda a la que hay que dar el foco en cuanto exista en la página (tras agregar, quitar o cambiar de página).
  const porEnfocar = useRef<PorEnfocar | null>(null);
  const paginar = filas.length > LIMITE_SIN_PAGINAR;
  const ultimaPagina = paginar ? Math.max(1, Math.ceil(filas.length / FILAS_POR_PAGINA)) : 1;
  const actual = Math.min(pagina, ultimaPagina);
  const visibles = paginar ? filas.slice((actual - 1) * FILAS_POR_PAGINA, actual * FILAS_POR_PAGINA) : filas;
  const primeraDeLaPagina = paginar ? (actual - 1) * FILAS_POR_PAGINA : 0;
  const idAgregar = `hoja-${tabla.clave}-agregar`;

  const enfocar = (destino: PorEnfocar) => {
    const id = destino === "agregar" ? idAgregar : idDeCelda(tabla.clave, destino.clave, destino.columna);
    const elemento = document.getElementById(id);
    if (elemento !== null) elemento.focus();
    else porEnfocar.current = destino;
  };

  // Tras cada pintura: si había un foco pendiente y su celda ya existe, se le da.
  useEffect(() => {
    const destino = porEnfocar.current;
    if (destino === null) return;
    const id = destino === "agregar" ? idAgregar : idDeCelda(tabla.clave, destino.clave, destino.columna);
    const elemento = document.getElementById(id);
    if (elemento === null) return;
    porEnfocar.current = null;
    elemento.focus();
  });

  // Una petición de fuera (por ejemplo «Ir a la fila 2»): primero se pasa a la página de esa fila...
  const [vistoIrA, setVistoIrA] = useState<number | null>(null);
  if (irA !== null && irA.vez !== vistoIrA) {
    setVistoIrA(irA.vez);
    if (paginar) setPagina(Math.floor((irA.fila - 1) / FILAS_POR_PAGINA) + 1);
  }
  // ...y ya pintada, se le da el foco a su celda.
  const vezPedida = irA?.vez;
  useEffect(() => {
    if (irA === null) return;
    const destino = filas[irA.fila - 1];
    if (destino === undefined) return;
    const columna = tabla.columnas.some((c) => c.clave === irA.columna) ? irA.columna! : tabla.columnas[0]!.clave;
    document.getElementById(idDeCelda(tabla.clave, destino.clave, columna))?.focus();
    // Solo cuando llega una petición nueva.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vezPedida]);

  const irAFila = (indice: number, columna: string) => {
    const destino = filas[indice];
    if (destino === undefined) return;
    if (paginar) setPagina(Math.floor(indice / FILAS_POR_PAGINA) + 1);
    enfocar({ clave: destino.clave, columna });
  };

  const cambiar = (clave: number, columna: string, valor: string) =>
    alCambiarFilas(filas.map((f) => (f.clave === clave ? { ...f, valores: { ...f.valores, [columna]: valor } } : f)));

  const agregar = () => {
    const nueva = filaEnBlanco(tabla, nuevaClaveDeFila());
    alCambiarFilas([...filas, nueva]);
    setPagina(Math.max(1, Math.ceil((filas.length + 1) / FILAS_POR_PAGINA)));
    enfocar({ clave: nueva.clave, columna: tabla.columnas[0]!.clave });
  };

  const quitar = (indice: number) => {
    const resto = filas.filter((_, i) => i !== indice);
    alCambiarFilas(resto);
    const vecina = resto[indice] ?? resto[indice - 1];
    enfocar(vecina === undefined ? "agregar" : { clave: vecina.clave, columna: tabla.columnas[0]!.clave });
  };

  // ↑/↓/Enter mueven entre filas de la misma columna en los campos de texto; Esc devuelve la celda a lo aceptado.
  // En un select no se intercepta nada: las flechas cambian de opción.
  const alTeclear = (indice: number, clave: number, columna: string) => (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown" || e.key === "Enter") {
      e.preventDefault();
      irAFila(Math.min(indice + 1, filas.length - 1), columna);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      irAFila(Math.max(indice - 1, 0), columna);
    } else if (e.key === "Escape") {
      e.preventDefault();
      cambiar(clave, columna, valorAceptado(clave, columna));
    }
  };

  const llenaDelTodo = !puedeAgregarFila(tabla.clave, filas.length);

  return (
    <section className="silice-hoja__seccion">
      <div className="silice-hoja__titulo-tabla">
        <h3 className="cds--type-heading-compact-01">{tabla.rotulo}</h3>
        <span className="cds--type-helper-text-01">{textoDeFilas(filas.length)}</span>
      </div>
      <div role="region" aria-label={`${tabla.rotulo}: desplazar horizontalmente`} tabIndex={0} className="silice-hoja__desplazable silice-hoja__editable">
        <Table size="sm" aria-label={tabla.rotulo}>
          <TableHead>
            <TableRow>
              {tabla.columnas.map((c) => (
                <TableHeader key={c.clave}>{c.rotulo}</TableHeader>
              ))}
              {tabla.con_estado && <TableHeader>Estado</TableHeader>}
              <TableHeader>Acciones</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {visibles.map((fila, i) => {
              const indice = primeraDeLaPagina + i;
              return (
                <TableRow key={fila.clave}>
                  {tabla.columnas.map((c, columna) => {
                    const etiqueta = `${c.rotulo}, ${tabla.rotulo} fila ${indice + 1}`;
                    const esInvalida =
                      invalida !== null &&
                      invalida.fila === indice + 1 &&
                      (invalida.columna === c.clave || (invalida.columna === null && columna === 0));
                    const comunes = {
                      id: idDeCelda(tabla.clave, fila.clave, c.clave),
                      labelText: etiqueta,
                      hideLabel: true,
                      size: "sm" as const,
                      invalid: esInvalida,
                      invalidText: "Valor no válido",
                      ...(esInvalida ? { "aria-describedby": idDelError } : {}),
                    };
                    const valor = fila.valores[c.clave] ?? "";
                    return (
                      <TableCell key={c.clave}>
                        {c.lista !== null ? (
                          <Select {...comunes} value={valor} onChange={(e) => cambiar(fila.clave, c.clave, e.target.value)}>
                            {c.lista.some((o) => o.valor === valor) ? null : <SelectItem value={valor} text={valor} />}
                            {c.lista.map((o) => (
                              <SelectItem key={o.valor} value={o.valor} text={o.rotulo} />
                            ))}
                          </Select>
                        ) : (
                          <TextInput
                            {...comunes}
                            value={valor}
                            maxLength={LARGO_DE_CELDA}
                            autoComplete="off"
                            onChange={(e) => cambiar(fila.clave, c.clave, e.target.value)}
                            onKeyDown={alTeclear(indice, fila.clave, c.clave)}
                          />
                        )}
                      </TableCell>
                    );
                  })}
                  {tabla.con_estado && (
                    <TableCell>
                      <EstadoDeLaFila tabla={tabla} fila={fila} estado={estado} />
                    </TableCell>
                  )}
                  <TableCell>
                    <Button kind="ghost" size="sm" aria-label={`Quitar fila ${indice + 1} de ${tabla.rotulo}`} onClick={() => quitar(indice)}>
                      Quitar
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
      {paginar && (
        <Pagination
          size="sm"
          page={actual}
          pageSize={FILAS_POR_PAGINA}
          pageSizes={[FILAS_POR_PAGINA]}
          totalItems={filas.length}
          itemsPerPageText="Filas por página"
          backwardText="Página anterior"
          forwardText="Página siguiente"
          itemRangeText={(min, max, total) => `${min}–${max} de ${total}`}
          onChange={({ page }) => setPagina(page)}
        />
      )}
      <div className="silice-hoja__agregar">
        <Button id={idAgregar} kind="tertiary" size="sm" disabled={llenaDelTodo} aria-label={`Agregar fila a ${tabla.rotulo}`} onClick={agregar}>
          Agregar fila
        </Button>
        {llenaDelTodo && (
          <span className="cds--type-helper-text-01">
            {tabla.rotulo} llegó a su tope de {LIMITE_DE_FILAS[tabla.clave]} filas.
          </span>
        )}
      </div>
    </section>
  );
}
