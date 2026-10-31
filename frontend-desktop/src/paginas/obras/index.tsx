import { Button, SkeletonText } from "@carbon/react";
import { useId } from "react";
import type { ReactNode } from "react";
import { AvisoError } from "../../comun/AvisoError";
import { FranjaDelPaso } from "../../comun/FranjaDelPaso";
import { EtapaDeObra } from "../../marco/EtapaDeObra";
import { useObraAbierta } from "../../marco/obraAbierta";
import type { ObraAbierta } from "../../marco/obraAbierta";
import { usePendientes } from "../../marco/usePendientes";
import { useAplicacion } from "../../shell/contexto";
import { useNavegarSeguro } from "../../shell/navegarSeguro";
import { claveDeObra, destinoDeLaAccion, destinoDelPendiente } from "../pendientes/logica";
import { etiquetaAvance, pantallaVisible, pasoDeLaObra, textoTotal } from "./logica";
import "./obras.scss";
import { TEXTOS } from "./textos";

// El Resumen de la obra abierta (Tarea 2 del plan F4; especificación §2.3 y §8 ter): la franja del paso, las cifras de
// esta obra y sus pendientes. Reemplaza a la mesa de todas las obras, que ya vive en el árbol de la barra lateral, en la
// bandeja de Pendientes y, para las cifras de la carpeta, en Empresa (F5). No lee nada por su cuenta: la ficha viene de
// `useObraAbierta()` (una lectura de `/v1/obras/resumen` por obra) y los pendientes de `usePendientes()` (una del marco).
export default function PaginaObras() {
  const { ficha, carpeta, obraId } = useObraAbierta();
  return (
    <div className="silice-pagina silice-resumen">
      <h1 className="cds--type-heading-04">{TEXTOS.titulo}</h1>
      <Cuerpo ficha={ficha} carpeta={carpeta} obraId={obraId} />
      <Pendientes carpeta={carpeta} obraId={obraId} />
    </div>
  );
}

function Cuerpo({ ficha, carpeta, obraId }: Pick<ObraAbierta, "ficha" | "carpeta" | "obraId">) {
  const { sesion } = useAplicacion();
  const navegarSeguro = useNavegarSeguro();
  if (ficha.estado === "cargando") {
    return (
      <div role="status" aria-busy="true" aria-label={TEXTOS.cargando}>
        <SkeletonText paragraph lineCount={3} />
      </div>
    );
  }
  if (ficha.estado === "sin_dato") return <p className="cds--type-body-compact-01">{TEXTOS.sinDato}</p>;

  const { obra } = ficha;
  const paso = pasoDeLaObra(obra);
  // El botón solo sale si la cuenta puede usar la pantalla de destino: la API le negaría el paso de todos modos.
  const accion = paso?.accion && pantallaVisible(paso.accion.pagina, sesion.acciones, sesion.modo_entrega) ? paso.accion : null;
  const total = textoTotal(obra.total, obra.moneda);
  return (
    <>
      {paso && (
        <FranjaDelPaso
          tipo={paso.tipo}
          texto={paso.texto}
          accion={
            accion
              ? { texto: accion.texto, alPulsar: () => void navegarSeguro(destinoDeLaAccion(carpeta, obraId, accion.pagina)) }
              : undefined
          }
        />
      )}
      <div role="group" aria-label={TEXTOS.cifras}>
        <dl className="silice-resumen__cifras">
          <Cifra nombre={TEXTOS.total}>{total ?? <span className="silice-resumen__sin-dato">{TEXTOS.sinTotal}</span>}</Cifra>
          <Cifra nombre={TEXTOS.avance}>{etiquetaAvance(obra.avance_real, obra.avance_plan)}</Cifra>
          <Cifra nombre={TEXTOS.version}>
            {obra.version ?? <span className="silice-resumen__sin-dato">{TEXTOS.sinVersion}</span>}
          </Cifra>
          <Cifra nombre={TEXTOS.etapa}>
            <EtapaDeObra etapa={obra.etapa} texto={obra.etapa_texto} />
          </Cifra>
        </dl>
      </div>
    </>
  );
}

function Cifra({ nombre, children }: { nombre: string; children: ReactNode }) {
  return (
    <div className="silice-resumen__cifra">
      <dt className="cds--type-label-01">{nombre}</dt>
      <dd className="cds--type-body-compact-02">{children}</dd>
    </div>
  );
}

// Los pendientes de esta obra: los del marco filtrados por su clave (la carpeta cuenta, porque dos carpetas pueden
// tener el mismo número de obra). Cada uno lleva su botón al lugar donde se resuelve.
function Pendientes({ carpeta, obraId }: Pick<ObraAbierta, "carpeta" | "obraId">) {
  const idTitulo = useId();
  const carga = usePendientes();
  const navegarSeguro = useNavegarSeguro();
  const clave = claveDeObra(carpeta, obraId);
  const propios = carga.estado === "listo" ? carga.pendientes.filter((p) => claveDeObra(p.carpeta, p.obra_id) === clave) : [];
  return (
    <section aria-labelledby={idTitulo} className="silice-resumen__pendientes">
      <h2 id={idTitulo} className="cds--type-heading-compact-02">
        {TEXTOS.pendientes}
      </h2>
      {carga.estado === "cargando" && (
        <div role="status" aria-busy="true" aria-label={TEXTOS.cargandoPendientes}>
          <SkeletonText paragraph lineCount={2} />
        </div>
      )}
      {carga.estado === "error" && <AvisoError error={carga.mensaje} titulo={TEXTOS.errorPendientes} />}
      {carga.estado === "listo" && propios.length === 0 && <p className="cds--type-body-compact-01">{TEXTOS.sinPendientes}</p>}
      {propios.length > 0 && (
        <ul className="silice-resumen__lista">
          {propios.map((p) => (
            <li key={`${p.grupo}|${p.texto}`} className="silice-resumen__pendiente">
              <span className="cds--type-body-compact-01">{p.texto}</span>
              <Button kind="tertiary" size="sm" onClick={() => void navegarSeguro(destinoDelPendiente(p))}>
                {p.accion.texto}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
