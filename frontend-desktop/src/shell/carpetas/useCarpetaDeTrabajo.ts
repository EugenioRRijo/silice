import { useCallback, useEffect, useRef, useState } from "react";
import { abrirCarpeta, volverALaCarpetaDeLaEmpresa } from "../../api/carpetaYObra";
import { ErrorDeApi, pedir } from "../../api/cliente";
import type { CasoRespuesta, CasosRespuesta, ProyectoRespuesta } from "../../api/tipos";
import { confirmarSalida } from "../salida";
import { nombreDeCarpeta } from "../Selectores";
import { hojasConCambios } from "./hojasConCambios";

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

  // Los borradores con cambios, nombrados con las obras de la carpeta abierta (ver `hojasConCambios`).
  const hojasPendientes = useCallback(
    async (): Promise<string[]> => (puedeVerBorradores ? hojasConCambios(obrasActuales.current) : []),
    [puedeVerBorradores],
  );

  // Pregunta, cambia y avisa. Resuelve true si cambio y false si la persona se quedo o la sesion vencio; si la API
  // rechaza el cambio, lanza el error (quien lo pidio lo muestra donde esta la persona).
  const cambiar = useCallback(
    async (peticion: () => Promise<CasoRespuesta>): Promise<boolean> => {
      try {
        if (!(await confirmarSalida("carpeta", await hojasPendientes()))) return false;
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
    [hojasPendientes, alCambiar, alExpirar],
  );

  // `preparar` (crear la carpeta, `POST /v1/casos`) corre DESPUES de la pregunta y antes de abrir, y da el nombre final
  // que se abre: si la persona elige «Quedarme» no se crea nada (ronda 2 del arbitro de MOD-3b). `abrirCon` abre por otra
  // ruta que `POST /v1/casos/actual` y devuelve la carpeta que quedo abierta (la de un envio por aprobar, `POST
  // /v1/aprobaciones/abrir`, Tarea 19, que no exige `cambiar_caso`); la pregunta y el aviso son los mismos.
  const abrir = useCallback(
    (nombre: string, preparar?: () => Promise<string>, abrirCon?: (nombre: string) => Promise<CasoRespuesta>) =>
      cambiar(async () => {
        const destino = preparar ? await preparar() : nombre;
        return abrirCon ? abrirCon(destino) : abrirCarpeta(destino);
      }),
    [cambiar],
  );

  // «Volver a la carpeta de la empresa» (MarcaDemostracion): la misma pregunta que «Cambiar carpeta…», porque
  // `DELETE /v1/casos/actual` tambien olvida los borradores de la Hoja de esta sesion.
  const volverALaEmpresa = useCallback(
    () => cambiar(volverALaCarpetaDeLaEmpresa),
    [cambiar],
  );

  return { casos, abrir, volverALaEmpresa };
}
