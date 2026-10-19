import { InlineNotification, Table, TableBody, TableCell, TableRow } from "@carbon/react";
import { AvisoError } from "../../comun/AvisoError";
import type { Advertencia, Contraste, Desglose, Evaluacion } from "./cliente";

interface Props {
  evaluacion: Evaluacion | null;
  cargando: boolean;
  error: unknown;
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

function TablaDeMontos({ desglose }: { desglose: Desglose }) {
  return (
    <div className="silice-tabla">
      <Table size="sm" aria-label="Desglose del precio unitario">
        <TableBody>
          {ROTULOS.map(([clave, rotulo]) => (
            <TableRow key={clave}>
              <TableCell>{rotulo}</TableCell>
              <TableCell className="silice-cifra">{desglose[clave]}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function BloqueContraste({ contraste }: { contraste: Contraste }) {
  return (
    <div className="silice-componer__contraste">
      <h3 className="cds--type-heading-compact-02">Contraste con la estimación por reglas (AACE)</h3>
      <p className="cds--type-body-compact-01">
        Técnica de la compuerta G2 para este dominio: {contraste.tecnica} ({contraste.registros} registro(s)). PU
        estimado por reglas: {contraste.pu_estimado}.
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
export function PanelDesglose({ evaluacion, cargando, error }: Props) {
  return (
    <section className="silice-componer__bloque" aria-labelledby="componer-desglose">
      <h2 id="componer-desglose" className="cds--type-heading-03">
        Desglose en vivo
      </h2>
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
          {evaluacion.desglose && <TablaDeMontos desglose={evaluacion.desglose} />}
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
          {evaluacion.contraste && <BloqueContraste contraste={evaluacion.contraste} />}
        </>
      )}
    </section>
  );
}
