import { Button } from "@carbon/react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { useAplicacion } from "../../shell/contexto";
import { RECORRIDO_AUDITAR, iniciarRecorrido, pasoDeRuta, useRecorrido } from "../../shell/recorrido";
import { paginaPorId, rutaDe, usable } from "../../shell/rutas";
import { fijarArchivoPendiente } from "../inicio/archivoPendiente";
import type { ModoDeAuditoria } from "../inicio/archivoPendiente";
import { UltimasAuditorias } from "../inicio/UltimasAuditorias";
import type { AuditoriaGuardadaRespuesta } from "../inicio/UltimasAuditorias";
import { useCarga } from "../inicio/useCarga";

const RUTA_AUDITORIAS = "/v1/auditorias-libro?limite=5";

// Inicio de «Auditoría»: arriba el Excel de un presupuesto (con o sin recorrido guiado), debajo lo ultimo que se audito.
// Cada bloque responde una pregunta («¿que hago?», «¿donde estaba?»); nada de tarjetas de adorno.
export default function PaginaAuditoria() {
  const { alExpirar, caso, proyecto, nombreProyecto, sesion } = useAplicacion();
  const navegar = useNavigate();
  const [archivo, setArchivo] = useState<File | null>(null);
  // Auditar y el historial son de quien puede leer proyectos (la API contestaria 403, VB-9); quien no puede no ve la
  // seccion vacia: se omite (VD-10).
  const puedeAuditar = sesion.acciones.includes("leer_proyecto");
  const auditorias = useCarga<AuditoriaGuardadaRespuesta[]>(puedeAuditar ? RUTA_AUDITORIAS : null, alExpirar);

  const recorrido = useRecorrido();
  // El paso que sigue a este, solo si su pantalla existe aqui y la cuenta puede abrirla.
  const posicion = recorrido ? pasoDeRuta(recorrido, "/auditoria") : null;
  const siguiente = recorrido && posicion !== null ? recorrido.pasos[posicion + 1] : undefined;
  const paginaSiguiente = siguiente ? paginaPorId(siguiente.pagina) : undefined;
  const puedeSeguir = paginaSiguiente !== undefined && usable(paginaSiguiente, sesion.acciones, sesion.modo_entrega);

  const auditar = (modo: ModoDeAuditoria) => {
    if (!archivo) return;
    fijarArchivoPendiente(archivo, modo);
    if (modo === "guiado") iniciarRecorrido(RECORRIDO_AUDITAR);
    void navegar("/libros");
  };

  return (
    <div className="silice-inicio silice-pagina">
      <h1 className="cds--type-heading-04">Inicio de auditoría</h1>

      {puedeAuditar ? (
        <section className="silice-inicio__bloque" aria-labelledby="auditoria-excel">
          <h2 id="auditoria-excel" className="cds--type-heading-compact-02">
            Audite un presupuesto
          </h2>
          <p className="silice-inicio__nota cds--type-body-compact-01">
            Suelte el Excel del presupuesto. Sílice recalcula cada partida y le dice lo que no cuadra. El archivo no se
            guarda; solo quedan el resumen y los hallazgos.
          </p>
          <SubidaArchivo
            id="auditoria-subida"
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
      ) : (
        <section className="silice-inicio__bloque" aria-labelledby="auditoria-excel">
          <h2 id="auditoria-excel" className="cds--type-heading-compact-02">
            Quién audita los presupuestos
          </h2>
          <p className="silice-inicio__nota cds--type-body-compact-01">
            Su cuenta no tiene permiso para auditar presupuestos. Pídale a quien arma o revisa presupuestos que suba el
            Excel desde su cuenta.
          </p>
        </section>
      )}

      {puedeAuditar && (
        <section className="silice-inicio__bloque" aria-labelledby="auditoria-seguir">
          <h2 id="auditoria-seguir" className="cds--type-heading-compact-02">
            Últimas auditorías guardadas
          </h2>
          <p className="silice-inicio__nota cds--type-body-compact-01">
            {`Carpeta de trabajo: ${caso?.nombre ?? "ninguna"}`}
            {proyecto ? ` · Obra: ${nombreProyecto ?? proyecto}` : ""}
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
      )}
    </div>
  );
}
