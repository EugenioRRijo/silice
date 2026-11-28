import { useMemo } from "react";
import type { CarpetaRespuesta, ResumenTodasRespuesta } from "../../api/tipos";
import { EmpiezaAqui } from "../../comun/ayuda/BloqueEmpiezaAqui";
import { pasosDeEmpiezaAqui } from "../../comun/ayuda/empiezaAqui";
import { useCarga } from "../../comun/useCarga";
import { ESPACIOS, rutaOPendientes } from "../../marco/espacios";
import type { EspacioId } from "../../marco/espacios";
import { obrasConMismoNombre } from "../../marco/homonimas";
import { ofertaDe } from "../../marco/oferta";
import { usePendientes } from "../../marco/usePendientes";
import { useAplicacion } from "../../shell/contexto";
import { paginaPorId, usable } from "../../shell/rutas";
import { claveDeObra, contarUrgencias } from "../pendientes/logica";
import { CarteraYAvance } from "./CarteraYAvance";
import { LanzadorDeEspacio } from "./LanzadorDeEspacio";
import { LoCargado } from "./LoCargado";
import type { InsumoResumenRespuesta, PartidaResumenRespuesta } from "./LoCargado";
import { LoQueBloquea, ResumenDeGravedad } from "./LoQueBloquea";
import type { ExistenciaRespuesta } from "./PanelArenera";
import { TEXTOS, resumirTituloDeCartera } from "./textos";
import type { AuditoriaGuardadaRespuesta } from "./UltimasAuditorias";

const RUTA_CARTERA = "/v1/obras/resumen/todas";
const RUTA_AUDITORIAS = "/v1/auditorias-libro?limite=100";
const RUTA_CARPETA = "/v1/carpeta";
const RUTA_PARTIDAS = "/partidas";
const RUTA_INSUMOS = "/insumos";
const RUTA_ARENERA = "/v1/produccion/existencias";
const RUTA_CUENTAS = "/v1/cuentas";

function herramientasUsables(id: EspacioId, acciones: readonly string[], modoEntrega: boolean, apagados: readonly string[]): string {
  return ESPACIOS[id].herramientas
    .filter((h) => {
      const pagina = paginaPorId(h.pagina);
      return pagina !== undefined && usable(pagina, acciones, modoEntrega, apagados);
    })
    .map((h) => h.titulo)
    .join(" · ");
}

function rutaSiUsable(
  paginaId: string,
  acciones: readonly string[],
  modoEntrega: boolean,
  apagados: readonly string[],
): string | null {
  const pagina = paginaPorId(paginaId);
  return pagina !== undefined && usable(pagina, acciones, modoEntrega, apagados) ? rutaOPendientes(paginaId) : null;
}

// Inicio › Resumen (`#/inicio/general`, especificación 00-inicio-resumen.html): h1 con el resumen de la cartera (obras y
// total por moneda, sin sumar Bs con USD), el gráfico principal de la cartera, y debajo, más pequeños y de otra clase, el
// avance de la cartera, los problemas abiertos por obra (con su palabra) y las tarjetas de lo cargado.
export default function Panorama() {
  const { alExpirar, sesion, modulosApagados, abrirNuevaObra } = useAplicacion();
  const apagados = useMemo(() => modulosApagados ?? [], [modulosApagados]);
  const oferta = useMemo(() => ofertaDe(sesion.acciones, sesion.modo_entrega, apagados), [sesion.acciones, sesion.modo_entrega, apagados]);

  const puedeLeer = sesion.acciones.includes("leer_proyecto");
  const puedeVerCarpeta = puedeLeer || sesion.acciones.includes("administrar_precios");
  const puedeVerArenera = sesion.acciones.includes("operar_arenera") && !apagados.includes("produccion");

  const cartera = useCarga<ResumenTodasRespuesta>(puedeLeer ? RUTA_CARTERA : null, alExpirar);
  const auditorias = useCarga<AuditoriaGuardadaRespuesta[]>(puedeLeer ? RUTA_AUDITORIAS : null, alExpirar);
  const carpeta = useCarga<CarpetaRespuesta>(puedeVerCarpeta ? RUTA_CARPETA : null, alExpirar);
  const partidas = useCarga<PartidaResumenRespuesta[]>(puedeLeer ? RUTA_PARTIDAS : null, alExpirar);
  const insumos = useCarga<InsumoResumenRespuesta[]>(puedeLeer ? RUTA_INSUMOS : null, alExpirar);
  const arenera = useCarga<ExistenciaRespuesta[]>(puedeVerArenera ? RUTA_ARENERA : null, alExpirar);
  const cuentas = useCarga<{ cuentas: { activa: boolean }[] }>(
    sesion.acciones.includes("administrar_cuentas") ? RUTA_CUENTAS : null,
    alExpirar,
  );

  const pendientes = usePendientes();
  const urgencias = contarUrgencias(pendientes.estado === "listo" ? pendientes.pendientes : []);

  const pasos = pasosDeEmpiezaAqui({
    acciones: sesion.acciones,
    obras: cartera.estado === "listo" && cartera.datos.carpetas_omitidas === 0 ? cartera.datos.obras.length : null,
    cuentasActivas: cuentas.estado === "listo" ? cuentas.datos.cuentas.filter((c) => c.activa).length : null,
  });

  const carpetas = useMemo(() => {
    if (cartera.estado !== "listo") return new Map<string, string>();
    return obrasConMismoNombre(
      cartera.datos.obras.map((o) => ({
        carpeta: o.carpeta,
        obra_id: o.obra_id,
        obra: o.nombre,
        carpeta_titulo: o.carpeta_titulo,
      })),
    );
  }, [cartera]);

  const problemasPorObra = useMemo(() => {
    const mapa = new Map<string, { bloquea: number; aviso: number }>();
    if (pendientes.estado !== "listo") return mapa;
    for (const p of pendientes.pendientes) {
      const clave = claveDeObra(p.carpeta, p.obra_id);
      const actual = mapa.get(clave) ?? { bloquea: 0, aviso: 0 };
      actual[p.urgencia] += 1;
      mapa.set(clave, actual);
    }
    return mapa;
  }, [pendientes]);

  const carteraLista = cartera.estado === "listo" ? cartera.datos : null;
  const titulo = resumirTituloDeCartera(carteraLista ? carteraLista.por_moneda : null, carteraLista ? carteraLista.obras.length : null);
  const enEjecucionTotal = carteraLista ? carteraLista.por_moneda.reduce((acc, m) => acc + m.en_ejecucion, 0) : 0;

  const enlaces = useMemo(
    () => ({
      auditoria: rutaSiUsable("auditoria", sesion.acciones, sesion.modo_entrega, apagados),
      precios:
        rutaSiUsable("precios_empresa", sesion.acciones, sesion.modo_entrega, apagados) ??
        rutaSiUsable("catalogo", sesion.acciones, sesion.modo_entrega, apagados),
      catalogo: rutaSiUsable("catalogo", sesion.acciones, sesion.modo_entrega, apagados),
      produccion: rutaSiUsable("existencias", sesion.acciones, sesion.modo_entrega, apagados),
    }),
    [sesion.acciones, sesion.modo_entrega, apagados],
  );

  return (
    <div className="silice-pagina silice-inicio">
      <header className="silice-inicio__encabezado">
        <span className="silice-inicio__sobre">{TEXTOS.sobre(carteraLista?.hoy ?? null)}</span>
        <h1 className="silice-inicio__h1 cds--type-heading-04" tabIndex={-1}>
          {titulo}
        </h1>
        <p className="silice-inicio__nota cds--type-body-compact-01">{TEXTOS.subtitulo}</p>
        {puedeLeer && (carteraLista !== null || pendientes.estado === "listo") && (
          <div className="silice-inicio__datos">
            {carteraLista !== null && carteraLista.obras.length > 0 && (
              <span>{TEXTOS.enEjecucion(enEjecucionTotal)}</span>
            )}
            {pendientes.estado === "listo" &&
              (urgencias.bloquea === 0 && urgencias.aviso === 0 ? (
                <span>{TEXTOS.sinProblemasAbiertos}</span>
              ) : (
                <ResumenDeGravedad bloquea={urgencias.bloquea} aviso={urgencias.aviso} />
              ))}
          </div>
        )}
      </header>

      <EmpiezaAqui pasos={pasos} acciones={sesion.acciones} />

      <CarteraYAvance
        carga={cartera}
        carpetas={carpetas}
        problemasPorObra={problemasPorObra}
        puedeCrear={sesion.acciones.includes("editar_hoja")}
        alCrear={abrirNuevaObra}
      />

      {puedeLeer && <LoQueBloquea obras={carteraLista?.obras ?? []} carpetas={carpetas} />}

      <LoCargado
        auditorias={auditorias}
        carpeta={carpeta}
        partidas={partidas}
        insumos={insumos}
        arenera={arenera}
        enlaces={enlaces}
      />

      {!puedeLeer && oferta.espacios.length > 0 && (
        <section className="silice-panel silice-lanzador" aria-label="Herramientas de la empresa">
          <div className="silice-panel__cabecera">
            <div>
              <h2 className="cds--type-heading-compact-02">Herramientas de la empresa</h2>
              <p className="silice-panel__subtitulo">Espacios de trabajo de la empresa</p>
            </div>
          </div>
          <div className="silice-lanzador__rejilla">
            {oferta.espacios.map((esp) => (
              <LanzadorDeEspacio
                key={esp.id}
                id={esp.id}
                titulo={esp.titulo}
                ruta={esp.ruta}
                herramientas={herramientasUsables(esp.id, sesion.acciones, sesion.modo_entrega, apagados)}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
