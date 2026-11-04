import { Button } from "@carbon/react";
import { useCallback, useContext, useEffect, useId, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { nombreDeEstado } from "../../comun/aprobacion";
import type { AprobacionesDeObra } from "../../comun/aprobacion";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { InformeAuditoria } from "../../comun/InformeAuditoria";
import { TablaDensa } from "../../comun/TablaDensa";
import { nombreDeResponsable } from "../../comun/responsable";
import { centesimasEsVe, fechaEsVe, formatoEsVe } from "../../indicadores/formatoEsVe";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import { useAplicacion } from "../../shell/contexto";
import { PanelDictamen } from "./PanelDictamen";
import { RastroDeAprobaciones } from "./RastroDeAprobaciones";
import { frase, informeDe, nombreDeCarpeta } from "./logica";
import type { DetalleDeEnvio, FilaDeEnvio, Resultado } from "./logica";
import "./aprobar.scss";

// Tarea 20: «Aprobar una versión» (diseño de montar un presupuesto §5.4; área Aprobaciones de Presupuestos y obras). Se llega
// con `?envio=` (la mesa, la Hoja, un enlace). Lee el envío en solo lectura (`GET /v1/aprobaciones/{id}`) y registra el
// dictamen (`POST .../dictamen`, en el panel). Sin `?envio=` busca el envío en aprobación de la obra elegida en esta carpeta
// (T19, punto 5) y, si no lo halla, lista los de la carpeta para elegir. Dentro de una obra, debajo va el «Rastro de la obra»
// (Tarea 6 del plan F4: se mudó aquí desde la pestaña «Trazabilidad» de la Hoja), para toda cuenta con `leer_proyecto`.
// Pasa de 250 líneas porque junta las dos maneras de llegar (con y sin `?envio=`), que comparten la cabecera y el dictamen.

function envioDeLaUrl(valor: string | null): number | null {
  if (valor === null || !/^\d+$/.test(valor)) return null;
  const n = Number(valor);
  return Number.isSafeInteger(n) && n > 0 ? n : null;
}

type Busqueda =
  | { estado: "buscando" }
  | { estado: "elegir"; deLaCarpeta: FilaDeEnvio[]; deOtras: number }
  | { estado: "fallo"; error: unknown };

export default function PaginaAprobar() {
  const [parametros, setParametros] = useSearchParams();
  const { proyecto, sesion } = useAplicacion();
  const enLaObra = useContext(ContextoDeLaObra) !== null;
  const envio = envioDeLaUrl(parametros.get("envio"));
  return (
    <div className="silice-aprobar silice-pagina">
      <h1 className="cds--type-heading-04">Aprobar una versión</h1>
      {envio === null ? (
        <BuscarEnvio alEncontrar={(id, reemplazar) => setParametros({ envio: String(id) }, { replace: reemplazar })} />
      ) : (
        <Envio key={envio} id={envio} />
      )}
      {enLaObra && proyecto !== null && sesion.acciones.includes("leer_proyecto") && <RastroDeAprobaciones proyecto={proyecto} />}
    </div>
  );
}

// --- sin `?envio=` ---------------------------------------------------------------------------------------------------

function BuscarEnvio({ alEncontrar }: { alEncontrar: (id: number, reemplazar: boolean) => void }) {
  const { alExpirar, caso, proyecto, sesion } = useAplicacion();
  const [busqueda, setBusqueda] = useState<Busqueda>({ estado: "buscando" });
  const carpeta = caso?.nombre ?? null;
  const puedeVerElRastro = sesion.acciones.includes("editar_hoja");
  // Quien llama cambia de identidad en cada vuelta de la ruta: la busqueda no debe repetirse por eso.
  const encontrar = useRef(alEncontrar);
  useEffect(() => {
    encontrar.current = alEncontrar;
  });

  useEffect(() => {
    let vigente = true;
    const deEstaCarpeta = (f: FilaDeEnvio) => f.estado === "en_aprobacion" && (carpeta === null || f.caso === carpeta);

    async function buscar() {
      let filas: FilaDeEnvio[] | null = null;
      let fallo: unknown = null;
      try {
        filas = await pedir<FilaDeEnvio[]>("/v1/aprobaciones/pendientes");
      } catch (e) {
        if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
        fallo = e;
      }
      if (!vigente) return;
      if (filas !== null) {
        const mia = proyecto === null ? undefined : filas.find((f) => deEstaCarpeta(f) && f.proyecto === proyecto);
        if (mia) return encontrar.current(mia.envio_id, true);
        const deLaCarpeta = filas.filter(deEstaCarpeta);
        setBusqueda({ estado: "elegir", deLaCarpeta, deOtras: filas.filter((f) => f.estado === "en_aprobacion").length - deLaCarpeta.length });
        return;
      }
      // Sin el indice (la cuenta no lo ve o falló): quien arma lo halla en el rastro de la obra elegida.
      if (puedeVerElRastro && proyecto !== null) {
        try {
          const rastro = await pedir<AprobacionesDeObra>(`/v1/aprobaciones?${new URLSearchParams({ proyecto }).toString()}`);
          if (!vigente) return;
          const cerrados = new Set(rastro.eventos.filter((e) => e.cierre_de !== null).map((e) => e.cierre_de));
          const abiertos = rastro.eventos.filter((e) => e.tipo === "envio" && !cerrados.has(e.id));
          const ultimo = abiertos[abiertos.length - 1];
          if (ultimo) return encontrar.current(ultimo.id, true);
        } catch (e) {
          if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
        }
      }
      if (!vigente) return;
      const sinPermiso = fallo instanceof ErrorDeApi && fallo.estado === 403;
      setBusqueda(sinPermiso ? { estado: "elegir", deLaCarpeta: [], deOtras: 0 } : { estado: "fallo", error: fallo });
    }

    void buscar();
    return () => {
      vigente = false;
    };
  }, [alExpirar, carpeta, proyecto, puedeVerElRastro]);

  if (busqueda.estado === "buscando") return <EsqueletoPagina etiqueta="Buscando los envíos por aprobar" />;
  if (busqueda.estado === "fallo") return <AvisoError error={busqueda.error} titulo="No se pudieron leer los envíos por aprobar" />;
  const { deLaCarpeta, deOtras } = busqueda;
  return (
    <>
      {deLaCarpeta.length === 0 && deOtras === 0 && <EstadoVacio titulo="No hay versiones esperando dictamen." />}
      {deLaCarpeta.length > 0 && (
        <ul className="silice-aprobar__lista" aria-label="Versiones que esperan dictamen en esta carpeta">
          {deLaCarpeta.map((f) => (
            <li key={f.envio_id} className="silice-aprobar__fila">
              <div>
                <p className="cds--type-heading-compact-01">{`${f.obra} · ${f.version}`}</p>
                <p className="cds--type-body-compact-01">
                  {`${centesimasEsVe(f.total)} ${f.moneda} · enviada por ${nombreDeResponsable(f.enviado_por)} el ${fechaEsVe(f.enviado_el)}`}
                </p>
              </div>
              <Button kind="tertiary" size="sm" onClick={() => alEncontrar(f.envio_id, false)}>
                Abrir el envío
              </Button>
            </li>
          ))}
        </ul>
      )}
      {deOtras > 0 && (
        <p className="silice-aprobar__nota cds--type-body-compact-01">
          {`Hay ${deOtras} ${deOtras === 1 ? "envío" : "envíos"} en otras carpetas: ${deOtras === 1 ? "ábralo" : "ábralos"} desde Pendientes.`}
        </p>
      )}
    </>
  );
}

// --- con `?envio=` ---------------------------------------------------------------------------------------------------

type Lectura = { estado: "leyendo" } | { estado: "listo"; datos: DetalleDeEnvio } | { estado: "fallo"; error: unknown };

function Envio({ id }: { id: number }) {
  const { alExpirar } = useAplicacion();
  const [lectura, setLectura] = useState<Lectura>({ estado: "leyendo" });
  const [intento, setIntento] = useState(0);
  const [aviso, setAviso] = useState("");

  useEffect(() => {
    let vigente = true;
    pedir<DetalleDeEnvio>(`/v1/aprobaciones/${id}`).then(
      (datos) => {
        if (vigente) setLectura({ estado: "listo", datos });
      },
      (error: unknown) => {
        if (!vigente) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setLectura({ estado: "fallo", error });
      },
    );
    return () => {
      vigente = false;
    };
  }, [id, intento, alExpirar]);

  const alRegistrar = useCallback(
    (resultado: Resultado) => {
      const version = lectura.estado === "listo" ? lectura.datos.version : "";
      setAviso(`Dictamen registrado: ${version} ${frase(resultado)}.`);
      setIntento((n) => n + 1); // se vuelve a leer: ya tiene dictamen y no se ofrece otro
    },
    [lectura],
  );

  if (lectura.estado === "leyendo") return <EsqueletoPagina etiqueta="Cargando el envío" />;
  if (lectura.estado === "fallo") return <AvisoError error={lectura.error} titulo="No se pudo leer el envío" />;
  const datos = lectura.datos;
  return (
    <>
      {/* Texto neutro, no un aviso verde: el color nunca dice solo que algo salió bien. */}
      {aviso !== "" && (
        <p className="cds--type-body-compact-01" role="status">
          {aviso}
        </p>
      )}
      <CabeceraDelEnvio datos={datos} />
      <Partidas datos={datos} />
      <InformeAuditoria informe={informeDe(datos)} />
      <PanelDictamen detalle={datos} alRegistrar={alRegistrar} />
    </>
  );
}

function CabeceraDelEnvio({ datos }: { datos: DetalleDeEnvio }) {
  const { caso } = useAplicacion();
  const titulo = useId();
  return (
    <section className="silice-aprobar__envio" aria-labelledby={titulo}>
      <h2 id={titulo} className="cds--type-heading-compact-02">{`${datos.obra} · ${datos.version}`}</h2>
      <dl className="silice-aprobar__datos">
        {caso !== null && (
          <div>
            <dt className="cds--type-label-01">Carpeta</dt>
            <dd className="cds--type-body-compact-01">{nombreDeCarpeta(caso.nombre)}</dd>
          </div>
        )}
        <div>
          <dt className="cds--type-label-01">Total</dt>
          <dd className="cds--type-heading-03 silice-aprobar__total">{`${centesimasEsVe(datos.total)} ${datos.moneda}`}</dd>
        </div>
        <div>
          <dt className="cds--type-label-01">Estado</dt>
          <dd className="cds--type-body-compact-01">{nombreDeEstado(datos.estado)}</dd>
        </div>
        <div>
          <dt className="cds--type-label-01">Enviada por</dt>
          <dd className="cds--type-body-compact-01">{`${nombreDeResponsable(datos.envio.por)}, el ${fechaEsVe(datos.envio.el)}`}</dd>
        </div>
      </dl>
      {datos.envio.nota.trim() !== "" && <p className="cds--type-body-compact-01">{`«${datos.envio.nota}»`}</p>}
      <p className="cds--type-body-compact-01">{datos.rastro.mensaje}</p>
    </section>
  );
}

function Partidas({ datos }: { datos: DetalleDeEnvio }) {
  return (
    <section className="silice-aprobar__partidas" aria-label="Partidas de la versión">
      <TablaDensa
        etiqueta={`Partidas de ${datos.version}`}
        columnas={[
          { clave: "codigo", titulo: "Código", ordenable: false },
          { clave: "descripcion", titulo: "Descripción", ordenable: false },
          { clave: "unidad", titulo: "Unidad", ordenable: false },
          { clave: "cantidad", titulo: "Cantidad", numerica: true, ordenable: false },
          { clave: "precio", titulo: "Precio unitario", numerica: true, ordenable: false },
          { clave: "total", titulo: "Total", numerica: true, ordenable: false },
        ]}
        filas={datos.partidas.map((p) => ({
          id: p.codigo,
          codigo: p.codigo,
          descripcion: p.descripcion,
          unidad: p.unidad,
          cantidad: formatoEsVe(p.cantidad),
          precio: p.pendiente || p.precio_unitario === null ? "Sin precio" : centesimasEsVe(p.precio_unitario),
          total: p.total === null ? "" : centesimasEsVe(p.total),
        }))}
        vacio={{ titulo: "Esta versión no tiene partidas." }}
      />
    </section>
  );
}
