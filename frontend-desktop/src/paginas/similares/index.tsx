import { Accordion, AccordionItem, Button, InlineNotification } from "@carbon/react";
import { useRef, useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { TablaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import {
  AVISO_SIN_DESCRIPCION,
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
} from "./logica";
import type { Composicion, Propuesta, SimilaresRespuesta } from "./logica";
import "./similares.scss";
import { CampoTexto } from "../../comun/CampoTexto";

type Estado =
  | { tipo: "inicial" }
  | { tipo: "buscando" }
  | { tipo: "listo"; respuesta: SimilaresRespuesta; buscado: string }
  | { tipo: "error"; error: unknown };

function Desglose({ composicion }: { composicion: Composicion }) {
  const { unidad, rendimiento } = rendimientoEnTexto(composicion);
  return (
    <div className="silice-similares__detalle">
      <p className="cds--type-body-compact-01">
        <strong>Unidad:</strong> {unidad} | <strong>Rendimiento:</strong>{" "}
        {rendimiento}
      </p>
      {composicion.materiales.length > 0 && (
        <section>
          <h3 className="cds--type-heading-compact-01">{ROTULO_MATERIALES}</h3>
          <TablaDensa
            etiqueta={ROTULO_MATERIALES}
            columnas={[
              { clave: "descripcion", titulo: "Descripción" },
              { clave: "unidad", titulo: "Unidad" },
              { clave: "cantidad", titulo: "Cantidad", numerica: true },
              { clave: "precio", titulo: "Precio", numerica: true },
            ]}
            filas={filasMateriales(composicion)}
          />
        </section>
      )}
      {composicion.equipos.length > 0 && (
        <section>
          <h3 className="cds--type-heading-compact-01">{ROTULO_EQUIPOS}</h3>
          <TablaDensa
            etiqueta={ROTULO_EQUIPOS}
            columnas={[
              { clave: "descripcion", titulo: "Descripción" },
              { clave: "cantidad", titulo: "Cantidad", numerica: true },
              { clave: "precio", titulo: "Precio", numerica: true },
              { clave: "depreciacion", titulo: "Depreciación", numerica: true },
            ]}
            filas={filasEquipos(composicion)}
          />
        </section>
      )}
      {composicion.mano_obra.length > 0 && (
        <section>
          <h3 className="cds--type-heading-compact-01">
            {ROTULO_MANO_DE_OBRA}
          </h3>
          <TablaDensa
            etiqueta={ROTULO_MANO_DE_OBRA}
            columnas={[
              { clave: "descripcion", titulo: "Descripción" },
              { clave: "cantidad", titulo: "Cantidad", numerica: true },
              { clave: "sueldo", titulo: "Sueldo", numerica: true },
            ]}
            filas={filasManoObra(composicion)}
          />
        </section>
      )}
    </div>
  );
}

function DetalleDePropuesta({ propuesta }: { propuesta: Propuesta }) {
  return (
    <div className="silice-similares__detalle">
      <p className="silice-similares__nota cds--type-label-01">
        {origenDePropuesta(propuesta)}
      </p>
      {propuesta.aviso !== null && (
        <InlineNotification
          kind="warning"
          role="status"
          title="Desglose incompleto"
          subtitle={propuesta.aviso}
          lowContrast
          hideCloseButton
        />
      )}
      {propuesta.composicion !== null && (
        <Desglose composicion={propuesta.composicion} />
      )}
    </div>
  );
}

// «Partidas similares» (UC-03): la descripcion en texto libre -> las partidas mas parecidas del catalogo con su
// desglose y rendimiento, para reutilizarlos. Solo lectura; la interfaz no calcula nada.
export default function PaginaSimilares() {
  const { alExpirar } = useAplicacion();
  const [descripcion, setDescripcion] = useState("");
  const [estado, setEstado] = useState<Estado>({ tipo: "inicial" });
  const consulta = useRef(0);
  const enBlanco = !descripcionLista(descripcion);

  const buscar = (evento: FormEvent) => {
    evento.preventDefault();
    if (!descripcionLista(descripcion)) return;
    const numero = ++consulta.current;
    const buscado = descripcion;
    setEstado({ tipo: "buscando" });
    pedir<SimilaresRespuesta>("/v1/similares", {
      metodo: "POST",
      cuerpo: { descripcion },
    }).then(
      (respuesta) => {
        if (numero === consulta.current)
          setEstado({ tipo: "listo", respuesta, buscado });
      },
      (error: unknown) => {
        if (numero !== consulta.current) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setEstado({ tipo: "error", error });
      },
    );
  };

  return (
    <div className="silice-similares silice-pagina">
      <h1 className="cds--type-heading-04">Partidas similares</h1>
      <p className="cds--type-body-compact-01">{AYUDA}</p>
      <form className="silice-similares__formulario" onSubmit={buscar}>
        <div className="silice-similares__campo">
          <CampoTexto
            id="similares-descripcion"
            labelText="Descripción de la partida"
            value={descripcion}
            onChange={(e) => setDescripcion(e.target.value)}
          />
        </div>
        <Button type="submit" kind="primary" size="md" disabled={enBlanco}>
          Buscar
        </Button>
      </form>

      <div aria-live="polite" aria-atomic="true">
        {estado.tipo === "inicial" && (
          <EstadoVacio titulo={AVISO_SIN_DESCRIPCION} />
        )}
        {estado.tipo === "buscando" && (
          <EsqueletoPagina etiqueta="Buscando partidas similares" />
        )}
        {estado.tipo === "error" && (
          <AvisoError error={estado.error} titulo="No se pudo buscar" />
        )}
        {estado.tipo === "listo" && (
          <>
            {descripcion.trim() !== estado.buscado.trim() && (
              <p className="silice-similares__nota cds--type-label-01">
                {resultadosDe(estado.buscado)}
              </p>
            )}
            <Resultado respuesta={estado.respuesta} />
          </>
        )}
      </div>
    </div>
  );
}

function Resultado({ respuesta }: { respuesta: SimilaresRespuesta }) {
  if (respuesta.falla !== null) {
    return (
      <AvisoError
        error={respuesta.falla}
        titulo="Las propuestas no están disponibles"
      />
    );
  }
  if (respuesta.propuestas.length === 0) {
    return (
      <EstadoVacio titulo={respuesta.mensaje ?? "No hay partidas similares."} />
    );
  }
  return (
    <section aria-labelledby="similares-lista">
      <h2 id="similares-lista" className="cds--type-heading-compact-02">
        {encabezadoDeLista(respuesta.propuestas.length)}
      </h2>
      <Accordion size="sm">
        {respuesta.propuestas.map((p) => (
          <AccordionItem
            key={p.codigo}
            title={
              <>
                <span className="cds--visually-hidden">Puntaje </span>
                {tituloDePropuesta(p)}
              </>
            }
          >
            <DetalleDePropuesta propuesta={p} />
          </AccordionItem>
        ))}
      </Accordion>
    </section>
  );
}
