import { Accordion, AccordionItem, Button } from "@carbon/react";
import { useRef, useState } from "react";
import type { JSX } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { InlineNotification } from "../../comun/carbonEs";
import { TablaDensa } from "../../comun/TablaDensa";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import {
  AYUDA,
  ROTULO_EQUIPOS,
  ROTULO_MANO_DE_OBRA,
  ROTULO_MATERIALES,
  descripcionLista,
  encabezadoDeLista,
  filasEquipos,
  filasManoObra,
  filasMateriales,
  origenDePropuesta,
  rendimientoEnTexto,
  resultadosDe,
  tituloDePropuesta,
} from "./logicaParecidas";
import type { Composicion, Propuesta, SimilaresRespuesta } from "./logicaParecidas";

// Lo que «Usar esta partida» entrega al diálogo: con la unidad, la cantidad dice en qué se mide (sin desglose, no se sabe).
export interface PartidaParecida {
  codigo: string;
  descripcion: string;
  unidad: string | null;
}

interface Props {
  // Lo escrito en el campo «Partida» del diálogo: es lo que se busca.
  descripcion: string;
  alUsar: (partida: PartidaParecida) => void;
  deshabilitado?: boolean;
}

type Estado =
  | { tipo: "inicial" }
  | { tipo: "buscando" }
  | { tipo: "listo"; respuesta: SimilaresRespuesta; buscado: string }
  | { tipo: "error"; error: unknown };

function Desglose({ composicion }: { composicion: Composicion }) {
  const { unidad, rendimiento } = rendimientoEnTexto(composicion);
  const cifra = { numerica: true, presentar: formatoEsVe } as const;
  return (
    <div className="silice-parecidas__desglose">
      <p className="cds--type-body-compact-01">
        <strong>Unidad:</strong> {unidad} | <strong>Rendimiento:</strong> {rendimiento}
      </p>
      {composicion.materiales.length > 0 && (
        <TablaDensa
          etiqueta={ROTULO_MATERIALES}
          columnas={[
            { clave: "descripcion", titulo: "Descripción" },
            { clave: "unidad", titulo: "Unidad" },
            { clave: "cantidad", titulo: "Cantidad", ...cifra },
            { clave: "precio", titulo: "Precio", ...cifra },
          ]}
          filas={filasMateriales(composicion)}
        />
      )}
      {composicion.equipos.length > 0 && (
        <TablaDensa
          etiqueta={ROTULO_EQUIPOS}
          columnas={[
            { clave: "descripcion", titulo: "Descripción" },
            { clave: "cantidad", titulo: "Cantidad", ...cifra },
            { clave: "precio", titulo: "Precio", ...cifra },
            { clave: "depreciacion", titulo: "Depreciación", ...cifra },
          ]}
          filas={filasEquipos(composicion)}
        />
      )}
      {composicion.mano_obra.length > 0 && (
        <TablaDensa
          etiqueta={ROTULO_MANO_DE_OBRA}
          columnas={[
            { clave: "descripcion", titulo: "Descripción" },
            { clave: "cantidad", titulo: "Cantidad", ...cifra },
            { clave: "sueldo", titulo: "Sueldo", ...cifra },
          ]}
          filas={filasManoObra(composicion)}
        />
      )}
    </div>
  );
}

function DetalleDePropuesta({ propuesta }: { propuesta: Propuesta }) {
  return (
    <div className="silice-parecidas__detalle">
      <p className="silice-parecidas__nota cds--type-label-01">{origenDePropuesta(propuesta)}</p>
      {propuesta.aviso !== null && (
        <InlineNotification kind="warning" role="status" title="Desglose incompleto" subtitle={propuesta.aviso} lowContrast hideCloseButton />
      )}
      {propuesta.composicion !== null && <Desglose composicion={propuesta.composicion} />}
    </div>
  );
}

function Resultado({ respuesta, alUsar, deshabilitado }: { respuesta: SimilaresRespuesta } & Omit<Props, "descripcion">) {
  if (respuesta.falla !== null) return <AvisoError error={respuesta.falla} titulo="Las propuestas no están disponibles" />;
  if (respuesta.propuestas.length === 0) {
    return <p className="cds--type-body-compact-01">{respuesta.mensaje ?? "No hay partidas parecidas."}</p>;
  }
  return (
    <>
      <h3 className="cds--type-heading-compact-01">{encabezadoDeLista(respuesta.propuestas.length)}</h3>
      <ul className="silice-parecidas__lista" aria-label="Partidas parecidas">
        {respuesta.propuestas.map((p) => (
          <li key={p.codigo} className="silice-parecidas__propuesta">
            <p className="cds--type-body-compact-01">
              <span className="cds--visually-hidden">Puntaje </span>
              {tituloDePropuesta(p)}
            </p>
            <div>
              <Button
                kind="tertiary"
                size="sm"
                aria-label={`Usar esta partida: ${p.codigo}`}
                disabled={deshabilitado}
                onClick={() => alUsar({ codigo: p.codigo, descripcion: p.descripcion, unidad: p.composicion?.unidad ?? null })}
              >
                Usar esta partida
              </Button>
            </div>
            <Accordion size="sm">
              <AccordionItem title={`Ver el análisis de ${p.codigo}`}>
                <DetalleDePropuesta propuesta={p} />
              </AccordionItem>
            </Accordion>
          </li>
        ))}
      </ul>
    </>
  );
}

// Por qué existe (plan F4, Tarea 9, baja 20): la pantalla «Partidas similares» pasa a ser una salida de «Agregar partida»,
// «Parecidas a esta descripción». Busca lo que la persona escribió en «Partida» con la misma ruta y el mismo cuerpo que la
// pantalla (`POST /v1/similares` `{descripcion}`) y lista las propuestas con su análisis plegado y «Usar esta partida»,
// que la deja elegida en el diálogo. Solo la usa el diálogo «Agregar partida». No calcula nada: cifras de la API en es-VE.
export function Parecidas({ descripcion, alUsar, deshabilitado = false }: Props): JSX.Element {
  const { alExpirar } = useAplicacion();
  const [estado, setEstado] = useState<Estado>({ tipo: "inicial" });
  const consulta = useRef(0);

  const buscar = () => {
    if (!descripcionLista(descripcion)) return;
    const numero = ++consulta.current;
    const buscado = descripcion;
    setEstado({ tipo: "buscando" });
    pedir<SimilaresRespuesta>("/v1/similares", { metodo: "POST", cuerpo: { descripcion } }).then(
      (respuesta) => {
        if (numero === consulta.current) setEstado({ tipo: "listo", respuesta, buscado });
      },
      (error: unknown) => {
        if (numero !== consulta.current) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setEstado({ tipo: "error", error });
      },
    );
  };

  return (
    <div className="silice-parecidas">
      <p className="cds--type-helper-text-01">{AYUDA}</p>
      <div>
        <Button kind="tertiary" size="sm" disabled={deshabilitado || !descripcionLista(descripcion)} onClick={buscar}>
          Buscar parecidas
        </Button>
      </div>
      <div aria-live="polite" aria-atomic="true" className="silice-parecidas__resultado">
        {estado.tipo === "buscando" && <p className="cds--type-helper-text-01">Buscando partidas parecidas…</p>}
        {estado.tipo === "error" && <AvisoError error={estado.error} titulo="No se pudo buscar" />}
        {estado.tipo === "listo" && (
          <>
            {descripcion.trim() !== estado.buscado.trim() && (
              <p className="silice-parecidas__nota cds--type-label-01">{resultadosDe(estado.buscado)}</p>
            )}
            <Resultado respuesta={estado.respuesta} alUsar={alUsar} deshabilitado={deshabilitado} />
          </>
        )}
      </div>
    </div>
  );
}
