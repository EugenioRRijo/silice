import { Button, InlineNotification, Select, SelectItem } from "@carbon/react";
import { useState } from "react";
import { CampoTexto } from "../../comun/CampoTexto";
import { useAplicacion } from "../../shell/contexto";
import { DialogoDeOperacion } from "./DialogoDeOperacion";
import { usuarioDeSesion } from "./logicaGuardar";
import {
  RUTA_DE_CONVERTIR,
  avisoDeCambiosPendientes,
  cuerpoDeConvertir,
  monedasDestino,
  motivoParaNoConvertir,
  textoDeVersionCreada,
} from "./logicaVersiones";
import type { LadoDeLaTasa, VersionCreada } from "./logicaVersiones";
import type { AlCrearVersion } from "./OperacionesDePrecios";
import { useDialogoDeOperacion } from "./useDialogoDeOperacion";
import { useOperacion } from "./useOperacion";

const LARGO_DE_FUENTE = 300;

interface PropsDeFormulario {
  proyecto: string;
  version: string;
  monedaActual: string | null;
  anfitrion: HTMLElement;
  alCancelar: () => void;
  alCrearVersion: AlCrearVersion;
}

function FormularioDeConvertir({ proyecto, version, monedaActual, anfitrion, alCancelar, alCrearVersion }: PropsDeFormulario) {
  const { alExpirar, sesion } = useAplicacion();
  const destinos = monedasDestino(monedaActual);
  const [moneda, setMoneda] = useState(destinos[0] ?? "");
  const [lado, setLado] = useState<LadoDeLaTasa>("venta");
  const [fuente, setFuente] = useState("");
  const operacion = useOperacion({
    ruta: RUTA_DE_CONVERTIR,
    alExpirar,
    alCrear: (r: VersionCreada) =>
      alCrearVersion(r.codigo, textoDeVersionCreada(r, `Se guardó la versión ${r.codigo}, convertida a ${moneda}.`)),
  });
  return (
    <DialogoDeOperacion
      operacion="convertir"
      titulo="Convertir la moneda"
      descripcion="Cambiar la moneda (crea una versión convertida; la actual no cambia). Se usa la tasa del BCV de hoy."
      anfitrion={anfitrion}
      usuario={usuarioDeSesion(sesion)}
      motivo={motivoParaNoConvertir(fuente)}
      textoConfirmar="Convertir la versión"
      enviando={operacion.enviando}
      error={operacion.error}
      alConfirmar={() => void operacion.enviar(cuerpoDeConvertir(proyecto, version, moneda, lado, fuente))}
      alCancelar={alCancelar}
    >
      <Select id="hoja-convertir-moneda" labelText="Moneda destino" value={moneda} onChange={(e) => setMoneda(e.target.value)}>
        {destinos.map((m) => (
          <SelectItem key={m} value={m} text={m} />
        ))}
      </Select>
      <Select
        id="hoja-convertir-lado"
        labelText="Tasa del BCV"
        helperText="Por omisión, venta."
        value={lado}
        onChange={(e) => setLado(e.target.value === "compra" ? "compra" : "venta")}
      >
        <SelectItem value="venta" text="Venta" />
        <SelectItem value="compra" text="Compra" />
      </Select>
      <CampoTexto
        id="hoja-convertir-fuente"
        labelText="Por qué se cambia la moneda (fuente)"
        value={fuente}
        maxLength={LARGO_DE_FUENTE}
        onChange={(e) => setFuente(e.target.value)}
      />
    </DialogoDeOperacion>
  );
}

interface Props {
  proyecto: string;
  // La versión guardada que está abierta (null: borrador en blanco, no hay de qué convertir).
  version: string | null;
  monedaActual: string | null;
  // El servidor dice si hay versión abierta y si la cuenta puede convertir.
  puedeConvertir: boolean;
  cambios: number;
  alCrearVersion: AlCrearVersion;
}

// «Convertir la moneda» (S5) de la pestaña Parámetros. Crea una versión convertida desde la guardada (RF-64).
export function ConvertirMoneda({ proyecto, version, monedaActual, puedeConvertir, cambios, alCrearVersion }: Props) {
  const { abierto, anfitrion, abrir, cerrar, anclaDelBoton } = useDialogoDeOperacion();
  if (!puedeConvertir || version === null) return null;
  if (cambios > 0) {
    return (
      <InlineNotification
        kind="warning"
        role="status"
        lowContrast
        hideCloseButton
        title="Hay cambios sin guardar"
        subtitle={avisoDeCambiosPendientes("convertir", cambios)}
      />
    );
  }
  return (
    <section className="silice-hoja__seccion" aria-label="Moneda del proyecto">
      <div className="silice-hoja__acciones">
        <Button ref={anclaDelBoton} kind="tertiary" size="md" onClick={abrir}>
          Convertir la moneda…
        </Button>
      </div>
      {abierto && anfitrion !== null && (
        <FormularioDeConvertir
          proyecto={proyecto}
          version={version}
          monedaActual={monedaActual}
          anfitrion={anfitrion}
          alCancelar={() => cerrar(true)}
          alCrearVersion={async (codigo, texto) => {
            cerrar(false);
            await alCrearVersion(codigo, texto);
          }}
        />
      )}
    </section>
  );
}
