import { Button } from "@carbon/react";
import { useId, useState } from "react";
import type { FormEvent, JSX } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { anularCosto } from "../../api/costos";
import type { CostoRespuesta } from "../../api/costos";
import { AvisoError } from "../../comun/AvisoError";
import { CampoTexto } from "../../comun/CampoTexto";
import { MarcoDeDialogo } from "../../shell/carpetas/MarcoDeDialogo";
import { CENTROS, CONCEPTOS, mensajeDeCostos, mostrarMonto, rotulo } from "./logica";

interface Props {
  costo: CostoRespuesta;
  alCerrar: () => void;
  // La anulación se guardó: la pantalla vuelve a leer la lista (hasta entonces la fila sigue ahí).
  alAnular: () => void;
  alExpirar: () => void;
}

const ID_FORMULARIO = "silice-costo-anular";

// «Anular un costo»: pide el motivo. Anular no borra: el costo queda en el registro, marcado, con su motivo.
export function DialogoAnular({ costo, alCerrar, alAnular, alExpirar }: Props): JSX.Element {
  const base = useId();
  const [motivo, setMotivo] = useState("");
  const [errorMotivo, setErrorMotivo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
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
      await anularCosto(costo.id, motivo.trim());
      alAnular();
    } catch (razon) {
      if (razon instanceof ErrorDeApi && razon.estado === 401) alExpirar();
      else setError(mensajeDeCostos(razon));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <MarcoDeDialogo
      titulo="Anular un costo"
      alCerrar={alCerrar}
      inicial={() => document.getElementById(`${base}-motivo`)}
      pie={
        <>
          <Button kind="secondary" onClick={alCerrar}>
            Cancelar
          </Button>
          <Button kind="danger" type="submit" form={ID_FORMULARIO} disabled={enviando}>
            Anular costo
          </Button>
        </>
      }
    >
      <form id={ID_FORMULARIO} className="costos-formulario" onSubmit={(e) => void enviar(e)} noValidate>
        <p className="costos-nota cds--type-body-compact-01">
          {rotulo(CONCEPTOS, costo.concepto)} de {rotulo(CENTROS, costo.centro).toLowerCase()} por {mostrarMonto(costo.monto)}{" "}
          {costo.moneda} ({costo.fuente}). Anular no lo borra: queda en el registro con su motivo y deja de sumar.
        </p>
        <CampoTexto
          id={`${base}-motivo`}
          labelText="Motivo de la anulación"
          autoComplete="off"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          invalid={errorMotivo !== null}
          invalidText={errorMotivo ?? ""}
        />
        <AvisoError error={error} titulo="No se pudo anular el costo" />
      </form>
    </MarcoDeDialogo>
  );
}
