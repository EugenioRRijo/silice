// La obra de la ruta `#/obra/<carpeta>/<obra>/<sección>` (plan del rediseño del marco, Tarea 4; especificación
// 2026-10-26, §8 ter): la ruta manda y la sesión del servidor solo la refleja. Al entrar en una obra:
//   0. `GET /v1/obras/todas` da la carpeta abierta y dice si la obra existe (`PUT /v1/sesion/proyecto` también
//      contesta 404 si la obra no existe, pero esta lectura evita cambiar de carpeta antes de saberlo);
//   1. si la carpeta de la ruta no es la abierta, `POST /v1/casos/actual` (o `DELETE`, si la ruta dice `empresa`);
//      sin `abrir_carpeta` y en la misma carpeta no se llama (Tarea 3);
//   2. `PUT /v1/sesion/proyecto` con la obra;
//   3. solo entonces `lista`, y se anuncia a las demás pestañas (marco/otraPestana).
// Cambiar de sección dentro de la misma obra no repite nada.
//
// Cambios respecto del plan (están en las pruebas): `lista.carpeta` es `string | null` (null = la de la empresa); hay
// un estado `error` con `reintentar` para los fallos que no dicen «no existe» (servidor caído, 500), porque mandar a
// Pendientes con «Esa obra ya no existe» sería falso. Dicen «no existe»: la obra o la carpeta que no están en la
// lista, un 403 o 404 al cambiar de carpeta, un 404 al fijar la obra, una sección desconocida o sin pantalla y un
// número de obra que no es un entero positivo.
//
// Sin carreras: cada entrada espera a que termine la anterior (una cola), y la que quedó vieja no sigue al paso
// siguiente ni toca el estado. No se aborta la petición en vuelo: el servidor podría aplicarla igual y el cambio
// viejo llegaría después del nuevo; esperándola, el nuevo siempre es el último que el servidor recibe.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router";
import { abrirCarpeta, recordarObra, volverALaCarpetaDeLaEmpresa } from "../api/carpetaYObra";
import { ErrorDeApi, pedir } from "../api/cliente";
import type { ObrasTodasRespuesta } from "../api/tipos";
import { vigilanteDelNavegador, type VigilanteDeObra } from "./otraPestana";
import { carpetaDeLaRuta, seccionPorId, type SeccionDef } from "./secciones";

export type EstadoObra =
  | { tipo: "cargando" }
  | { tipo: "lista"; carpeta: string | null; obraId: number; seccion: SeccionDef }
  | { tipo: "no_existe" }
  | { tipo: "en_otra_pestana"; retomar: () => void }
  | { tipo: "error"; reintentar: () => void };

export interface OpcionesObraDeLaRuta {
  // Las pruebas dan uno con un canal de mentira.
  vigilante?: VigilanteDeObra;
}

type Fase = "lista" | "no_existe" | "error" | "en_otra_pestana";

interface Resultado {
  clave: string;
  fase: Fase;
}

type Paso = "leer" | "carpeta" | "obra";

function esEstado(e: unknown, ...estados: number[]): boolean {
  return e instanceof ErrorDeApi && estados.includes(e.estado);
}

function dicenQueNoExiste(paso: Paso, e: unknown): boolean {
  if (paso === "leer") return esEstado(e, 403);
  if (paso === "carpeta") return esEstado(e, 403, 404);
  return esEstado(e, 404);
}

// Los pasos 0-2. Devuelve null si la entrada quedó vieja (otra la reemplazó): entonces no sigue escribiendo.
async function entrar(carpeta: string | null, obraId: number, vigente: () => boolean): Promise<Fase | null> {
  let paso: Paso = "leer";
  try {
    if (!vigente()) return null;
    const todas = await pedir<ObrasTodasRespuesta>("/v1/obras/todas");
    if (!vigente()) return null;
    if (!Array.isArray(todas?.obras)) return "error";
    if (!todas.obras.some((o) => o.carpeta === carpeta && o.obra_id === obraId)) return "no_existe";
    if (todas.carpeta_actual !== carpeta) {
      paso = "carpeta";
      await (carpeta === null ? volverALaCarpetaDeLaEmpresa() : abrirCarpeta(carpeta));
      if (!vigente()) return null;
    }
    paso = "obra";
    // Ventana entre el GET de arriba y este PUT: si otra persona borra la obra en ese instante el servidor contesta 404
    // y se dice «no existe», igual que si la ruta hubiera apuntado a una obra que nunca estuvo (`dicenQueNoExiste`).
    await recordarObra(String(obraId));
    return vigente() ? "lista" : null;
  } catch (e) {
    if (!vigente()) return null;
    return dicenQueNoExiste(paso, e) ? "no_existe" : "error";
  }
}

interface Destino {
  carpeta: string | null;
  obraId: number;
  seccion: SeccionDef;
}

function leerDestino(params: Readonly<Partial<Record<string, string>>>): Destino | null {
  const { carpeta, obraId, seccion } = params;
  if (carpeta === undefined || obraId === undefined || seccion === undefined) return null;
  const def = seccionPorId(seccion);
  if (!def || def.pagina === null || !/^[1-9]\d*$/.test(obraId)) return null;
  const numero = Number(obraId);
  return Number.isSafeInteger(numero) ? { carpeta: carpetaDeLaRuta(carpeta), obraId: numero, seccion: def } : null;
}

const CARGANDO: EstadoObra = { tipo: "cargando" };
const NO_EXISTE: EstadoObra = { tipo: "no_existe" };

// `vigilante` por omisión es el de la aplicación, que `vigilanteDelNavegador` crea una sola vez por pestaña: la misma
// referencia en cada dibujo, así que no reinicia el efecto de entrada (que lo lista como dependencia). Quien pase otro
// (las pruebas) debe pasar siempre el mismo objeto.
export function useObraDeLaRuta({ vigilante = vigilanteDelNavegador() }: OpcionesObraDeLaRuta = {}): EstadoObra {
  const destino = leerDestino(useParams());
  const hayDestino = destino !== null;
  const carpeta = destino?.carpeta ?? null;
  const obraId = destino?.obraId ?? 0;
  const seccion = destino?.seccion ?? null;

  // `intento` sube con «Reintentar» y «Retomar»: la misma obra vuelve a entrar.
  const [intento, setIntento] = useState(0);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const cola = useRef<Promise<void>>(Promise.resolve());
  const clave = JSON.stringify([carpeta, obraId, intento]);

  useEffect(() => {
    if (!hayDestino) return;
    let vigente = true;
    const turno = cola.current.then(async () => {
      const fase = await entrar(carpeta, obraId, () => vigente);
      if (fase === null || !vigente) return;
      setResultado({ clave, fase });
      if (fase === "lista") vigilante.anunciarObra(carpeta, obraId);
    });
    cola.current = turno.catch(() => undefined);
    return () => {
      vigente = false;
    };
  }, [hayDestino, carpeta, obraId, clave, vigilante]);

  // Otra pestaña abrió otra obra: la sesión del servidor ya no es la de esta. Solo importa si esta estaba lista.
  useEffect(
    () =>
      vigilante.escucharOtraPestana(() =>
        setResultado((r) => (r?.fase === "lista" ? { ...r, fase: "en_otra_pestana" } : r)),
      ),
    [vigilante],
  );

  const volverAEntrar = useCallback(() => setIntento((n) => n + 1), [setIntento]);

  const fase = resultado?.clave === clave ? resultado.fase : null;
  return useMemo((): EstadoObra => {
    if (seccion === null) return NO_EXISTE;
    switch (fase) {
      case null:
        return CARGANDO;
      case "lista":
        return { tipo: "lista", carpeta, obraId, seccion };
      case "no_existe":
        return NO_EXISTE;
      case "error":
        return { tipo: "error", reintentar: volverAEntrar };
      case "en_otra_pestana":
        return { tipo: "en_otra_pestana", retomar: volverAEntrar };
    }
  }, [seccion, fase, carpeta, obraId, volverAEntrar]);
}
