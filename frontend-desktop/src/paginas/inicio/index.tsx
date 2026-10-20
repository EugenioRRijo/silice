import { Button } from "@carbon/react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { useAplicacion } from "../../shell/contexto";
import { RECORRIDO_AUDITAR, iniciarRecorrido, pasoDeRuta, useRecorrido } from "../../shell/recorrido";
import { PAGINAS, estaMigrada, paginaPorId, rutaDe, visible } from "../../shell/rutas";
import { fijarArchivoPendiente } from "./archivoPendiente";
import type { ModoDeAuditoria } from "./archivoPendiente";
import { PanelArenera } from "./PanelArenera";
import type { ExistenciaRespuesta } from "./PanelArenera";
import { UltimasAuditorias } from "./UltimasAuditorias";
import type { AuditoriaGuardadaRespuesta } from "./UltimasAuditorias";
import { useCarga } from "./useCarga";

const RUTA_ARENERA = "/v1/produccion/existencias";
const RUTA_AUDITORIAS = "/v1/auditorias-libro?limite=5";

// Inicio «panel del dia» (spec 2026-10-18-silice-ui-inicio-panel-del-dia-design.md, §2.1): arriba el Excel de un
// presupuesto, debajo la arenera y lo ultimo que se audito. Cada bloque responde una pregunta («¿que hago?»,
// «¿que falta en la arenera?», «¿donde estaba?»); nada de tarjetas de adorno.
export default function PaginaInicio() {
  const { alExpirar, caso, proyecto, nombreProyecto, sesion } = useAplicacion();
  const navegar = useNavigate();
  const [archivo, setArchivo] = useState<File | null>(null);
  const arenera = useCarga<ExistenciaRespuesta[]>(RUTA_ARENERA, alExpirar);
  const auditorias = useCarga<AuditoriaGuardadaRespuesta[]>(RUTA_AUDITORIAS, alExpirar);

  const recorrido = useRecorrido();
  // El paso que sigue a este, solo si su pantalla existe aqui y la cuenta puede abrirla.
  const posicion = recorrido ? pasoDeRuta(recorrido, "/inicio") : null;
  const siguiente = recorrido && posicion !== null ? recorrido.pasos[posicion + 1] : undefined;
  const paginaSiguiente = siguiente ? paginaPorId(siguiente.pagina, PAGINAS) : undefined;
  const puedeSeguir =
    paginaSiguiente !== undefined &&
    estaMigrada(paginaSiguiente) &&
    visible(paginaSiguiente, sesion.acciones, sesion.modo_entrega);

  const auditar = (modo: ModoDeAuditoria) => {
    if (!archivo) return;
    fijarArchivoPendiente(archivo, modo);
    if (modo === "guiado") iniciarRecorrido(RECORRIDO_AUDITAR);
    void navegar("/libros");
  };

  return (
    <div className="silice-inicio silice-pagina">
      <h1 className="cds--type-heading-04">Inicio</h1>

      <section className="silice-inicio__bloque" aria-labelledby="inicio-excel">
        <h2 id="inicio-excel" className="cds--type-heading-compact-02">
          Audite un presupuesto
        </h2>
        <p className="silice-inicio__nota cds--type-body-compact-01">
          Suelte el Excel del presupuesto. Sílice recalcula cada partida y le dice lo que no cuadra. El archivo no se
          guarda; solo quedan el resumen y los hallazgos.
        </p>
        <SubidaArchivo
          id="inicio-subida"
          etiqueta="Suelte aquí el libro .xlsx del presupuesto, o haga clic para elegirlo"
          extensiones={[".xlsx"]}
          alElegir={setArchivo}
        />
        <p role="status" className="silice-inicio__nota cds--type-body-compact-01">
          {archivo ? `Archivo elegido: ${archivo.name}` : ""}
        </p>
        {archivo && (
          <div className="silice-inicio__acciones">
            <Button kind="primary" size="md" onClick={() => auditar("guiado")}>
              Auditar con recorrido guiado
            </Button>
            <Button kind="tertiary" size="md" onClick={() => auditar("propio")}>
              Auditar por mi cuenta
            </Button>
          </div>
        )}
      </section>

      <PanelArenera carga={arenera} />

      <section className="silice-inicio__bloque" aria-labelledby="inicio-seguir">
        <h2 id="inicio-seguir" className="cds--type-heading-compact-02">
          Últimas auditorías guardadas
        </h2>
        <p className="silice-inicio__nota cds--type-body-compact-01">
          {`Caso abierto: ${caso?.nombre ?? "ninguno"}`}
          {proyecto ? ` · Proyecto: ${nombreProyecto ?? proyecto}` : ""}
        </p>
        {recorrido && (
          <p className="silice-inicio__nota cds--type-body-compact-01">
            {`Recorrido en curso: ${recorrido.titulo}.`}
            {siguiente && paginaSiguiente && puedeSeguir && (
              <>
                {" "}
                <Link className="cds--link" to={rutaDe(paginaSiguiente)}>
                  {`Seguir con el paso ${(posicion ?? 0) + 2}: ${siguiente.titulo}`}
                </Link>
              </>
            )}
          </p>
        )}
        <UltimasAuditorias carga={auditorias} />
      </section>
    </div>
  );
}
