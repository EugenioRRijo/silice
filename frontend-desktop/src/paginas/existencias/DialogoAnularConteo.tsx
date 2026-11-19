import { Button } from "@carbon/react";
import { useId, useState } from "react";
import type { FormEvent, JSX } from "react";
import { pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { fechaEsVe } from "../../indicadores/formatoEsVe";
import { MarcoDeDialogo } from "../../shell/carpetas/MarcoDeDialogo";
import { reaccionar } from "./fallos";
import type { Reacciones } from "./fallos";
import { mostrarCantidad, rotuloUnidad } from "./formato";
import type { ConteoVigente, ExistenciaRespuesta, MovimientoRespuesta } from "./tipos";

// Un material con su ultimo conteo vigente (el unico que la API deja anular).
export type ConConteo = ExistenciaRespuesta & { ultimo_conteo: ConteoVigente };

interface Props {
  material: ConConteo;
  alCerrar: () => void;
  // La anulacion se guardo: la pestana vuelve a leer la existencia.
  alAnular: () => void;
  reacciones: Reacciones;
}

const ID_FORMULARIO = "silice-conteo-anular";

// «Anular un conteo físico» (tanda 2026-11-19), como «Anular un costo»: pide el motivo. Anular no borra: el conteo queda
// en el registro con un ajuste que lo compensa, y el pasado lo vuelve a cerrar el conteo anterior.
export function DialogoAnularConteo({ material, alCerrar, alAnular, reacciones }: Props): JSX.Element {
  const base = useId();
  const conteo = material.ultimo_conteo;
  const [motivo, setMotivo] = useState("");
  const [errorMotivo, setErrorMotivo] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    if (motivo.trim() === "") {
      setErrorMotivo("Escriba el motivo de la anulación.");
      return;
    }
    setErrorMotivo(null);
    setEnviando(true);
    try {
      await pedir<MovimientoRespuesta>(`/v1/produccion/conteos/${conteo.id}/anular`, {
        metodo: "POST",
        cuerpo: { motivo: motivo.trim() },
      });
      alAnular();
    } catch (razon) {
      setError(reaccionar(razon, reacciones));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <MarcoDeDialogo
      titulo="Anular un conteo físico"
      alCerrar={alCerrar}
      inicial={() => document.getElementById(`${base}-motivo`)}
      pie={
        <>
          <Button kind="secondary" onClick={alCerrar}>
            Cancelar
          </Button>
          <Button kind="danger" type="submit" form={ID_FORMULARIO} disabled={enviando}>
            Anular conteo
          </Button>
        </>
      }
    >
      <form id={ID_FORMULARIO} className="existencias-formulario" onSubmit={(e) => void enviar(e)} noValidate>
        <p className="existencias-nota cds--type-body-compact-01">
          Conteo físico de {material.nombre} del {fechaEsVe(conteo.fecha)}, con un ajuste de {mostrarCantidad(conteo.diferencia)}{" "}
          {rotuloUnidad(material.unidad_venta)}. Anular no lo borra: queda en el registro con su motivo, la existencia vuelve a
          la de antes del conteo y lo anterior a esa fecha queda abierto hasta el conteo previo.
        </p>
        <CampoTexto
          id={`${base}-motivo`}
          labelText="Motivo de la anulación"
          autoComplete="off"
          maxLength={300}
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          invalid={errorMotivo !== null}
          invalidText={errorMotivo ?? ""}
        />
        <AvisoError error={error} titulo="No se pudo anular el conteo" />
      </form>
    </MarcoDeDialogo>
  );
}
