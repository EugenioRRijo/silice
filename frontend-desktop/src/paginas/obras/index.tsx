import { Button } from "@carbon/react";
import { useCallback, useState } from "react";
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
import { bloquesPedidos, pantallaVisible } from "./logica";
import type { PendientesRespuesta, ResumenObrasRespuesta } from "./logica";
import "./obras.scss";
import { TablaObras } from "./TablaObras";

const RUTA_RESUMEN = "/v1/obras/resumen";
const RUTA_PENDIENTES = "/v1/obras/pendientes";

// Inicio de «Presupuestos y obras»: la mesa de control (diseno de modulos §6 y §12.3, opcion B que eligio Eugenio). Cifras
// arriba, las obras con su siguiente paso y, a la derecha, los pendientes. Cada bloque se pide aparte y solo si la cuenta
// puede leerlo; un 403 lo oculta (nunca lo pinta vacio) y un fallo se dice en su bloque sin tumbar los demas. Quien no
// lee obras (el administrador) ve lo que puede hacer en el modulo.
export default function PaginaObras() {
  const { sesion, alExpirar, elegirObra, abrirNuevaObra, abrirCarpeta } = useAplicacion();
  const { acciones, modo_entrega: modoEntrega } = sesion;
  const bloques = bloquesPedidos(acciones);
  const resumen = useCarga<ResumenObrasRespuesta>(bloques.includes("obras") ? RUTA_RESUMEN : null, alExpirar);
  const pendientes = useCarga<PendientesRespuesta>(bloques.includes("pendientes") ? RUTA_PENDIENTES : null, alExpirar);
  const navegarSeguro = useNavegarSeguro();

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

  const puedeCrear = acciones.includes("editar_hoja") && abrirNuevaObra !== undefined;
  const sinObras = resumen.estado === "listo" && resumen.datos.obras.length === 0;
  const pedidos = bloques.filter((b) => b !== "accesos");
  // Si todo lo pedido resulto prohibido, la pagina no queda en blanco: quedan los accesos del modulo.
  const todoOculto = pedidos.every((b) => (b === "pendientes" ? pendientes : resumen).estado === "sin_permiso");
  const conPendientes = bloques.includes("pendientes") && pendientes.estado !== "sin_permiso";

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
      {pedidos.length > 0 && (
        <div className={conPendientes ? "silice-mesa__rejilla silice-mesa__rejilla--con-pendientes" : "silice-mesa__rejilla"}>
          <div className="silice-mesa__principal">
            <CifrasMesa carga={resumen} />
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
          <ColumnaPendientes carga={pendientes} puedeIr={puedeIr} alIr={(codigo, pagina) => void alIr(codigo, pagina)} />
        </div>
      )}
      {(bloques.includes("accesos") || todoOculto) && <AccesosDelModulo modulo="obras" titulo="Lo que puede hacer aquí" />}
    </div>
  );
}

interface PrimerosPasosProps {
  abrirNuevaObra: (() => void) | undefined;
  // Sin `cambiar_caso` no se ofrece la demostracion (abrirla es cambiar de carpeta).
  abrirCarpeta: ((nombre: string) => Promise<boolean>) | undefined;
  alExpirar: () => void;
}

// El vacio que ensena: crear la primera obra o estrenar la carpeta de demostracion (`POST /v1/casos/demostracion`, 201 si
// la crea y 200 si ya estaba) y abrirla por el armazon, que pregunta si hay trabajo sin guardar y avisa del cambio.
function PrimerosPasos({ abrirNuevaObra, abrirCarpeta, alExpirar }: PrimerosPasosProps) {
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function probarDemostracion() {
    if (!abrirCarpeta) return;
    setOcupado(true);
    setError(null);
    try {
      const demo = await pedir<CasoRespuesta>("/v1/casos/demostracion", { metodo: "POST" });
      await abrirCarpeta(demo.nombre);
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
