import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";

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
}

interface Entrada {
  listo: { datos: unknown } | null;
  vuelo: Vuelo | null;
  // Sube con cada cambio de la entrada (dato nuevo o invalidación): es lo que observan los componentes.
  generacion: number;
  oyentes: Set<() => void>;
}

const entradas = new Map<string, Entrada>();

function entradaDe(clave: string): Entrada {
  let entrada = entradas.get(clave);
  if (entrada === undefined) {
    entrada = { listo: null, vuelo: null, generacion: 0, oyentes: new Set() };
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
  const vuelo: Vuelo = { controlador, interesados: 0, terminado: false, promesa: Promise.resolve() };
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
  const [fallo, setFallo] = useState<{ clave: string; error: unknown } | null>(null);

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

  useEffect(() => {
    if (clave === null) return;
    const entrada = entradaDe(clave);
    if (entrada.listo !== null) return;
    const vuelo = entrada.vuelo ?? (entrada.vuelo = iniciar(entrada, ultimaCarga.current));
    vuelo.interesados += 1;
    vuelo.promesa.then(undefined, (error: unknown) => {
      // Una petición cancelada (cambio de clave, invalidación o desmontaje) no es un error que mostrar.
      if (vuelo.controlador.signal.aborted) return;
      setFallo({ clave, error });
    });
    return () => soltar(entrada, vuelo);
  }, [clave, generacion]);

  const recargar = useCallback(() => {
    if (clave === null) return;
    setFallo(null);
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
  else if (fallo !== null && fallo.clave === clave) carga = { estado: "error", error: fallo.error };
  return { carga, recargar, reemplazar };
}
