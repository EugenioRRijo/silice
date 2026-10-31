import { useCallback, useEffect, useState } from "react";
import { leerModulos } from "../api/modulos";

const NINGUNO: readonly string[] = [];

// Los módulos que la instalación apagó (`GET /v1/modulos`), para que el marco no ofrezca ni abra sus pantallas. Lo puede leer
// cualquier cuenta. Mientras carga, o si la lectura falla, no se oculta nada: la API sigue cortando lo apagado con su 404,
// y un fallo aquí no debe esconder pantallas que sí funcionan. `recargar` vuelve a leer (Administración › Especialidades).
export function useModulos(): { apagados: readonly string[]; recargar: () => void } {
  const [apagados, setApagados] = useState<readonly string[]>(NINGUNO);
  const [intento, setIntento] = useState(0);
  const recargar = useCallback(() => setIntento((n) => n + 1), []);

  useEffect(() => {
    let vigente = true;
    leerModulos().then(
      (r) => {
        if (vigente && Array.isArray(r?.modulos)) setApagados(r.modulos.filter((m) => !m.activo).map((m) => m.clave));
      },
      () => undefined,
    );
    return () => {
      vigente = false;
    };
  }, [intento]);

  return { apagados, recargar };
}
