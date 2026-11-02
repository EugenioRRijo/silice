import { Button } from "@carbon/react";
import { useContext, useState } from "react";
import { nombreDeEstado } from "../../comun/aprobacion";
import { AvisoError } from "../../comun/AvisoError";
import { InlineNotification } from "../../comun/carbonEs";
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
import { avisoDeCambiosPendientes } from "../hoja/logicaVersiones";
import type { AlCrearVersion } from "../hoja/OperacionesDePrecios";
import { ContextoDeLaHoja, useHojaDeLaObra } from "../hoja/ProveedorDeLaHoja";
import { usePuedeEditarLaHoja } from "../hoja/puedeEditar";
import { textoDelBoton } from "../hoja/textos";
import { useEstadosDeAprobacion } from "../hoja/useAprobacionDeVersion";
import { ID_DEL_TITULO } from "../hoja/useGuardadoDeLaPagina";
import { EstadoDeLaCadena } from "./EstadoDeLaCadena";
import { RegistroDeCambios } from "./RegistroDeCambios";
import { RestaurarVersion } from "./RestaurarVersion";
import { filasDeVersiones, pasoDeVersiones } from "./logica";
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
      {proyecto === null || hoja === null ? <EstadoVacio titulo="Elija una obra" /> : <CuerpoDeVersiones />}
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

  if (versiones.estado === "cargando") return <EsqueletoPagina etiqueta="Cargando las versiones" />;
  if (versiones.estado === "error") return <AvisoError error={versiones.error} />;

  const abierta = estado.estado === "listo" ? estado.borrador.base.version : (codigo ?? null);
  const cambios = estado.estado === "listo" ? estado.borrador.resumen.cambios : 0;
  const filas = filasDeVersiones(versiones.datos, estados.estado === "listo" ? estados.datos : null, abierta);
  const paso = pasoDeVersiones({ cambios, puedeGuardar: puedeEditar, filas });
  const guardar = { texto: textoDelBoton("guardar", abierta === null), alPulsar: abrirGuardado, id: ID_GUARDAR };
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
          <InlineNotification
            kind="success"
            role="status"
            lowContrast
            title="Versión guardada"
            subtitle={hoja.exito.texto}
            onCloseButtonClick={hoja.quitarExito}
          />
        )}
        {paso !== null && <FranjaDelPaso tipo="siguiente" texto={paso.texto} accion={paso.accion === null ? undefined : guardar} />}
        {filas.length === 0 ? (
          <EstadoVacio titulo={T.sinVersiones} descripcion={puedeEditar ? T.sinVersionesDescripcion : undefined} />
        ) : (
          <>
            <EstadoDeLaCadena proyecto={proyecto} />
            {puedeRestaurar && cambios > 0 && <p className="cds--type-helper-text-01">{avisoDeCambiosPendientes("restaurar", cambios)}</p>}
            <TablaDeVersiones
              proyecto={proyecto}
              filas={filas}
              restaurar={puedeRestaurar && cambios === 0}
              alAbrir={abrir}
              alVerCambios={setEnPanel}
              alCrearVersion={alCrearVersion}
            />
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
  // Se ofrece «Restaurar…» en cada fila (el permiso y sin cambios sin guardar).
  restaurar: boolean;
  alAbrir: (version: string) => void;
  alVerCambios: (version: string) => void;
  alCrearVersion: AlCrearVersion;
}

// Las siete columnas del plan y las acciones de cada fila. La abierta lleva la palabra «abierta» (Foco 5): no solo un color.
function TablaDeVersiones({ proyecto, filas, restaurar, alAbrir, alVerCambios, alCrearVersion }: PropsDeLaTabla) {
  const C = T.columnas;
  const codigos = filas.map((f) => f.codigo);
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
            </span>
          ),
        },
        { clave: "fecha", titulo: C.fecha, ordenable: false },
        { clave: "motivo", titulo: C.motivo, ordenable: false },
        { clave: "origen", titulo: C.origen, ordenable: false },
        { clave: "cambios", titulo: C.cambios, numerica: true, ordenable: false },
        { clave: "estado", titulo: C.estado, ordenable: false },
        { clave: "vigente", titulo: C.vigente, ordenable: false },
        {
          clave: "acciones",
          titulo: C.acciones,
          ordenable: false,
          celda: (f) => (
            <span className="silice-versiones__acciones">
              <Button kind="ghost" size="sm" aria-label={T.abrirLa(f.codigo!)} onClick={() => alAbrir(f.codigo!)}>
                {T.abrir}
              </Button>
              <Button kind="ghost" size="sm" aria-label={T.verCambiosDe(f.codigo!)} onClick={() => alVerCambios(f.codigo!)}>
                {T.verCambios}
              </Button>
              {restaurar && <RestaurarVersion proyecto={proyecto} versiones={codigos} inicial={f.codigo!} alCrearVersion={alCrearVersion} />}
            </span>
          ),
        },
      ]}
      filas={filas.map((f) => ({
        id: `version-${f.codigo}`,
        codigo: f.codigo,
        fecha: fechaEsVe(f.fecha),
        motivo: f.motivo === "" ? T.elaborada : f.motivo,
        origen: f.origen,
        cambios: formatoEsVe(String(f.cambios)),
        estado: f.estado === null ? "" : nombreDeEstado(f.estado),
        vigente: f.vigente ? T.vigente : "",
        abierta: f.abierta ? "sí" : "",
        acciones: "",
      }))}
    />
  );
}
