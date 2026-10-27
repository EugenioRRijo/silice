import { useSyncExternalStore } from "react";

// «Nueva obra» tiene un solo diálogo, el de la barra lateral, que sabe dónde se creará la obra (Tarea 6b del plan del
// marco). La mesa (Pendientes y Resumen) también lo pide («Nueva obra», «Cree su primera obra»): por aquí, para que no
// quede otro camino que cree obras sin decir dónde. Solo en memoria.
let abierta = false;
const oyentes = new Set<() => void>();

function cambiar(valor: boolean): void {
  if (abierta === valor) return;
  abierta = valor;
  for (const oyente of oyentes) oyente();
}

export function abrirNuevaObra(): void {
  cambiar(true);
}

export function cerrarNuevaObra(): void {
  cambiar(false);
}

function suscribir(oyente: () => void): () => void {
  oyentes.add(oyente);
  return () => {
    oyentes.delete(oyente);
  };
}

const leer = () => abierta;

export function useNuevaObraAbierta(): boolean {
  return useSyncExternalStore(suscribir, leer, leer);
}
