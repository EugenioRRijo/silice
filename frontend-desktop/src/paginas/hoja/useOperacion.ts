import { useCallback, useRef, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { clasificarErrorDeOperacion } from "./logicaVersiones";
import type { ErrorDeOperacion, VersionCreada } from "./logicaVersiones";

interface Opciones {
  ruta: string;
  alExpirar: () => void;
  // El servidor creó la versión nueva: la página la abre. No debe lanzar.
  alCrear: (respuesta: VersionCreada) => Promise<void>;
}

// Una operación que crea una versión nueva (S2 a S5): una sola petición en vuelo a la vez; si falla, el error queda a la vista
// y el formulario como estaba.
export function useOperacion({ ruta, alExpirar, alCrear }: Opciones) {
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<ErrorDeOperacion | null>(null);
  const enVuelo = useRef(false);

  const enviar = useCallback(
    async (cuerpo: object) => {
      if (enVuelo.current) return;
      enVuelo.current = true;
      setEnviando(true);
      setError(null);
      let respuesta: VersionCreada;
      try {
        respuesta = await pedir<VersionCreada>(ruta, { metodo: "POST", cuerpo });
      } catch (e) {
        if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
        setError(clasificarErrorDeOperacion(e));
        enVuelo.current = false;
        setEnviando(false);
        return;
      }
      enVuelo.current = false;
      setEnviando(false);
      await alCrear(respuesta);
    },
    [ruta, alExpirar, alCrear],
  );
  return { enviando, error, enviar };
}
