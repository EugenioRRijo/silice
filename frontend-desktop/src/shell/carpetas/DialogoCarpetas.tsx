import { Button } from "@carbon/react";
import type { JSX } from "react";
import { GestionCarpetas } from "./GestionCarpetas";
import type { OrigenDeApertura } from "./GestionCarpetas";
import { MarcoDeDialogo } from "./MarcoDeDialogo";

interface Props {
  abierto: boolean;
  alCerrar: () => void;
  alAbrir: (nombre: string) => void | Promise<boolean>;
  conDemostracion: boolean;
  puedeDeclararMoneda?: boolean;
}

// «Carpetas de trabajo» (BCP-5 §4.7), desde «Cambiar carpeta…» al pie del selector de obra. Abrir una carpeta de la
// lista o la demostracion cierra el dialogo (el armazon avisa del cambio); crear y subir se quedan para contar lo que
// paso (el nombre final saneado, el aviso de la migracion).
export function DialogoCarpetas({ abierto, alCerrar, alAbrir, conDemostracion, puedeDeclararMoneda }: Props): JSX.Element | null {
  if (!abierto) return null;
  const alAbierta = (origen: OrigenDeApertura) => {
    if (origen === "lista" || origen === "demostracion") alCerrar();
  };
  return (
    <MarcoDeDialogo
      titulo="Carpetas de trabajo"
      alCerrar={alCerrar}
      ancho="ancho"
      pie={
        <Button kind="secondary" onClick={alCerrar}>
          Cerrar
        </Button>
      }
    >
      <GestionCarpetas
        alAbrir={alAbrir}
        conDemostracion={conDemostracion}
        puedeDeclararMoneda={puedeDeclararMoneda}
        alAbierta={alAbierta}
      />
    </MarcoDeDialogo>
  );
}
