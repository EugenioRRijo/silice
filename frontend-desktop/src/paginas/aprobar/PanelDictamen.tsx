import { Button, RadioButton, RadioButtonGroup } from "@carbon/react";
import { useId, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { nombreDeEstado } from "../../comun/aprobacion";
import { AreaTexto } from "../../comun/AreaTexto";
import { AvisoError } from "../../comun/AvisoError";
import { MarcoDeDialogo } from "../../shell/carpetas/MarcoDeDialogo";
import { useAplicacion } from "../../shell/contexto";
import { useFormularioSucio } from "../../shell/sucio";
import { AVISO_CADENA_ROTA, OPCIONES, SIN_ELEGIR, SIN_NOTAS, SOLO_SI_ROTA, frase, necesitaNotas } from "./logica";
import type { DetalleDeEnvio, Resultado } from "./logica";

const ID_NOTAS = "aprobar-notas";

interface Props {
  detalle: DetalleDeEnvio;
  // Se registro el dictamen: la pantalla vuelve a leer el envio y lo dice.
  alRegistrar: (resultado: Resultado) => void;
}

// El panel «Dictamen» (diseno de montar un presupuesto §5.4): quien revisa elige aprobada, aprobada con observaciones o
// devuelta, escribe las notas (obligatorias salvo al aprobar a secas), confirma y el dictamen queda en el rastro, sin
// poder cambiarse. No hay campos para editar la version: lo que se aprueba es solo lectura.
export function PanelDictamen({ detalle, alRegistrar }: Props) {
  const { alExpirar } = useAplicacion();
  const titulo = useId();
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [notas, setNotas] = useState("");
  const [falta, setFalta] = useState<"" | "dictamen" | "notas">("");
  const [confirmando, setConfirmando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<unknown>(null);

  // Las notas escritas son trabajo sin guardar de esta pantalla: salir de ella pregunta antes.
  useFormularioSucio("aprobar", notas.trim() !== "");

  const abierto = detalle.estado === "en_aprobacion";
  // Con la cadena de versiones rota solo se puede devolver: devolver no certifica nada, aprobar si.
  const cadenaRota = !detalle.cadena.integra;
  const opciones = cadenaRota ? OPCIONES.filter((o) => o.valor === SOLO_SI_ROTA) : OPCIONES;
  const elegido: Resultado | null = cadenaRota ? SOLO_SI_ROTA : resultado;

  function pedirConfirmacion() {
    setError(null);
    if (elegido === null) {
      setFalta("dictamen");
      document.getElementById(`${ID_NOTAS}-${opciones[0]!.valor}`)?.focus();
      return;
    }
    if (necesitaNotas(elegido) && notas.trim() === "") {
      setFalta("notas");
      document.getElementById(ID_NOTAS)?.focus();
      return;
    }
    setFalta("");
    setConfirmando(true);
  }

  async function registrar() {
    if (elegido === null || enviando) return;
    setEnviando(true);
    try {
      await pedir(`/v1/aprobaciones/${detalle.envio_id}/dictamen`, {
        metodo: "POST",
        cuerpo: { resultado: elegido, notas: notas.trim() },
      });
      setConfirmando(false);
      setEnviando(false);
      setNotas("");
      alRegistrar(elegido);
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      setConfirmando(false);
      setEnviando(false);
      setError(e); // lo escrito se conserva
    }
  }

  return (
    <section className="silice-aprobar__panel" aria-labelledby={titulo}>
      <h2 id={titulo} className="cds--type-heading-compact-02">
        Dictamen
      </h2>
      {detalle.estado === "retirada" ? (
        <p className="cds--type-body-compact-01">Este envío fue retirado: se envió otra versión de la obra.</p>
      ) : !abierto ? (
        <p className="cds--type-body-compact-01">{`Este envío ya tiene dictamen: ${nombreDeEstado(detalle.estado)}.`}</p>
      ) : (
        <>
          {cadenaRota && (
            <p className="cds--type-body-compact-01">{`${detalle.cadena.mensaje} ${AVISO_CADENA_ROTA}`}</p>
          )}
          {detalle.armo && (
            <p className="cds--type-body-compact-01">Usted armó esta versión: el dictamen quedará rotulado así.</p>
          )}
          <RadioButtonGroup
            legendText="Su dictamen"
            name="aprobar-dictamen"
            orientation="vertical"
            valueSelected={elegido ?? ""}
            invalid={falta === "dictamen"}
            invalidText={SIN_ELEGIR}
            onChange={(valor) => {
              setResultado(valor as Resultado);
              setFalta("");
            }}
          >
            {opciones.map((o) => (
              <RadioButton key={o.valor} id={`${ID_NOTAS}-${o.valor}`} labelText={o.texto} value={o.valor} />
            ))}
          </RadioButtonGroup>
          <AreaTexto
            id={ID_NOTAS}
            labelText="Notas (obligatorias para devolver o aprobar con observaciones)"
            rows={4}
            maxLength={2000}
            value={notas}
            invalid={falta === "notas"}
            invalidText={SIN_NOTAS}
            onChange={(e) => {
              setNotas(e.target.value);
              if (falta === "notas") setFalta("");
            }}
          />
          <div>
            <Button id="aprobar-registrar" kind="primary" size="md" onClick={pedirConfirmacion}>
              Registrar el dictamen…
            </Button>
          </div>
          <AvisoError error={error} titulo="No se registró el dictamen" />
        </>
      )}
      {confirmando && elegido !== null && (
        <MarcoDeDialogo
          titulo="Registrar el dictamen"
          alCerrar={() => {
            if (!enviando) setConfirmando(false);
          }}
          inicial={() => document.getElementById("aprobar-volver")}
          pie={
            <>
              <Button id="aprobar-volver" kind="secondary" size="lg" disabled={enviando} onClick={() => setConfirmando(false)}>
                Volver
              </Button>
              <Button kind="primary" size="lg" disabled={enviando} onClick={() => void registrar()}>
                Registrar el dictamen
              </Button>
            </>
          }
        >
          <p className="cds--type-body-compact-01">
            {`${detalle.version} de ${detalle.obra} quedará ${frase(elegido)}. El dictamen no se cambia después.`}
          </p>
        </MarcoDeDialogo>
      )}
    </section>
  );
}
