import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { alPerderSesion } from "../api/cliente";

// Capa de recursos: lecturas con caché por clave, una sola petición en vuelo por clave y cancelación cuando ya nadie
// espera el dato. Generaliza `paginas/vial/useTramos.ts`. El 401 NO se trata aquí: lo resuelve `api/cliente.ts`
// (`alPerderSesion`).

export type EstadoDeRecurso<T> = { estado: "cargando" } | { estado: "listo"; datos: T } | { estado: "error"; error: unknown };

// Una petición compartida. `interesados` cuenta los componentes que la esperan: al llegar a cero se cancela.
interface Vuelo {
  controlador: AbortController;
  interesados: number;
  terminado: boolean;
  promesa: Promise<void>;
  // Número de intento de la entrada al que corresponde esta petición (ver `Entrada.intentos`).
  intento: number;
}

interface Entrada {
  listo: { datos: unknown } | null;
  vuelo: Vuelo | null;
  // Sube con cada cambio de la entrada (dato nuevo o invalidación): es lo que observan los componentes.
  generacion: number;
  // Cuántas peticiones se han iniciado para esta clave. Un error se guarda con el intento que lo produjo y solo se muestra
  // mientras siga siendo el último: en cuanto se pide de nuevo (volver a la clave, invalidar, recargar) deja de valer.
  intentos: number;
  oyentes: Set<() => void>;
}

const entradas = new Map<string, Entrada>();

function entradaDe(clave: string): Entrada {
  let entrada = entradas.get(clave);
  if (entrada === undefined) {
    entrada = { listo: null, vuelo: null, generacion: 0, intentos: 0, oyentes: new Set() };
    entradas.set(clave, entrada);
  }
  return entrada;
}

function avisar(entrada: Entrada): void {
  entrada.generacion += 1;
  for (const oyente of [...entrada.oyentes]) oyente();
}

// Olvida el dato y cancela lo que viajaba: los componentes montados se enteran y vuelven a pedir.
function descartar(entrada: Entrada): void {
  if (entrada.vuelo !== null) {
    entrada.vuelo.controlador.abort();
    entrada.vuelo = null;
  }
  entrada.listo = null;
  avisar(entrada);
}

// Se llama después de una escritura: borra de la caché las claves que empiezan con `prefijo`.
export function invalidarRecursos(prefijo: string): void {
  for (const [clave, entrada] of entradas) {
    if (clave.startsWith(prefijo)) descartar(entrada);
  }
}

// La caché es de la sesión: cuando el servidor da la sesión por perdida (401) se vacía entera, para que la cuenta que
// entre después no vea los datos de la anterior. Al cerrar sesión lo hace `useSesion.salir`. `api/cliente.ts` no importa
// este módulo, así que no hay dependencia circular.
alPerderSesion(() => invalidarRecursos(""));

// SOLO PARA PRUEBAS: vacía la caché y cancela lo que viaja, para que una prueba no herede datos de la anterior.
export function vaciarRecursosParaPruebas(): void {
  for (const entrada of entradas.values()) {
    entrada.vuelo?.controlador.abort();
    entrada.vuelo = null;
    entrada.listo = null;
    entrada.generacion += 1;
  }
}

function iniciar<T>(entrada: Entrada, cargar: (senal: AbortSignal) => Promise<T>): Vuelo {
  const controlador = new AbortController();
  entrada.intentos += 1;
  const vuelo: Vuelo = { controlador, interesados: 0, terminado: false, promesa: Promise.resolve(), intento: entrada.intentos };
  vuelo.promesa = cargar(controlador.signal).then(
    (datos) => {
      vuelo.terminado = true;
      // Si la entrada ya apunta a otra petición (se invalidó mientras viajaba), este dato es viejo y se descarta.
      if (entrada.vuelo === vuelo) {
        entrada.vuelo = null;
        entrada.listo = { datos };
        avisar(entrada);
      }
    },
    (error: unknown) => {
      vuelo.terminado = true;
      if (entrada.vuelo === vuelo) entrada.vuelo = null;
      throw error; // el error no se guarda en la caché: lo recibe cada componente que esperaba
    },
  );
  vuelo.promesa.catch(() => undefined); // evita el aviso de rechazo sin atender si todos se fueron
  // Quien mostraba el error del intento anterior se entera de que ya hay otro en camino (no cambia `generacion`).
  for (const oyente of [...entrada.oyentes]) oyente();
  return vuelo;
}

// Un componente deja de esperar la petición; si era el último y sigue viajando, se cancela.
function soltar(entrada: Entrada, vuelo: Vuelo): void {
  vuelo.interesados -= 1;
  if (vuelo.interesados <= 0 && !vuelo.terminado) {
    vuelo.controlador.abort();
    if (entrada.vuelo === vuelo) entrada.vuelo = null;
  }
}

export function useRecurso<T>(
  clave: string | null,
  cargar: (senal: AbortSignal) => Promise<T>,
): {
  carga: EstadoDeRecurso<T>;
  recargar: () => void;
  reemplazar: (datos: T) => void;
} {
  const [fallo, setFallo] = useState<{ clave: string; error: unknown; intento: number } | null>(null);

  // `cargar` suele ser una función nueva en cada render: se guarda aparte para que no dispare la petición.
  const ultimaCarga = useRef(cargar);
  useEffect(() => {
    ultimaCarga.current = cargar;
  });

  const suscribir = useCallback(
    (aviso: () => void) => {
      if (clave === null) return () => undefined;
      const entrada = entradaDe(clave);
      entrada.oyentes.add(aviso);
      return () => {
        entrada.oyentes.delete(aviso);
      };
    },
    [clave],
  );
  const generacion = useSyncExternalStore(suscribir, () => (clave === null ? 0 : (entradas.get(clave)?.generacion ?? 0)));

  // Solo para volver a renderizar cuando se inicia otro intento.
  const intentos = useSyncExternalStore(suscribir, () => (clave === null ? 0 : (entradas.get(clave)?.intentos ?? 0)));

  useEffect(() => {
    if (clave === null) return;
    const entrada = entradaDe(clave);
    if (entrada.listo !== null) return;
    const vuelo = entrada.vuelo ?? (entrada.vuelo = iniciar(entrada, ultimaCarga.current));
    vuelo.interesados += 1;
    // Este efecto sigue vigente mientras la clave y la generación no cambien: un fallo tardío de una petición que ya se
    // dejó (otra clave, otra generación) no debe pisar lo que muestra el componente ahora.
    let vigente = true;
    vuelo.promesa.then(undefined, (error: unknown) => {
      // Una petición cancelada (cambio de clave, invalidación o desmontaje) no es un error que mostrar: todo aborto va
      // acompañado de `vigente = false` (la limpieza del efecto corre antes de que llegue este rechazo).
      if (!vigente) return;
      setFallo({ clave, error, intento: vuelo.intento });
    });
    return () => {
      vigente = false;
      soltar(entrada, vuelo);
    };
  }, [clave, generacion]);

  const recargar = useCallback(() => {
    if (clave === null) return;
    descartar(entradaDe(clave));
  }, [clave]);

  const reemplazar = useCallback(
    (datos: T) => {
      if (clave === null) return;
      const entrada = entradaDe(clave);
      entrada.listo = { datos };
      avisar(entrada);
    },
    [clave],
  );

  let carga: EstadoDeRecurso<T> = { estado: "cargando" };
  const listo = clave === null ? null : (entradas.get(clave)?.listo ?? null);
  if (listo !== null) carga = { estado: "listo", datos: listo.datos as T };
  else if (fallo !== null && fallo.clave === clave && fallo.intento === intentos) carga = { estado: "error", error: fallo.error };
  return { carga, recargar, reemplazar };
}
