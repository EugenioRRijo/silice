import { Button, InlineNotification } from "@carbon/react";
import { useEffect, useRef } from "react";
import type { CarpetaRespuesta } from "../../api/tipos";
import { AvisoError } from "../../comun/AvisoError";
import { mensajeDeError } from "../../comun/errores";
import { nombreConFecha } from "../../shell/ListaDeLaCarpeta";

export type Desde = "maprex" | "convertir";

interface Props {
  carpeta: CarpetaRespuesta | null;
  // La lista que se acaba de crear desde este aviso: se dice una vez, con el foco, porque el boton pulsado desaparece.
  creada: CarpetaRespuesta["lista"];
  creando: boolean;
  error: unknown;
  alCrear: (desde: Desde) => void;
}

// Prueba en vivo 2026-10-25: la carpeta no tenia lista de precios y solo se supo al guardar, despues de llenar unos 40
// campos. Se dice arriba, al abrir, con el aviso de la carpeta (`GET /v1/carpeta`, T2) y sus dos salidas (diseno de
// montar, §5.1 y D-MP1): crear la lista para armar a partir de MaPreX o convertir la que tiene a la moneda de la carpeta.
// Sin respuesta de la API no se dice nada: guardar lo dira si hace falta.
export function AvisoSinLista({ carpeta, creada, creando, error, alCrear }: Props) {
  const hecho = useRef<HTMLDivElement>(null);
  const aviso = carpeta?.aviso ?? null;
  const mostrarHecho = aviso === null && creada !== null;
  // Crear respondio 409 porque la carpeta ya tenia lista (un aviso viejo, de antes de crearla en otra pestana): la
  // pagina relee la carpeta, el aviso se va y se dice por que, con el foco (el boton pulsado desaparecio).
  const yaTenia = aviso === null && creada === null && error !== null && error !== undefined;
  useEffect(() => {
    if (mostrarHecho || yaTenia) hecho.current?.focus();
  }, [mostrarHecho, yaTenia]);

  if (mostrarHecho) {
    return (
      <div ref={hecho} tabIndex={-1} className="silice-componer__aviso">
        <InlineNotification
          kind="success"
          lowContrast
          hideCloseButton
          role="status"
          title="Listo"
          subtitle={`Lista para armar creada: ${nombreConFecha(creada)}. Ya puede guardar la composición.`}
        />
      </div>
    );
  }
  if (yaTenia) {
    return (
      <div ref={hecho} tabIndex={-1} className="silice-componer__aviso">
        <InlineNotification
          kind="info"
          lowContrast
          hideCloseButton
          role="status"
          title="Sin cambios"
          subtitle={mensajeDeError(error)}
        />
      </div>
    );
  }
  if (aviso === null || !carpeta) return null;

  // Solo hay algo que convertir si la carpeta tiene una lista en otra moneda que la suya.
  const lista = carpeta.lista;
  const convertible = lista !== null && carpeta.moneda !== null && lista.moneda !== carpeta.moneda;
  return (
    <div className="silice-componer__aviso">
      <InlineNotification
        kind="warning"
        lowContrast
        hideCloseButton
        role="status"
        title="Sin lista de precios para armar"
        subtitle={`${aviso} Puede componer la partida y ver su desglose, pero no guardarla hasta tener esa lista.`}
      />
      {carpeta.moneda === "USD" && (
        <p className="silice-componer__nota cds--type-body-compact-01">
          Los precios de MaPreX están en Bs: se convertirán a USD con la tasa del BCV de los últimos 7 días, y la lista
          dirá esa tasa y su fecha.
        </p>
      )}
      {convertible && (
        <p className="silice-componer__nota cds--type-body-compact-01">
          {`Convertir pasa los precios de «${lista.nombre}» de ${lista.moneda} a ${carpeta.moneda} con la tasa del BCV de los últimos 7 días, en una lista nueva que dirá esa tasa y su fecha.`}
        </p>
      )}
      <div className="silice-componer__acciones">
        <Button kind="secondary" size="sm" disabled={creando} onClick={() => alCrear("maprex")}>
          Crear la lista a partir de MaPreX
        </Button>
        {convertible && (
          <Button kind="tertiary" size="sm" disabled={creando} onClick={() => alCrear("convertir")}>
            Convertir la lista que tiene
          </Button>
        )}
      </div>
      <AvisoError error={error} titulo="No se creó la lista para armar" />
    </div>
  );
}
