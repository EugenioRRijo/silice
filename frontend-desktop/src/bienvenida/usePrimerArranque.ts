import { useEffect, useState } from "react";
import { pedir } from "../api/cliente";

// Contrato P0 del diseño (GET /v1/primer-arranque): sin nombres, sin rutas absolutas, sin el código. La política de la
// contraseña sale de la API (`cuentas.MINIMO_CONTRASENA` y `MAXIMO_CONTRASENA`); el front no la duplica más que como
// respaldo si la respuesta llega rota.
export interface EstadoPrimerArranque {
  sin_cuentas: boolean;
  archivo_presente: boolean;
  modo: "producto" | "desarrollo";
  politica: { minimo: number; maximo: number };
}

export type ConsultaPrimerArranque =
  | { tipo: "cargando" }
  | { tipo: "sin_cuentas"; info: EstadoPrimerArranque }
  // `info` es null si la API no contestó (403 por equipo ajeno, error, red): el front no inventa un estado.
  | { tipo: "con_cuentas"; info: EstadoPrimerArranque | null };

const POLITICA_DE_RESPALDO = { minimo: 10, maximo: 128 };

function entero(valor: unknown, respaldo: number): number {
  return typeof valor === "number" && Number.isInteger(valor) && valor > 0 ? valor : respaldo;
}

// Solo `sin_cuentas === true` (booleano) abre la bienvenida; cualquier otra cosa es «Entrar».
function leer(bruto: unknown): EstadoPrimerArranque | null {
  if (!bruto || typeof bruto !== "object") return null;
  const dato = bruto as Record<string, unknown>;
  if (typeof dato.sin_cuentas !== "boolean") return null;
  const politica = (dato.politica && typeof dato.politica === "object" ? dato.politica : {}) as Record<string, unknown>;
  return {
    sin_cuentas: dato.sin_cuentas,
    archivo_presente: dato.archivo_presente === true,
    modo: dato.modo === "desarrollo" ? "desarrollo" : "producto",
    politica: {
      minimo: entero(politica.minimo, POLITICA_DE_RESPALDO.minimo),
      maximo: entero(politica.maximo, POLITICA_DE_RESPALDO.maximo),
    },
  };
}

// Pregunta una vez, cada vez que `activo` pasa a verdadero (sin sesión), si la instalación aún no tiene cuentas. Un fallo
// nunca es un error para la persona: se muestra «Entrar».
export function usePrimerArranque(activo: boolean): ConsultaPrimerArranque {
  // Sin respuesta vigente (null) la consulta está «cargando»; al desactivarse se descarta la respuesta, para que la
  // siguiente vez no se vea la anterior mientras llega la nueva.
  const [respuesta, setRespuesta] = useState<ConsultaPrimerArranque | null>(null);

  useEffect(() => {
    if (!activo) return;
    let vigente = true;
    pedir<unknown>("/v1/primer-arranque")
      .then((bruto) => {
        if (!vigente) return;
        const info = leer(bruto);
        setRespuesta(info?.sin_cuentas ? { tipo: "sin_cuentas", info } : { tipo: "con_cuentas", info });
      })
      .catch(() => {
        if (vigente) setRespuesta({ tipo: "con_cuentas", info: null });
      });
    return () => {
      vigente = false;
      setRespuesta(null);
    };
  }, [activo]);

  return respuesta ?? { tipo: "cargando" };
}
