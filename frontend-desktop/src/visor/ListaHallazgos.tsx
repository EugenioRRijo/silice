import { DataTable, SelectableTag, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from "@carbon/react";
import { InlineNotification, TableHeader } from "../comun/carbonEs";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import type { CausaRaizRespuesta, HallazgoLibroRespuesta, HojaVisualRespuesta } from "../api/tipos";
import { formatoEsVe } from "../indicadores/formatoEsVe";
import type { Severidad } from "../indicadores/tipos";
import { IconoDeSeveridad } from "../severidad/IconoDeSeveridad";
import { SEVERIDADES, estiloDeSeveridad, normalizarSeveridad } from "../severidad/severidad";
import { parsearCelda } from "./celdas";
import { CODIGO_ATIPICO, construirHalos, estiloDeHallazgo } from "./halos";
import type { CeldaRef } from "./hojaVisor";

interface Props {
  hallazgos: HallazgoLibroRespuesta[];
  // Causas raiz agrupadas por el servidor (opcional: una API anterior no las manda).
  causas?: CausaRaizRespuesta[];
  // Posiciones en `hallazgos` de reglas no aplicables (no cuentan ni salen en las tablas).
  noAplicables?: number[];
  // Posicion del hallazgo elegido en `hallazgos`, o null.
  seleccionado: number | null;
  // Pide mover el foco del teclado a una fila (`n` cambia en cada pedido, para repetir sobre la misma fila).
  enfocar?: { indice: number; n: number } | null;
  // Las hojas del libro (para saber que esta oculto o no existe).
  hojas?: HojaVisualRespuesta[];
  // El filtro por severidad viene de afuera al volver a montar la lista y sale hacia afuera al cambiar.
  filtroInicial?: Severidad[];
  alFiltrar?: (filtro: Severidad[]) => void;
  // El texto de la fila de la celda (su descripcion), para decir de que fila habla el hallazgo elegido aunque la hoja
  // no deje ver esa columna junto a la celda marcada.
  contextoDeCelda?: (celda: CeldaRef) => string | null;
  irACelda: (celda: CeldaRef, indice: number) => void;
  onElegir: (indice: number) => void;
}

// Una sola columna: el impacto va en la primera linea de cada hallazgo, no en una columna aparte (casi siempre vacia).
const CABECERAS = [{ key: "hallazgo", header: "Hallazgo" }];

const severidadDe = (h: HallazgoLibroRespuesta): Severidad => normalizarSeveridad(h.severidad);

function primeraClausula(descripcion: string): string {
  const corte = descripcion.indexOf(";");
  return (corte >= 0 ? descripcion.slice(0, corte) : descripcion).trim();
}

function EtiquetaRegla({ codigo, nombreRegla }: { codigo: string; nombreRegla?: string }) {
  const nombre = nombreRegla?.trim();
  return nombre ? (
    <span>
      {nombre} (<span className="silice-codigo">{codigo}</span>)
    </span>
  ) : (
    <span className="silice-codigo">{codigo}</span>
  );
}

interface TablaProps {
  etiqueta: string;
  hallazgos: HallazgoLibroRespuesta[];
  indices: number[];
  seleccionado: number | null;
  alElegir: (indice: number) => void;
  // Para los hallazgos ocultos: que esta oculto.
  motivos?: ReadonlyMap<number, string>;
  // La fila que entra en el orden de Tab (las demas se alcanzan con las flechas).
  paradaDeTab: number | null;
  contextoDeCelda?: (celda: CeldaRef) => string | null;
}

function TablaHallazgos({ etiqueta, hallazgos, indices, seleccionado, alElegir, motivos, paradaDeTab, contextoDeCelda }: TablaProps) {
  const filas = indices.map((indice) => {
    const h = hallazgos[indice];
    const estilo = estiloDeHallazgo(h);
    const motivo = motivos?.get(indice);
    const elegida = seleccionado === indice;
    const celda = elegida && contextoDeCelda ? parsearCelda(h.celda) : null;
    const contexto = celda ? contextoDeCelda?.(celda) : null;
    const accion = elegida ? (h.accion ?? "").trim() : "";
    return {
      id: String(indice),
      hallazgo: (
        <div className="hallazgo">
          <div className="hallazgo__encabezado cds--type-label-01">
            <span className="hallazgo__severidad" style={{ ["--halo-color" as string]: `var(${estilo.token})` }}>
              <IconoDeSeveridad nombre={estilo.icono} size={16} className="hallazgo__icono" />
            </span>
            {h.celda ? <span className="silice-codigo">{h.celda}</span> : <span>Sin celda</span>}
            <span aria-hidden="true"> · </span>
            <span>{estilo.texto}</span>
            <span aria-hidden="true"> · </span>
            <EtiquetaRegla codigo={h.codigo} nombreRegla={h.nombre_regla} />
            {h.impacto !== null && (
              <>
                <span aria-hidden="true"> · </span>
                <span className="silice-cifra">
                  <span className="silice-oculto">Impacto </span>
                  {formatoEsVe(h.impacto)}
                </span>
              </>
            )}
          </div>
          <div className="hallazgo__descripcion cds--type-body-compact-01">{h.descripcion}</div>
          {contexto && <div className="hallazgo__contexto cds--type-label-01">{contexto}</div>}
          {accion && <div className="hallazgo__accion cds--type-label-01">{`Acción: ${accion}`}</div>}
          {motivo && <div className="hallazgo__motivo cds--type-label-01">{motivo}</div>}
        </div>
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
                    <TableHeader key={key} {...resto}>
                      <span className="silice-oculto">{cabecera.header}</span>
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
                    tabIndex={indice === paradaDeTab ? 0 : -1}
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
                      <TableCell key={celda.id}>{celda.value}</TableCell>
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
  causas,
  noAplicables,
  seleccionado,
  enfocar,
  hojas,
  contextoDeCelda,
  filtroInicial,
  alFiltrar,
  irACelda,
  onElegir,
}: Props) {
  const [filtro, setFiltro] = useState<ReadonlySet<Severidad>>(new Set(filtroInicial ?? []));
  const [aviso, setAviso] = useState<string | null>(null);
  // La fila que tuvo el foco por ultimo: es la parada de Tab (roving tabindex).
  const [conFoco, setConFoco] = useState<number | null>(null);
  const raiz = useRef<HTMLElement>(null);
  const idCausas = useId();
  const idUnoPorUno = useId();
  const idNoAplicables = useId();
  const idSinCelda = useId();
  const idOcultos = useId();

  const noAplicablesValidos = useMemo(() => {
    const vistos = new Set<number>();
    const lista: number[] = [];
    for (const i of noAplicables ?? []) {
      if (i >= 0 && i < hallazgos.length && !vistos.has(i)) {
        vistos.add(i);
        lista.push(i);
      }
    }
    return lista;
  }, [noAplicables, hallazgos.length]);

  const noAplicablesSet = useMemo(() => new Set(noAplicablesValidos), [noAplicablesValidos]);
  const aplicablesIndices = useMemo(
    () => hallazgos.map((_, i) => i).filter((i) => !noAplicablesSet.has(i)),
    [hallazgos, noAplicablesSet],
  );

  const { sinCelda, ocultos } = useMemo(() => construirHalos(hallazgos, hojas), [hallazgos, hojas]);
  const hayAtipicos = useMemo(
    () => aplicablesIndices.some((i) => hallazgos[i].codigo === CODIGO_ATIPICO),
    [hallazgos, aplicablesIndices],
  );
  const sinCeldaSet = useMemo(() => new Set(sinCelda), [sinCelda]);
  const motivos = useMemo(() => new Map(ocultos.map((o) => [o.indice, o.motivo])), [ocultos]);
  const ocultosIndices = useMemo(() => ocultos.map((o) => o.indice), [ocultos]);
  const sinCeldaAplicables = useMemo(
    () => sinCelda.filter((i) => !noAplicablesSet.has(i)),
    [sinCelda, noAplicablesSet],
  );
  const ocultosAplicables = useMemo(
    () => ocultosIndices.filter((i) => !noAplicablesSet.has(i)),
    [ocultosIndices, noAplicablesSet],
  );

  const cuentas = useMemo(() => {
    const c: Record<Severidad, number> = { CRITICO: 0, ERROR: 0, ADVERTENCIA: 0, INFO: 0 };
    for (const i of aplicablesIndices) c[severidadDe(hallazgos[i])] += 1;
    return c;
  }, [hallazgos, aplicablesIndices]);

  const pasan = (i: number) => filtro.size === 0 || filtro.has(severidadDe(hallazgos[i]));
  const conCelda = aplicablesIndices.filter((i) => !sinCeldaSet.has(i) && !motivos.has(i) && pasan(i));
  const sinCeldaVisibles = sinCeldaAplicables.filter(pasan);
  const ocultosVisibles = ocultosAplicables.filter(pasan);

  const hayCausas = (causas?.length ?? 0) > 0;
  const causasVisibles = useMemo(
    () => (causas ?? []).filter((c) => filtro.size === 0 || filtro.has(normalizarSeveridad(c.severidad))),
    [causas, filtro],
  );
  const totalCasosCausas = useMemo(() => causasVisibles.reduce((a, c) => a + c.ocurrencias, 0), [causasVisibles]);

  const orden = [...conCelda, ...ocultosVisibles, ...sinCeldaVisibles];
  const paradaDeTab =
    conFoco !== null && orden.includes(conFoco)
      ? conFoco
      : seleccionado !== null && orden.includes(seleccionado)
        ? seleccionado
        : (orden[0] ?? null);

  // Flechas, Inicio y Fin: mueven el foco entre las filas de todos los grupos, en el orden en que se ven.
  const moverConFlechas = (e: KeyboardEvent<HTMLElement>) => {
    const actual = (e.target as HTMLElement).closest<HTMLElement>("tr[data-indice]");
    if (!actual || e.target !== actual) return;
    const filas = [...(raiz.current?.querySelectorAll<HTMLElement>("tr[data-indice]") ?? [])];
    const posicion = filas.indexOf(actual);
    let destino = -1;
    if (e.key === "ArrowDown") destino = Math.min(filas.length - 1, posicion + 1);
    else if (e.key === "ArrowUp") destino = Math.max(0, posicion - 1);
    else if (e.key === "Home") destino = 0;
    else if (e.key === "End") destino = filas.length - 1;
    if (destino < 0) return;
    e.preventDefault();
    filas[destino].focus();
    filas[destino].scrollIntoView?.({ block: "nearest" });
  };

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
    <section
      className="lista-hallazgos"
      aria-label="Hallazgos de la auditoría"
      ref={raiz}
      onKeyDown={moverConFlechas}
      onFocus={(e) => {
        const f = (e.target as HTMLElement).closest<HTMLElement>("tr[data-indice]");
        if (f && e.target === f) setConFoco(Number(f.dataset.indice));
      }}
    >
      <div className="lista-hallazgos__cabecera">
        <h2 className="cds--type-heading-compact-01">Hallazgos ({aplicablesIndices.length})</h2>
        <div className="lista-hallazgos__filtro" role="group" aria-label="Filtrar por severidad">
          {SEVERIDADES.map((clave) => (
            <SelectableTag
              key={clave}
              size="md"
              className={`silice-sev silice-sev--${clave.toLowerCase()}`}
              renderIcon={() => (
                <IconoDeSeveridad nombre={estiloDeSeveridad(clave).icono} size={16} className="silice-sev__icono" />
              )}
              text={`${estiloDeSeveridad(clave).texto} ${cuentas[clave]}`}
              selected={filtro.has(clave)}
              onChange={(activa: boolean) => alternar(clave, activa)}
            />
          ))}
        </div>
        {hayAtipicos && (
          <p className="cds--type-body-compact-01">
            En morado: precios muy distintos al histórico; revise si tienen justificación
          </p>
        )}
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

      {/* Se desplaza: con nombre y en el orden de Tab para leerla con el teclado aunque no traiga filas (axe). */}
      <div className="lista-hallazgos__cuerpo" role="region" aria-label="Lista de hallazgos" tabIndex={0}>
        {aplicablesIndices.length === 0 && (
          <p className="lista-hallazgos__vacio cds--type-body-compact-01">
            La auditoría terminó y el libro no tiene hallazgos.
          </p>
        )}

        {causasVisibles.length > 0 && (
          <section aria-labelledby={idCausas}>
            <h3 id={idCausas} className="lista-hallazgos__subtitulo cds--type-heading-compact-01">
              Por causa raíz ({causasVisibles.length})
            </h3>
            <p className="lista-hallazgos__resumen cds--type-body-compact-01">
              {totalCasosCausas === 1 ? "1 hallazgo viene" : `Los ${totalCasosCausas} hallazgos vienen`} de{" "}
              {causasVisibles.length === 1 ? "1 causa" : `${causasVisibles.length} causas`}: corregir una causa arregla
              todos sus casos.
            </p>
            <ul className="lista-hallazgos__causas">
              {causasVisibles.map((causa, idx) => {
                const estilo = estiloDeSeveridad(normalizarSeveridad(causa.severidad));
                const casos = causa.ocurrencias === 1 ? "1 caso" : `${causa.ocurrencias} casos`;
                const primerIndice = causa.indices[0];
                return (
                  <li key={`${causa.codigo}-${primerIndice ?? idx}`}>
                    <button
                      type="button"
                      className="lista-hallazgos__causa"
                      onClick={() => {
                        if (primerIndice !== undefined) elegir(primerIndice);
                      }}
                    >
                      <span className="hallazgo__encabezado cds--type-label-01">
                        <span
                          className="hallazgo__severidad"
                          style={{ ["--halo-color" as string]: `var(${estilo.token})` }}
                        >
                          <IconoDeSeveridad nombre={estilo.icono} size={16} className="hallazgo__icono" />
                        </span>
                        <span>{estilo.texto}</span>
                        <span aria-hidden="true"> · </span>
                        <span className="silice-cifra">{casos}</span>
                        <span aria-hidden="true"> · </span>
                        <EtiquetaRegla codigo={causa.codigo} nombreRegla={causa.nombre_regla} />
                      </span>
                      <span className="lista-hallazgos__causa-desc cds--type-body-compact-01">
                        {primeraClausula(causa.descripcion)}
                      </span>
                      {causa.observado && causa.esperado && (
                        <span className="lista-hallazgos__causa-traza cds--type-label-01 silice-cifra">
                          {`Encontrado ${formatoEsVe(causa.observado)} · esperado ${formatoEsVe(causa.esperado)}`}
                        </span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>
        )}

        {conCelda.length > 0 && (
          <section
            aria-labelledby={hayCausas ? idUnoPorUno : undefined}
            aria-label={hayCausas ? undefined : "Hallazgos con celda en el libro"}
          >
            {hayCausas && (
              <h3 id={idUnoPorUno} className="lista-hallazgos__subtitulo cds--type-heading-compact-01">
                Uno por uno ({conCelda.length})
              </h3>
            )}
            <TablaHallazgos
              etiqueta="Hallazgos con celda en el libro"
              hallazgos={hallazgos}
              indices={conCelda}
              seleccionado={seleccionado}
              alElegir={elegir}
              paradaDeTab={paradaDeTab}
              contextoDeCelda={contextoDeCelda}
            />
          </section>
        )}

        {ocultosAplicables.length > 0 && (
          <section aria-labelledby={idOcultos}>
            <h3 id={idOcultos} className="lista-hallazgos__subtitulo cds--type-heading-compact-01">
              En hoja, fila o columna oculta ({ocultosAplicables.length})
            </h3>
            {ocultosVisibles.length > 0 && (
              <TablaHallazgos
                etiqueta="Hallazgos en una hoja, fila o columna oculta"
                hallazgos={hallazgos}
                indices={ocultosVisibles}
                seleccionado={seleccionado}
                alElegir={elegir}
                motivos={motivos}
                paradaDeTab={paradaDeTab}
                contextoDeCelda={contextoDeCelda}
              />
            )}
          </section>
        )}

        {sinCeldaAplicables.length > 0 && (
          <section aria-labelledby={idSinCelda}>
            <h3 id={idSinCelda} className="lista-hallazgos__subtitulo cds--type-heading-compact-01">
              Sin celda en el libro ({sinCeldaAplicables.length})
            </h3>
            {sinCeldaVisibles.length > 0 && (
              <TablaHallazgos
                etiqueta="Hallazgos sin celda en el libro"
                hallazgos={hallazgos}
                indices={sinCeldaVisibles}
                seleccionado={seleccionado}
                alElegir={elegir}
                paradaDeTab={paradaDeTab}
                contextoDeCelda={contextoDeCelda}
              />
            )}
          </section>
        )}

        {noAplicablesValidos.length > 0 && (
          <section aria-labelledby={idNoAplicables}>
            <h3 id={idNoAplicables} className="lista-hallazgos__subtitulo cds--type-heading-compact-01">
              Reglas que no aplicaron a este libro ({noAplicablesValidos.length})
            </h3>
            <p className="lista-hallazgos__resumen cds--type-body-compact-01">
              No son errores: la regla no tenía nada que revisar en este libro.
            </p>
            <ul className="lista-hallazgos__no-aplicables">
              {noAplicablesValidos.map((indice) => {
                const h = hallazgos[indice];
                return (
                  <li key={indice} className="lista-hallazgos__no-aplicable">
                    <div className="hallazgo__encabezado cds--type-label-01">
                      <EtiquetaRegla codigo={h.codigo} nombreRegla={h.nombre_regla} />
                    </div>
                    <div className="cds--type-body-compact-01">{h.descripcion}</div>
                  </li>
                );
              })}
            </ul>
          </section>
        )}
      </div>
    </section>
  );
}
