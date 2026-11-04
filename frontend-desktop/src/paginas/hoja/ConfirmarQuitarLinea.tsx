import { useContext, useEffect } from "react";
import { createPortal } from "react-dom";
import { ContextoDeDialogos } from "./ContextoDeDialogos";
import { DialogoDeVersion } from "./DialogoDeVersion";

interface Props {
  partida: string;
  descripcion: string;
  enFrase: string;
  alQuitar: () => void;
  alCancelar: () => void;
}

// Por qué existe (Tarea 8 del plan F4): «Quitar» de una línea del APU. Salió del antiguo formulario de agregar línea cuando éste pasó
// a ser `LineaDelApu.tsx` (agregar y cambiar insumo), para que ese archivo no mezcle una confirmación con un formulario; lo usa
// `EditorDeApu`, que sirve a la pestaña APU y al panel lateral. Es la confirmación de siempre de la Hoja
// (`DialogoDeVersion`), pintada fuera de la página, que queda `inert` mientras está abierta.
export function ConfirmarQuitarLinea({ partida, descripcion, enFrase, alQuitar, alCancelar }: Props) {
  const { anfitrion, registrar } = useContext(ContextoDeDialogos);
  useEffect(() => {
    registrar(1);
    return () => registrar(-1);
  }, [registrar]);
  if (anfitrion === null) return null;
  return createPortal(
    <DialogoDeVersion
      titulo="Quitar línea"
      texto={`¿Quitar «${descripcion}» de ${enFrase} de ${partida}? Lo puede descartar antes de guardar.`}
      textoConfirmar="Quitar"
      textoCancelar="Cancelar"
      alConfirmar={alQuitar}
      alCancelar={alCancelar}
    />,
    anfitrion,
  );
}
