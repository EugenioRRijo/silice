import { useCallback, useState } from "react";
import { Link } from "react-router";
import { rutaOPendientes } from "../../marco/espacios";
import { useAplicacion } from "../../shell/contexto";
import { pasoDeRuta, useRecorrido } from "../../shell/recorrido";
import { paginaPorId, usable } from "../../shell/rutas";
import { UltimasAuditorias } from "../inicio/UltimasAuditorias";
import { AuditarApuPorHoja } from "./AuditarApuPorHoja";
import { AuditarUnLibro } from "./AuditarUnLibro";
import type { AuditoriaGuardadaRespuesta } from "../inicio/UltimasAuditorias";
import { useCarga } from "../../comun/useCarga";

const RUTA_AUDITORIAS = "/v1/auditorias-libro?limite=5";

// Aislado en su propio componente para volver a pedir `useCarga` cambiando la `key` al guardar una auditoría nueva.
function HistorialReciente({ alExpirar }: { alExpirar: () => void }) {
  const auditorias = useCarga<AuditoriaGuardadaRespuesta[]>(RUTA_AUDITORIAS, alExpirar);
  return <UltimasAuditorias carga={auditorias} />;
}

// «Auditar un libro» (B2): arriba el flujo de una sola página (subir, qué se encontró, conclusión y entrega), plegado el libro
// con un APU por hoja y debajo lo último que se auditó. Cada bloque responde una pregunta («¿qué hago?», «¿dónde estaba?»).
export default function PaginaAuditoria() {
  const { alExpirar, caso, proyecto, nombreProyecto, sesion, modulosApagados } = useAplicacion();
  // Auditar y el historial son de quien puede leer proyectos (la API contestaria 403, VB-9); quien no puede no ve la
  // seccion vacia: se omite (VD-10).
  const puedeAuditar = sesion.acciones.includes("leer_proyecto");
  const [claveHistorial, setClaveHistorial] = useState(0);
  const refrescarHistorial = useCallback(() => setClaveHistorial((n) => n + 1), []);

  const recorrido = useRecorrido();
  // El paso que sigue a este, solo si su pantalla existe aqui y la cuenta puede abrirla.
  const posicion = recorrido ? pasoDeRuta(recorrido, rutaOPendientes("auditoria")) : null;
  const siguiente = recorrido && posicion !== null ? recorrido.pasos[posicion + 1] : undefined;
  const paginaSiguiente = siguiente ? paginaPorId(siguiente.pagina) : undefined;
  const puedeSeguir = paginaSiguiente !== undefined && usable(paginaSiguiente, sesion.acciones, sesion.modo_entrega, modulosApagados);

  return (
    <div className="silice-inicio silice-pagina">
      <h1 className="cds--type-heading-04">Auditar un libro</h1>
      <p className="silice-inicio__nota cds--type-body-compact-01">
        Suba un presupuesto en Excel para recalcular sus partidas y detectar errores
      </p>

      {puedeAuditar ? (
        <AuditarUnLibro alAuditar={refrescarHistorial} />
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

      {/* F5 vial, tarea 6: el libro con un APU por hoja y su presupuesto (otro perfil, otra subida). */}
      {puedeAuditar && (
        <details className="silice-libro__plegado">
          <summary>Otro tipo de libro: un APU por hoja</summary>
          <AuditarApuPorHoja
            alExpirar={alExpirar}
            obra={nombreProyecto ?? null}
            puedeLlevar={sesion.acciones.includes("editar_hoja")}
          />
        </details>
      )}

      {puedeAuditar && (
        <section className="silice-inicio__bloque" aria-labelledby="auditoria-seguir">
          <h2 id="auditoria-seguir" className="cds--type-heading-compact-02">
            Últimas auditorías guardadas
          </h2>
          <p className="silice-inicio__nota cds--type-body-compact-01">
            {`Carpeta: ${caso?.nombre ? caso.nombre.replace(/\.db$/i, "") : "ninguna"}`}
            {proyecto ? ` · Obra: ${nombreProyecto ?? proyecto}` : ""}
          </p>
          {recorrido && (
            <p className="silice-inicio__nota cds--type-body-compact-01">
              {`Recorrido en curso: ${recorrido.titulo}.`}
              {siguiente && paginaSiguiente && puedeSeguir && (
                <>
                  {" "}
                  <Link className="cds--link" to={rutaOPendientes(paginaSiguiente.id)}>
                    {`Seguir con el paso ${(posicion ?? 0) + 2}: ${siguiente.titulo}`}
                  </Link>
                </>
              )}
            </p>
          )}
          <HistorialReciente key={claveHistorial} alExpirar={alExpirar} />
        </section>
      )}
    </div>
  );
}
