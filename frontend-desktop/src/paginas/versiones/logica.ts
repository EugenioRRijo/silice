// Lógica pura de la sección Versiones (Tarea 6 del plan F4). Por qué existe: la tabla junta tres lecturas (las versiones
// del proveedor de la Hoja, el estado de aprobación de cada una y cuál está abierta) y la franja decide un solo paso; aquí
// se combinan sin pintar nada, para probarlas sin montar la pantalla. La interfaz no calcula: solo junta lo que da la API.
import type { EstadoDeAprobacion } from "../../comun/aprobacion";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { versionesOfrecidas } from "../hoja/logica";
import type { VersionFila, VersionesRespuesta } from "../hoja/logica";
import { TEXTOS_DEL_PASO } from "../hoja/textos";

export interface FilaDeVersion extends VersionFila {
  // La clave del estado de aprobación (`guardada`, `en_aprobacion`, `devuelta`…), o null si no se pudo leer.
  estado: string | null;
  abierta: boolean;
  // Si se ofrece «Abrir»: no en una descartada, salvo que todas lo estén (`versionesOfrecidas`, la regla del proveedor).
  seAbre: boolean;
}

// Todo el historial de la obra, porque solo crece (RF-54): también las descartadas, que siguen guardadas, se pueden mirar y
// restaurar (restaurar es la única manera de deshacer un descarte) y la cadena de sellos puede romperse en una de ellas. La
// descartada lleva `descartada` (la tabla lo dice con la palabra) y no se abre: abrirla pediría una versión que el proveedor
// cambiaría por otra sin decirlo. Cada fila lleva su estado de aprobación y la marca de la abierta.
export function filasDeVersiones(
  v: VersionesRespuesta,
  estados: Record<string, EstadoDeAprobacion> | null,
  abierta: string | null,
): FilaDeVersion[] {
  const ofrecidas = new Set(versionesOfrecidas(v.versiones).map((f) => f.codigo));
  return v.versiones.map((f) => ({
    ...f,
    estado: estados?.[f.codigo]?.estado ?? null,
    abierta: abierta !== null && f.codigo === abierta,
    seAbre: ofrecidas.has(f.codigo),
  }));
}

// E2E-3: la columna «Motivo» decía la clave del servidor («edicion», «elaborada»). Ahora dice cómo se creó, con tilde, y
// lo que escribió quien la guardó: «Edición: Acta de obra 3». Una clave que no se conoce se muestra tal cual.
const MOTIVOS: Record<string, string> = {
  "": "Elaborada",
  edicion: "Edición",
  restauracion: "Restauración",
  cotizacion: "Cotización",
  revaloracion: "Revaloración",
  conversion: "Conversión",
  recuperacion: "Recuperación",
};

export function motivoDeVersion(f: Pick<VersionFila, "motivo" | "fuente">): string {
  const tipo = MOTIVOS[f.motivo] ?? f.motivo;
  const fuente = (f.fuente ?? "").trim();
  return fuente === "" ? tipo : `${tipo}: ${fuente}`;
}

export interface PasoDeVersiones {
  texto: string;
  // «guardar» abre «Guardar versión»; null, la franja solo informa.
  accion: "guardar" | null;
}

// La franja de Versiones: con cambios sin guardar, guardarlos (el botón, solo si se puede guardar); si no, con la vigente en
// aprobación, que espera dictamen. Los textos son los de la franja del Presupuesto (`TEXTOS_DEL_PASO`).
export function pasoDeVersiones(e: { cambios: number; puedeGuardar: boolean; filas: FilaDeVersion[] }): PasoDeVersiones | null {
  if (e.cambios > 0) {
    return { texto: TEXTOS_DEL_PASO.sinGuardar(formatoEsVe(String(e.cambios)), e.cambios === 1), accion: e.puedeGuardar ? "guardar" : null };
  }
  const vigente = e.filas.find((f) => f.vigente);
  if (vigente?.estado === "en_aprobacion") return { texto: TEXTOS_DEL_PASO.enAprobacion(vigente.codigo), accion: null };
  return null;
}
