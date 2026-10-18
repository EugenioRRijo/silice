import {
  DataTable,
  InlineNotification,
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
import type { HallazgoLibroRespuesta, HojaVisualRespuesta } from "../api/tipos";
import type { Severidad } from "../indicadores/tipos";
import { IconoDeSeveridad } from "../severidad/IconoDeSeveridad";
import { SEVERIDADES, estiloDeSeveridad, normalizarSeveridad } from "../severidad/severidad";
import { parsearCelda } from "./celdas";
import { construirHalos, estiloDeHallazgo } from "./halos";
import type { CeldaRef } from "./hojaVisor";

interface Props {
  hallazgos: HallazgoLibroRespuesta[];
  // Posicion del hallazgo elegido en `hallazgos`, o null.
  seleccionado: number | null;
  // Pide mover el foco del teclado a una fila (`n` cambia en cada pedido, para repetir sobre la misma fila).
  enfocar?: { indice: number; n: number } | null;
  // Las hojas del libro (para saber que esta oculto o no existe).
  hojas?: HojaVisualRespuesta[];
  // El filtro por severidad viene de afuera al volver a montar la lista y sale hacia afuera al cambiar.
  filtroInicial?: Severidad[];
  alFiltrar?: (filtro: Severidad[]) => void;
  irACelda: (celda: CeldaRef, indice: number) => void;
  onElegir: (indice: number) => void;
}

const CABECERAS = [
  { key: "hallazgo", header: "Hallazgo" },
  { key: "impacto", header: "Impacto" },
];

const severidadDe = (h: HallazgoLibroRespuesta): Severidad => normalizarSeveridad(h.severidad);

interface TablaProps {
  etiqueta: string;
  hallazgos: HallazgoLibroRespuesta[];
  indices: number[];
  seleccionado: number | null;
  alElegir: (indice: number) => void;
  // Para los hallazgos ocultos: que esta oculto.
  motivos?: ReadonlyMap<number, string>;
}

function TablaHallazgos({ etiqueta, hallazgos, indices, seleccionado, alElegir, motivos }: TablaProps) {
  const filas = indices.map((indice) => {
    const h = hallazgos[indice];
    const estilo = estiloDeHallazgo(h);
    const motivo = motivos?.get(indice);
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
          <div className="hallazgo__descripcion cds--type-body-compact-01">{h.descripcion}</div>
          {motivo && <div className="hallazgo__motivo cds--type-label-01">{motivo}</div>}
          {h.celda && <div className="hallazgo__celda silice-codigo cds--type-label-01">{h.celda}</div>}
        </div>
      ),
      impacto:
        h.impacto === null ? (
          <span className="silice-oculto">sin impacto</span>
        ) : (
          <span className="silice-cifra cds--type-body-compact-01">{h.impacto}</span>
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

// Lista de 320 px a la derecha de la hoja. Clic (o Enter) en una fila: la hoja va a su celda. El encabezado y los
// filtros quedan fijos; solo el cuerpo desplaza.
export function ListaHallazgos({
  hallazgos,
  seleccionado,
  enfocar,
  hojas,
  filtroInicial,
  alFiltrar,
  irACelda,
  onElegir,
}: Props) {
  const [filtro, setFiltro] = useState<ReadonlySet<Severidad>>(new Set(filtroInicial ?? []));
  const [aviso, setAviso] = useState<string | null>(null);
  const raiz = useRef<HTMLElement>(null);
  const idSinCelda = useId();
  const idOcultos = useId();

  const { sinCelda, ocultos } = useMemo(() => construirHalos(hallazgos, hojas), [hallazgos, hojas]);
  const sinCeldaSet = useMemo(() => new Set(sinCelda), [sinCelda]);
  const motivos = useMemo(() => new Map(ocultos.map((o) => [o.indice, o.motivo])), [ocultos]);
  const ocultosIndices = useMemo(() => ocultos.map((o) => o.indice), [ocultos]);

  const cuentas = useMemo(() => {
    const c: Record<Severidad, number> = { CRITICO: 0, ERROR: 0, ADVERTENCIA: 0, INFO: 0 };
    for (const h of hallazgos) c[severidadDe(h)] += 1;
    return c;
  }, [hallazgos]);

  const pasan = (i: number) => filtro.size === 0 || filtro.has(severidadDe(hallazgos[i]));
  const conCelda = hallazgos.map((_, i) => i).filter((i) => !sinCeldaSet.has(i) && !motivos.has(i) && pasan(i));
  const sinCeldaVisibles = sinCelda.filter(pasan);
  const ocultosVisibles = ocultosIndices.filter(pasan);

  useEffect(() => {
    if (!enfocar) return;
    const fila = raiz.current?.querySelector<HTMLElement>(`tr[data-indice="${enfocar.indice}"]`);
    if (!fila) return;
    fila.focus();
    fila.scrollIntoView?.({ block: "nearest" });
  }, [enfocar]);

  const elegir = (indice: number) => {
    onElegir(indice);
    const oculto = motivos.get(indice);
    if (oculto) {
      setAviso(`No se puede mostrar sobre la hoja: ${oculto} en el libro.`);
      return;
    }
    const celda = parsearCelda(hallazgos[indice].celda);
    if (!celda || sinCeldaSet.has(indice)) {
      setAviso("Este hallazgo no tiene una celda que se pueda mostrar en la hoja.");
      return;
    }
    setAviso(null);
    irACelda(celda, indice);
  };

  const alternar = (clave: Severidad, activa: boolean) => {
    const siguiente = new Set(filtro);
    if (activa) siguiente.add(clave);
    else siguiente.delete(clave);
    setFiltro(siguiente);
    alFiltrar?.(SEVERIDADES.filter((s) => siguiente.has(s)));
  };

  return (
    <section className="lista-hallazgos" aria-label="Hallazgos de la auditoría" ref={raiz}>
      <div className="lista-hallazgos__cabecera">
        <h2 className="cds--type-heading-compact-01">Hallazgos ({hallazgos.length})</h2>
        <div className="lista-hallazgos__filtro" role="group" aria-label="Filtrar por severidad">
          {SEVERIDADES.map((clave) => (
            <SelectableTag
              key={clave}
              size="sm"
              text={`${estiloDeSeveridad(clave).texto} ${cuentas[clave]}`}
              selected={filtro.has(clave)}
              onChange={(activa: boolean) => alternar(clave, activa)}
            />
          ))}
        </div>
        {aviso && (
          <InlineNotification
            kind="info"
            role="status"
            title="Sin celda a la vista"
            subtitle={aviso}
            lowContrast
            hideCloseButton
            className="lista-hallazgos__aviso"
          />
        )}
      </div>

      <div className="lista-hallazgos__cuerpo">
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

        {ocultosIndices.length > 0 && (
          <section aria-labelledby={idOcultos}>
            <h3 id={idOcultos} className="lista-hallazgos__subtitulo cds--type-heading-compact-01">
              En hoja, fila o columna oculta ({ocultosIndices.length})
            </h3>
            {ocultosVisibles.length > 0 && (
              <TablaHallazgos
                etiqueta="Hallazgos en una hoja, fila o columna oculta"
                hallazgos={hallazgos}
                indices={ocultosVisibles}
                seleccionado={seleccionado}
                alElegir={elegir}
                motivos={motivos}
              />
            )}
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
      </div>
    </section>
  );
}
