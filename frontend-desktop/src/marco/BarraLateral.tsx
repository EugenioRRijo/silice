import { Add } from "@carbon/icons-react";
import { useEffect, useId, useMemo } from "react";
import { Link, useLocation } from "react-router";
import { Pildora } from "../comun/Pildora";
import { claveDeObra, contarPorObra, contarUrgencias } from "../paginas/pendientes/logica";
import { TEXTOS as TEXTOS_PENDIENTES } from "../paginas/pendientes/textos";
import type { PendienteDeObra } from "../api/tipos";
import { useNavegarSeguro } from "../shell/navegarSeguro";
import { DialogoNuevaObra } from "../shell/obras/DialogoNuevaObra";
import type { DestinoDeNuevaObra } from "../shell/obras/DialogoNuevaObra";
import "./BarraLateral.scss";
import { rutaDeCuenta } from "./espacios";
import { obrasConMismoNombre } from "./homonimas";
import { NombreDeObra } from "./NombreDeObra";
import { abrirNuevaObra, cerrarNuevaObra, useNuevaObraAbierta } from "./nuevaObra";
import { obrasAlcanzables, useOferta } from "./oferta";
import { iconoDeOpcion } from "./riel";
import { RielLateral } from "./RielLateral";
import type { CifraDeRiel, CifrasDeRiel, OpcionDeRiel } from "./RielLateral";
import { RUTA_DE_PENDIENTES, RUTA_DE_VISTA_GENERAL, SECCION_DE_ENTRADA, esRutaDeInicio, rutaDeObra } from "./secciones";
import { useObras, type ObraDeCarpeta } from "./useObras";
import { usePendientes } from "./usePendientes";
import { useWorkspaceLayout } from "./useWorkspaceLayout";
import { ZonaDeCostos } from "./ZonaDeCostos";

interface Props {
  obraAbierta: { carpeta: string | null; obraId: number } | null;
}

// Los pendientes de la obra abierta, contados por urgencia y dichos con las palabras de la bandeja (bloquea, aviso): la
// gravedad va siempre con su palabra. Un grupo en cero no se nombra.
function cifrasDeLaObra(pendientes: readonly PendienteDeObra[]): CifraDeRiel[] {
  const { bloquea, aviso } = contarUrgencias(pendientes);
  const filas: CifraDeRiel[] = [];
  if (bloquea > 0) {
    filas.push({ id: "bloquean", texto: TEXTOS_PENDIENTES.resumen(bloquea, 0), valor: bloquea, gravedad: "error", ruta: RUTA_DE_PENDIENTES });
  }
  if (aviso > 0) {
    filas.push({ id: "avisos", texto: TEXTOS_PENDIENTES.resumen(0, aviso), valor: aviso, gravedad: "advertencia", ruta: RUTA_DE_PENDIENTES });
  }
  return filas;
}

export function BarraLateral({ obraAbierta }: Props) {
  const { acciones, puedeCambiarDeCarpeta, oferta } = useOferta();
  const { sidebarCollapsed, toggleSidebar } = useWorkspaceLayout();
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

  const pendientesDe = (clave: string) =>
    carga.estado === "listo" ? carga.pendientes.filter((p) => claveDeObra(p.carpeta, p.obra_id) === clave) : [];

  function filaDeObra(o: ObraDeCarpeta) {
    const clave = claveDeObra(o.carpeta, o.obra_id);
    const carpeta = carpetaDeHomonimas.get(clave);
    const cuenta = porObra.get(clave) ?? 0;
    const urgencias = contarUrgencias(pendientesDe(clave));
    const gravedad = TEXTOS_PENDIENTES.resumen(urgencias.bloquea, urgencias.aviso);
    // El id no puede llevar espacios ni «|»: la clave de la obra trae el nombre del archivo de la carpeta.
    const idDeGravedad = `${base}-g-${clave.replace(/[^A-Za-z0-9_-]/g, "_")}`;
    const nombre = [o.obra, carpeta, cuenta > 0 ? TEXTOS_PENDIENTES.porHacer(cuenta) : undefined].filter(Boolean).join(", ");
    return (
      <li key={clave}>
        <Link
          to={rutaDeObra(o.carpeta, o.obra_id, SECCION_DE_ENTRADA)}
          aria-label={nombre === o.obra ? undefined : nombre}
          aria-current={clave === claveAbierta ? "page" : undefined}
          aria-describedby={gravedad === "" ? undefined : idDeGravedad}
          className="silice-marco-lateral__fila silice-marco-lateral__obra"
        >
          <span className="silice-marco-lateral__nombre">
            <NombreDeObra nombre={o.obra} />
            {carpeta !== undefined && <span className="silice-marco-lateral__de-carpeta">{carpeta}</span>}
            {gravedad !== "" && (
              <span id={idDeGravedad} className="silice-marco-lateral__gravedad" data-gravedad={urgencias.bloquea > 0 ? "error" : "advertencia"}>
                {gravedad}
              </span>
            )}
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

  const cuentaDeCarpetas = oferta.cuenta.some((c) => c.id === "carpetas");
  const carpetaAbierta =
    estado !== "sin_permiso" && tituloActual !== ""
      ? { nombre: tituloActual, rutaDeCambio: puedeCambiarDeCarpeta && cuentaDeCarpetas ? rutaDeCuenta("carpetas") : undefined }
      : undefined;

  const opciones: OpcionDeRiel[] = [
    {
      id: "vista-general",
      texto: "Inicio",
      icono: iconoDeOpcion("vista-general"),
      ruta: RUTA_DE_VISTA_GENERAL,
      actual: enInicio,
      cuenta: total,
      detalle: total > 0 ? TEXTOS_PENDIENTES.porHacer(total) : undefined,
    },
  ];
  const obrasReducidas: OpcionDeRiel[] = visibles.map((o) => {
    const clave = claveDeObra(o.carpeta, o.obra_id);
    const cuenta = porObra.get(clave) ?? 0;
    return {
      id: `obra-${clave}`,
      texto: o.obra,
      icono: iconoDeOpcion("resumen"),
      inicial: o.obra.trim().charAt(0).toLocaleUpperCase("es"),
      ruta: rutaDeObra(o.carpeta, o.obra_id, SECCION_DE_ENTRADA),
      actual: clave === claveAbierta,
      cuenta,
      detalle: cuenta > 0 ? TEXTOS_PENDIENTES.porHacer(cuenta) : undefined,
    };
  });
  const soloReducida: OpcionDeRiel[] = [
    ...(estado !== "sin_permiso" && puedeCrear
      ? [{ id: "nueva-obra", texto: "Nueva obra", icono: iconoDeOpcion("nueva-obra"), alPulsar: abrirNuevaObra }]
      : []),
    ...(estado !== "sin_permiso" ? obrasReducidas : []),
  ];
  const espaciosReducidos: OpcionDeRiel[] = espacios.map((e) => ({
    id: e.id,
    texto: e.titulo,
    icono: iconoDeOpcion(e.id),
    ruta: e.ruta,
    actual: espacioActivo === e.id,
  }));

  // «En cifras»: con una obra abierta, las de esa obra; sin ella, las de todas. Solo lo que la aplicación ya sabe: los
  // pendientes con su palabra (bloquea / aviso, las de la bandeja). El avance no va: pedirlo repetiría la lectura de la ficha
  // de la obra, que el marco ya hace una sola vez (Marco.test lo vigila). Nada se calcula aquí.
  const pendientesDelBloque =
    carga.estado !== "listo" ? [] : claveAbierta === null ? carga.pendientes : pendientesDe(claveAbierta);
  const filasDeCifras = cifrasDeLaObra(pendientesDelBloque);
  const cifras: CifrasDeRiel | undefined =
    obraAbierta === null && filasDeCifras.length === 0
      ? undefined
      : {
          titulo: "En cifras",
          filas: filasDeCifras,
          extra: (
            <>
              {obraAbierta !== null && carga.estado === "listo" && filasDeCifras.length === 0 && (
                <p className="silice-marco-lateral__avance">Sin pendientes en esta obra</p>
              )}
            </>
          ),
        };

  return (
    <RielLateral
      lugar={obraAbierta !== null ? "Obra abierta" : enInicio ? "Inicio" : (oferta.espacios.find((e) => e.id === espacioActivo)?.titulo ?? "Obras y espacios")}
      reducida={sidebarCollapsed}
      alAlternar={toggleSidebar}
      rotuloDeOpciones="Espacios de la empresa"
      opciones={opciones}
      soloReducida={soloReducida}
      grupoReducido={{ rotulo: "Costos y producción", opciones: espaciosReducidos }}
      cifras={cifras}
      carpeta={carpetaAbierta}
      fuera={
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
      }
    >
      <ZonaDeCostos espacios={espacios} espacioActivo={espacioActivo} idBase={base} />

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
    </RielLateral>
  );
}
