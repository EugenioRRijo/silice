import { Button } from "@carbon/react";
import { useContext, useEffect } from "react";
import type { JSX } from "react";
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
import { ContextoDeLaObra } from "../../../marco/obraAbierta";
import { rutaDeObra } from "../../../marco/secciones";
import { useAplicacion } from "../../../shell/contexto";
import { porcentajeDeAlicuota } from "../../control/logica";
import { BotonExcel } from "../BotonExcel";
import { FranjaDelPresupuesto } from "../FranjaDelPresupuesto";
import { leerInforme, leerVistaPresupuesto } from "../analizadores";
import { esBorradorAusente } from "../logica";
import type { BorradorAbierto, Hallazgos, VistaPresupuesto } from "../logica";
import { CAUSA_SOLO_LECTURA } from "../logicaGuardar";
import { usePuedeEditarLaHoja } from "../puedeEditar";
import { TEXTOS_DEL_IVA } from "../textos";
import { MasAcciones } from "./MasAcciones";
import { columnasDePresupuesto } from "./columnas";
import { cuentaDeProblemas, filasDeLaGrilla, fraseDeRespuesta } from "./logica";
import type { FilaDeLaGrilla, RevisionDeLaSuperficie } from "./logica";
import "./superficie.scss";

// Superficie de solo lectura del Presupuesto (lote B1-4, ficha-b1 §1.8 y §4).
// Lee la vista (`GET /v1/hoja/borradores/{id}/vistas/presupuesto`) y la revisión (`.../vistas/auditoria`) mediante
// `useRecurso` con la clave `ruta@rev`. Presenta cabecera fija, frase de respuesta antes de la grilla, `Grilla` sin
// edición y `tfoot` con total sin IVA (`MontoExacto`) e IVA calculados por el servidor.

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
}

const NOTA_SOLO_LECTURA = "Está viendo este presupuesto en solo lectura.";
const FILAS_DE_ESQUELETO = [0, 1, 2, 3, 4] as const;
const SEVERIDADES_DE_PROBLEMA = new Set(["CRITICO", "CRÍTICO", "ERROR", "ADVERTENCIA"]);
const sinAccion = () => {};

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

/** Superficie principal del Presupuesto en modo de solo lectura. */
export function SuperficiePresupuesto({
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
}: PropiedadesDeSuperficiePresupuesto): JSX.Element {
  const { alExpirar } = useAplicacion();
  const permiso = usePuedeEditarLaHoja(borrador?.base ?? null);
  const puedeEditarEfectivo = (puedeEditar ?? permiso) && permiso;
  const obra = useContext(ContextoDeLaObra);
  const enRouter = useInRouterContext();

  const rutaVista = borrador === null ? null : rutaDeVista(borrador.id, "presupuesto");
  const claveVista = borrador === null || rutaVista === null ? null : `${rutaVista}@${borrador.resumen.rev}`;
  const vistaRecurso = useRecurso<VistaPresupuesto>(claveVista, (senal) => {
    if (rutaVista === null) return Promise.reject(new Error("Sin borrador abierto."));
    return pedir(rutaVista, { senal, leer: leerVistaPresupuesto });
  });

  const rutaRevision = borrador === null ? null : rutaDeVista(borrador.id, "auditoria");
  const claveRevision = borrador === null || rutaRevision === null ? null : `${rutaRevision}@${borrador.resumen.rev}`;
  const revisionRecurso = useRecurso<InformeAuditoriaRespuesta>(claveRevision, (senal) => {
    if (rutaRevision === null) return Promise.reject(new Error("Sin borrador abierto."));
    return pedir(rutaRevision, { senal, leer: leerInforme });
  });

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

  const columnas = columnasDePresupuesto();
  const vistaLista = vistaRecurso.carga.estado === "listo" ? vistaRecurso.carga.datos : null;
  const informeListo = revisionRecurso.carga.estado === "listo" ? revisionRecurso.carga.datos : null;
  const totalProblemas =
    informeListo !== null
      ? cuentaDeProblemas(informeListo, vistaLista?.filas).total
      : contarHallazgosDelResumen(borrador?.resumen.hallazgos ?? []);

  const revisionParaFrase: RevisionDeLaSuperficie =
    revisionRecurso.carga.estado === "listo"
      ? { estado: "lista", informe: revisionRecurso.carga.datos }
      : revisionRecurso.carga.estado === "error"
        ? { estado: "error" }
        : { estado: "cargando" };

  return (
    <div className="silice-superficie">
      {borrador === null ? (
        <div className="silice-hoja__cabecera-fija">
          <p className="silice-hoja__total cds--type-heading-compact-02">Total sin IVA: Calculando…</p>
        </div>
      ) : (
        <FranjaDelPresupuesto
          key={`${proyecto}|${borrador.base.version ?? ""}`}
          proyecto={proyecto}
          borrador={borrador}
          puedeEditar={puedeEditarEfectivo}
          alAgregarPartida={alAgregarPartida ?? sinAccion}
          alGuardar={alGuardar ?? sinAccion}
          alVerRevision={alAbrirProblemas ?? sinAccion}
          alHacerVersionNueva={alHacerVersionNueva ?? sinAccion}
          alDescartar={puedeEditarEfectivo ? alDescartar : undefined}
          problemas={
            <Button kind="tertiary" size="md" onClick={alAbrirProblemas}>
              {`Problemas (${formatoEsVe(String(totalProblemas))})`}
            </Button>
          }
          masAcciones={
            <MasAcciones cambios={borrador.resumen.cambios} alDescartar={puedeEditarEfectivo ? alDescartar : undefined}>
              <BotonExcel id={borrador.id} />
            </MasAcciones>
          }
        />
      )}

      {!puedeEditarEfectivo && borrador !== null && (
        <p role="note" className="silice-hoja__solo-lectura cds--type-body-compact-01">
          {NOTA_SOLO_LECTURA}
          {borrador.base.solo_lectura ? ` Esta versión no se puede guardar: ${CAUSA_SOLO_LECTURA}.` : ""}
        </p>
      )}

      {(borrador === null || vistaRecurso.carga.estado === "cargando") && <EsqueletoDePresupuesto columnas={columnas} />}

      {borrador !== null && vistaRecurso.carga.estado === "error" && (
        vistaAusente ? (
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
        )
      )}

      {borrador !== null && vistaLista !== null && vistaLista.filas.length === 0 && (
        <EstadoVacio
          titulo={vistaLista.vacio_mensaje?.trim() || "Esta obra aún no tiene partidas"}
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

      {borrador !== null && vistaLista !== null && vistaLista.filas.length > 0 && (
        <>
          <div className="silice-superficie__respuesta">
            <p className="silice-superficie__frase cds--type-body-compact-01">
              {fraseDeRespuesta(vistaLista, revisionParaFrase)}
            </p>
            {revisionRecurso.carga.estado === "error" && (
              <Button kind="tertiary" size="sm" onClick={revisionRecurso.recargar}>
                Reintentar la revisión
              </Button>
            )}
          </div>
          <Grilla<FilaDeLaGrilla>
            etiqueta="Presupuesto"
            columnas={columnas}
            filas={filasDeLaGrilla(vistaLista, informeListo)}
            idDeFila={(f) => f.clave}
            pie={<PieDelPresupuesto vista={vistaLista} />}
          />
        </>
      )}
    </div>
  );
}
