import { useMemo } from "react";
import { Link } from "react-router";
import type { ResumenTodasRespuesta } from "../../api/tipos";
import { ESPACIOS, rutaOPendientes } from "../../marco/espacios";
import type { EspacioId } from "../../marco/espacios";
import { obrasConMismoNombre } from "../../marco/homonimas";
import { ofertaDe } from "../../marco/oferta";
import { useAplicacion } from "../../shell/contexto";
import { paginaPorId, usable } from "../../shell/rutas";
import { EmpiezaAqui } from "../../comun/ayuda/BloqueEmpiezaAqui";
import { pasosDeEmpiezaAqui } from "../../comun/ayuda/empiezaAqui";
import { claveDeObra } from "../pendientes/logica";
import { CarteraYAvance } from "./CarteraYAvance";
import { LanzadorDeEspacio } from "./LanzadorDeEspacio";
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
const RUTA_CUENTAS = "/v1/cuentas";

// La Vista general (`#/inicio/general`; plan F6, T8; contrato de rutas 4; diseño visual B): la primera vez, «Empieza aquí»
// (F7, A4); después, lo que bloquea (los pendientes del marco), la cartera por moneda y el avance de cada obra contra el plan (una lectura de
// `GET /v1/obras/resumen/todas`), las últimas auditorías y, solo con `operar_arenera` y su especialidad encendida, la arenera.
// Cada bloque lee y falla por su cuenta: uno que falla dice su error y no tumba a los demás. La pantalla no calcula nada: las
// cifras son las del servidor, solo formateadas (el anillo por estado cuenta las obras de la lista).
//
// Los lanzadores de los espacios (rediseño 2026-11-21): cada uno se llama como su espacio en `marco/espacios.ts` (el mismo
// nombre de la barra lateral) y lo describe con las herramientas que la cuenta puede abrir allí, con sus nombres. El número
// de orden es adorno: va oculto a la lectora y fuera del nombre del enlace.
const CODIGO: Record<EspacioId, string> = { auditoria: "01", precios: "02", produccion: "03" };

function herramientasUsables(id: EspacioId, acciones: readonly string[], modoEntrega: boolean, apagados: readonly string[]): string {
  return ESPACIOS[id].herramientas
    .filter((h) => {
      const pagina = paginaPorId(h.pagina);
      return pagina !== undefined && usable(pagina, acciones, modoEntrega, apagados);
    })
    .map((h) => h.titulo)
    .join(" · ");
}

export default function Panorama() {
  const { alExpirar, sesion, modulosApagados, abrirNuevaObra } = useAplicacion();
  const espaciosOfrecidos = useMemo(
    () => ofertaDe(sesion.acciones, sesion.modo_entrega, modulosApagados ?? []).espacios,
    [sesion.acciones, sesion.modo_entrega, modulosApagados],
  );
  // Cada recurso se pide solo si la cuenta puede leerlo (la API contestaría 403): sin la acción, el bloque se omite.
  const puedeLeer = sesion.acciones.includes("leer_proyecto");
  const puedeVerArenera = sesion.acciones.includes("operar_arenera") && !(modulosApagados ?? []).includes("produccion");
  const cartera = useCarga<ResumenTodasRespuesta>(puedeLeer ? RUTA_CARTERA : null, alExpirar);
  const auditorias = useCarga<AuditoriaGuardadaRespuesta[]>(puedeLeer ? RUTA_AUDITORIAS : null, alExpirar);
  const arenera = useCarga<ExistenciaRespuesta[]>(puedeVerArenera ? RUTA_ARENERA : null, alExpirar);
  // F7, A4: «Empieza aquí» se deriva de lo que ya se sabe (la cartera) y, para quien administra, de cuántas cuentas activas
  // hay. Una cartera con carpetas que no se pudieron leer no dice que no haya obras.
  const cuentas = useCarga<{ cuentas: { activa: boolean }[] }>(sesion.acciones.includes("administrar_cuentas") ? RUTA_CUENTAS : null, alExpirar);
  const pasos = pasosDeEmpiezaAqui({
    acciones: sesion.acciones,
    obras: cartera.estado === "listo" && cartera.datos.carpetas_omitidas === 0 ? cartera.datos.obras.length : null,
    cuentasActivas: cuentas.estado === "listo" ? cuentas.datos.cuentas.filter((c) => c.activa).length : null,
  });

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
      <EmpiezaAqui pasos={pasos} acciones={sesion.acciones} />
      {espaciosOfrecidos.length > 0 && (
        <section className="silice-panel silice-lanzador" aria-label="Herramientas dedicadas">
          <div className="silice-panel__cabecera">
            <div>
              <h2 className="cds--type-heading-compact-02">Herramientas dedicadas</h2>
              <p className="silice-panel__subtitulo">
                Abra cualquiera de los espacios especializados a pantalla completa sin salir de su instalación.
              </p>
            </div>
          </div>
          <div className="silice-lanzador__rejilla">
            {espaciosOfrecidos.map((esp) => (
              <LanzadorDeEspacio
                key={esp.id}
                id={esp.id}
                codigo={CODIGO[esp.id]}
                titulo={esp.titulo}
                ruta={esp.ruta}
                herramientas={herramientasUsables(esp.id, sesion.acciones, sesion.modo_entrega, modulosApagados ?? [])}
              />
            ))}
          </div>
        </section>
      )}
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
