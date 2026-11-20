import { InlineNotification } from "../../comun/carbonEs";
import type { HojaDeLaObra } from "./ProveedorDeLaHoja";

type Exito = NonNullable<HojaDeLaObra["exito"]>;

// El aviso de éxito de guardar o restaurar, que pintan la Hoja y Versiones: lo que pasó lo dice `titulo` («Desglose guardado»
// cuando solo se guardó el desglose del desperdicio y no se creó ninguna versión); sin él, «Versión guardada».
export function AvisoDeGuardado({ exito, alCerrar }: { exito: Exito; alCerrar: () => void }) {
  return (
    <InlineNotification
      kind="success"
      role="status"
      lowContrast
      title={exito.titulo ?? "Versión guardada"}
      subtitle={exito.texto}
      onCloseButtonClick={alCerrar}
    />
  );
}
