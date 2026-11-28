// Las herramientas de una obra en la barra del lugar (especificación 2026-11-26, «Cara Papel y resaltador»): Presupuestar,
// Auditar y Anticipar agrupan las secciones de hoy sin cambiar ninguna ruta (contrato de rutas del 2026-11-04). La
// portada es el Resumen (y su Tablero); Versiones no es una herramienta: se llega por el menú de versión. Lógica pura.
import { SUBVISTAS } from "./espacios";
import { rutaDeObra } from "./secciones";
import type { SeccionId } from "./secciones";

export type HerramientaDeObra = "presupuestar" | "auditar" | "anticipar";
export type Herramienta = HerramientaDeObra | "portada" | "versiones";

export interface HerramientaDef {
  id: HerramientaDeObra;
  titulo: string;
  // En el orden en que se ofrecen; la primera es a la que lleva la herramienta.
  secciones: readonly SeccionId[];
}

export const HERRAMIENTAS_DE_OBRA: readonly HerramientaDef[] = [
  { id: "presupuestar", titulo: "Presupuestar", secciones: ["presupuesto", "tramos", "archivos", "mercado"] },
  { id: "auditar", titulo: "Auditar", secciones: ["aprobaciones"] },
  { id: "anticipar", titulo: "Anticipar", secciones: ["control", "riesgo"] },
];

// Las subvistas (Componer, Espacio plan y ajustes, Actualizar, Revisar, Entregar, Reajuste, Escenarios, Tablero) siguen a su sección: no cambian de
// herramienta. `subvista` queda en la firma para quien la tiene a mano.
export function herramientaDe(seccion: SeccionId, subvista?: string): Herramienta {
  void subvista;
  const propia = HERRAMIENTAS_DE_OBRA.find((h) => h.secciones.includes(seccion));
  if (propia !== undefined) return propia.id;
  return seccion === "versiones" ? "versiones" : "portada";
}

// La ruta a la que lleva una herramienta: la de su primera sección. `usables` (opcional) son las secciones que la cuenta
// puede usar: se salta las que no; sin ninguna, null.
export function primeraRutaDe(
  herramienta: Herramienta,
  carpeta: string | null,
  obraId: number,
  usables?: readonly SeccionId[],
): string | null {
  const secciones: readonly SeccionId[] =
    herramienta === "portada"
      ? ["resumen"]
      : herramienta === "versiones"
        ? ["versiones"]
        : (HERRAMIENTAS_DE_OBRA.find((h) => h.id === herramienta)?.secciones ?? []);
  const primera = secciones.find((s) => usables === undefined || usables.includes(s));
  return primera === undefined ? null : rutaDeObra(carpeta, obraId, primera);
}

// La segunda fila de la barra de la obra: las opciones de la herramienta activa, como pestañas secundarias. Cada una es una
// sección y, a veces, una subvista (contrato de rutas 2.1); ninguna ruta es nueva. `subvista` vacío es la pantalla principal.
export interface OpcionDeObra {
  id: string;
  titulo: string;
  seccion: SeccionId;
  subvista: string;
}

export type HerramientaConOpciones = HerramientaDeObra | "portada";

export const OPCIONES_DE_HERRAMIENTA: Record<HerramientaConOpciones, readonly OpcionDeObra[]> = {
  portada: [
    { id: "resumen", titulo: "Resumen", seccion: "resumen", subvista: "" },
    { id: "tablero", titulo: "Tablero", seccion: "resumen", subvista: "tablero" },
  ],
  presupuestar: [
    { id: "partidas", titulo: "Partidas", seccion: "presupuesto", subvista: "" },
    { id: "componer", titulo: "Componer un APU", seccion: "presupuesto", subvista: "componer" },
    // B1-10: las pestañas de antes (espacio, APU, plan, precios y ajustes), a un clic de la superficie.
    { id: "pestanas", titulo: "Espacio, plan y ajustes", seccion: "presupuesto", subvista: "pestanas" },
    { id: "tramos", titulo: "Tramos de la vía", seccion: "tramos", subvista: "" },
    { id: "archivos", titulo: "Plano o cómputo", seccion: "archivos", subvista: "" },
    { id: "mercado", titulo: "Precios de mercado", seccion: "mercado", subvista: "" },
  ],
  auditar: [
    { id: "aprobar", titulo: "Aprobar", seccion: "aprobaciones", subvista: "" },
    { id: "revisar", titulo: "Revisar un paquete", seccion: "aprobaciones", subvista: "revisar" },
    { id: "entregar", titulo: "Entregar", seccion: "aprobaciones", subvista: "entregar" },
  ],
  anticipar: [
    { id: "control", titulo: "Control de obra", seccion: "control", subvista: "" },
    { id: "reajuste", titulo: "Reajuste de precios", seccion: "control", subvista: "reajuste" },
    { id: "escenarios", titulo: "Escenarios", seccion: "control", subvista: "escenarios" },
    { id: "riesgo", titulo: "Riesgo", seccion: "riesgo", subvista: "" },
  ],
};

export function rutaDeOpcion(opcion: OpcionDeObra, carpeta: string | null, obraId: number): string {
  return rutaDeObra(carpeta, obraId, opcion.seccion, opcion.subvista || undefined);
}

// La opción que está abierta: la de la sección y subvista exactas; si la subvista no tiene opción propia (Actualizar
// precios, dentro de Mercado), la principal de esa sección; en Versiones, ninguna.
export function opcionActual(herramienta: Herramienta, seccion: SeccionId, subvista?: string): OpcionDeObra | undefined {
  if (herramienta === "versiones") return undefined;
  const opciones = OPCIONES_DE_HERRAMIENTA[herramienta];
  const sub = subvista ?? "";
  return opciones.find((o) => o.seccion === seccion && o.subvista === sub) ?? opciones.find((o) => o.seccion === seccion && o.subvista === "");
}

// Una sección conserva su barra de subvistas («Vistas de …») solo si alguna de sus subvistas no es una opción de la
// segunda fila de la obra (hoy, Mercado › Actualizar precios); si todas lo son, esa barra repetiría la segunda fila.
export function seccionConSubvistasPropias(seccion: SeccionId): boolean {
  const opciones = Object.values(OPCIONES_DE_HERRAMIENTA).flat();
  return (SUBVISTAS[seccion] ?? []).some((v) => !opciones.some((o) => o.seccion === seccion && o.subvista === v.id));
}
