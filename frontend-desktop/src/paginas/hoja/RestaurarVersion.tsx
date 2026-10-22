import { Button, InlineNotification, Select, SelectItem } from "@carbon/react";
import { useState } from "react";
import { CampoTexto } from "../../comun/CampoTexto";
import { useAplicacion } from "../../shell/contexto";
import { DialogoDeOperacion } from "./DialogoDeOperacion";
import { usuarioDeSesion } from "./logicaGuardar";
import {
  RUTA_DE_RESTAURAR,
  avisoDeCambiosPendientes,
  cuerpoDeRestaurar,
  motivoParaNoRestaurar,
  textoDeVersionCreada,
} from "./logicaVersiones";
import type { VersionCreada } from "./logicaVersiones";
import type { AlCrearVersion } from "./OperacionesDePrecios";
import { useDialogoDeOperacion } from "./useDialogoDeOperacion";
import { useOperacion } from "./useOperacion";

const LARGO_DE_FUENTE = 300;

interface PropsDeFormulario {
  proyecto: string;
  versiones: string[];
  anfitrion: HTMLElement;
  alCancelar: () => void;
  alCrearVersion: AlCrearVersion;
}

function FormularioDeRestaurar({ proyecto, versiones, anfitrion, alCancelar, alCrearVersion }: PropsDeFormulario) {
  const { alExpirar, sesion } = useAplicacion();
  const [elegida, setElegida] = useState(versiones[0] ?? "");
  const [fuente, setFuente] = useState("");
  const operacion = useOperacion({
    ruta: RUTA_DE_RESTAURAR,
    alExpirar,
    alCrear: (r: VersionCreada) =>
      alCrearVersion(r.codigo, textoDeVersionCreada(r, `La versión ${elegida} se restauró como la versión ${r.codigo} (la vigente).`)),
  });
  return (
    <DialogoDeOperacion
      operacion="restaurar"
      titulo="Restaurar una versión"
      descripcion="Crea una versión nueva, copia de la elegida; nada se borra."
      anfitrion={anfitrion}
      usuario={usuarioDeSesion(sesion)}
      motivo={motivoParaNoRestaurar(fuente)}
      textoConfirmar="Restaurar"
      enviando={operacion.enviando}
      error={operacion.error}
      alConfirmar={() => void operacion.enviar(cuerpoDeRestaurar(proyecto, elegida, fuente))}
      alCancelar={alCancelar}
    >
      <Select id="hoja-restaurar-version" labelText="Versión a restaurar" value={elegida} onChange={(e) => setElegida(e.target.value)}>
        {versiones.map((v) => (
          <SelectItem key={v} value={v} text={v} />
        ))}
      </Select>
      <CampoTexto
        id="hoja-restaurar-fuente"
        labelText="Fuente (por qué se restaura)"
        value={fuente}
        maxLength={LARGO_DE_FUENTE}
        onChange={(e) => setFuente(e.target.value)}
      />
    </DialogoDeOperacion>
  );
}

interface Props {
  proyecto: string;
  // Los códigos de las versiones del proyecto, de la más nueva a la más vieja (el historial de Trazabilidad).
  versiones: string[];
  cambios: number;
  alCrearVersion: AlCrearVersion;
}

// «Restaurar una versión» (S2) de la pestaña Trazabilidad (RF-54): una versión nueva, copia de la elegida, que queda vigente.
export function RestaurarVersion({ proyecto, versiones, cambios, alCrearVersion }: Props) {
  const { abierto, anfitrion, abrir, cerrar, anclaDelBoton } = useDialogoDeOperacion();
  if (cambios > 0) {
    return (
      <InlineNotification
        kind="warning"
        role="status"
        lowContrast
        hideCloseButton
        title="Hay cambios sin guardar"
        subtitle={avisoDeCambiosPendientes("restaurar", cambios)}
      />
    );
  }
  if (versiones.length === 0) return null;
  return (
    <section className="silice-hoja__seccion" aria-label="Restaurar">
      <div className="silice-hoja__acciones">
        <Button ref={anclaDelBoton} kind="tertiary" size="md" onClick={abrir}>
          Restaurar una versión…
        </Button>
      </div>
      {abierto && anfitrion !== null && (
        <FormularioDeRestaurar
          proyecto={proyecto}
          versiones={versiones}
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
