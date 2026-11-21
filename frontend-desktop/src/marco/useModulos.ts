import { useCallback, useEffect, useState } from "react";
import { leerModulos } from "../api/modulos";

const NINGUNO: readonly string[] = [];

// Los módulos que la instalación apagó (`GET /v1/modulos`), para que el marco no ofrezca ni abra sus pantallas. Lo puede leer
// cualquier cuenta. Mientras carga, o si la lectura falla, no se oculta nada: la API sigue cortando lo apagado con su 404,
// y un fallo aquí no debe esconder pantallas que sí funcionan. `leidos` dice si ya volvió la primera lectura (con éxito o
// con fallo): una pantalla que solo se monta con su módulo encendido espera a eso, porque `apagados` vacío todavía no
// significa «ninguno apagado». `recargar` vuelve a leer (Administración › Especialidades) y conserva lo leído entre tanto.
export function useModulos(): { apagados: readonly string[]; leidos: boolean; recargar: () => void } {
  const [apagados, setApagados] = useState<readonly string[]>(NINGUNO);
  const [leidos, setLeidos] = useState(false);
  const [intento, setIntento] = useState(0);
  const recargar = useCallback(() => setIntento((n) => n + 1), []);

  useEffect(() => {
    let vigente = true;
    leerModulos().then(
      (r) => {
        if (!vigente) return;
        if (Array.isArray(r?.modulos)) setApagados(r.modulos.filter((m) => !m.activo).map((m) => m.clave));
        setLeidos(true);
      },
      () => {
        if (vigente) setLeidos(true);
      },
    );
    return () => {
      vigente = false;
    };
  }, [intento]);

  return { apagados, leidos, recargar };
}
