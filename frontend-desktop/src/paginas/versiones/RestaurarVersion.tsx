import { Button, Select, SelectItem } from "@carbon/react";
import { useState } from "react";
import { CampoTexto } from "../../comun/CampoTexto";
import { useAplicacion } from "../../shell/contexto";
import { DialogoDeOperacion } from "../hoja/DialogoDeOperacion";
import { usuarioDeSesion } from "../hoja/logicaGuardar";
import { RUTA_DE_RESTAURAR, cuerpoDeRestaurar, motivoParaNoRestaurar, textoDeVersionCreada } from "../hoja/logicaVersiones";
import type { VersionCreada } from "../hoja/logicaVersiones";
import type { AlCrearVersion } from "../hoja/OperacionesDePrecios";
import { useDialogoDeOperacion } from "../hoja/useDialogoDeOperacion";
import { useOperacion } from "../hoja/useOperacion";

const LARGO_DE_FUENTE = 300;

interface PropsDeFormulario {
  proyecto: string;
  versiones: string[];
  inicial: string;
  anfitrion: HTMLElement;
  alCancelar: () => void;
  alCrearVersion: AlCrearVersion;
}

function FormularioDeRestaurar({ proyecto, versiones, inicial, anfitrion, alCancelar, alCrearVersion }: PropsDeFormulario) {
  const { alExpirar, sesion } = useAplicacion();
  const [elegida, setElegida] = useState(inicial);
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
  // Los códigos de las versiones de la obra, en el orden de la tabla de Versiones.
  versiones: string[];
  // La versión de la fila: el diálogo la trae elegida.
  inicial: string;
  alCrearVersion: AlCrearVersion;
}

// «Restaurar una versión» (S2, RF-54): una versión nueva, copia de la elegida, que queda vigente. Desde la Tarea 6 del plan F4
// es el botón «Restaurar…» de cada fila de Versiones (antes, uno solo en la pestaña «Trazabilidad»): el diálogo es el mismo y
// trae elegida la versión de la fila. Quien lo monta decide si se ofrece (el permiso y que no haya cambios sin guardar).
export function RestaurarVersion({ proyecto, versiones, inicial, alCrearVersion }: Props) {
  const { abierto, anfitrion, abrir, cerrar, anclaDelBoton } = useDialogoDeOperacion();
  return (
    <>
      <Button ref={anclaDelBoton} kind="ghost" size="sm" aria-label={`Restaurar ${inicial}…`} onClick={abrir}>
        Restaurar…
      </Button>
      {abierto && anfitrion !== null && (
        <FormularioDeRestaurar
          proyecto={proyecto}
          versiones={versiones}
          inicial={inicial}
          anfitrion={anfitrion}
          alCancelar={() => cerrar(true)}
          alCrearVersion={async (codigo, texto) => {
            cerrar(false);
            await alCrearVersion(codigo, texto);
          }}
        />
      )}
    </>
  );
}
