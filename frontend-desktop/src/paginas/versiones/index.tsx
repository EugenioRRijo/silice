import { Button, Select, SelectItem } from "@carbon/react";
import { useContext, useState } from "react";
import { nombreDeEstado } from "../../comun/aprobacion";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { FranjaDelPaso } from "../../comun/FranjaDelPaso";
import { PanelLateral } from "../../comun/PanelLateral";
import { TablaDensa } from "../../comun/TablaDensa";
import { fechaEsVe, formatoEsVe } from "../../indicadores/formatoEsVe";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import { rutaDeObra } from "../../marco/secciones";
import { useAplicacion } from "../../shell/contexto";
import { useNavegarSeguro } from "../../shell/navegarSeguro";
import { esSoloDesglose } from "../hoja/logicaGuardar";
import { AvisoDeGuardado } from "../../comun/AvisoDeGuardado";
import { avisoDeCambiosPendientes } from "../hoja/logicaVersiones";
import type { AlCrearVersion } from "../hoja/logicaVersiones";
import { ContextoDeLaHoja, useHojaDeLaObra } from "../hoja/ProveedorDeLaHoja";
import { usePuedeEditarLaHoja } from "../hoja/puedeEditar";
import { textoDelBoton } from "../hoja/textos";
import { useEstadosDeAprobacion } from "../hoja/useAprobacionDeVersion";
import { ID_DEL_TITULO } from "../hoja/useGuardadoDeLaPagina";
import { EnlaceDePersona } from "../../comun/EnlaceDePersona";
import { EstadoDeLaCadena } from "./EstadoDeLaCadena";
import { RegistroDeCambios } from "./RegistroDeCambios";
import { RestaurarVersion } from "./RestaurarVersion";
import {
  extraerPersona,
  filasDeVersiones,
  filtrarVersionesPorPersona,
  listarPersonasDeVersiones,
  motivoDeVersion,
  pasoDeVersiones,
  textoDeConteoDeVersiones,
} from "./logica";
import type { FilaDeVersion } from "./logica";
import { TEXTOS_DE_VERSIONES as T } from "./textos";
import "./versiones.scss";

// Por qué existe (Tarea 6 del plan F4): la sección Versiones de la obra. Junta lo que estaba repartido en la Hoja: el
// selector «Versión» (baja 9: aquí cada versión se abre con «Abrir», que lleva al Presupuesto con `?version=`) y la pestaña
// «Trazabilidad» (baja 24: la tabla de las versiones, la cadena de sellos encima, el registro de cambios de cada una en el
// panel lateral y «Restaurar…»). Trabaja sobre el borrador que comparte `ProveedorDeLaHoja` con Presupuesto y Archivos y
// planos, así que pasar de una a otra no lo cierra; su franja guarda los cambios de ese borrador. Lo que escribe (guardar,
// restaurar) se pinta solo con permiso: quien revisa ve la tabla, abre y mira los cambios.

const ID_GUARDAR = "hoja-guardar-version"; // a él vuelve el foco al cancelar «Guardar versión» (useGuardadoDeLaPagina)

export default function PaginaVersiones() {
  const { proyecto } = useAplicacion();
  const hoja = useContext(ContextoDeLaHoja);
  return (
    <section className="silice-pagina silice-versiones">
      <h1 id={ID_DEL_TITULO} tabIndex={-1} className="cds--type-heading-04">
        {T.titulo}
      </h1>
      {/* Fuera de una obra (una dirección vieja) no hay borrador que compartir. */}
      {proyecto === null || hoja === null ? <EstadoVacio titulo="Elija una obra" descripcion="Abra una obra en «Obras» de la barra lateral, o búsquela con Ctrl+K." /> : <CuerpoDeVersiones />}
    </section>
  );
}

function CuerpoDeVersiones() {
  const hoja = useHojaDeLaObra();
  const { proyecto, versiones, codigo, estado, puedeEditar, pedirVersion, abrirGuardado, alCrearVersion, refrescar } = hoja;
  // Restaurar crea una versión desde la GUARDADA: su regla es solo el permiso (decisión 16 de la Tarea 2b, Eugenio).
  const puedeRestaurar = usePuedeEditarLaHoja(null);
  const estados = useEstadosDeAprobacion(proyecto);
  const obra = useContext(ContextoDeLaObra);
  const navegar = useNavegarSeguro();
  const [enPanel, setEnPanel] = useState<string | null>(null);
  const [refresco, setRefresco] = useState(0);
  const [persona, setPersona] = useState("");
  // El nombre de quien se eligió: si sus versiones desaparecen (una restauración), el vacío lo sigue nombrando.
  const [nombreElegido, setNombreElegido] = useState("");
  const alCrearYRefrescar: AlCrearVersion = async (...args) => {
    await alCrearVersion(...args);
    estados.recargar();
    setRefresco((n) => n + 1);
  };

  if (versiones.estado === "cargando") return <EsqueletoPagina etiqueta="Cargando las versiones" />;
  if (versiones.estado === "error") return <AvisoError error={versiones.error} />;

  const abierta = estado.estado === "listo" ? estado.borrador.base.version : (codigo ?? null);
  const cambios = estado.estado === "listo" ? estado.borrador.resumen.cambios : 0;
  const filas = filasDeVersiones(versiones.datos, estados.estado === "listo" ? estados.datos : null, abierta);
  const personas = listarPersonasDeVersiones(filas);
  const visibles = filtrarVersionesPorPersona(filas, persona);
  const personaElegida = personas.find((p) => p.clave === persona)?.etiqueta ?? nombreElegido;
  const paso = pasoDeVersiones({ cambios, puedeGuardar: puedeEditar, filas });
  // Anexo A.6: el mismo rótulo que la franja del Presupuesto; lo decide `esSoloDesglose`, como el diálogo.
  const desgloses = estado.estado === "listo" ? (estado.borrador.resumen.desgloses ?? 0) : 0;
  const guardar = { texto: textoDelBoton("guardar", abierta === null, esSoloDesglose(abierta === null, cambios, desgloses)), alPulsar: abrirGuardado, id: ID_GUARDAR };
  // «Abrir» lleva al Presupuesto de la obra con la versión pedida; el proveedor la abre (con cambios, pregunta antes).
  const abrir = (version: string) => {
    if (obra === null) return pedirVersion(version);
    void navegar(`${rutaDeObra(obra.carpeta, obra.obraId, "presupuesto")}?${new URLSearchParams({ version }).toString()}`);
  };

  return (
    // Con un diálogo de la Hoja abierto (guardar, restaurar) la sección entera, panel incluido, queda inerte.
    <div className="silice-con-panel" inert={hoja.inerte}>
      <div className="silice-versiones__contenido">
        {hoja.exito !== null && hoja.exito.proyecto === proyecto && (
          <AvisoDeGuardado exito={hoja.exito} alCerrar={hoja.quitarExito} />
        )}
        {paso !== null && <FranjaDelPaso tipo="siguiente" texto={paso.texto} accion={paso.accion === null ? undefined : guardar} />}
        {filas.length === 0 ? (
          <EstadoVacio titulo={T.sinVersiones} descripcion={puedeEditar ? T.sinVersionesDescripcion : undefined} />
        ) : (
          <>
            <EstadoDeLaCadena key={`${proyecto}-${refresco}`} proyecto={proyecto} />
            {puedeRestaurar && cambios > 0 && <p className="cds--type-helper-text-01">{avisoDeCambiosPendientes("restaurar", cambios)}</p>}
            <div className="silice-versiones__barra">
              <div className="silice-versiones__filtro">
                <Select
                  id="versiones-persona"
                  size="sm"
                  labelText={T.filtroPersona}
                  value={persona}
                  onChange={(e) => {
                    setPersona(e.target.value);
                    setNombreElegido(personas.find((p) => p.clave === e.target.value)?.etiqueta ?? "");
                  }}
                >
                  <SelectItem value="" text={T.todasLasPersonas} />
                  {personas.map((p) => (
                    <SelectItem key={p.clave} value={p.clave} text={p.etiqueta} />
                  ))}
                </Select>
              </div>
              <p className="cds--type-label-01 silice-versiones__cuenta" role="status">
                {textoDeConteoDeVersiones(visibles.length, filas.length)}
              </p>
            </div>
            {visibles.length === 0 ? (
              <EstadoVacio titulo={T.sinCoincidencias} descripcion={T.sinCoincidenciasDescripcion(personaElegida)}>
                <Button kind="tertiary" size="sm" onClick={() => setPersona("")}>
                  {T.quitarFiltro}
                </Button>
              </EstadoVacio>
            ) : (
              <TablaDeVersiones
                proyecto={proyecto}
                filas={visibles}
                todosLosCodigos={filas.map((f) => f.codigo)}
                restaurar={puedeRestaurar && cambios === 0}
                alAbrir={abrir}
                alVerCambios={setEnPanel}
                alCrearVersion={alCrearYRefrescar}
              />
            )}
            {estados.estado === "fallo" && <p className="cds--type-helper-text-01">{T.sinEstados}</p>}
          </>
        )}
      </div>
      <PanelLateral
        titulo={enPanel === null ? "" : T.registro(enPanel)}
        abierto={enPanel !== null}
        alCerrar={() => setEnPanel(null)}
        ancho="ancho"
      >
        {enPanel !== null && (
          <RegistroDeCambios key={enPanel} proyecto={proyecto} version={enPanel} alAusente={() => void refrescar()} />
        )}
      </PanelLateral>
    </div>
  );
}

interface PropsDeLaTabla {
  proyecto: string;
  filas: FilaDeVersion[];
  todosLosCodigos: string[];
  // Se ofrece «Restaurar…» en cada fila (el permiso y sin cambios sin guardar).
  restaurar: boolean;
  alAbrir: (version: string) => void;
  alVerCambios: (version: string) => void;
  alCrearVersion: AlCrearVersion;
}

// Las siete columnas del plan y las acciones de cada fila. La abierta lleva la palabra «abierta» (Foco 5) y la descartada la
// palabra «descartada»: no solo un color. La descartada no tiene «Abrir» (salvo que todas lo estén, `seAbre`), pero sí «Ver
// cambios» y, con permiso, «Restaurar…»; el diálogo de restaurar ofrece todo el historial, descartadas incluidas.
function TablaDeVersiones({ proyecto, filas, todosLosCodigos, restaurar, alAbrir, alVerCambios, alCrearVersion }: PropsDeLaTabla) {
  const C = T.columnas;
  return (
    <TablaDensa
      etiqueta={T.tabla}
      columnas={[
        {
          clave: "codigo",
          titulo: C.version,
          ordenable: false,
          celda: (f) => (
            <span className="silice-versiones__codigo">
              {f.codigo}
              {f["abierta"] === "sí" && <span className="silice-versiones__abierta">{` (${T.abierta})`}</span>}
              {f["descartada"] === "sí" && <span className="silice-versiones__descartada">{` (${T.descartada})`}</span>}
            </span>
          ),
        },
        { clave: "fecha", titulo: C.fecha, ordenable: false },
        {
          clave: "motivo",
          titulo: C.motivo,
          ordenable: false,
          celda: (f) => {
            const autor = extraerPersona(f["responsable"], f["usuario"]);
            if (autor === null) return f["motivo"];
            return (
              <span>
                {f["motivo"]}
                <span className="silice-versiones__por">
                  {" · por "}
                  <EnlaceDePersona dato={f["responsable"]} usuarioExplicito={f["usuario"]} />
                </span>
              </span>
            );
          },
        },
        { clave: "origen", titulo: C.origen, ordenable: false },
        { clave: "cambios", titulo: C.cambios, numerica: true, ordenable: false },
        {
          clave: "estado",
          titulo: C.estado,
          ordenable: false,
          celda: (f) => {
            if (f["estado"] === "") return "";
            const quien = extraerPersona(f["por"]);
            if (quien === null) return f["estado"];
            return (
              <span>
                {f["estado"]}
                <span className="silice-versiones__por">
                  {" por "}
                  <EnlaceDePersona dato={f["por"]} />
                </span>
              </span>
            );
          },
        },
        { clave: "vigente", titulo: C.vigente, ordenable: false },
        {
          clave: "acciones",
          titulo: C.acciones,
          ordenable: false,
          celda: (f) => (
            <span className="silice-versiones__acciones">
              {f["seAbre"] === "sí" && (
                <Button kind="ghost" size="sm" aria-label={T.abrirLa(f.codigo!)} onClick={() => alAbrir(f.codigo!)}>
                  {T.abrir}
                </Button>
              )}
              <Button kind="ghost" size="sm" aria-label={T.verCambiosDe(f.codigo!)} onClick={() => alVerCambios(f.codigo!)}>
                {T.verCambios}
              </Button>
              {restaurar && <RestaurarVersion proyecto={proyecto} versiones={todosLosCodigos} inicial={f.codigo!} alCrearVersion={alCrearVersion} />}
            </span>
          ),
        },
      ]}
      filas={filas.map((f) => ({
        id: `version-${f.codigo}`,
        codigo: f.codigo,
        fecha: fechaEsVe(f.fecha),
        motivo: motivoDeVersion(f),
        origen: f.origen,
        cambios: formatoEsVe(String(f.cambios)),
        estado: f.estado === null ? "" : nombreDeEstado(f.estado),
        por: f.por ?? "",
        responsable: f.responsable ?? "",
        usuario: f.usuario ?? "",
        vigente: f.vigente ? T.vigente : "",
        abierta: f.abierta ? "sí" : "",
        descartada: f.descartada ? "sí" : "",
        seAbre: f.seAbre ? "sí" : "",
        acciones: "",
      }))}
    />
  );
}
