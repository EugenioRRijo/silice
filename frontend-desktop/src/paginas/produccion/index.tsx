import { Link } from "react-router";
import { EnlacesDeCostos } from "../../comun/EnlacesDeCostos";
import { rutaOPendientes } from "../../marco/espacios";
import { useAplicacion } from "../../shell/contexto";
import { PanelArenera } from "../inicio/PanelArenera";
import type { ExistenciaRespuesta } from "../inicio/PanelArenera";
import { useCarga } from "../../comun/useCarga";

const RUTA_ARENERA = "/v1/produccion/existencias";

// Inicio de «Producción»: lo que requiere atención en la arenera (lo negativo primero) y el paso a Existencias.
export default function PaginaProduccion() {
  const { alExpirar, sesion } = useAplicacion();
  // Solo quien opera la arenera la pide (la API contestaria 403, VB-9); sin la accion el modulo ni siquiera se ve.
  const puedeVerArenera = sesion.acciones.includes("operar_arenera");
  const puedeRegistrarCostos = sesion.acciones.includes("registrar_costos_produccion");
  const arenera = useCarga<ExistenciaRespuesta[]>(puedeVerArenera ? RUTA_ARENERA : null, alExpirar);

  return (
    <div className="silice-inicio silice-pagina">
      <h1 className="cds--type-heading-04">Inicio de producción</h1>
      {puedeVerArenera ? (
        <PanelArenera carga={arenera} />
      ) : (
        <p className="silice-inicio__nota cds--type-body-compact-01">
          Su cuenta no opera la arenera. Pídale a quien administra Sílice que revise su rol.
        </p>
      )}
      {puedeVerArenera && (
        <p className="cds--type-body-compact-01">
          <Link className="cds--link" to={rutaOPendientes("receta_planta")}>
            Receta de la planta
          </Link>{" "}
          ·{" "}
          <Link className="cds--link" to={rutaOPendientes("producir_mezcla")}>
            Producir mezcla
          </Link>
        </p>
      )}
      {puedeRegistrarCostos && <EnlacesDeCostos />}
    </div>
  );
}
