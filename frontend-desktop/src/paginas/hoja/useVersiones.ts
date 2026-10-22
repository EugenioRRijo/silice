import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { rutaDeVersiones } from "./logica";
import type { VersionesRespuesta } from "./logica";
import { conVersionGuardada } from "./logicaGuardar";

// La lista de versiones del proyecto con el sentido que le da la página: la que cargó el marco, o la que se volvió a leer tras
// guardar (o tras crear una versión con restaurar, cotizar, retirar o convertir) sin desmontar nada. Las frescas valen mientras
// la carga inicial sea la misma.
export function useVersiones(proyecto: string, cargadas: VersionesRespuesta | null, alExpirar: () => void) {
  const [frescas, setFrescas] = useState<{ proyecto: string; sobre: VersionesRespuesta; datos: VersionesRespuesta } | null>(null);
  const datos = frescas !== null && frescas.proyecto === proyecto && frescas.sobre === cargadas ? frescas.datos : cargadas;
  const datosActuales = useRef(datos);
  useEffect(() => {
    datosActuales.current = datos;
  });

  // Vuelve a leer la lista de versiones sin desmontar nada. Con `nueva`, si no se pudo leer, se agrega esa versión a mano para
  // que el selector la tenga (la persona no pierde su sitio por un fallo de lectura).
  const recargarVersiones = useCallback(
    async (nueva?: string) => {
      const sobre = cargadas;
      if (sobre === null) return;
      try {
        const frescos = await pedir<VersionesRespuesta>(rutaDeVersiones(proyecto));
        setFrescas({ proyecto, sobre, datos: frescos });
      } catch (error) {
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        if (nueva !== undefined) setFrescas({ proyecto, sobre, datos: conVersionGuardada(datosActuales.current ?? sobre, nueva) });
      }
    },
    [cargadas, proyecto, alExpirar],
  );

  return { datos, recargarVersiones };
}
