import { useSyncExternalStore } from "react";

// Recorridos guiados (spec 2026-10-18 del Inicio, §2.5): una lista de pasos, uno por pantalla, cada uno con «que
// hacer» y «sabra que termino cuando». El paso actual no se guarda: sale de la pantalla en que esta la persona. Lo
// unico que se recuerda es cual recorrido esta en curso, y solo en memoria (RT-9: nada en localStorage).
export interface PasoRecorrido {
  // Id de la pantalla (rutas.ts): un paso por pantalla, sin repetir.
  pagina: string;
  titulo: string;
  queHacer: string;
  sabraQueTermino: string;
}

export interface Recorrido {
  titulo: string;
  pasos: readonly PasoRecorrido[];
}

export const RECORRIDO_AUDITAR: Recorrido = {
  titulo: "Auditar un libro de la empresa",
  pasos: [
    {
      pagina: "inicio",
      titulo: "Suba el libro",
      queHacer: "Suelte el Excel del presupuesto en la zona de arriba. Pulse «Auditar con recorrido guiado».",
      sabraQueTermino: "Sabrá que terminó cuando se abra «Libro de la empresa» con su libro ya revisado.",
    },
    {
      pagina: "libros",
      titulo: "Lea el resumen y los hallazgos",
      queHacer:
        "Compare el total del libro con el que recalculó Sílice y revise los hallazgos por severidad, de errores a avisos. Descargue el libro devuelto si lo necesita.",
      sabraQueTermino: "Sabrá que terminó cuando haya revisado cada hallazgo con error o advertencia.",
    },
    {
      pagina: "historial",
      titulo: "Compruebe que quedó guardada",
      queHacer: "Abra la auditoría más reciente de la lista y compare su resumen con el que acaba de ver.",
      sabraQueTermino: "Sabrá que terminó cuando vea su archivo en la lista, con los mismos conteos.",
    },
  ],
};

// Posicion (desde 0) del paso cuya pantalla es la de la ruta, o null si la ruta no es de ningun paso.
export function pasoDeRuta(recorrido: Recorrido, ruta: string): number | null {
  const i = recorrido.pasos.findIndex((p) => `/${p.pagina}` === ruta);
  return i < 0 ? null : i;
}

let enCurso: Recorrido | null = null;
const oyentes = new Set<() => void>();

function avisar(): void {
  for (const oyente of oyentes) oyente();
}

export function recorridoEnCurso(): Recorrido | null {
  return enCurso;
}

export function iniciarRecorrido(recorrido: Recorrido): void {
  enCurso = recorrido;
  avisar();
}

export function terminarRecorrido(): void {
  if (enCurso === null) return;
  enCurso = null;
  avisar();
}

export function suscribirRecorrido(oyente: () => void): () => void {
  oyentes.add(oyente);
  return () => {
    oyentes.delete(oyente);
  };
}

export function useRecorrido(): Recorrido | null {
  return useSyncExternalStore(suscribirRecorrido, recorridoEnCurso, recorridoEnCurso);
}
