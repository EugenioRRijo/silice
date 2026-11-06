import { useMemo } from "react";
import { Link } from "react-router";
import type { ResumenTodasRespuesta } from "../../api/tipos";
import { rutaOPendientes } from "../../marco/espacios";
import { obrasConMismoNombre } from "../../marco/homonimas";
import { useAplicacion } from "../../shell/contexto";
import { claveDeObra } from "../pendientes/logica";
import { CarteraYAvance } from "./CarteraYAvance";
import { LoQueBloquea } from "./LoQueBloquea";
import { PanelArenera } from "./PanelArenera";
import type { ExistenciaRespuesta } from "./PanelArenera";
import { TEXTOS } from "./textos";
import { UltimasAuditorias } from "./UltimasAuditorias";
import type { AuditoriaGuardadaRespuesta } from "./UltimasAuditorias";
import { useCarga } from "../../comun/useCarga";

const RUTA_CARTERA = "/v1/obras/resumen/todas";
const RUTA_AUDITORIAS = "/v1/auditorias-libro?limite=5";
const RUTA_ARENERA = "/v1/produccion/existencias";

// La Vista general (`#/inicio/general`; plan F6, T8; contrato de rutas 4; diseño visual B): lo primero es lo que bloquea (los
// pendientes del marco), después la cartera por moneda y el avance de cada obra contra el plan (una lectura de
// `GET /v1/obras/resumen/todas`), las últimas auditorías y, solo con `operar_arenera` y su especialidad encendida, la arenera.
// Cada bloque lee y falla por su cuenta: uno que falla dice su error y no tumba a los demás. La pantalla no calcula nada: las
// cifras son las del servidor, solo formateadas.
export default function Panorama() {
  const { alExpirar, sesion, modulosApagados, abrirNuevaObra } = useAplicacion();
  // Cada recurso se pide solo si la cuenta puede leerlo (la API contestaría 403): sin la acción, el bloque se omite.
  const puedeLeer = sesion.acciones.includes("leer_proyecto");
  const puedeVerArenera = sesion.acciones.includes("operar_arenera") && !(modulosApagados ?? []).includes("produccion");
  const cartera = useCarga<ResumenTodasRespuesta>(puedeLeer ? RUTA_CARTERA : null, alExpirar);
  const auditorias = useCarga<AuditoriaGuardadaRespuesta[]>(puedeLeer ? RUTA_AUDITORIAS : null, alExpirar);
  const arenera = useCarga<ExistenciaRespuesta[]>(puedeVerArenera ? RUTA_ARENERA : null, alExpirar);

  // La carpeta de las obras que se llaman igual en carpetas distintas: sale de la misma cartera (que lista todas las obras
  // que la cuenta puede abrir), así la Vista general no pide otra vez la lista de obras.
  const carpetas = useMemo(() => {
    if (cartera.estado !== "listo") return new Map<string, string>();
    return obrasConMismoNombre(cartera.datos.obras.map((o) => ({ carpeta: o.carpeta, obra_id: o.obra_id, obra: o.nombre, carpeta_titulo: o.carpeta_titulo })));
  }, [cartera]);

  return (
    <div className="silice-pagina silice-inicio">
      <h1 className="cds--type-heading-04" tabIndex={-1}>
        {TEXTOS.titulo}
      </h1>
      <LoQueBloquea carpetaDe={(p) => carpetas.get(claveDeObra(p.carpeta, p.obra_id))} />
      <CarteraYAvance carga={cartera} carpetas={carpetas} puedeCrear={sesion.acciones.includes("editar_hoja")} alCrear={abrirNuevaObra} />
      {puedeLeer && (
        <section className="silice-inicio__bloque" aria-labelledby="inicio-auditorias">
          <h2 id="inicio-auditorias" className="cds--type-heading-compact-02">
            {TEXTOS.auditorias.titulo}
          </h2>
          <UltimasAuditorias carga={auditorias} desde="vista-general" />
          <Link className="cds--link" to={rutaOPendientes("auditoria")}>
            {TEXTOS.auditorias.ir}
          </Link>
        </section>
      )}
      {puedeVerArenera && <PanelArenera carga={arenera} />}
    </div>
  );
}
