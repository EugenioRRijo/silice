import { Button } from "@carbon/react";
import { useCallback, useEffect, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import type { CasoRespuesta } from "../../api/tipos";
import { AvisoError } from "../../comun/AvisoError";
import { AccesosDelModulo } from "../../shell/AccesosDelModulo";
import { useAplicacion } from "../../shell/contexto";
import { useNavegarSeguro } from "../../shell/EnlaceSeguro";
import { rutaDe } from "../../shell/rutas";
import { confirmarSalida } from "../../shell/salida";
import { useCarga } from "../inicio/useCarga";
import { CifrasMesa } from "./CifrasMesa";
import { ColumnaPendientes } from "./ColumnaPendientes";
import { bloquesPedidos, columnaDeLaMesa, pantallaVisible } from "./logica";
import type { CifraPorAprobar, EnvioPorAprobar, PendientesRespuesta, ResumenObrasRespuesta } from "./logica";
import "./obras.scss";
import { TablaObras } from "./TablaObras";

const RUTA_RESUMEN = "/v1/obras/resumen";
const RUTA_PENDIENTES = "/v1/obras/pendientes";
// Tarea 19: la cifra «Por aprobar» y lo que espera dictamen en todas las carpetas (api/rutas/aprobaciones.py).
const RUTA_POR_APROBAR = "/v1/aprobaciones/resumen";
const RUTA_ENVIOS = "/v1/aprobaciones/pendientes";
const RUTA_ABRIR_ENVIO = "/v1/aprobaciones/abrir";

// Inicio de «Presupuestos y obras»: la mesa de control (diseno de modulos §6 y §12.3, opcion B que eligio Eugenio). Cifras
// arriba, las obras con su siguiente paso y, a la derecha, los pendientes. Cada bloque se pide aparte y solo si la cuenta
// puede leerlo; un 403 lo oculta (nunca lo pinta vacio) y un fallo se dice en su bloque sin tumbar los demas. Quien no
// lee obras (el administrador) ve lo que puede hacer en el modulo.
//
// La obra elegida en el armazon (`proyecto`) cambia al crear una con «Nueva obra» o «Cree su primera obra»: si la mesa no
// la conoce, se vuelve a montar y pide de nuevo el resumen y los pendientes (una sola vez por obra, para que una obra que
// el resumen no traiga no repita la lectura sin fin). Elegir una obra que la mesa ya muestra no vuelve a pedir nada.
export default function PaginaObras() {
  const [generacion, setGeneracion] = useState(0);
  const [recargadaPor, setRecargadaPor] = useState<string | null>(null);
  const alObraNueva = useCallback((codigo: string) => {
    setRecargadaPor(codigo);
    setGeneracion((g) => g + 1);
  }, []);
  return <Mesa key={generacion} recargadaPor={recargadaPor} alObraNueva={alObraNueva} />;
}

function Mesa({ recargadaPor, alObraNueva }: { recargadaPor: string | null; alObraNueva: (codigo: string) => void }) {
  const { sesion, proyecto, caso, alExpirar, elegirObra, abrirNuevaObra, abrirCarpeta } = useAplicacion();
  const { acciones, modo_entrega: modoEntrega } = sesion;
  const bloques = bloquesPedidos(acciones);
  const pideAprobar = bloques.includes("por_aprobar");
  const resumen = useCarga<ResumenObrasRespuesta>(bloques.includes("obras") ? RUTA_RESUMEN : null, alExpirar);
  const pendientes = useCarga<PendientesRespuesta>(bloques.includes("pendientes") ? RUTA_PENDIENTES : null, alExpirar);
  const porAprobar = useCarga<CifraPorAprobar>(pideAprobar ? RUTA_POR_APROBAR : null, alExpirar);
  const envios = useCarga<EnvioPorAprobar[]>(pideAprobar ? RUTA_ENVIOS : null, alExpirar);
  const casoActual = caso?.nombre ?? null;
  const columna = columnaDeLaMesa(pendientes, envios, casoActual);
  const [falloAlAbrir, setFalloAlAbrir] = useState<unknown>(null);
  const navegarSeguro = useNavegarSeguro();

  const desconocida =
    proyecto !== null &&
    proyecto !== recargadaPor &&
    resumen.estado === "listo" &&
    !resumen.datos.obras.some((o) => o.codigo === proyecto);
  useEffect(() => {
    if (desconocida && proyecto !== null) alObraNueva(proyecto);
  }, [desconocida, proyecto, alObraNueva]);

  const puedeIr = useCallback((pagina: string) => pantallaVisible(pagina, acciones, modoEntrega), [acciones, modoEntrega]);
  // Primero se pregunta (si hay trabajo sin guardar); con «Quedarme» no se elige obra ni se navega.
  const alIr = useCallback(
    async (codigo: string, pagina: string) => {
      if (!(await confirmarSalida("salir"))) return;
      elegirObra?.(codigo);
      await navegarSeguro(rutaDe({ id: pagina }));
    },
    [elegirObra, navegarSeguro],
  );

  // «Abrir» un envio por aprobar (Tarea 19): uno de la carpeta abierta va directo a la pantalla de aprobar; uno de otra
  // pasa por el armazon (`abrirCarpeta`): la confirmacion unica de cambiar de carpeta con los borradores de la Hoja
  // (`confirmarSalida("carpeta", borradores)`) ANTES de `POST /v1/aprobaciones/abrir`, que abre la carpeta del envio sin
  // `cambiar_caso`, y el aviso del cambio. Con «Quedarme» no se abre nada.
  const alAbrirEnvio = useCallback(
    async ({ caso: carpeta, envio_id }: { caso: string; envio_id: number }) => {
      const destino = `${rutaDe({ id: "aprobar" })}?envio=${envio_id}`;
      setFalloAlAbrir(null);
      if (carpeta === casoActual || abrirCarpeta === undefined) {
        await navegarSeguro(destino);
        return;
      }
      try {
        const abierta = await abrirCarpeta(carpeta, undefined, async () => {
          const r = await pedir<{ caso: string }>(RUTA_ABRIR_ENVIO, { metodo: "POST", cuerpo: { caso: carpeta, envio_id } });
          return { nombre: r.caso, ruta_relativa: "" };
        });
        if (abierta) await navegarSeguro(destino);
      } catch (e) {
        if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
        else setFalloAlAbrir(e);
      }
    },
    [casoActual, abrirCarpeta, navegarSeguro, alExpirar],
  );

  const puedeCrear = acciones.includes("editar_hoja") && abrirNuevaObra !== undefined;
  const sinObras = resumen.estado === "listo" && resumen.datos.obras.length === 0;
  const pedidos = bloques.filter((b) => b !== "accesos");
  // Si todo lo pedido resulto prohibido, la pagina no queda en blanco: quedan los accesos del modulo.
  const todoOculto = pedidos.every((b) => (b === "obras" || b === "cifras" ? resumen : columna.carga).estado === "sin_permiso");
  // Ninguna columna vacia: la de las obras solo existe si el resumen no se oculto, y las dos columnas solo con las dos.
  // La de pendientes junta los de las obras y los envios por aprobar (quien solo revisa ve solo estos).
  const conPrincipal = bloques.includes("obras") && resumen.estado !== "sin_permiso";
  const conPendientes = columna.carga.estado !== "sin_permiso";

  return (
    <div className="silice-pagina silice-mesa">
      <div className="silice-mesa__cabecera">
        <h1 className="cds--type-heading-04">Inicio de presupuestos y obras</h1>
        {puedeCrear && !sinObras && (
          <Button kind="primary" size="md" onClick={() => abrirNuevaObra?.()}>
            Nueva obra
          </Button>
        )}
      </div>
      {(conPrincipal || conPendientes) && (
        <div
          className={
            conPrincipal && conPendientes ? "silice-mesa__rejilla silice-mesa__rejilla--con-pendientes" : "silice-mesa__rejilla"
          }
        >
          {conPrincipal && (
            <div className="silice-mesa__principal">
              <CifrasMesa carga={resumen} porAprobar={porAprobar} />
              <TablaObras
                carga={resumen}
                puedeIr={puedeIr}
                alIr={(codigo, pagina) => void alIr(codigo, pagina)}
                vacio={{
                  descripcion: puedeCrear
                    ? "Cree la primera con su nombre y su cliente, o pruebe Sílice con una obra de ejemplo."
                    : "Cuando quien arma los presupuestos cree una obra, la verá aquí con su avance.",
                  acciones: puedeCrear ? (
                    <PrimerosPasos
                      abrirNuevaObra={abrirNuevaObra}
                      abrirCarpeta={acciones.includes("cambiar_caso") ? abrirCarpeta : undefined}
                      alExpirar={alExpirar}
                    />
                  ) : null,
                }}
              />
            </div>
          )}
          <ColumnaPendientes
            carga={columna.carga}
            puedeIr={puedeIr}
            alIr={(codigo, pagina) => void alIr(codigo, pagina)}
            alAbrirEnvio={(envio) => void alAbrirEnvio(envio)}
            avisos={
              <>
                <AvisoError error={columna.falloEnvios} titulo="No se pudieron leer los envíos de otras carpetas" />
                <AvisoError error={falloAlAbrir} titulo="No se pudo abrir el envío" />
              </>
            }
          />
        </div>
      )}
      {(bloques.includes("accesos") || todoOculto) && <AccesosDelModulo modulo="obras" titulo="Lo que puede hacer aquí" />}
    </div>
  );
}

// El nombre de la carpeta de demostracion; el que se abre es el que devuelve la API al estrenarla.
const CARPETA_DEMOSTRACION = "demostracion.db";

interface PrimerosPasosProps {
  abrirNuevaObra: (() => void) | undefined;
  // Sin `cambiar_caso` no se ofrece la demostracion (abrirla es cambiar de carpeta).
  abrirCarpeta: ((nombre: string, preparar?: () => Promise<string>) => Promise<boolean>) | undefined;
  alExpirar: () => void;
}

// El vacio que ensena: crear la primera obra o estrenar la carpeta de demostracion (`POST /v1/casos/demostracion`, 201 si
// la crea y 200 si ya estaba) y abrirla por el armazon, que pregunta si hay trabajo sin guardar y avisa del cambio.
function PrimerosPasos({ abrirNuevaObra, abrirCarpeta, alExpirar }: PrimerosPasosProps) {
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState<unknown>(null);

  // La pregunta del armazon va antes de estrenarla: `preparar` (el POST) corre solo si la persona acepta salir.
  async function probarDemostracion() {
    if (!abrirCarpeta) return;
    setError(null);
    try {
      await abrirCarpeta(CARPETA_DEMOSTRACION, async () => {
        setOcupado(true);
        const demo = await pedir<CasoRespuesta>("/v1/casos/demostracion", { metodo: "POST" });
        return demo.nombre;
      });
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      else setError(e);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <>
      <div className="silice-mesa__primeros">
        <Button kind="primary" size="md" onClick={() => abrirNuevaObra?.()}>
          Cree su primera obra
        </Button>
        {abrirCarpeta && (
          <Button kind="tertiary" size="md" disabled={ocupado} onClick={() => void probarDemostracion()}>
            Probar con datos de demostración
          </Button>
        )}
      </div>
      {ocupado && (
        <p className="silice-mesa__nota cds--type-body-compact-01" role="status">
          Preparando la demostración… La primera vez tarda hasta dos minutos.
        </p>
      )}
      <AvisoError error={error} titulo="No se pudo abrir la demostración" />
    </>
  );
}
