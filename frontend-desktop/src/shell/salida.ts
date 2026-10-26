import { useSyncExternalStore } from "react";
import { formulariosSucios, olvidarFormularios } from "./sucio";

// Confirmacion al salir con trabajo sin guardar (diseno de modulos §4 y §12.5). Un solo punto para todas las
// navegaciones que inician los controles de Silice; atras/adelante del navegador no se interceptan (sin migrar de
// enrutador). El dialogo lo pinta `DialogoSalida`, que el armazon monta una vez.
export type MotivoSalida = "salir" | "carpeta";

export interface SalidaPendiente {
  // Cambia con cada pregunta: el dialogo se vuelve a montar (foco inicial de nuevo).
  numero: number;
  motivo: MotivoSalida;
  // Ids de pantalla (rutas.ts) con formularios sucios, en orden de registro.
  pantallas: readonly string[];
  // Otros cambios que se perderian, ya dichos en palabras (p. ej. «la obra nueva»).
  extras: readonly string[];
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
// pregunta nueva deja sin efecto la anterior (que resuelve false: nadie navega por ella).
export function confirmarSalida(motivo: MotivoSalida, extras: readonly string[] = []): Promise<boolean> {
  const pantallas = formulariosSucios();
  if (pantallas.length === 0 && extras.length === 0) return Promise.resolve(true);
  return new Promise<boolean>((resolver) => {
    const anterior = pendiente;
    numero += 1;
    pendiente = { numero, motivo, pantallas, extras: [...extras], resolver };
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
