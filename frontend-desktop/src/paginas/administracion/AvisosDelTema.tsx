import { InlineNotification } from "../../comun/carbonEs";
import { useEffect, useState } from "react";
import { pedir } from "../../api/cliente";
import { leerTema } from "../../marco/tema";
import { useAplicacion } from "../../shell/contexto";

// Avisa a quien administra de los colores de la empresa que no se leen bien (el servidor mide y redacta; el tema se
// aplica igual). Sin permiso no pide nada; sin avisos, o si la peticion falla, no dibuja nada.
export default function AvisosDelTema() {
  const { sesion } = useAplicacion();
  const puede = sesion.acciones.includes("administrar_cuentas");
  const [avisos, setAvisos] = useState<string[]>([]);

  useEffect(() => {
    if (!puede) return;
    let vigente = true;
    pedir("/v1/tema").then(
      (bruto) => vigente && setAvisos(leerTema(bruto).avisos),
      () => {
        // Sin tema no hay nada que avisar.
      },
    );
    return () => {
      vigente = false;
    };
  }, [puede]);

  if (!puede || avisos.length === 0) return null;
  return (
    <InlineNotification
      kind="warning"
      lowContrast
      hideCloseButton
      title="Algunos colores de la empresa no se leen bien"
    >
      <ul>
        {avisos.map((a) => (
          <li key={a}>{a}</li>
        ))}
      </ul>
    </InlineNotification>
  );
}
