import { CheckmarkFilled } from "@carbon/icons-react";
import { Button } from "@carbon/react";
import type { JSX } from "react";
import type { HallazgoInformeRespuesta, InformeAuditoriaRespuesta } from "../../../api/tipos";
import { AvisoError } from "../../../comun/AvisoError";
import { PanelLateral } from "../../../comun/PanelLateral";
import { Severidad } from "../../../comun/Severidad";
import { cifraSiLoEs, cifrasEnTextoEsVe, formatoEsVe } from "../../../indicadores/formatoEsVe";
import type { FilaPresupuesto } from "../logica";
import { cuentaDeProblemas, gruposDeProblemas } from "./logica";
import type { CuentaDeProblemas, RevisionDeLaSuperficie, SeveridadDeProblema } from "./logica";
import "./problemas.scss";

// Inspector lateral no modal de «Problemas» (lote B1-7, ficha-b1 §1.10 prueba 8, §2 T3 y §4).
// Se abre solo cuando la persona lo pide, agrupa los hallazgos (Crítico, Error y Advertencia) por regla evaluada, dice
// siempre la severidad en palabra, usa `sin_hallazgos` del servidor cuando no hay problemas y avisa por callback qué fila
// activar en la grilla al elegir un problema.

export interface PropiedadesDeInspectorDeProblemas {
  readonly abierto: boolean;
  readonly revision: RevisionDeLaSuperficie;
  readonly filas: readonly Pick<FilaPresupuesto, "clave" | "partida" | "descripcion">[];
  readonly alElegirFila: (claveFila: string) => void;
  readonly alCerrar: () => void;
  readonly error?: unknown;
  readonly alReintentar?: (() => void) | undefined;
}

const CLASE_POR_SEVERIDAD: Record<SeveridadDeProblema, string> = {
  CRITICO: "critico",
  ERROR: "error",
  ADVERTENCIA: "advertencia",
};

const cifra = (n: number): string => formatoEsVe(String(n));

function resumenDeCuenta(cuenta: CuentaDeProblemas): string {
  const problemas = cuenta.total === 1 ? "1 problema" : `${cifra(cuenta.total)} problemas`;
  if (cuenta.partidasConProblemas === 0) {
    return `${problemas} en el presupuesto`;
  }
  const partidas = cuenta.partidasConProblemas === 1 ? "1 partida" : `${cifra(cuenta.partidasConProblemas)} partidas`;
  return `${problemas} en ${partidas}`;
}

function desgloseDeSeveridad(cuenta: CuentaDeProblemas): string {
  const partes: string[] = [];
  if (cuenta.criticos > 0) {
    partes.push(cuenta.criticos === 1 ? "1 crítico" : `${cifra(cuenta.criticos)} críticos`);
  }
  if (cuenta.errores > 0) {
    partes.push(cuenta.errores === 1 ? "1 error" : `${cifra(cuenta.errores)} errores`);
  }
  if (cuenta.advertencias > 0) {
    partes.push(cuenta.advertencias === 1 ? "1 advertencia" : `${cifra(cuenta.advertencias)} advertencias`);
  }
  if (partes.length <= 1) return partes[0] ?? "";
  return `${partes.slice(0, -1).join(", ")} y ${partes[partes.length - 1]}`;
}

function textoSinHallazgos(informe: InformeAuditoriaRespuesta): string {
  const delServidor = informe.sin_hallazgos?.trim() ?? "";
  if (delServidor !== "") return delServidor;
  const nReglas = informe.reglas_evaluadas.length;
  if (nReglas === 0) return "Sílice no halló problemas.";
  const textoReglas = nReglas === 1 ? "1 regla" : `${cifra(nReglas)} reglas`;
  return `Sílice revisó ${textoReglas} y no halló problemas.`;
}

function datosDeComparacion(hallazgo: HallazgoInformeRespuesta): string | null {
  const partes: string[] = [];
  if (hallazgo.observado !== null && hallazgo.observado.trim() !== "") {
    partes.push(`En el presupuesto: ${cifraSiLoEs(hallazgo.observado.trim())}`);
  }
  if (hallazgo.esperado !== null && hallazgo.esperado.trim() !== "") {
    partes.push(`Según Sílice: ${cifraSiLoEs(hallazgo.esperado.trim())}`);
  }
  if (hallazgo.impacto !== null && hallazgo.impacto.trim() !== "") {
    partes.push(`Diferencia: ${cifraSiLoEs(hallazgo.impacto.trim())}`);
  }
  return partes.length > 0 ? partes.join(" · ") : null;
}

function rotuloDePartida(partida: string | null, descripcionPartida: string | null): string {
  if (partida === null || partida === "") return "En el presupuesto";
  if (descripcionPartida !== null && descripcionPartida !== "") {
    return `${partida} · ${descripcionPartida}`;
  }
  return partida;
}

function ContenidoDeRevision({
  revision,
  filas,
  alElegirFila,
  error,
  alReintentar,
}: Omit<PropiedadesDeInspectorDeProblemas, "abierto" | "alCerrar">): JSX.Element {
  if (revision.estado === "cargando") {
    return <p className="silice-problemas-inspector__cargando cds--type-body-compact-01">Revisando el presupuesto…</p>;
  }

  if (revision.estado === "error") {
    return (
      <div className="silice-problemas-inspector__error">
        <AvisoError error={error ?? "No se pudo revisar el presupuesto."} titulo="No se pudo revisar el presupuesto" />
        {alReintentar !== undefined && (
          <Button kind="tertiary" size="sm" onClick={alReintentar}>
            Reintentar la revisión
          </Button>
        )}
      </div>
    );
  }

  const cuenta = cuentaDeProblemas(revision.informe, filas);
  const grupos = gruposDeProblemas(revision.informe, filas);

  if (cuenta.total === 0 || grupos.length === 0) {
    return (
      <div className="silice-problemas-inspector__sin-hallazgos">
        <CheckmarkFilled size={16} aria-hidden="true" className="silice-problemas-inspector__ok-icono" />
        <div className="silice-problemas-inspector__ok-cuerpo">
          <p className="silice-problemas-inspector__ok-titulo cds--type-heading-compact-01">Sin problemas</p>
          <p className="silice-problemas-inspector__ok-texto cds--type-body-compact-01">
            {textoSinHallazgos(revision.informe)}
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="silice-problemas-inspector__cabecera-lista">
        <p className="silice-problemas-inspector__resumen cds--type-heading-compact-01">{resumenDeCuenta(cuenta)}</p>
        <p className="silice-problemas-inspector__desglose cds--type-body-compact-01">{desgloseDeSeveridad(cuenta)}</p>
      </div>
      <div className="silice-problemas-inspector__grupos">
        {grupos.map((grupo) => (
          <div key={grupo.regla} className="silice-problemas-inspector__grupo">
            <div className="silice-problemas-inspector__grupo-cabecera">
              <h3 className="silice-problemas-inspector__grupo-titulo cds--type-heading-compact-01">{grupo.nombre}</h3>
              <span className="silice-problemas-inspector__grupo-cuenta cds--type-label-01">
                {grupo.problemas.length === 1 ? "1 problema" : `${cifra(grupo.problemas.length)} problemas`}
              </span>
            </div>
            <ul className="silice-problemas-inspector__lista">
              {grupo.problemas.map((problema) => {
                const claseSev = CLASE_POR_SEVERIDAD[problema.severidad];
                const comparacion = datosDeComparacion(problema.hallazgo);
                const claveDestino = problema.claveFila;
                return (
                  <li
                    key={`${grupo.regla}-${problema.numero}-${claveDestino ?? "global"}`}
                    className={`silice-problemas-inspector__item silice-problemas-inspector__item--${claseSev}`}
                  >
                    <div className="silice-problemas-inspector__item-cabecera">
                      <Severidad valor={problema.severidad} />
                      <span className="silice-problemas-inspector__partida cds--type-label-01">
                        {rotuloDePartida(problema.partida, problema.descripcionPartida)}
                      </span>
                    </div>
                    <p className="silice-problemas-inspector__descripcion cds--type-body-compact-01">
                      {cifrasEnTextoEsVe(problema.descripcion)}
                    </p>
                    {comparacion !== null && (
                      <p className="silice-problemas-inspector__comparacion cds--type-helper-text-01">{comparacion}</p>
                    )}
                    {claveDestino !== null && (
                      <div className="silice-problemas-inspector__item-acciones">
                        <Button
                          kind="tertiary"
                          size="sm"
                          aria-label={`Ir a la partida ${problema.partida ?? claveDestino} (${grupo.nombre}, hallazgo ${cifra(problema.numero)})`}
                          onClick={() => alElegirFila(claveDestino)}
                        >
                          Ir a la partida
                        </Button>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </>
  );
}

/** Inspector lateral no modal de problemas del Presupuesto agrupados por regla. */
export function InspectorDeProblemas({
  abierto,
  revision,
  filas,
  alElegirFila,
  alCerrar,
  error,
  alReintentar,
}: PropiedadesDeInspectorDeProblemas): JSX.Element {
  return (
    <PanelLateral titulo="Problemas" abierto={abierto} alCerrar={alCerrar} ancho="normal">
      <div className="silice-problemas-inspector">
        <ContenidoDeRevision
          revision={revision}
          filas={filas}
          alElegirFila={alElegirFila}
          error={error}
          alReintentar={alReintentar}
        />
      </div>
    </PanelLateral>
  );
}
