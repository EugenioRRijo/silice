// Relevo entre Inicio y «Libro de la empresa»: el archivo que se suelta en Inicio no sobrevive al cambio de
// pantalla, asi que queda aqui, solo en memoria del navegador (RT-9: nada en localStorage) y solo hasta que la
// pagina de destino lo toma. El libro nunca se guarda (spec del Inicio, antimeta de §3).

export type ModoDeAuditoria = "guiado" | "propio";

export interface ArchivoPendiente {
  archivo: File;
  modo: ModoDeAuditoria;
}

let pendiente: ArchivoPendiente | null = null;

export function fijarArchivoPendiente(archivo: File, modo: ModoDeAuditoria): void {
  pendiente = { archivo, modo };
}

export function hayArchivoPendiente(): boolean {
  return pendiente !== null;
}

// Entrega el archivo y lo olvida: quien lo toma se hace cargo.
export function tomarArchivoPendiente(): ArchivoPendiente | null {
  const valor = pendiente;
  pendiente = null;
  return valor;
}
