import { Button, ClickableTile } from "@carbon/react";
import { useState } from "react";
import type { KeyboardEvent, MouseEvent } from "react";
import { Link, useHref, useNavigate } from "react-router";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { useAplicacion } from "../../shell/contexto";
import { RECORRIDO_AUDITAR, iniciarRecorrido, pasoDeRuta, useRecorrido } from "../../shell/recorrido";
import { PAGINAS, herramientasVisibles, paginaPorId, rutaDe, visible } from "../../shell/rutas";
import type { HerramientaVisible } from "../../shell/rutas";
import { fijarArchivoPendiente } from "./archivoPendiente";
import type { ModoDeAuditoria } from "./archivoPendiente";
import { PanelArenera } from "./PanelArenera";
import type { ExistenciaRespuesta } from "./PanelArenera";
import { UltimasAuditorias } from "./UltimasAuditorias";
import type { AuditoriaGuardadaRespuesta } from "./UltimasAuditorias";
import { useCarga } from "./useCarga";

const RUTA_ARENERA = "/v1/produccion/existencias";
const RUTA_AUDITORIAS = "/v1/auditorias-libro?limite=5";

// Una herramienta principal como mosaico: un enlace de verdad (abre en otra pestana con Ctrl o el boton central) que,
// con el clic normal, navega dentro de la aplicacion sin recargar. Nombre: el titulo; descripcion: su linea de ayuda.
function Mosaico({ herramienta }: { herramienta: HerramientaVisible }) {
  const ruta = rutaDe({ id: herramienta.pagina });
  const href = useHref(ruta);
  const navegar = useNavigate();
  const idTitulo = `inicio-herramienta-${herramienta.pagina}`;
  const idAyuda = `${idTitulo}-ayuda`;
  const alPulsar = (e: MouseEvent<HTMLAnchorElement> | KeyboardEvent<HTMLAnchorElement>) => {
    if ("button" in e && (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey)) return;
    e.preventDefault();
    void navegar(ruta);
  };
  return (
    <li>
      <ClickableTile
        href={href}
        className="silice-inicio__mosaico"
        aria-labelledby={idTitulo}
        aria-describedby={idAyuda}
        onClick={alPulsar}
      >
        <span id={idTitulo} className="silice-inicio__mosaico-titulo cds--type-heading-compact-01">
          {herramienta.titulo}
        </span>
        <span id={idAyuda} className="silice-inicio__mosaico-ayuda cds--type-body-compact-01">
          {herramienta.ayuda}
        </span>
      </ClickableTile>
    </li>
  );
}

// Inicio «panel del dia» (spec 2026-10-18-silice-ui-inicio-panel-del-dia-design.md, §2.1): arriba el Excel de un
// presupuesto, debajo la arenera y lo ultimo que se audito. Cada bloque responde una pregunta («¿que hago?»,
// «¿que falta en la arenera?», «¿donde estaba?»); nada de tarjetas de adorno.
export default function PaginaInicio() {
  const { alExpirar, caso, proyecto, nombreProyecto, sesion } = useAplicacion();
  const navegar = useNavigate();
  const [archivo, setArchivo] = useState<File | null>(null);
  // Cada recurso se pide solo si la cuenta tiene la accion que lo permite (la API contestaria 403): la arenera es de
  // quien la opera; auditar y el historial, de quien puede leer proyectos (VB-9).
  // Y quien no la tiene no ve la seccion vacia: se omite (VD-10). Un 403 de la API con la accion presente sigue
  // diciendo «sin datos».
  const puedeAuditar = sesion.acciones.includes("leer_proyecto");
  const puedeVerArenera = sesion.acciones.includes("operar_arenera");
  const arenera = useCarga<ExistenciaRespuesta[]>(puedeVerArenera ? RUTA_ARENERA : null, alExpirar);
  const auditorias = useCarga<AuditoriaGuardadaRespuesta[]>(puedeAuditar ? RUTA_AUDITORIAS : null, alExpirar);

  // Las tres herramientas del dia a dia (spec de la barra superior, §5.5): salieron de la navegacion y quedan aqui.
  const herramientas = herramientasVisibles(sesion.acciones, sesion.modo_entrega, PAGINAS);

  const recorrido = useRecorrido();
  // El paso que sigue a este, solo si su pantalla existe aqui y la cuenta puede abrirla.
  const posicion = recorrido ? pasoDeRuta(recorrido, "/inicio") : null;
  const siguiente = recorrido && posicion !== null ? recorrido.pasos[posicion + 1] : undefined;
  const paginaSiguiente = siguiente ? paginaPorId(siguiente.pagina, PAGINAS) : undefined;
  const puedeSeguir =
    paginaSiguiente !== undefined &&
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

      {puedeAuditar ? (
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
      ) : (
        <section className="silice-inicio__bloque" aria-labelledby="inicio-excel">
          <h2 id="inicio-excel" className="cds--type-heading-compact-02">
            Quién audita los presupuestos
          </h2>
          <p className="silice-inicio__nota cds--type-body-compact-01">
            {sesion.roles.includes("administrador")
              ? "Su cuenta administra Sílice y no audita presupuestos: audita quien arma o revisa presupuestos. Pídale que suba el Excel desde su cuenta."
              : "Su cuenta no tiene permiso para auditar presupuestos. Pídale a quien arma o revisa presupuestos que suba el Excel desde su cuenta."}
          </p>
        </section>
      )}

      {herramientas.length > 0 && (
        <section className="silice-inicio__bloque" aria-labelledby="inicio-herramientas">
          <h2 id="inicio-herramientas" className="cds--type-heading-compact-02">
            Herramientas principales
          </h2>
          <ul className="silice-inicio__mosaicos">
            {herramientas.map((h) => (
              <Mosaico key={h.pagina} herramienta={h} />
            ))}
          </ul>
        </section>
      )}

      {puedeVerArenera && <PanelArenera carga={arenera} />}

      {puedeAuditar && (
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
      )}
    </div>
  );
}
