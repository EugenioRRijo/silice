import { useCallback, useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";

// Panel que se abre con clic o teclado (nunca al pasar el raton): Esc lo cierra y devuelve el foco al boton; un clic
// fuera tambien lo cierra. `envoltorio` es el elemento que contiene el boton y el panel.
export function useDespliegue() {
  const [abierto, setAbierto] = useState(false);
  const envoltorio = useRef<HTMLDivElement>(null);
  const boton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!abierto) return;
    function fuera(e: MouseEvent) {
      if (envoltorio.current && !envoltorio.current.contains(e.target as Node)) setAbierto(false);
    }
    document.addEventListener("mousedown", fuera);
    return () => document.removeEventListener("mousedown", fuera);
  }, [abierto]);

  const alTeclear = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape" && abierto) {
        e.stopPropagation();
        setAbierto(false);
        boton.current?.focus();
      }
    },
    [abierto],
  );

  const alternar = useCallback(() => setAbierto((a) => !a), []);
  return { abierto, alternar, envoltorio, boton, alTeclear };
}
