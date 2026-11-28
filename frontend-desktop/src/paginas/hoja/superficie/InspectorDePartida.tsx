import { Button } from "@carbon/react";
import { useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { JSX } from "react";
import { ErrorDeApi, pedir } from "../../../api/cliente";
import { useAnunciar } from "../../../comun/Anunciador";
import { AvisoError } from "../../../comun/AvisoError";
import { Dialogo } from "../../../comun/Dialogo";
import { textoDeEquivalencia } from "../../../comun/LineaDeEquivalencia";
import { MontoExacto } from "../../../comun/MontoExacto";
import { PanelLateral } from "../../../comun/PanelLateral";
import { invalidarRecursos } from "../../../comun/recurso";
import { unidadEscrita } from "../../../comun/unidades";
import { formatoEsVe } from "../../../indicadores/formatoEsVe";
import { useAplicacion } from "../../../shell/contexto";
import { EditorDeApu } from "../EditorDeApu";
import { AYUDA_OBJETIVO, consultasDeObjetivos, margenEsVe } from "../ObjetivoDeMercado";
import type { ObjetivoDeMercado } from "../ObjetivoDeMercado";
import { ContextoDeLaHoja } from "../ProveedorDeLaHoja";
import type { HojaDeLaObra } from "../ProveedorDeLaHoja";
import { esperarEnvios } from "../envioPendiente";
import { PESTANAS, comoSeMidio, esBorradorAusente, rutaDeQuitarPartida, rutaDeVista } from "../logica";
import type { BorradorAbierto, FilaPresupuesto, RespuestaDeEdicion, Resumen } from "../logica";
import { claseDeConflicto, rutaDeCantidades } from "../logicaSecciones";
import { usePuedeEditarLaHoja } from "../puedeEditar";
import type { FilaDeLaGrilla } from "./logica";
import type { CantidadesDeLaSuperficie } from "./useCantidadesDeLaSuperficie";
import "./inspector.scss";

// Inspector lateral acoplado de una partida del Presupuesto (lote B1-6, ficha-b1 §1.6, §1.10 prueba 7 y §4).
// Guías `dialog` («Use for … inspectors…», «DO include a visible close button in every non-modal dialog», «autofocus on
// the safe action») y `html` (región `<aside>` con un encabezado de segundo nivel, sin trampa de foco cuando va acoplado).

export type AccionarEnOrden = CantidadesDeLaSuperficie["accionarEnOrden"];

export interface PropiedadesDeInspectorDePartida {
  readonly borrador: BorradorAbierto | null;
  readonly fila: FilaPresupuesto | FilaDeLaGrilla | null;
  readonly moneda?: string | undefined;
  readonly puedeEditar?: boolean | undefined;
  // Celda de la grilla que abrió el inspector: Esc y «Cerrar» le devuelven el foco.
  readonly celdaOrigen?: HTMLElement | null | undefined;
  // Objetivo de mercado ya leído para la partida; si se omite, el inspector lo pide a `/v1/mercado/objetivos`.
  readonly objetivoDeMercado?: ObjetivoDeMercado | null | undefined;
  readonly alCerrar: () => void;
  readonly alAceptar?: ((resumen: Resumen) => void) | undefined;
  readonly alVolverALaCalculada?: ((clave: string, cantidadCalculada: string) => void) | undefined;
  readonly alQuitar?: ((partida: string, resumen: Resumen, clave: string) => void) | undefined;
  // La cola de las cantidades de la grilla (`useCantidadesDeLaSuperficie().accionarEnOrden`). Con ella, «Quitar» espera lo
  // escrito, no sale si el servidor lo rechazó y no se pisa el `rev` con una cantidad nueva. Sin ella (el inspector suelto)
  // se vacía lo pendiente con `esperarEnvios` y el POST sale solo.
  readonly alAccionarEnOrden?: AccionarEnOrden | undefined;
  readonly alAusente?: (() => void) | undefined;
  readonly alRecargarBorrador?: (() => Promise<void>) | undefined;
  readonly alReabrir?: (() => void) | undefined;
}

interface RespuestaObjetivos {
  objetivos?: ObjetivoDeMercado[];
}

const sinAccion = () => {};
const sinPromesa = async () => {};

function esFilaDeLaGrilla(entrada: FilaPresupuesto | FilaDeLaGrilla): entrada is FilaDeLaGrilla {
  return "fila" in entrada && "puTexto" in entrada;
}

function resolverFila(entrada: FilaPresupuesto | FilaDeLaGrilla | null): FilaPresupuesto | null {
  if (entrada === null) return null;
  return esFilaDeLaGrilla(entrada) ? entrada.fila : entrada;
}

function tituloDelInspector(fila: FilaPresupuesto): string {
  const unidad = unidadEscrita(fila.unidad).trim();
  const descripcion = fila.descripcion.trim();
  const partes = [fila.partida];
  if (descripcion !== "") partes.push(descripcion);
  if (unidad !== "") partes.push(unidad);
  return partes.join(" · ");
}

/** Construye la línea de resumen sobre cómo se midió la partida y si su cantidad se escribió a mano (§1.6). */
export function resumenDeMedicion(
  fila: Pick<FilaPresupuesto, "quitable" | "calculo" | "nota" | "de_tramo" | "escrita">,
): string {
  const medicion = comoSeMidio(fila);
  if (medicion.calculo !== null) {
    return fila.escrita
      ? `Con cálculo: ${medicion.calculo}; cantidad escrita a mano`
      : `Con cálculo: ${medicion.calculo}`;
  }
  if (fila.escrita) {
    return "Medida sin cálculo; cantidad escrita a mano";
  }
  if (medicion.texto !== null) {
    return medicion.texto;
  }
  return "Medida con nota";
}

function textoDelObjetivo(
  objetivo: ObjetivoDeMercado | null,
  puExacto: string | null,
  moneda: string,
): string {
  if (objetivo === null) return "Sin objetivo de mercado";
  const precio = formatoEsVe(objetivo.precio);
  const margen =
    objetivo.margen !== null && puExacto !== null ? ` · margen ${margenEsVe(objetivo.margen)}` : " · sin margen";
  if (objetivo.moneda !== moneda) {
    if (objetivo.equivalencia) {
      const sufijo = puExacto === null ? " · sin precio unitario, sin margen" : margen;
      return `${textoDeEquivalencia(objetivo.equivalencia)}${sufijo}`;
    }
    const motivo = objetivo.sin_tasa ? objetivo.sin_tasa : `en otra moneda que la obra (${moneda})`;
    return `${precio} ${objetivo.moneda} · ${motivo}, sin margen`;
  }
  if (puExacto === null) return `${precio} · sin precio unitario, sin margen`;
  return `${precio}${margen}`;
}

function crearHojaDeRespaldo(
  borrador: BorradorAbierto,
  puedeEditar: boolean,
  alAceptar: (resumen: Resumen) => void,
  alRecargarBorrador: () => Promise<void>,
  alReabrir: () => void,
): HojaDeLaObra {
  return {
    pestana: "partidas",
    irAPestana: sinAccion,
    visibles: PESTANAS,
    espacioPedido: false,
    pedirEspacio: sinAccion,
    partidaElegida: null,
    elegirPartida: sinAccion,
    proyecto: borrador.base.proyecto,
    nombreProyecto: null,
    versiones: { estado: "cargando" },
    codigo: borrador.base.version,
    estado: { estado: "listo", borrador },
    hayCambios: borrador.resumen.cambios > 0,
    puedeEditar,
    nadaQueRevisar: false,
    ofrecidos: [],
    retomar: sinAccion,
    descartarOfrecidos: sinPromesa,
    descartando: false,
    falloAlDescartar: null,
    existente: null,
    pedirVersion: sinAccion,
    refrescar: alRecargarBorrador,
    relecturasDelDesglose: 0,
    aplicar: alAceptar,
    reabrirNuevo: alReabrir,
    descartarCambios: sinPromesa,
    abrirGuardado: sinAccion,
    alCrearVersion: sinPromesa,
    exito: null,
    quitarExito: sinAccion,
    inerte: false,
  };
}

/** Inspector lateral no modal de una partida del Presupuesto (lote B1-6). */
export function InspectorDePartida({
  borrador,
  fila: entradaFila,
  moneda,
  puedeEditar,
  celdaOrigen,
  objetivoDeMercado,
  alCerrar,
  alAceptar,
  alVolverALaCalculada,
  alQuitar,
  alAccionarEnOrden,
  alAusente,
  alRecargarBorrador,
  alReabrir,
}: PropiedadesDeInspectorDePartida): JSX.Element | null {
  const { alExpirar } = useAplicacion();
  const anunciar = useAnunciar();
  const hojaEnContexto = useContext(ContextoDeLaHoja);
  const permiso = usePuedeEditarLaHoja(borrador?.base ?? null);
  const puedeEditarEfectivo = (puedeEditar ?? permiso) && permiso;

  const fila = resolverFila(entradaFila);
  const abierto = borrador !== null && fila !== null;
  const monedaEfectiva = (moneda ?? borrador?.resumen.moneda ?? borrador?.base.moneda ?? "").trim();

  const refCeldaOrigen = useRef<HTMLElement | null>(null);
  const refBotonQuitar = useRef<HTMLButtonElement>(null);
  const devolverFocoAQuitar = useRef(false);

  const claveDeFila = fila?.clave ?? null;
  const [confirmandoEnClave, setConfirmandoEnClave] = useState<string | null>(null);
  const [quitando, setQuitando] = useState(false);
  const [volviendoACalculada, setVolviendoACalculada] = useState(false);
  const [errorEnClave, setErrorEnClave] = useState<{ clave: string; error: unknown } | null>(null);
  const [objetivoLeido, setObjetivoLeido] = useState<{
    clave: string;
    objetivo: ObjetivoDeMercado | null;
  } | null>(null);

  const confirmandoQuitar = claveDeFila !== null && confirmandoEnClave === claveDeFila;
  const errorDeAccion = claveDeFila !== null && errorEnClave?.clave === claveDeFila ? errorEnClave.error : null;

  useLayoutEffect(() => {
    if (celdaOrigen !== undefined && celdaOrigen !== null) {
      refCeldaOrigen.current = celdaOrigen;
    }
  }, [celdaOrigen]);

  // Al cerrarse o desmontarse abierto, si se recibió la celda de origen por props, el foco vuelve a ella (después del
  // efecto de PanelLateral, para que prevalezca incluso cuando el inspector se abrió sin que la celda tuviera document.activeElement).
  useEffect(() => {
    if (!abierto) return;
    return () => {
      const celda = refCeldaOrigen.current;
      if (celda !== null && celda.isConnected) {
        celda.focus();
      }
    };
  }, [abierto]);

  // Al cancelar el diálogo destructivo de quitar, el foco regresa al botón «Quitar del presupuesto» del inspector.
  useEffect(() => {
    if (confirmandoQuitar || !devolverFocoAQuitar.current) return;
    devolverFocoAQuitar.current = false;
    refBotonQuitar.current?.focus();
  }, [confirmandoQuitar]);

  // Consulta del objetivo de mercado de la partida abierta cuando no viene dado por props.
  const consultaObjetivo = useMemo(() => {
    if (fila === null || objetivoDeMercado !== undefined) return null;
    const { rutas } = consultasDeObjetivos([fila], monedaEfectiva);
    return {
      ruta: rutas[0] ?? null,
      codigo: fila.partida,
      clave: `${fila.partida}|${fila.pu?.exacto ?? ""}|${monedaEfectiva}`,
    };
  }, [fila, monedaEfectiva, objetivoDeMercado]);

  useEffect(() => {
    if (consultaObjetivo === null || consultaObjetivo.ruta === null) return;
    const { ruta, codigo, clave } = consultaObjetivo;
    let vigente = true;
    pedir<RespuestaObjetivos>(ruta).then(
      (respuesta) => {
        if (!vigente) return;
        const hallado = (respuesta?.objetivos ?? []).find((o) => o.codigo === codigo) ?? null;
        setObjetivoLeido({ clave, objetivo: hallado });
      },
      (e: unknown) => {
        if (!vigente) return;
        if (e instanceof ErrorDeApi && e.estado === 401) {
          alExpirar();
          return;
        }
        setObjetivoLeido({ clave, objetivo: null });
      },
    );
    return () => {
      vigente = false;
    };
  }, [consultaObjetivo, alExpirar]);

  const manejarAceptar = useCallback(
    (resumen: Resumen) => {
      alAceptar?.(resumen);
      hojaEnContexto?.aplicar(resumen);
    },
    [alAceptar, hojaEnContexto],
  );

  const manejarAusente = useCallback(() => {
    if (alAusente !== undefined) {
      alAusente();
    } else {
      void hojaEnContexto?.refrescar();
    }
  }, [alAusente, hojaEnContexto]);

  const manejarRecargarBorrador = useCallback(async () => {
    if (alRecargarBorrador !== undefined) {
      await alRecargarBorrador();
    } else if (hojaEnContexto !== null) {
      await hojaEnContexto.refrescar();
    }
  }, [alRecargarBorrador, hojaEnContexto]);

  const manejarReabrir = useCallback(() => {
    if (alReabrir !== undefined) {
      alReabrir();
    } else {
      hojaEnContexto?.reabrirNuevo();
    }
  }, [alReabrir, hojaEnContexto]);

  const hojaEfectiva = useMemo<HojaDeLaObra | null>(() => {
    if (hojaEnContexto !== null) return hojaEnContexto;
    if (borrador === null) return null;
    return crearHojaDeRespaldo(
      borrador,
      puedeEditarEfectivo,
      manejarAceptar,
      manejarRecargarBorrador,
      manejarReabrir,
    );
  }, [hojaEnContexto, borrador, puedeEditarEfectivo, manejarAceptar, manejarRecargarBorrador, manejarReabrir]);

  const manejarCerrar = useCallback(() => {
    alCerrar();
    const celda = celdaOrigen ?? refCeldaOrigen.current;
    if (celda !== null && celda.isConnected) {
      celda.focus();
    }
  }, [alCerrar, celdaOrigen]);

  const cancelarQuitar = useCallback(() => {
    if (quitando) return;
    devolverFocoAQuitar.current = true;
    setConfirmandoEnClave(null);
  }, [quitando]);

  async function resolverRevActual(actual: BorradorAbierto): Promise<number> {
    const pendientes = await esperarEnvios(actual.id);
    let rev = actual.resumen.rev;
    for (const r of pendientes) {
      if (r !== null) rev = r.rev;
    }
    return rev;
  }

  async function manejarVolverALaCalculada() {
    if (borrador === null || fila === null || !puedeEditarEfectivo) return;
    if (alVolverALaCalculada !== undefined) {
      alVolverALaCalculada(fila.clave, fila.cantidad_calculada);
      return;
    }
    setErrorEnClave(null);
    setVolviendoACalculada(true);
    try {
      const rev = await resolverRevActual(borrador);
      const respuesta = await pedir<RespuestaDeEdicion>(rutaDeCantidades(borrador.id), {
        metodo: "PUT",
        cuerpo: { rev, filas: [{ clave: fila.clave, cantidad: fila.cantidad_calculada }] },
      });
      invalidarRecursos(rutaDeVista(borrador.id, "presupuesto"));
      invalidarRecursos(rutaDeVista(borrador.id, "auditoria"));
      manejarAceptar(respuesta.resumen);
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) {
        alExpirar();
      } else if (esBorradorAusente(e)) {
        manejarAusente();
      } else {
        setErrorEnClave({ clave: fila.clave, error: e });
        if (e instanceof ErrorDeApi && e.estado === 409 && claseDeConflicto(e.detalle) === "rev") {
          await manejarRecargarBorrador();
        }
      }
    } finally {
      setVolviendoACalculada(false);
    }
  }

  // «Quitar» dentro de la cola de las cantidades (B1-6): lo escrito que espera la pausa sale antes, lo que se escriba mientras el
  // POST va en vuelo espera a su `rev`, y si el servidor rechazó lo escrito el POST no sale. El error de cualquiera de las dos
  // peticiones (409, 422…) lo deja el motor en el aviso de la grilla, igual que el de una celda; aquí solo se cierra el diálogo.
  async function quitarEnLaCola(alAccionar: AccionarEnOrden, actual: BorradorAbierto, filaActual: FilaPresupuesto) {
    const resumen = await alAccionar((rev) => ({
      ruta: rutaDeQuitarPartida(actual.id),
      metodo: "POST",
      cuerpo: { rev, clave: filaActual.clave },
      frase: "",
    }));
    setConfirmandoEnClave(null);
    if (resumen === null) {
      devolverFocoAQuitar.current = true;
      return;
    }
    invalidarRecursos(rutaDeVista(actual.id, "presupuesto"));
    invalidarRecursos(rutaDeVista(actual.id, "auditoria"));
    alQuitar?.(filaActual.partida, resumen, filaActual.clave);
    anunciar(`Se quitó ${filaActual.partida} del presupuesto.`);
    manejarCerrar();
  }

  async function confirmarQuitar() {
    if (borrador === null || fila === null || quitando) return;
    setErrorEnClave(null);
    setQuitando(true);
    if (alAccionarEnOrden !== undefined) {
      try {
        await quitarEnLaCola(alAccionarEnOrden, borrador, fila);
      } finally {
        setQuitando(false);
      }
      return;
    }
    try {
      const rev = await resolverRevActual(borrador);
      const respuesta = await pedir<RespuestaDeEdicion>(rutaDeQuitarPartida(borrador.id), {
        metodo: "POST",
        cuerpo: { rev, clave: fila.clave },
      });
      setConfirmandoEnClave(null);
      invalidarRecursos(rutaDeVista(borrador.id, "presupuesto"));
      invalidarRecursos(rutaDeVista(borrador.id, "auditoria"));
      manejarAceptar(respuesta.resumen);
      alQuitar?.(fila.partida, respuesta.resumen, fila.clave);
      anunciar(`Se quitó ${fila.partida} del presupuesto.`);
      manejarCerrar();
    } catch (e) {
      setConfirmandoEnClave(null);
      devolverFocoAQuitar.current = true;
      if (e instanceof ErrorDeApi && e.estado === 401) {
        alExpirar();
      } else if (esBorradorAusente(e)) {
        manejarAusente();
      } else {
        setErrorEnClave({ clave: fila.clave, error: e });
        if (e instanceof ErrorDeApi && e.estado === 409 && claseDeConflicto(e.detalle) === "rev") {
          await manejarRecargarBorrador();
        }
      }
    } finally {
      setQuitando(false);
    }
  }

  if (!abierto || borrador === null || fila === null) {
    return null;
  }

  const medicion = comoSeMidio(fila);
  const unidadLegible = unidadEscrita(fila.unidad).trim();
  const cantidadCalculadaTexto =
    unidadLegible !== ""
      ? `${formatoEsVe(fila.cantidad_calculada)} ${unidadLegible}`
      : formatoEsVe(fila.cantidad_calculada);

  const objetivoActual: ObjetivoDeMercado | null =
    objetivoDeMercado !== undefined
      ? objetivoDeMercado
      : consultaObjetivo !== null && objetivoLeido?.clave === consultaObjetivo.clave
        ? objetivoLeido.objetivo
        : null;

  return (
    <>
      <PanelLateral
        titulo={tituloDelInspector(fila)}
        abierto={abierto}
        alCerrar={manejarCerrar}
        ancho="ancho"
        modo="acoplado"
      >
        <div className="silice-inspector">
          <p className="silice-inspector__resumen cds--type-body-compact-01">{resumenDeMedicion(fila)}</p>

          {errorDeAccion !== null && (
            <AvisoError error={errorDeAccion} titulo="No se pudo aplicar el cambio en la partida" />
          )}

          <dl className="silice-inspector__datos">
            <div className="silice-inspector__campo">
              <dt className="silice-inspector__rotulo cds--type-helper-text-01">Cómo se midió</dt>
              <dd className="silice-inspector__valor cds--type-body-compact-01">
                <div className="silice-inspector__medicion">
                  {medicion.calculo !== null && (
                    <span>
                      <span className="cds--visually-hidden">Cálculo: </span>
                      <code className="silice-codigo">{medicion.calculo}</code>
                    </span>
                  )}
                  {medicion.nota !== null && <span>{medicion.nota}</span>}
                  {medicion.texto !== null && <span>{medicion.texto}</span>}
                </div>
              </dd>
            </div>

            <div className="silice-inspector__campo">
              <dt className="silice-inspector__rotulo cds--type-helper-text-01">Cantidad calculada</dt>
              <dd className="silice-inspector__valor cds--type-body-compact-01">
                <div className="silice-inspector__calculada">
                  <span>{cantidadCalculadaTexto}</span>
                  {fila.escrita && puedeEditarEfectivo && (
                    <Button
                      kind="tertiary"
                      size="sm"
                      disabled={volviendoACalculada}
                      onClick={() => void manejarVolverALaCalculada()}
                    >
                      Volver a la calculada
                    </Button>
                  )}
                </div>
              </dd>
            </div>

            <div className="silice-inspector__campo">
              <dt className="silice-inspector__rotulo cds--type-helper-text-01">Precio unitario</dt>
              <dd className="silice-inspector__valor cds--type-body-compact-01">
                {fila.pu === null ? (
                  "Pendiente"
                ) : (
                  <MontoExacto
                    texto={fila.pu.texto}
                    exacto={fila.pu.exacto}
                    unidad={monedaEfectiva !== "" ? monedaEfectiva : undefined}
                    enLinea
                  />
                )}
              </dd>
            </div>

            <div className="silice-inspector__campo">
              <dt className="silice-inspector__rotulo cds--type-helper-text-01">Total</dt>
              <dd className="silice-inspector__valor cds--type-body-compact-01">
                {fila.total === null ? (
                  "Pendiente"
                ) : (
                  <MontoExacto
                    texto={fila.total.texto}
                    exacto={fila.total.exacto}
                    unidad={monedaEfectiva !== "" ? monedaEfectiva : undefined}
                    enLinea
                  />
                )}
              </dd>
            </div>

            <div className="silice-inspector__campo">
              <dt className="silice-inspector__rotulo cds--type-helper-text-01">Objetivo de mercado</dt>
              <dd className="silice-inspector__valor cds--type-body-compact-01">
                <span>{textoDelObjetivo(objetivoActual, fila.pu?.exacto ?? null, monedaEfectiva)}</span>
                {objetivoActual !== null && (
                  <p className="silice-inspector__ayuda cds--type-helper-text-01">{AYUDA_OBJETIVO}</p>
                )}
              </dd>
            </div>
          </dl>

          <section className="silice-inspector__apu" aria-label={`Análisis de precio unitario de ${fila.partida}`}>
            <h3 className="silice-inspector__apu-titulo cds--type-heading-compact-01">
              Análisis de precio unitario (APU)
            </h3>
            {hojaEfectiva !== null && (
              <ContextoDeLaHoja.Provider value={hojaEfectiva}>
                <EditorDeApu
                  key={fila.partida}
                  borrador={borrador}
                  partida={fila.partida}
                  alAceptar={manejarAceptar}
                  alAusente={manejarAusente}
                />
              </ContextoDeLaHoja.Provider>
            )}
          </section>

          {puedeEditarEfectivo && fila.quitable && (
            <div className="silice-inspector__acciones">
              <Button
                ref={refBotonQuitar}
                kind="danger--tertiary"
                size="sm"
                disabled={quitando}
                onClick={() => {
                  setErrorEnClave(null);
                  setConfirmandoEnClave(fila.clave);
                }}
              >
                Quitar del presupuesto
              </Button>
            </div>
          )}
        </div>
      </PanelLateral>

      <Dialogo
        abierto={confirmandoQuitar}
        titulo="Quitar partida"
        alCerrar={cancelarQuitar}
        enviando={quitando}
        destructivo
        pie={
          <>
            <Button kind="secondary" size="md" disabled={quitando} onClick={cancelarQuitar}>
              Cancelar
            </Button>
            <Button kind="danger" size="md" disabled={quitando} onClick={() => void confirmarQuitar()}>
              Quitar
            </Button>
          </>
        }
      >
        <p className="cds--type-body-compact-01">
          {`¿Quitar ${fila.partida} del presupuesto? Lo puede descartar antes de guardar.`}
        </p>
      </Dialogo>
    </>
  );
}
