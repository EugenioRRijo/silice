import {
  DataTable,
  SelectableTag,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
} from "@carbon/react";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import type { HallazgoLibroRespuesta } from "../api/tipos";
import type { Severidad } from "../indicadores/tipos";
import { construirHalos, estiloDeHallazgo } from "./halos";
import { parsearCelda } from "./celdas";
import type { CeldaRef } from "./hojaVisor";
import { IconoDeSeveridad } from "./iconos";
import { montosEnFormatoUnico } from "./montos";

interface Props {
  hallazgos: HallazgoLibroRespuesta[];
  // Posicion del hallazgo elegido en `hallazgos`, o null.
  seleccionado: number | null;
  // Pide mover el foco del teclado a una fila (`n` cambia en cada pedido, para repetir sobre la misma fila).
  enfocar?: { indice: number; n: number } | null;
  hojasDelLibro?: string[];
  irACelda: (celda: CeldaRef, indice: number) => void;
  onElegir: (indice: number) => void;
}

const FILTROS: { clave: Severidad; texto: string }[] = [
  { clave: "CRITICO", texto: "Crítico" },
  { clave: "ERROR", texto: "Error" },
  { clave: "ADVERTENCIA", texto: "Advertencia" },
  { clave: "INFO", texto: "Información" },
];

const CABECERAS = [
  { key: "hallazgo", header: "Hallazgo" },
  { key: "impacto", header: "Impacto" },
];

function severidadDe(h: HallazgoLibroRespuesta): Severidad {
  return FILTROS.some((f) => f.clave === h.severidad) ? (h.severidad as Severidad) : "INFO";
}

interface TablaProps {
  etiqueta: string;
  hallazgos: HallazgoLibroRespuesta[];
  indices: number[];
  seleccionado: number | null;
  alElegir: (indice: number) => void;
}

function TablaHallazgos({ etiqueta, hallazgos, indices, seleccionado, alElegir }: TablaProps) {
  const filas = indices.map((indice) => {
    const h = hallazgos[indice];
    const estilo = estiloDeHallazgo(h);
    return {
      id: String(indice),
      hallazgo: (
        <div className="hallazgo">
          <div className="hallazgo__encabezado cds--type-label-01">
            <span className="hallazgo__severidad" style={{ ["--halo-color" as string]: `var(${estilo.token})` }}>
              <IconoDeSeveridad nombre={estilo.icono} size={16} className="hallazgo__icono" />
              <span>{estilo.texto}</span>
            </span>
            <span className="silice-codigo">{h.codigo}</span>
          </div>
          <div className="hallazgo__descripcion cds--type-body-compact-01" title={h.descripcion}>
            {montosEnFormatoUnico(h.descripcion)}
          </div>
          {h.celda && <div className="hallazgo__celda silice-codigo cds--type-label-01">{h.celda}</div>}
        </div>
      ),
      impacto:
        h.impacto === null ? (
          <span className="silice-oculto">sin impacto</span>
        ) : (
          <span className="silice-cifra cds--type-body-compact-01" title={h.impacto}>
            {montosEnFormatoUnico(h.impacto)}
          </span>
        ),
    };
  });

  return (
    <DataTable rows={filas} headers={CABECERAS} size="sm">
      {({ rows, headers, getTableProps, getHeaderProps, getRowProps }) => (
        <TableContainer>
          <Table {...getTableProps()} aria-label={etiqueta} size="sm" className="lista-hallazgos__tabla">
            <TableHead>
              <TableRow>
                {headers.map((cabecera) => {
                  const { key, ...resto } = getHeaderProps({ header: cabecera });
                  return (
                    <TableHeader
                      key={key}
                      {...resto}
                      className={cabecera.key === "impacto" ? "silice-cifra" : undefined}
                    >
                      {cabecera.header}
                    </TableHeader>
                  );
                })}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((fila) => {
                const indice = Number(fila.id);
                const { key, ...resto } = getRowProps({ row: fila });
                const elegida = seleccionado === indice;
                return (
                  <TableRow
                    key={key}
                    {...resto}
                    data-indice={indice}
                    tabIndex={0}
                    aria-current={elegida ? "true" : undefined}
                    className={elegida ? "lista-hallazgos__fila lista-hallazgos__fila--elegida" : "lista-hallazgos__fila"}
                    onClick={() => alElegir(indice)}
                    onKeyDown={(e: KeyboardEvent<HTMLTableRowElement>) => {
                      if (e.target !== e.currentTarget) return;
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        alElegir(indice);
                      }
                    }}
                  >
                    {fila.cells.map((celda) => (
                      <TableCell key={celda.id} className={celda.info.header === "impacto" ? "silice-cifra" : undefined}>
                        {celda.value}
                      </TableCell>
                    ))}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </DataTable>
  );
}

// Lista de 320 px a la derecha de la hoja. Clic (o Enter) en una fila: la hoja va a su celda.
export function ListaHallazgos({ hallazgos, seleccionado, enfocar, hojasDelLibro, irACelda, onElegir }: Props) {
  const [filtro, setFiltro] = useState<ReadonlySet<Severidad>>(new Set());
  const raiz = useRef<HTMLElement>(null);
  const idSinCelda = useId();

  const { sinCelda } = useMemo(() => construirHalos(hallazgos, hojasDelLibro), [hallazgos, hojasDelLibro]);
  const sinCeldaSet = useMemo(() => new Set(sinCelda), [sinCelda]);

  const cuentas = useMemo(() => {
    const c: Record<Severidad, number> = { CRITICO: 0, ERROR: 0, ADVERTENCIA: 0, INFO: 0 };
    for (const h of hallazgos) c[severidadDe(h)] += 1;
    return c;
  }, [hallazgos]);

  const pasan = (i: number) => filtro.size === 0 || filtro.has(severidadDe(hallazgos[i]));
  const conCelda = hallazgos.map((_, i) => i).filter((i) => !sinCeldaSet.has(i) && pasan(i));
  const sinCeldaVisibles = sinCelda.filter(pasan);

  useEffect(() => {
    if (!enfocar) return;
    const fila = raiz.current?.querySelector<HTMLElement>(`tr[data-indice="${enfocar.indice}"]`);
    if (!fila) return;
    fila.focus();
    fila.scrollIntoView?.({ block: "nearest" });
  }, [enfocar]);

  const elegir = (indice: number) => {
    onElegir(indice);
    const celda = parsearCelda(hallazgos[indice].celda);
    if (celda && !sinCeldaSet.has(indice)) irACelda(celda, indice);
  };

  const alternar = (clave: Severidad, activa: boolean) => {
    setFiltro((anterior) => {
      const siguiente = new Set(anterior);
      if (activa) siguiente.add(clave);
      else siguiente.delete(clave);
      return siguiente;
    });
  };

  return (
    <section className="lista-hallazgos" aria-label="Hallazgos de la auditoría" ref={raiz}>
      <div className="lista-hallazgos__cabecera">
        <h2 className="cds--type-heading-compact-01">Hallazgos ({hallazgos.length})</h2>
        <div className="lista-hallazgos__filtro" role="group" aria-label="Filtrar por severidad">
          {FILTROS.map(({ clave, texto }) => (
            <SelectableTag
              key={clave}
              size="sm"
              text={`${texto} ${cuentas[clave]}`}
              selected={filtro.has(clave)}
              onChange={(activa: boolean) => alternar(clave, activa)}
            />
          ))}
        </div>
      </div>

      {hallazgos.length === 0 && (
        <p className="lista-hallazgos__vacio cds--type-body-compact-01">
          La auditoría terminó y el libro no tiene hallazgos.
        </p>
      )}

      {conCelda.length > 0 && (
        <section aria-label="Hallazgos con celda en el libro">
          <TablaHallazgos
            etiqueta="Hallazgos con celda en el libro"
            hallazgos={hallazgos}
            indices={conCelda}
            seleccionado={seleccionado}
            alElegir={elegir}
          />
        </section>
      )}

      {sinCelda.length > 0 && (
        <section aria-labelledby={idSinCelda}>
          <h3 id={idSinCelda} className="lista-hallazgos__subtitulo cds--type-heading-compact-01">
            Sin celda en el libro ({sinCelda.length})
          </h3>
          {sinCeldaVisibles.length > 0 && (
            <TablaHallazgos
              etiqueta="Hallazgos sin celda en el libro"
              hallazgos={hallazgos}
              indices={sinCeldaVisibles}
              seleccionado={seleccionado}
              alElegir={elegir}
            />
          )}
        </section>
      )}
    </section>
  );
}
