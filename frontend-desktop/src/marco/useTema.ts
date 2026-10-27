import { useEffect, useState } from "react";
import { pedir } from "../api/cliente";
import { aplicarTema, leerTema, RUTA_DEL_LOGO } from "./tema";

// Pide GET /v1/tema (publico), fija los colores validos en la raiz del documento y devuelve la ruta del logo, o null
// si no hay. Si la API no contesta queda el tema neutro del repositorio. El marco lo usa desde la Tarea 5.
export function useTema(): { logo: string | null } {
  const [logo, setLogo] = useState<string | null>(null);

  useEffect(() => {
    let vigente = true;
    pedir("/v1/tema")
      .then((bruto) => {
        if (!vigente) return;
        const tema = leerTema(bruto);
        aplicarTema(tema, document.documentElement);
        setLogo(tema.tiene_logo ? RUTA_DEL_LOGO : null);
      })
      .catch(() => {
        // Sin tema no hay nada que avisar: la persona ve el marco neutro.
      });
    return () => {
      vigente = false;
    };
  }, []);

  return { logo };
}
