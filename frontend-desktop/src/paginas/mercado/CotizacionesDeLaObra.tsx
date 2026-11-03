import { InlineNotification } from "../../comun/carbonEs";
import { useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Link, useInRouterContext } from "react-router";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { TablaDensa } from "../../comun/TablaDensa";
import { formatoEsVe, fechaEsVe } from "../../indicadores/formatoEsVe";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import { rutaDeObra } from "../../marco/secciones";
import { useAplicacion } from "../../shell/contexto";
import { ContextoDeDialogos } from "../hoja/ContextoDeDialogos";
import { rutaDePrecios, rutaDeVersiones } from "../hoja/logica";
import type { CeldaPrecio, PreciosRespuesta, VersionesRespuesta } from "../hoja/logica";
import { cotizadasDePrecios } from "../hoja/logicaVersiones";
import { useOfertas } from "../hoja/useOfertas";
import { useCarga } from "../inicio/useCarga";
import { OperacionesDePrecios } from "./OperacionesDePrecios";

// Por qué existe (Tarea 13 del plan F4; preguntas 4 y 8 del inventario): «Registrar / Retirar una cotización…» salieron de
// Presupuesto › Precios y viven aquí, en la pestaña «Cotizaciones de la obra» de Mercado (`index.tsx`, la única que la usa).
// Trabajan sobre la versión VIGENTE de la obra: cada una crea una versión nueva desde ella y se avisa con el enlace para
// abrirla en el Presupuesto. La tabla enseña las cotizaciones con el rastro de la conversión que ya decidió Eugenio (precio
// original, tasa del día exacto del precio, su fecha y su fuente): la interfaz no convierte, lo lee del servidor.
// Cotizar exige `editar_hoja`: quien solo revisa ve las cotizaciones sin ningún control que escriba.

const COLUMNAS = [
  { clave: "codigo", titulo: "Código" },
  { clave: "insumo", titulo: "Insumo" },
  { clave: "cotizacion", titulo: "Cotización" },
  { clave: "moneda_original", titulo: "Moneda original" },
  { clave: "precio_original", titulo: "Precio original", numerica: true, presentar: formatoEsVe },
  { clave: "tasa", titulo: "Tasa", numerica: true, presentar: formatoEsVe },
  { clave: "fecha_tasa", titulo: "Fecha de la tasa", presentar: fechaEsVe },
  { clave: "fuente_tasa", titulo: "Fuente de la tasa" },
];

// El texto de una celda; la tasa va con su valor exacto (puede tener más de dos decimales), como en Precios.
function textoDe(celda: CeldaPrecio | undefined, exacto: boolean): string {
  if (celda === null || celda === undefined) return "";
  if (typeof celda === "string") return celda;
  return exacto ? celda.exacto : celda.texto;
}

type AlCrear = (codigo: string, texto: string) => Promise<void>;

type Filas = PreciosRespuesta["filas"];

// Ronda 2 de la Tarea 13: cotizar crea una versión nueva desde la vigente GUARDADA. Si el Presupuesto de esta obra tiene un
// borrador con cambios sin guardar (los que el servidor conserva de esta ficha, los mismos que la Hoja ofrece retomar), esos
// cambios quedarían en un borrador de una versión vieja: no se ofrece cotizar y se dice por qué, como hacía la pestaña Precios
// (la clásica, P:1946). Mientras se leen los borradores no se ofrece nada.
function Operaciones({ proyecto, version, filas, alCrearVersion }: { proyecto: string; version: string; filas: Filas; alCrearVersion: AlCrear }) {
  const { alExpirar, nombreProyecto } = useAplicacion();
  const { ofertas } = useOfertas(proyecto, nombreProyecto ?? null, alExpirar);
  if (ofertas.estado !== "listo") return null;
  const cambios = ofertas.lista.reduce((suma, o) => suma + o.cambios, 0);
  return <OperacionesDePrecios proyecto={proyecto} version={version} filas={filas} cambios={cambios} alCrearVersion={alCrearVersion} />;
}

function ConPrecios({ proyecto, version, alCrearVersion }: { proyecto: string; version: string; alCrearVersion: AlCrear }) {
  const { alExpirar, sesion } = useAplicacion();
  const carga = useCarga<PreciosRespuesta>(rutaDePrecios(proyecto, version), alExpirar);
  if (carga.estado === "cargando") return <EsqueletoPagina etiqueta="Cargando las cotizaciones" />;
  if (carga.estado !== "listo") return <AvisoError error={carga.error} titulo="No se pudieron cargar las cotizaciones" />;
  const filas = carga.datos.filas;
  const cotizadas = new Set(cotizadasDePrecios(filas).map((i) => i.codigo));
  return (
    <>
      <TablaDensa
        etiqueta="Cotizaciones de la obra"
        columnas={COLUMNAS}
        filas={filas
          .filter((f) => cotizadas.has(textoDe(f["codigo"], false)))
          .map((f, i) => ({ id: `cotizacion-${i}`, ...Object.fromEntries(COLUMNAS.map((c) => [c.clave, textoDe(f[c.clave], c.clave === "tasa")])) }))}
        vacio={{ titulo: "Esta versión no tiene cotizaciones propias", descripcion: "Los precios vienen de la lista de la obra." }}
      />
      {sesion.acciones.includes("editar_hoja") && (
        <Operaciones proyecto={proyecto} version={version} filas={filas} alCrearVersion={alCrearVersion} />
      )}
    </>
  );
}

// Los diálogos de las operaciones se pintan en un hermano de la pantalla de Mercado (pestañas incluidas), que queda `inert`
// mientras haya uno abierto. La pantalla (`index.tsx`) envuelve todo en esto; sin diálogo abierto no cambia nada.
export function PantallaConDialogos({ children }: { children: ReactNode }) {
  const [anfitrion, setAnfitrion] = useState<HTMLElement | null>(null);
  const [abiertos, setAbiertos] = useState(0);
  const registrar = useCallback((delta: number) => setAbiertos((n) => n + delta), []);
  const valor = useMemo(() => ({ anfitrion, abiertos, registrar }), [anfitrion, abiertos, registrar]);
  return (
    <ContextoDeDialogos.Provider value={valor}>
      <div className="silice-hoja__anfitrion" inert={abiertos > 0}>
        {children}
      </div>
      <div ref={setAnfitrion} className="silice-hoja__anfitrion" />
    </ContextoDeDialogos.Provider>
  );
}

// Lee las versiones y, con la vigente, las cotizaciones. El padre lo desmonta (`key`) al crearse una versión: así se vuelve
// a leer todo y la vigente ya es la nueva.
function Cuerpo({ proyecto, alCrearVersion }: { proyecto: string; alCrearVersion: AlCrear }) {
  const { alExpirar, sesion } = useAplicacion();
  const versiones = useCarga<VersionesRespuesta>(rutaDeVersiones(proyecto), alExpirar);
  if (versiones.estado === "cargando") return <EsqueletoPagina etiqueta="Cargando las cotizaciones" />;
  if (versiones.estado !== "listo") return <AvisoError error={versiones.error} titulo="No se pudieron cargar las versiones" />;
  const vigente = versiones.datos.versiones.find((v) => v.vigente)?.codigo ?? null;
  if (vigente === null) {
    const hay = versiones.datos.versiones.length > 0;
    return (
      <EstadoVacio
        titulo={hay ? "Ninguna versión es la vigente todavía." : "Esta obra aún no tiene versiones guardadas."}
        descripcion="Guarde una versión del presupuesto para poder registrar cotizaciones."
      />
    );
  }
  return (
    <>
      <p className="cds--type-body-compact-01">
        Las cotizaciones valen solo para esta obra y se leen de la versión vigente ({vigente}).
        {sesion.acciones.includes("editar_hoja") && " Registrar o retirar una crea una versión nueva desde ella."}
      </p>
      <ConPrecios proyecto={proyecto} version={vigente} alCrearVersion={alCrearVersion} />
    </>
  );
}

export function CotizacionesDeLaObra() {
  const { proyecto } = useAplicacion();
  const obra = useContext(ContextoDeLaObra);
  const enRuta = useInRouterContext();
  const [creada, setCreada] = useState<{ codigo: string; texto: string } | null>(null);
  const [lectura, setLectura] = useState(0);
  if (proyecto === null) return <p className="cds--type-body-compact-01">Elija una obra para ver sus cotizaciones.</p>;
  const alCrearVersion: AlCrear = async (codigo, texto) => {
    setCreada({ codigo, texto });
    setLectura((n) => n + 1);
  };
  return (
    <div className="silice-mercado__cotizaciones">
      {creada !== null && (
        <div role="status">
          <InlineNotification kind="success" title="Versión nueva" subtitle={creada.texto} lowContrast hideCloseButton />
          {obra !== null && enRuta && (
            <Link className="cds--link" to={`${rutaDeObra(obra.carpeta, obra.obraId, "presupuesto")}?version=${encodeURIComponent(creada.codigo)}`}>
              Abrirla en el Presupuesto
            </Link>
          )}
        </div>
      )}
      <Cuerpo key={`${proyecto}-${lectura}`} proyecto={proyecto} alCrearVersion={alCrearVersion} />
    </div>
  );
}
