import { Button, InlineNotification } from "@carbon/react";
import { CampoTexto } from "../../comun/CampoTexto";
import { useState } from "react";
import { Link } from "react-router";
import { AvisoError } from "../../comun/AvisoError";
import type { Guardado } from "./cliente";

export interface Props {
  // Las condiciones del rendimiento estan vacias (RF-33): el boton queda deshabilitado.
  sinCondiciones: boolean;
  // La API detecto la advertencia de rendimiento (RF-27): solo entonces se ofrece la justificacion (UC-06, 4a).
  requiereJustificacion: boolean;
  guardando: boolean;
  resultado: Guardado | null;
  error: unknown;
  alGuardar: (justificacion: string | null) => void;
}

export function Guardar({ sinCondiciones, requiereJustificacion, guardando, resultado, error, alGuardar }: Props) {
  const [justificacion, setJustificacion] = useState("");
  const guardar = () => alGuardar(requiereJustificacion ? justificacion.trim() || null : null);

  return (
    <section className="silice-componer__bloque" aria-labelledby="componer-guardar">
      <h2 id="componer-guardar" className="cds--type-heading-compact-02">
        Guardar
      </h2>
      {requiereJustificacion && (
        <CampoTexto
          id="componer-justificacion"
          labelText="Justificación de la advertencia"
          helperText="Opcional: el motivo con el que acepta el rendimiento pese a la advertencia. Se guarda junto al rendimiento que registre este guardado; la advertencia no impide guardar."
          value={justificacion}
          onChange={(e) => setJustificacion(e.target.value)}
        />
      )}
      {sinCondiciones && (
        <p className="silice-componer__nota cds--type-body-compact-01">
          Las condiciones del rendimiento son obligatorias para guardar: el botón de guardar permanece
          deshabilitado hasta que se declaren.
        </p>
      )}
      <div>
        <Button kind="primary" size="md" disabled={sinCondiciones || guardando} onClick={guardar}>
          Guardar composición
        </Button>
      </div>
      <AvisoError error={error} titulo="No se guardó la composición" />
      {resultado && (
        <>
          <InlineNotification
            kind="success"
            lowContrast
            hideCloseButton
            role="status"
            title="Guardado"
            subtitle={resultado.mensaje}
          />
          {resultado.avisos.map((a, i) => (
            <InlineNotification key={i} kind="info" lowContrast hideCloseButton role="status" title="Aviso" subtitle={a} />
          ))}
          <p className="cds--type-body-compact-01">
            Siguiente paso: <Link to="/elaborar">Elaborar un presupuesto</Link>
          </p>
        </>
      )}
    </section>
  );
}
