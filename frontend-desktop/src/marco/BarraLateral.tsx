import {
  Add,
  Catalog,
  Dashboard,
  DocumentView,
  Industry,
  SidePanelClose,
  SidePanelOpen,
} from "@carbon/icons-react";
import { useEffect, useId, useLayoutEffect, useMemo, useRef } from "react";
import { Link, useLocation } from "react-router";
import { Pildora } from "../comun/Pildora";
import { claveDeObra, contarPorObra } from "../paginas/pendientes/logica";
import { TEXTOS as TEXTOS_PENDIENTES } from "../paginas/pendientes/textos";
import { useNavegarSeguro } from "../shell/navegarSeguro";
import { DialogoNuevaObra } from "../shell/obras/DialogoNuevaObra";
import type { DestinoDeNuevaObra } from "../shell/obras/DialogoNuevaObra";
import "./BarraLateral.scss";
import { obrasConMismoNombre } from "./homonimas";
import { NombreDeObra } from "./NombreDeObra";
import { abrirNuevaObra, cerrarNuevaObra, useNuevaObraAbierta } from "./nuevaObra";
import { obrasAlcanzables, useOferta } from "./oferta";
import { RUTA_DE_VISTA_GENERAL, esRutaDeInicio, rutaDeObra } from "./secciones";
import { useObras, type ObraDeCarpeta } from "./useObras";
import { usePendientes } from "./usePendientes";
import { useWorkspaceLayout } from "./useWorkspaceLayout";
import { ZonaDeCostos } from "./ZonaDeCostos";

interface Props {
  obraAbierta: { carpeta: string | null; obraId: number } | null;
}

function iconoDeEspacio(id: string) {
  if (id === "auditoria") return <DocumentView size={16} aria-hidden="true" />;
  if (id === "precios") return <Catalog size={16} aria-hidden="true" />;
  return <Industry size={16} aria-hidden="true" />;
}

export function BarraLateral({ obraAbierta }: Props) {
  const { acciones, puedeCambiarDeCarpeta, oferta } = useOferta();
  const { sidebarCollapsed, toggleSidebar } = useWorkspaceLayout();
  // Plegar o desplegar desmonta una rama y monta la otra: el botón pulsado (o la obra enfocada, con Ctrl+B) desaparece y el
  // foco caería en el cuerpo del documento. Si se perdió, pasa al botón equivalente de la rama nueva (WCAG 2.4.3); si lo
  // tiene otro control (el contenido, con Ctrl+B), no se toca.
  const alternador = useRef<HTMLButtonElement>(null);
  const plegadaAntes = useRef(sidebarCollapsed);
  useLayoutEffect(() => {
    if (plegadaAntes.current === sidebarCollapsed) return;
    plegadaAntes.current = sidebarCollapsed;
    const activo = document.activeElement;
    if (activo === null || activo === document.body) alternador.current?.focus();
  }, [sidebarCollapsed]);
  const navegar = useNavegarSeguro();
  const base = useId();
  const { obras, carpetaActual, tituloActual, estado, recargar } = useObras();
  const carga = usePendientes();
  const porObra = useMemo(() => contarPorObra(carga.estado === "listo" ? carga.pendientes : []), [carga]);
  const total = carga.estado === "listo" ? carga.pendientes.length : 0;
  const { pathname } = useLocation();
  const enInicio = esRutaDeInicio(pathname);
  const primerSegmento = pathname.split("/")[1] ?? "";
  const espacioActivo = oferta.espacios.find((e) => e.id === primerSegmento)?.id ?? null;
  const nuevaAbierta = useNuevaObraAbierta();
  useEffect(() => cerrarNuevaObra, []);
  const { espacios } = oferta;
  const puedeCrear = acciones.includes("editar_hoja");

  const visibles = useMemo(
    () =>
      obrasAlcanzables(obras, carpetaActual, puedeCambiarDeCarpeta).toSorted(
        (a, b) =>
          a.obra.localeCompare(b.obra, "es", { sensitivity: "base" }) ||
          a.carpeta_titulo.localeCompare(b.carpeta_titulo, "es", { sensitivity: "base" }),
      ),
    [obras, carpetaActual, puedeCambiarDeCarpeta],
  );
  const carpetaDeHomonimas = useMemo(() => obrasConMismoNombre(visibles), [visibles]);
  const carpetaDeCreacion = obraAbierta === null ? carpetaActual : obraAbierta.carpeta;
  const tituloDeCreacion =
    carpetaDeCreacion === carpetaActual
      ? tituloActual
      : (obras.find((o) => o.carpeta === carpetaDeCreacion)?.carpeta_titulo ?? "");
  const destino: DestinoDeNuevaObra = {
    carpeta: carpetaDeCreacion,
    titulo: tituloDeCreacion,
    enOtraCarpeta: carpetaDeCreacion !== carpetaActual,
  };

  const claveAbierta = obraAbierta === null ? null : claveDeObra(obraAbierta.carpeta, obraAbierta.obraId);

  function filaDeObra(o: ObraDeCarpeta) {
    const clave = claveDeObra(o.carpeta, o.obra_id);
    const carpeta = carpetaDeHomonimas.get(clave);
    const cuenta = porObra.get(clave) ?? 0;
    const nombre = [o.obra, carpeta, cuenta > 0 ? TEXTOS_PENDIENTES.porHacer(cuenta) : undefined].filter(Boolean).join(", ");
    return (
      <li key={clave}>
        <Link
          to={rutaDeObra(o.carpeta, o.obra_id, "resumen")}
          aria-label={nombre === o.obra ? undefined : nombre}
          aria-current={clave === claveAbierta ? "page" : undefined}
          className="silice-marco-lateral__fila silice-marco-lateral__obra"
        >
          <span className="silice-marco-lateral__nombre">
            <NombreDeObra nombre={o.obra} />
            {carpeta !== undefined && <span className="silice-marco-lateral__de-carpeta">{carpeta}</span>}
          </span>
          {cuenta > 0 && <Pildora valor={cuenta} />}
        </Link>
      </li>
    );
  }

  function zonaDeObras() {
    if (estado === "error") {
      return (
        <div className="silice-marco-lateral__aviso" role="alert">
          <p>No se pudieron cargar las obras</p>
          <button type="button" className="silice-marco-lateral__reintentar" onClick={recargar}>
            Reintentar
          </button>
        </div>
      );
    }
    if (visibles.length === 0) {
      return estado === "cargando" ? (
        <p className="silice-marco-lateral__aviso" role="status">
          Cargando obras…
        </p>
      ) : (
        <p className="silice-marco-lateral__aviso">Todavía no hay obras</p>
      );
    }
    return (
      <ul aria-label="Obras" className="silice-marco-lateral__arbol">
        {visibles.map(filaDeObra)}
      </ul>
    );
  }

  return (
    <aside
      className={`silice-marco-lateral${sidebarCollapsed ? " silice-marco-lateral--colapsada" : ""}`}
      data-collapsed={sidebarCollapsed ? "true" : "false"}
      aria-label="Barra lateral"
    >
      {sidebarCollapsed ? (
        <div className="silice-marco-lateral__riel">
          <div className="silice-marco-lateral__riel-arriba">
            <button
              ref={alternador}
              type="button"
              className="silice-marco-lateral__riel-btn silice-marco-lateral__riel-btn--toggle"
              onClick={toggleSidebar}
              aria-label="Mostrar barra lateral"
              aria-expanded={false}
              title="Mostrar barra lateral (Ctrl+B)"
            >
              <SidePanelOpen size={16} aria-hidden="true" />
            </button>
            <div className="silice-marco-lateral__riel-sep" aria-hidden="true" />
            <Link
              to={RUTA_DE_VISTA_GENERAL}
              aria-current={enInicio ? "page" : undefined}
              aria-label={total > 0 ? `Vista general, ${TEXTOS_PENDIENTES.porHacer(total)}` : "Vista general"}
              title={total > 0 ? `Vista general (${total})` : "Vista general"}
              className="silice-marco-lateral__riel-btn"
            >
              <Dashboard size={16} aria-hidden="true" />
            </Link>
            {estado !== "sin_permiso" && puedeCrear && (
              <button
                type="button"
                className="silice-marco-lateral__riel-btn silice-marco-lateral__riel-btn--primario"
                onClick={abrirNuevaObra}
                aria-label="Nueva obra"
                title="Nueva obra"
              >
                <Add size={16} aria-hidden="true" />
              </button>
            )}
          </div>
          {espacios.length > 0 && (
            <nav aria-label="Costos y producción" className="silice-marco-lateral__riel-abajo">
              {espacios.map((e) => (
                <Link
                  key={e.id}
                  to={e.ruta}
                  aria-current={espacioActivo === e.id ? "page" : undefined}
                  aria-label={e.titulo}
                  title={e.titulo}
                  className="silice-marco-lateral__riel-btn silice-marco-lateral__riel-btn--oro"
                >
                  {iconoDeEspacio(e.id)}
                </Link>
              ))}
            </nav>
          )}
        </div>
      ) : (
        <>
          <div className="silice-marco-lateral__cabecera">
            <Link
              to={RUTA_DE_VISTA_GENERAL}
              aria-current={enInicio ? "page" : undefined}
              aria-label={total > 0 ? `Vista general, ${TEXTOS_PENDIENTES.porHacer(total)}` : undefined}
              className="silice-marco-lateral__fila silice-marco-lateral__pendientes"
            >
              <Dashboard size={16} aria-hidden="true" />
              <span>Vista general</span>
              {total > 0 && <Pildora valor={total} />}
            </Link>
            <button
              ref={alternador}
              type="button"
              className="silice-marco-lateral__plegar"
              onClick={toggleSidebar}
              aria-label="Ocultar barra lateral"
              aria-expanded={true}
              title="Ocultar barra lateral (Ctrl+B)"
            >
              <SidePanelClose size={16} aria-hidden="true" />
            </button>
          </div>

          {estado !== "sin_permiso" && (
            <div className="silice-marco-lateral__obras">
              <div className="silice-marco-lateral__obras-cabecera">
                <h2 className="silice-marco-lateral__titulo">Obras</h2>
                {visibles.length > 0 && (
                  <span className="silice-marco-lateral__conteo" aria-hidden="true">
                    {visibles.length}
                  </span>
                )}
              </div>
              {puedeCrear && (
                <div className="silice-marco-lateral__accion">
                  <button type="button" className="silice-marco-boton-principal" onClick={abrirNuevaObra}>
                    <Add size={16} aria-hidden="true" />
                    Nueva obra
                  </button>
                </div>
              )}
              {zonaDeObras()}
            </div>
          )}

          <ZonaDeCostos espacios={espacios} espacioActivo={espacioActivo} idBase={base} />
        </>
      )}

      <DialogoNuevaObra
        abierto={nuevaAbierta}
        alCerrar={cerrarNuevaObra}
        destino={destino}
        alCrear={(obra) => {
          cerrarNuevaObra();
          recargar();
          if (/^\d+$/.test(obra.codigo)) void navegar(rutaDeObra(destino.carpeta, Number(obra.codigo), "resumen"));
        }}
      />
    </aside>
  );
}
