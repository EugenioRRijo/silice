import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import type { CasoRespuesta, CasosRespuesta, ProyectoRespuesta } from "../../api/tipos";
import { confirmarSalida } from "../salida";
import { nombreDeCarpeta } from "../Selectores";

interface Opciones {
  // `GET /v1/hoja/borradores` exige `editar_hoja` (BCP-5 §4.6): sin ella no se pregunta por borradores.
  puedeVerBorradores: boolean;
  // Las obras de la carpeta abierta, para nombrar los borradores («Hoja de Casa Demo»).
  obras: readonly ProyectoRespuesta[] | null;
  alExpirar: () => void;
  // Un error al leer la lista (que no sea 401 ni 403): lo muestra el armazon.
  alFallar: (error: unknown) => void;
  // La carpeta cambio (con su nombre sin .db): el armazon olvida la obra, vuelve a montar la pagina y avisa.
  alCambiar: (carpeta: string) => void;
}

function esEstado(e: unknown, estado: number): boolean {
  return e instanceof ErrorDeApi && e.estado === estado;
}

// La carpeta de trabajo de la sesion (diseno de modulos §7 y §12.2; BCP-5): la lista de `GET /v1/casos`, abrir otra
// (`POST /v1/casos/actual`) y volver a la de la empresa (`DELETE /v1/casos/actual`). Las dos pasan por la misma
// confirmacion, `confirmarSalida("carpeta", extras)`: cambiar de carpeta descarta los formularios sucios del navegador
// y los borradores de la Hoja de esta sesion (`caso_web.olvidar`), que se nombran como «Hoja de {obra}» (§4.6).
export function useCarpetaDeTrabajo({ puedeVerBorradores, obras, alExpirar, alFallar, alCambiar }: Opciones) {
  const [casos, setCasos] = useState<CasosRespuesta | null>(null);
  const [recarga, setRecarga] = useState(0);
  // Las obras cambian mas que las funciones: se leen al preguntar, sin rehacer `abrir` y `volver` en cada lista.
  const obrasActuales = useRef(obras);
  useEffect(() => {
    obrasActuales.current = obras;
  }, [obras]);

  useEffect(() => {
    let vigente = true;
    pedir<CasosRespuesta>("/v1/casos")
      .then((r) => {
        // Una API que no trae la forma esperada no tumba la pantalla: simplemente no hay carpeta que mostrar.
        if (vigente && r?.actual && Array.isArray(r.casos)) setCasos(r);
      })
      .catch((e: unknown) => {
        if (!vigente || esEstado(e, 403)) return;
        if (esEstado(e, 401)) alExpirar();
        else alFallar(e);
      });
    return () => {
      vigente = false;
    };
  }, [recarga, alExpirar, alFallar]);

  // «Hoja de {obra}» por cada borrador de esta sesion con cambios. Un 403 o un fallo cuentan como ninguno (no se puede
  // saber); un 401 sigue hacia arriba (la sesion vencio).
  const hojasConCambios = useCallback(async (): Promise<string[]> => {
    if (!puedeVerBorradores) return [];
    try {
      const r = await pedir<{ borradores?: { proyecto: string; cambios: number }[] }>("/v1/hoja/borradores");
      const lista = Array.isArray(r?.borradores) ? r.borradores : [];
      const nombre = (p: string) => obrasActuales.current?.find((o) => o.codigo === p || o.nombre === p)?.nombre ?? p;
      return [...new Set(lista.filter((b) => b.cambios > 0).map((b) => `Hoja de ${nombre(b.proyecto)}`))];
    } catch (e) {
      if (esEstado(e, 401)) throw e;
      return [];
    }
  }, [puedeVerBorradores]);

  // Pregunta, cambia y avisa. Resuelve true si cambio y false si la persona se quedo o la sesion vencio; si la API
  // rechaza el cambio, lanza el error (quien lo pidio lo muestra donde esta la persona).
  const cambiar = useCallback(
    async (peticion: () => Promise<CasoRespuesta>): Promise<boolean> => {
      try {
        if (!(await confirmarSalida("carpeta", await hojasConCambios()))) return false;
        const carpeta = await peticion();
        setRecarga((n) => n + 1);
        alCambiar(nombreDeCarpeta(carpeta.nombre));
        return true;
      } catch (e) {
        if (esEstado(e, 401)) {
          alExpirar();
          return false;
        }
        throw e;
      }
    },
    [hojasConCambios, alCambiar, alExpirar],
  );

  const abrir = useCallback(
    (nombre: string) =>
      cambiar(async () => {
        const r = await pedir<Partial<CasoRespuesta> | null>("/v1/casos/actual", { metodo: "POST", cuerpo: { nombre } });
        return { nombre: typeof r?.nombre === "string" ? r.nombre : nombre, ruta_relativa: r?.ruta_relativa ?? "" };
      }),
    [cambiar],
  );

  // «Volver a la carpeta de la empresa» (MarcaDemostracion): la misma pregunta que «Cambiar carpeta…», porque
  // `DELETE /v1/casos/actual` tambien olvida los borradores de la Hoja de esta sesion.
  const volverALaEmpresa = useCallback(
    () => cambiar(() => pedir<CasoRespuesta>("/v1/casos/actual", { metodo: "DELETE" })),
    [cambiar],
  );

  return { casos, abrir, volverALaEmpresa };
}
