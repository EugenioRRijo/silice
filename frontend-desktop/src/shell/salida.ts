import { useSyncExternalStore } from "react";
import { formulariosSucios, olvidarFormularios, soloTrabajoEnElServidor } from "./sucio";

// Confirmacion al salir con trabajo sin guardar (diseno de modulos §4 y §12.5). Un solo punto para todas las
// navegaciones que inician los controles de Silice; atras/adelante del navegador no se interceptan (sin migrar de
// enrutador). El dialogo lo pinta `DialogoSalida`, que el armazon monta una vez.
// «cambiar»: la pantalla sigue abierta pero cambia lo que muestra (otro insumo o partida en el estudio de mercado); quien
// pregunta dice la consecuencia en sus palabras.
export type MotivoSalida = "salir" | "carpeta" | "cambiar";

export interface SalidaPendiente {
  // Cambia con cada pregunta: el dialogo se vuelve a montar (foco inicial de nuevo).
  numero: number;
  motivo: MotivoSalida;
  // Ids de pantalla (rutas.ts) con formularios sucios, en orden de registro.
  pantallas: readonly string[];
  // Otros cambios que se perderian, ya dichos en palabras (p. ej. «la obra nueva»).
  extras: readonly string[];
  // La consecuencia dicha por quien pregunta («Si elige otro insumo o partida, se perderán.»); null = la del motivo.
  consecuencia: string | null;
  // Todo lo sucio vive en el servidor y se retoma al volver (el borrador de la Hoja, Tarea 3 del plan F4): solo al salir
  // («salir»), sin extras; cambiar de carpeta si lo pierde.
  retomable: boolean;
}

let pendiente: (SalidaPendiente & { resolver: (salir: boolean) => void }) | null = null;
let numero = 0;
const oyentes = new Set<() => void>();

function avisar(): void {
  for (const oyente of oyentes) oyente();
}

function suscribir(oyente: () => void): () => void {
  oyentes.add(oyente);
  return () => {
    oyentes.delete(oyente);
  };
}

function salidaPendiente(): SalidaPendiente | null {
  return pendiente;
}

export function useSalidaPendiente(): SalidaPendiente | null {
  return useSyncExternalStore(suscribir, salidaPendiente, salidaPendiente);
}

// Resuelve true sin preguntar si no hay nada que perder; si lo hay, abre el dialogo y resuelve con la respuesta. Una
// pregunta nueva deja sin efecto la anterior (que resuelve false: nadie navega por ella). Con `destino` (la ruta a la que
// se va) no cuenta lo que sobrevive al ir alli (el borrador de la Hoja entre las secciones de su obra, sucio.ts).
export function confirmarSalida(
  motivo: MotivoSalida,
  extras: readonly string[] = [],
  consecuencia: string | null = null,
  destino: string | null = null,
): Promise<boolean> {
  const pantallas = formulariosSucios(destino);
  if (pantallas.length === 0 && extras.length === 0) return Promise.resolve(true);
  return new Promise<boolean>((resolver) => {
    const anterior = pendiente;
    numero += 1;
    const retomable = motivo === "salir" && extras.length === 0 && soloTrabajoEnElServidor(destino);
    pendiente = { numero, motivo, pantallas, extras: [...extras], consecuencia, retomable, resolver };
    anterior?.resolver(false);
    avisar();
  });
}

// La respuesta del dialogo. «Salir/Cambiar y descartar» olvida los formularios antes de que la pantalla se desmonte.
export function responderSalida(salir: boolean): void {
  const actual = pendiente;
  if (!actual) return;
  pendiente = null;
  if (salir) olvidarFormularios();
  avisar();
  actual.resolver(salir);
}

// Al salir de la sesion o desmontar el armazon: la pregunta abierta se da por «Quedarme».
export function cancelarSalida(): void {
  responderSalida(false);
}

// «A», «A y B», «A, B y C».
export function unirConY(nombres: readonly string[]): string {
  if (nombres.length <= 1) return nombres[0] ?? "";
  return `${nombres.slice(0, -1).join(", ")} y ${nombres[nombres.length - 1]}`;
}
