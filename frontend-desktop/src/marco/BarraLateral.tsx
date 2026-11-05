import { Add } from "@carbon/icons-react";
import { useEffect, useId, useMemo } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import { Pildora } from "../comun/Pildora";
import { claveDeObra, contarPorObra } from "../paginas/pendientes/logica";
import { TEXTOS as TEXTOS_PENDIENTES } from "../paginas/pendientes/textos";
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
import { ZonaDeCostos } from "./ZonaDeCostos";

interface Props {
  obraAbierta: { carpeta: string | null; obraId: number } | null;
}

// Barra lateral del marco nuevo: Vista general (con los pendientes por hacer), la lista plana de Obras y «Costos y producción». Cada obra es un enlace a su Resumen (F6, T5;
// decisión de Eugenio, 2026-11-04: elegir otra obra no conserva la sección); las secciones de la obra abierta están en su
// barra, bajo la cabecera (EspacioDeObra). Sin títulos de grupo por carpeta (D-F3-3): las obras van por nombre y solo las de
// nombre repetido dicen su carpeta. Las píldoras de Pendientes y de cada obra salen de los pendientes que el marco ya
// cargó (`usePendientes`). «Costos y producción» vive en ZonaDeCostos; la Cuenta, a la que ya no lleva ninguna entrada de
// esta barra, se abre desde el botón de la persona (F6, T6).
export function BarraLateral({ obraAbierta }: Props) {
  const { acciones, puedeCambiarDeCarpeta, oferta } = useOferta();
  const navegar = useNavigate();
  const base = useId();
  const { obras, carpetaActual, tituloActual, estado, recargar } = useObras();
  // Los contadores solo se pintan con la lectura lista y mayor que cero: cargando o con error no hay número (ni uno falso).
  const carga = usePendientes();
  const porObra = useMemo(() => contarPorObra(carga.estado === "listo" ? carga.pendientes : []), [carga]);
  const total = carga.estado === "listo" ? carga.pendientes.length : 0;
  // Las dos vistas de Inicio (Vista general y Pendientes) son del mismo espacio: la entrada está activa en cualquiera.
  const { pathname } = useLocation();
  const enInicio = esRutaDeInicio(pathname);
  // El espacio de la ruta (`/produccion/…`, `/auditoria/…`, `/precios/…`): el primer segmento.
  const primerSegmento = pathname.split("/")[1] ?? "";
  const espacioActivo = oferta.espacios.find((e) => e.id === primerSegmento)?.id ?? null;
  // El diálogo lo puede pedir también la mesa (marco/nuevaObra); al irse la barra (salir de la sesión) se cierra.
  const nuevaAbierta = useNuevaObraAbierta();
  useEffect(() => cerrarNuevaObra, []);
  const { espacios } = oferta;
  const puedeCrear = acciones.includes("editar_hoja");

  // Por nombre (sin tildes ni mayúsculas) y, si se repite, por carpeta: la API las trae por carpeta (D-F3-3).
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
  // «Nueva obra» crea donde está la persona: en la carpeta de la obra abierta en la ruta o, sin obra, en la de la sesión.
  const carpetaDeCreacion = obraAbierta === null ? carpetaActual : obraAbierta.carpeta;
  // El título lo da el servidor: el de la carpeta de la sesión viene con la lista; el de otra, con sus obras.
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
    // El nombre accesible dice lo mismo que se ve: la obra, su carpeta si hay homónima y cuántos pendientes tiene.
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
    // Sin nada que mostrar: mientras llega la primera lista (o una recarga de una lista vacía) se dice que carga; no se
    // pinta una lista vacía. Con obras ya cargadas, una recarga conserva la lista.
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
    <aside className="silice-marco-lateral" aria-label="Barra lateral">
      <Link
        to={RUTA_DE_VISTA_GENERAL}
        aria-current={enInicio ? "page" : undefined}
        aria-label={total > 0 ? `Vista general, ${TEXTOS_PENDIENTES.porHacer(total)}` : undefined}
        className="silice-marco-lateral__fila silice-marco-lateral__pendientes"
      >
        Vista general
        {total > 0 && <Pildora valor={total} />}
      </Link>

      {/* Sin `leer_proyecto` la cuenta no ve obras: la zona no se pinta. */}
      {estado !== "sin_permiso" && (
        <div className="silice-marco-lateral__obras">
          <h2 className="silice-marco-lateral__titulo">Obras</h2>
          {puedeCrear && (
            <button type="button" className="silice-marco-boton-principal" onClick={abrirNuevaObra}>
              <Add size={20} aria-hidden="true" />
              Nueva obra
            </button>
          )}
          {zonaDeObras()}
        </div>
      )}

      <ZonaDeCostos espacios={espacios} espacioActivo={espacioActivo} idBase={base} />

      <DialogoNuevaObra
        abierto={nuevaAbierta}
        alCerrar={cerrarNuevaObra}
        destino={destino}
        alCrear={(obra) => {
          cerrarNuevaObra();
          recargar();
          // El código lo da el servidor como texto; si no son dígitos no hay ruta a la obra nueva y se queda donde está.
          if (/^\d+$/.test(obra.codigo)) navegar(rutaDeObra(destino.carpeta, Number(obra.codigo), "resumen"));
        }}
      />
    </aside>
  );
}
