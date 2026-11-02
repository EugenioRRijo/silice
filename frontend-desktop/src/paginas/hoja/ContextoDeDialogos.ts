import { createContext } from "react";

// Los diálogos de las operaciones sobre versiones (restaurar, cotizar, retirar, convertir) los abre una pestaña, pero deben
// quedar FUERA del resto de la página, que se vuelve `inert` mientras haya uno abierto. La página reparte el lugar donde se
// pintan (`anfitrion`, un hermano del contenido inerte) y cuenta cuántos hay abiertos.
export interface DialogosDeLaPagina {
  anfitrion: HTMLElement | null;
  abiertos: number;
  // +1 al abrirse un diálogo, -1 al cerrarse.
  registrar: (delta: number) => void;
}

export const ContextoDeDialogos = createContext<DialogosDeLaPagina>({
  anfitrion: null,
  abiertos: 0,
  registrar: () => undefined,
});
