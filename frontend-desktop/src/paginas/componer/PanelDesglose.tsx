import { Table, TableBody, TableCell, TableRow } from "@carbon/react";
import { InlineNotification } from "../../comun/carbonEs";
import { AvisoError } from "../../comun/AvisoError";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import type { Advertencia, Contraste, Desglose, Evaluacion } from "./cliente";

interface Props {
  evaluacion: Evaluacion | null;
  cargando: boolean;
  error: unknown;
  // El ultimo desglose valido: con un dato mal escrito (estado `incompleto`) se sigue viendo, marcado como anterior,
  // en vez de dejar la pantalla solo con el aviso (prueba en vivo 2026-10-25).
  anterior?: Desglose | null;
  // La moneda de trabajo de la carpeta (D-MP1): cada monto la dice. Sin ella (la API no la dio) no se inventa.
  moneda?: string | null;
  // El nivel de su titulo: h2 en la pantalla, h3 en el panel de «Agregar partida» (plan F4, Tarea 9).
  nivel?: 2 | 3;
}

// «2.074,44 Bs»: el texto de la API en es-VE (una sola conversion) y la moneda, si se sabe.
function conMoneda(decimal: string, moneda: string | null): string {
  return moneda ? `${formatoEsVe(decimal)} ${moneda}` : formatoEsVe(decimal);
}

const ROTULOS: readonly (readonly [keyof Desglose, string])[] = [
  ["materiales", "Materiales"],
  ["equipos", "Equipos"],
  ["mano_obra", "Mano de obra"],
  ["costo_directo", "Costo directo"],
  ["con_administracion", "Con administración"],
  ["precio_unitario", "Precio unitario"],
];

const TITULO_ADVERTENCIA: Record<Advertencia["tipo"], string> = {
  rendimiento: "Rendimiento",
  rendimiento_ml: "Rendimiento atípico",
  precio_atipico: "Precio atípico",
  contraste_aace: "Contraste con la estimación por reglas",
  partida_nueva: "Partida nueva",
};

function TablaDeMontos({ desglose, moneda }: { desglose: Desglose; moneda: string | null }) {
  return (
    <div className="silice-tabla">
      <Table size="sm" aria-label="Desglose del precio unitario">
        <TableBody>
          {ROTULOS.map(([clave, rotulo]) => (
            <TableRow key={clave}>
              <TableCell>{rotulo}</TableCell>
              {/* La interfaz no calcula: el texto exacto de la API, en es-VE; el exacto queda en el title. */}
              <TableCell className="silice-cifra" title={desglose[clave]}>
                {conMoneda(desglose[clave], moneda)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function BloqueContraste({ contraste, moneda, nivel }: { contraste: Contraste; moneda: string | null; nivel: 3 | 4 }) {
  const Titulo = `h${nivel}` as const;
  return (
    <div className="silice-componer__contraste">
      <Titulo className="cds--type-heading-compact-02">Contraste con la estimación por reglas (AACE)</Titulo>
      <p className="cds--type-body-compact-01">
        Técnica de estimación que corresponde a este dominio: {contraste.tecnica} ({contraste.registros} registro(s)).
        Precio unitario estimado por reglas: {conMoneda(contraste.pu_estimado, moneda)}.
      </p>
      {contraste.dentro_de_rango && (
        <p className="cds--type-body-compact-01">
          El precio construido cae dentro del rango de la clase 3 de AACE International frente a la estimación por
          reglas.
        </p>
      )}
    </div>
  );
}

// Desglose en vivo (RF-27): lo calcula la API; aqui solo se pinta. Las advertencias informan, nunca bloquean.
export function PanelDesglose({ evaluacion, cargando, error, anterior = null, moneda = null, nivel = 2 }: Props) {
  const Titulo = `h${nivel}` as const;
  const conservado = evaluacion && !evaluacion.desglose && evaluacion.estado === "incompleto" ? anterior : null;
  return (
    <section className="silice-componer__bloque" aria-labelledby="componer-desglose">
      <Titulo id="componer-desglose" className="cds--type-heading-compact-02">
        Desglose en vivo
      </Titulo>
      <p role="status" className="silice-componer__nota cds--type-label-01">
        {cargando ? "Recalculando…" : ""}
      </p>
      <AvisoError error={error} titulo="No se pudo calcular el desglose" />
      {!evaluacion && !error && (
        <p className="silice-componer__nota cds--type-body-compact-01">
          Aún no hay desglose: comience por la cabecera y declare al menos un insumo.
        </p>
      )}
      {evaluacion && (
        <>
          {evaluacion.aviso && (
            <InlineNotification
              kind="info"
              lowContrast
              hideCloseButton
              role="status"
              title="Aviso"
              subtitle={evaluacion.aviso}
            />
          )}
          {evaluacion.desglose && <TablaDeMontos desglose={evaluacion.desglose} moneda={moneda} />}
          {(evaluacion.desperdicios ?? []).length > 0 && (
            // F5 vial: la cantidad con desperdicio la calcula el servidor; aquí solo se dice.
            <ul className="silice-componer__nota cds--type-body-compact-01" aria-label="Materiales con desperdicio">
              {(evaluacion.desperdicios ?? []).map((d) => (
                <li key={d.fila}>{`${d.descripcion} (fila ${d.fila}): consume ${d.leyenda}`}</li>
              ))}
            </ul>
          )}
          {conservado && (
            <>
              <p className="silice-componer__nota cds--type-body-compact-01">
                Se muestra el último desglose calculado, sin el cambio del aviso: corrija ese dato para actualizarlo.
              </p>
              <TablaDeMontos desglose={conservado} moneda={moneda} />
            </>
          )}
          {evaluacion.advertencias.map((a, i) => (
            <InlineNotification
              key={`${a.tipo}-${i}`}
              kind={a.tipo === "partida_nueva" ? "info" : "warning"}
              lowContrast
              hideCloseButton
              role="status"
              title={TITULO_ADVERTENCIA[a.tipo]}
              subtitle={a.texto}
            />
          ))}
          {evaluacion.contraste && <BloqueContraste contraste={evaluacion.contraste} moneda={moneda} nivel={nivel === 2 ? 3 : 4} />}
        </>
      )}
    </section>
  );
}
