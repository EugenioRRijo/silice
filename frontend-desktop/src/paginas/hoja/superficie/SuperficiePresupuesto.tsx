import { Button } from "@carbon/react";
import { useCallback, useContext, useEffect, useId, useRef, useState } from "react";
import type { JSX } from "react";
import { createPortal } from "react-dom";
import { Link, useInRouterContext } from "react-router";
import { ErrorDeApi, pedir } from "../../../api/cliente";
import type { InformeAuditoriaRespuesta } from "../../../api/tipos";
import { AvisoError } from "../../../comun/AvisoError";
import { EstadoVacio } from "../../../comun/EstadoVacio";
import { Grilla } from "../../../comun/Grilla";
import type { ColumnaDeGrilla } from "../../../comun/Grilla";
import { MontoExacto } from "../../../comun/MontoExacto";
import { rutaDeVista } from "../../../comun/borradorAbierto";
import { useRecurso } from "../../../comun/recurso";
import { formatoEsVe } from "../../../indicadores/formatoEsVe";
import { SUBVISTAS } from "../../../marco/espacios";

// La subvista «Espacio, plan y ajustes» (B1-10): la que monta la página de las pestañas de antes.
const SUBVISTA_DE_PESTANAS = SUBVISTAS.presupuesto?.find((v) => v.pagina === "hoja_pestanas")?.id;
import { ContextoDeLaObra } from "../../../marco/obraAbierta";
import { rutaDeObra } from "../../../marco/secciones";
import { useAplicacion } from "../../../shell/contexto";
import type { PartidaCompuesta } from "../../componer/ComponerPartida";
import { porcentajeDeAlicuota } from "../../control/logica";
import { AvisoDeEdicion } from "../AvisoDeEdicion";
import { BotonExcel } from "../BotonExcel";
import { ComponerEnPanel } from "../ComponerEnPanel";
import type { PartidaPorComponer } from "../ComponerEnPanel";
import { ContextoDeDialogos } from "../ContextoDeDialogos";
import { FranjaDelPresupuesto } from "../FranjaDelPresupuesto";
import { leerInforme, leerVistaPresupuesto } from "../analizadores";
import { esBorradorAusente } from "../logica";
import type { BorradorAbierto, Hallazgos, Resumen, VistaPresupuesto } from "../logica";
import { CAUSA_SOLO_LECTURA } from "../logicaGuardar";
import { usePuedeEditarLaHoja } from "../puedeEditar";
import { TEXTOS_DEL_IVA } from "../textos";
import { FilaDeAlta } from "./FilaDeAlta";
import { InspectorDeFrentes } from "./InspectorDeFrentes";
import { InspectorDePartida } from "./InspectorDePartida";
import { InspectorDeProblemas } from "./InspectorDeProblemas";
import { MasAcciones } from "./MasAcciones";
import { columnasDePresupuesto } from "./columnas";
import { useCantidadesDeLaSuperficie } from "./useCantidadesDeLaSuperficie";
import { cuentaDeProblemas, filasDeLaGrilla, fraseDeRespuesta } from "./logica";
import type { FilaDeLaGrilla, RevisionDeLaSuperficie } from "./logica";
import "./superficie.scss";

// La superficie del Presupuesto (lotes B1-4 a B1-10, ficha-b1 §1.8 y §4).
// Lee la vista (`GET /v1/hoja/borradores/{id}/vistas/presupuesto`) y la revisión (`.../vistas/auditoria`) mediante
// `useRecurso` con la clave `ruta@rev`. Presenta cabecera fija, frase de respuesta antes de la grilla, `Grilla` y `tfoot` con
// el total sin IVA (`MontoExacto`) y el IVA calculados por el servidor. Con permiso de edición junta lo que construyeron los
// lotes B1-5 a B1-9: las celdas de cantidad, el inspector de la partida, el de problemas y la fila de alta. «Crear la partida»
// usa el plan B de la ficha (R1, §5): el panel de Componer de siempre, sin un inspector nuevo.

export interface PropiedadesDeSuperficiePresupuesto {
  readonly proyecto: string;
  readonly borrador: BorradorAbierto | null;
  readonly puedeEditar?: boolean | undefined;
  readonly alAusente: () => void;
  readonly alGuardar?: (() => void) | undefined;
  readonly alDescartar?: (() => void) | undefined;
  readonly alReabrir?: (() => void) | undefined;
  readonly alAgregarPartida?: (() => void) | undefined;
  readonly alHacerVersionNueva?: (() => void) | undefined;
  readonly alAbrirProblemas?: (() => void) | undefined;
  readonly alIrAArchivos?: (() => void) | undefined;
  // B1-10: lo que lo conecta con la página. El servidor aceptó una edición: la página sube su `rev` y su resumen.
  readonly alAceptar?: ((resumen: Resumen) => void) | undefined;
  // Vuelve a leer el borrador del servidor (su `rev` y su resumen), tras un 409 por `rev` viejo.
  readonly alRecargarBorrador?: (() => Promise<void>) | undefined;
  // La partida con la que se llega desde la subvista Componer («Agregar X al presupuesto»): queda elegida en la fila de alta
  // con el foco en su Cantidad, y se avisa una vez (`alConsumirPartidaInicial`) para que la página la suelte.
  readonly partidaInicial?: PartidaCompuesta | null | undefined;
  readonly alConsumirPartidaInicial?: (() => void) | undefined;
  // Se llega desde «Ver en el presupuesto» de Archivos y planos: el foco va a la grilla en cuanto llega la vista, y se avisa
  // una vez (`alEnfocarGrilla`).
  readonly enfocarGrilla?: boolean | undefined;
  readonly alEnfocarGrilla?: (() => void) | undefined;
}

const NOTA_SOLO_LECTURA = "Está viendo este presupuesto en solo lectura.";
const FILAS_DE_ESQUELETO = [0, 1, 2, 3, 4] as const;
const SEVERIDADES_DE_PROBLEMA = new Set(["CRITICO", "CRÍTICO", "ERROR", "ADVERTENCIA"]);
const sinAccion = () => {};
const sinPromesa = async () => {};
// La posición de «Cantidad» entre las columnas de la grilla: a esa celda va el foco al agregar una partida.
const COLUMNA_DE_CANTIDAD = 3;

function contarHallazgosDelResumen(hallazgos: readonly Hallazgos[]): number {
  let total = 0;
  for (const h of hallazgos) {
    if (SEVERIDADES_DE_PROBLEMA.has(h.severidad.trim().toUpperCase())) {
      total += h.total;
    }
  }
  return total;
}

function EsqueletoDePresupuesto({ columnas }: { columnas: readonly ColumnaDeGrilla<FilaDeLaGrilla>[] }): JSX.Element {
  return (
    <section className="silice-superficie__esqueleto" aria-label="Cargando el presupuesto" aria-busy="true">
      <div className="silice-superficie__esqueleto-estado">
        <progress aria-label="Cargando el presupuesto" className="silice-superficie__progreso" />
        <span className="cds--type-body-compact-01">Cargando el presupuesto…</span>
      </div>
      <div className="silice-grilla">
        <table className="silice-grilla__tabla" aria-label="Presupuesto">
          <thead>
            <tr>
              {columnas.map((c, j) => (
                <th
                  key={c.clave}
                  scope="col"
                  className={[
                    "silice-grilla__cabecera",
                    j === 0 ? "silice-grilla__celda--fija" : "",
                    c.numerica ? "silice-grilla__celda--numerica" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                >
                  {c.titulo}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {FILAS_DE_ESQUELETO.map((indice) => (
              <tr key={indice} className="silice-grilla__fila">
                {columnas.map((c, j) =>
                  j === 0 ? (
                    <th key={c.clave} scope="row" className="silice-grilla__celda silice-grilla__celda--fija">
                      <span className="silice-superficie__esqueleto-barra" aria-hidden="true" />
                    </th>
                  ) : (
                    <td
                      key={c.clave}
                      className={c.numerica ? "silice-grilla__celda silice-grilla__celda--numerica" : "silice-grilla__celda"}
                    >
                      <span className="silice-superficie__esqueleto-barra" aria-hidden="true" />
                    </td>
                  ),
                )}
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row" colSpan={5} className="silice-superficie__pie-rotulo">
                Total sin IVA
              </th>
              <td className="silice-grilla__celda--numerica silice-superficie__pie-monto">Calculando…</td>
              <td />
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  );
}

function PieDelPresupuesto({ vista }: { vista: VistaPresupuesto }): JSX.Element {
  const moneda = vista.moneda.trim();
  const sufijo = moneda !== "" ? ` ${moneda}` : "";
  const porcentaje = porcentajeDeAlicuota(vista.impuestos.alicuota);
  return (
    <>
      <tr>
        <th scope="row" colSpan={5} className="silice-superficie__pie-rotulo">
          Total sin IVA
        </th>
        <td className="silice-grilla__celda--numerica silice-superficie__pie-monto">
          <MontoExacto
            texto={vista.total.texto}
            exacto={vista.total.exacto}
            unidad={moneda !== "" ? moneda : undefined}
            nombre="del total sin IVA"
          />
        </td>
        <td />
      </tr>
      <tr>
        <th scope="row" colSpan={5} className="silice-superficie__pie-rotulo">
          {TEXTOS_DEL_IVA.iva(porcentaje)}
        </th>
        <td className="silice-grilla__celda--numerica silice-superficie__pie-monto">
          {`${formatoEsVe(vista.impuestos.iva)}${sufijo}`}
        </td>
        <td />
      </tr>
      <tr>
        <th scope="row" colSpan={5} className="silice-superficie__pie-rotulo silice-superficie__pie-total">
          {TEXTOS_DEL_IVA.totalConIva}
        </th>
        <td className="silice-grilla__celda--numerica silice-superficie__pie-monto silice-superficie__pie-total">
          {`${formatoEsVe(vista.impuestos.total)}${sufijo}`}
        </td>
        <td />
      </tr>
    </>
  );
}

function SuperficieSinBorrador(): JSX.Element {
  return (
    <div className="silice-superficie">
      <div className="silice-hoja__cabecera-fija">
        <p className="silice-hoja__total cds--type-heading-compact-02">Total sin IVA: Calculando…</p>
      </div>
      <EsqueletoDePresupuesto columnas={columnasDePresupuesto()} />
    </div>
  );
}

// Qué panel está abierto junto a la grilla: uno solo a la vez.
type PanelAbierto =
  | { tipo: "partida"; clave: string; celda: HTMLElement | null }
  | { tipo: "problemas" }
  | { tipo: "frentes" }
  | null;

// A qué celda se lleva el foco cuando llegue la vista nueva: `base` es la vista que había al pedirlo (la nueva es otra), y
// `clave` la fila cuya Cantidad se enfoca (sin ella, la celda activa de la grilla).
interface PedidoDeFoco {
  readonly base: VistaPresupuesto | null;
  readonly clave: string | null;
}

// Lo que se hace al cerrarse la capa de Componer, cuando la página ya dejó de ser inerte y se puede enfocar.
type AlVolverDeComponer = { tipo: "partida" } | { tipo: "compuesta"; partida: PartidaCompuesta };

type PropiedadesAbiertas = Omit<PropiedadesDeSuperficiePresupuesto, "borrador"> & { readonly borrador: BorradorAbierto };

function SuperficieAbierta({
  proyecto,
  borrador,
  puedeEditar,
  alAusente,
  alGuardar,
  alDescartar,
  alReabrir,
  alAgregarPartida,
  alHacerVersionNueva,
  alAbrirProblemas,
  alIrAArchivos,
  alAceptar = sinAccion,
  alRecargarBorrador = sinPromesa,
  partidaInicial = null,
  alConsumirPartidaInicial,
  enfocarGrilla = false,
  alEnfocarGrilla,
}: PropiedadesAbiertas): JSX.Element {
  const { alExpirar } = useAplicacion();
  const permiso = usePuedeEditarLaHoja(borrador.base);
  const puedeEditarEfectivo = (puedeEditar ?? permiso) && permiso;
  const obra = useContext(ContextoDeLaObra);
  const enRouter = useInRouterContext();
  const { anfitrion, abiertos, registrar } = useContext(ContextoDeDialogos);
  const raiz = useRef<HTMLDivElement>(null);
  const idAviso = useId();

  // Cada lectura que pide la persona (tras una edición) suma uno a la clave: junto con el `rev` nuevo es una sola clave nueva
  // y, por tanto, una sola petición.
  const [relecturas, setRelecturas] = useState(0);
  const alRelectura = useCallback(() => setRelecturas((n) => n + 1), []);
  const sufijo = relecturas === 0 ? "" : `.${relecturas}`;

  const rutaVista = rutaDeVista(borrador.id, "presupuesto");
  const vistaRecurso = useRecurso<VistaPresupuesto>(`${rutaVista}@${borrador.resumen.rev}${sufijo}`, (senal) =>
    pedir(rutaVista, { senal, leer: leerVistaPresupuesto }),
  );
  const rutaRevision = rutaDeVista(borrador.id, "auditoria");
  const revisionRecurso = useRecurso<InformeAuditoriaRespuesta>(`${rutaRevision}@${borrador.resumen.rev}${sufijo}`, (senal) =>
    pedir(rutaRevision, { senal, leer: leerInforme }),
  );

  // Mientras llega la lectura nueva (tras cada edición) sigue a la vista la anterior: la grilla no se vacía ni pierde la celda
  // activa. Solo la primera vez se ve el esqueleto.
  const vistaFresca = vistaRecurso.carga.estado === "listo" ? vistaRecurso.carga.datos : null;
  const [vistaViva, setVistaViva] = useState<VistaPresupuesto | null>(null);
  if (vistaFresca !== null && vistaFresca !== vistaViva) setVistaViva(vistaFresca);
  const vista = vistaFresca ?? vistaViva;
  const informeFresco = revisionRecurso.carga.estado === "listo" ? revisionRecurso.carga.datos : null;
  const [informeVivo, setInformeVivo] = useState<InformeAuditoriaRespuesta | null>(null);
  if (informeFresco !== null && informeFresco !== informeVivo) setInformeVivo(informeFresco);
  const informe = informeFresco ?? informeVivo;

  const vistaConError = vistaRecurso.carga.estado === "error";
  const revisionConError = revisionRecurso.carga.estado === "error";
  const vistaAusente = vistaRecurso.carga.estado === "error" && esBorradorAusente(vistaRecurso.carga.error);
  const revisionAusente = revisionRecurso.carga.estado === "error" && esBorradorAusente(revisionRecurso.carga.error);
  const expirada =
    (vistaRecurso.carga.estado === "error" &&
      vistaRecurso.carga.error instanceof ErrorDeApi &&
      vistaRecurso.carga.error.estado === 401) ||
    (revisionRecurso.carga.estado === "error" &&
      revisionRecurso.carga.error instanceof ErrorDeApi &&
      revisionRecurso.carga.error.estado === 401);

  useEffect(() => {
    if (vistaAusente || revisionAusente) alAusente();
  }, [vistaAusente, revisionAusente, alAusente]);

  useEffect(() => {
    if (expirada) alExpirar();
  }, [expirada, alExpirar]);

  // --- Cantidades, paneles y foco ---
  const alRecargar = useCallback(async () => {
    await alRecargarBorrador();
    alRelectura();
  }, [alRecargarBorrador, alRelectura]);
  const cantidades = useCantidadesDeLaSuperficie({
    borrador: borrador.id,
    rev: borrador.resumen.rev,
    filas: vista?.filas ?? [],
    puedeEditar: puedeEditarEfectivo,
    alAceptar,
    alRelectura,
    alRecargarBorrador,
    alAusente,
    alExpirar,
  });
  const columnas = columnasDePresupuesto(puedeEditarEfectivo ? cantidades : undefined);
  const filasDeGrilla = vista === null ? [] : filasDeLaGrilla(vista, informe);

  const [panel, setPanel] = useState<PanelAbierto>(null);
  const [filaElegida, setFilaElegida] = useState<string | null>(null);
  const [irAFila, setIrAFila] = useState(0);
  // El pedido se anota al agregar o quitar una partida; la vista nueva que llega después lo cumple (ver el efecto de abajo).
  const pedidoDeFoco = useRef<PedidoDeFoco | null>(null);
  const [focoEnPartida, setFocoEnPartida] = useState(0);

  // Lleva el foco a una celda de la grilla: la Cantidad de la fila `indiceDeFila` o, sin `conIndice`, la celda activa.
  const enfocarEnLaGrilla = useCallback((indiceDeFila: number | null) => {
    const base = raiz.current;
    if (base === null) return;
    const selector =
      indiceDeFila === null
        ? "[data-celda][tabindex='0']"
        : `[data-celda][data-fila="${indiceDeFila}"][data-columna="${COLUMNA_DE_CANTIDAD}"]`;
    base.querySelector<HTMLElement>(selector)?.focus();
  }, []);

  // Llegó la vista nueva que se esperaba: el foco va a la Cantidad de la fila agregada (o a la celda activa si ya no está).
  useEffect(() => {
    const pedido = pedidoDeFoco.current;
    if (pedido === null || vistaFresca === null || vistaFresca === pedido.base) return;
    pedidoDeFoco.current = null;
    const indice = pedido.clave === null ? -1 : vistaFresca.filas.findIndex((f) => f.clave === pedido.clave);
    enfocarEnLaGrilla(indice >= 0 ? indice : null);
  }, [vistaFresca, enfocarEnLaGrilla]);

  // Llegó la primera vista tras «Ver en el presupuesto»: el foco va a la celda activa de la grilla.
  useEffect(() => {
    if (!enfocarGrilla || vistaFresca === null || vistaFresca.filas.length === 0) return;
    enfocarEnLaGrilla(null);
    alEnfocarGrilla?.();
  }, [enfocarGrilla, vistaFresca, enfocarEnLaGrilla, alEnfocarGrilla]);

  // «Ir a la partida» de un problema: la fila queda activa y el foco va a su primera celda.
  useEffect(() => {
    if (irAFila === 0) return;
    raiz.current?.querySelector<HTMLElement>('tr[aria-selected="true"] [data-celda]')?.focus();
  }, [irAFila]);

  const abrirProblemas = () => {
    setPanel({ tipo: "problemas" });
    alAbrirProblemas?.();
  };
  const filaAbierta = panel?.tipo === "partida" ? (filasDeGrilla.find((f) => f.clave === panel.clave) ?? null) : null;

  // --- Crear la partida (plan B de R1): el panel de Componer de siempre, con la descripción ya escrita ---
  const [componiendo, setComponiendo] = useState<PartidaPorComponer | null>(null);
  const [alVolver, setAlVolver] = useState<AlVolverDeComponer | null>(null);
  const [partidaDeAlta, setPartidaDeAlta] = useState<PartidaCompuesta | null>(null);
  const hayCapa = componiendo !== null;
  useEffect(() => {
    if (!hayCapa) return;
    registrar(1);
    return () => registrar(-1);
  }, [hayCapa, registrar]);
  // Con la capa cerrada la página deja de ser inerte (lo decide quien reparte `abiertos`): solo entonces se puede enfocar. Se
  // ajusta durante el render (react.dev, «You might not need an effect»): el foco lo mueve `FilaDeAlta` al recibir lo nuevo.
  if (componiendo === null && alVolver !== null && abiertos === 0) {
    setAlVolver(null);
    if (alVolver.tipo === "partida") setFocoEnPartida((n) => n + 1);
    else setPartidaDeAlta(alVolver.partida);
  }

  const totalProblemas =
    informe !== null && !revisionConError
      ? cuentaDeProblemas(informe, vista?.filas).total
      : contarHallazgosDelResumen(borrador.resumen.hallazgos);
  const revisionParaFrase: RevisionDeLaSuperficie = revisionConError
    ? { estado: "error" }
    : informe !== null
      ? { estado: "lista", informe }
      : { estado: "cargando" };
  const mostrarGrilla = vista !== null && !vistaConError;

  return (
    <div className="silice-superficie" ref={raiz}>
      <FranjaDelPresupuesto
        key={`${proyecto}|${borrador.base.version ?? ""}`}
        proyecto={proyecto}
        borrador={borrador}
        puedeEditar={puedeEditarEfectivo}
        alAgregarPartida={() => {
          setFocoEnPartida((n) => n + 1);
          alAgregarPartida?.();
        }}
        alGuardar={() => {
          // Primero sale lo escrito que espera la pausa: la versión guardada lleva lo que se ve.
          void cantidades.esperarEnvios().then(() => alGuardar?.());
        }}
        alVerRevision={abrirProblemas}
        alHacerVersionNueva={() => {
          enfocarEnLaGrilla(null);
          alHacerVersionNueva?.();
        }}
        alDescartar={puedeEditarEfectivo ? alDescartar : undefined}
        impuestos={mostrarGrilla && vista.filas.length > 0 ? vista.impuestos : undefined}
        problemas={
          <Button kind="tertiary" size="md" onClick={abrirProblemas}>
            {`Problemas (${formatoEsVe(String(totalProblemas))})`}
          </Button>
        }
        masAcciones={
          <MasAcciones
            cambios={borrador.resumen.cambios}
            alDescartar={puedeEditarEfectivo ? alDescartar : undefined}
            alVerFrentes={() => setPanel({ tipo: "frentes" })}
            rutaArchivos={obra !== null && enRouter ? rutaDeObra(obra.carpeta, obra.obraId, "archivos") : undefined}
            alIrAArchivos={alIrAArchivos}
            rutaPestanas={
              obra !== null && enRouter
                ? rutaDeObra(obra.carpeta, obra.obraId, "presupuesto", SUBVISTA_DE_PESTANAS)
                : undefined
            }
          >
            <BotonExcel id={borrador.id} />
          </MasAcciones>
        }
      />

      {!puedeEditarEfectivo && (
        <p role="note" className="silice-hoja__solo-lectura cds--type-body-compact-01">
          {NOTA_SOLO_LECTURA}
          {borrador.base.solo_lectura ? ` Esta versión no se puede guardar: ${CAUSA_SOLO_LECTURA}.` : ""}
        </p>
      )}

      <div className={panel === null ? "silice-superficie__cuerpo" : "silice-con-panel silice-superficie__cuerpo"}>
        <div className="silice-superficie__principal">
          {vista === null && vistaRecurso.carga.estado === "cargando" && <EsqueletoDePresupuesto columnas={columnas} />}

          {vistaRecurso.carga.estado === "error" &&
            (vistaAusente ? (
              <div className="silice-hoja__ausente">
                <AvisoError error={vistaRecurso.carga.error} titulo="El borrador ya no está" />
                {alReabrir && (
                  <Button kind="tertiary" size="sm" onClick={alReabrir}>
                    Abrir de nuevo
                  </Button>
                )}
              </div>
            ) : (
              <div className="silice-superficie__error">
                <AvisoError error={vistaRecurso.carga.error} titulo="No se pudo cargar el presupuesto" />
                <Button kind="tertiary" size="md" onClick={vistaRecurso.recargar}>
                  Reintentar
                </Button>
              </div>
            ))}

          {mostrarGrilla && vista.filas.length === 0 && (
            <EstadoVacio
              titulo={vista.vacio_mensaje?.trim() || "Esta obra aún no tiene partidas"}
              descripcion={
                puedeEditarEfectivo
                  ? "Agregue la primera partida o traiga un cómputo (.csv) desde Archivos y planos."
                  : "Esta versión del presupuesto no tiene partidas registradas."
              }
            >
              {puedeEditarEfectivo &&
                (obra !== null && enRouter ? (
                  <Link className="cds--btn cds--btn--secondary cds--btn--md" to={rutaDeObra(obra.carpeta, obra.obraId, "archivos")}>
                    Traer un cómputo (.csv)
                  </Link>
                ) : alIrAArchivos !== undefined ? (
                  <Button kind="secondary" size="md" onClick={alIrAArchivos}>
                    Traer un cómputo (.csv)
                  </Button>
                ) : null)}
            </EstadoVacio>
          )}

          {mostrarGrilla && vista.filas.length > 0 && (
            <>
              <div className="silice-superficie__respuesta">
                <p className="silice-superficie__frase cds--type-body-compact-01">{fraseDeRespuesta(vista, revisionParaFrase)}</p>
                {revisionConError && (
                  <Button kind="tertiary" size="sm" onClick={revisionRecurso.recargar}>
                    Reintentar la revisión
                  </Button>
                )}
              </div>
              {cantidades.error !== null && puedeEditarEfectivo && (
                <AvisoDeEdicion
                  error={cantidades.error}
                  id={idAviso}
                  alRecargar={() => void cantidades.recargar().then(alRelectura)}
                  alReabrir={alReabrir ?? sinAccion}
                />
              )}
              <Grilla<FilaDeLaGrilla>
                etiqueta="Presupuesto"
                columnas={columnas}
                filas={filasDeGrilla}
                idDeFila={(f) => f.clave}
                filaElegida={filaElegida}
                alAbrir={(id, _clave, celda) => {
                  setFilaElegida(id);
                  setPanel({ tipo: "partida", clave: id, celda });
                }}
                pie={<PieDelPresupuesto vista={vista} />}
              />
            </>
          )}

          {mostrarGrilla && puedeEditarEfectivo && (
            <FilaDeAlta
              borradorId={borrador.id}
              revActual={cantidades.esperarEnvios}
              alAgregada={(agregada) => {
                // El `rev` nuevo cambia la clave de la lectura: la vista y la revisión se piden solas.
                alAceptar(agregada.resumen);
                pedidoDeFoco.current = { base: vistaFresca, clave: agregada.clave };
              }}
              alAusente={alAusente}
              alReleer={alRecargar}
              alCrearPartida={(partida) => setComponiendo(partida)}
              partidaInicial={partidaInicial ?? partidaDeAlta}
              alConsumirPartidaInicial={() => {
                setPartidaDeAlta(null);
                alConsumirPartidaInicial?.();
              }}
              solicitudDeFocoEnPartida={focoEnPartida}
            />
          )}
        </div>

        <InspectorDePartida
          borrador={borrador}
          fila={filaAbierta}
          moneda={borrador.resumen.moneda}
          puedeEditar={puedeEditarEfectivo}
          celdaOrigen={panel?.tipo === "partida" ? panel.celda : null}
          alCerrar={() => setPanel(null)}
          alAceptar={alAceptar}
          alVolverALaCalculada={cantidades.escribir}
          alAccionarEnOrden={cantidades.accionarEnOrden}
          alQuitar={() => {
            pedidoDeFoco.current = { base: vistaFresca, clave: null };
          }}
          alAusente={alAusente}
          alRecargarBorrador={alRecargar}
          alReabrir={alReabrir}
        />
        <InspectorDeProblemas
          abierto={panel?.tipo === "problemas"}
          revision={revisionParaFrase}
          filas={vista?.filas ?? []}
          alElegirFila={(clave) => {
            setFilaElegida(clave);
            setIrAFila((n) => n + 1);
          }}
          alCerrar={() => setPanel(null)}
          error={revisionRecurso.carga.estado === "error" ? revisionRecurso.carga.error : undefined}
          alReintentar={revisionRecurso.recargar}
        />
        <InspectorDeFrentes
          abierto={panel?.tipo === "frentes"}
          id={borrador.id}
          rev={borrador.resumen.rev}
          filas={vista?.filas ?? []}
          moneda={borrador.resumen.moneda}
          puedeEditar={puedeEditarEfectivo}
          alAceptar={(resumen) => alAceptar?.(resumen)}
          alAusente={alAusente}
          alCerrar={() => setPanel(null)}
        />
      </div>

      {componiendo !== null &&
        createPortal(
          <div className="silice-hoja__dialogo-fondo silice-hoja__dialogo-fondo--con-panel">
            <ComponerEnPanel
              partida={componiendo}
              alCerrar={() => {
                setComponiendo(null);
                setAlVolver({ tipo: "partida" });
              }}
              alGuardar={(compuesta) => {
                setComponiendo(null);
                setAlVolver({ tipo: "compuesta", partida: compuesta });
              }}
            />
          </div>,
          anfitrion ?? document.body,
        )}
    </div>
  );
}

/** Superficie principal del Presupuesto. */
export function SuperficiePresupuesto(propiedades: PropiedadesDeSuperficiePresupuesto): JSX.Element {
  const { borrador } = propiedades;
  if (borrador === null) return <SuperficieSinBorrador />;
  return <SuperficieAbierta key={borrador.id} {...propiedades} borrador={borrador} />;
}
