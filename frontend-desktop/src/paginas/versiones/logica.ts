// Lógica pura de la sección Versiones (Tarea 6 del plan F4). Por qué existe: la tabla junta tres lecturas (las versiones
// del proveedor de la Hoja, el estado de aprobación de cada una y cuál está abierta) y la franja decide un solo paso; aquí
// se combinan sin pintar nada, para probarlas sin montar la pantalla. La interfaz no calcula: solo junta lo que da la API.
import type { EstadoDeAprobacion } from "../../comun/aprobacion";
import { extraerPersona } from "../../comun/responsable";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { versionesOfrecidas } from "../hoja/logica";
import type { VersionFila, VersionesRespuesta } from "../hoja/logica";
import { TEXTOS_DEL_PASO } from "../hoja/textos";

export interface VersionConPersona extends VersionFila {
  // Si el servidor envía quién guardó la versión (`Nombre <login>` o solo nombre).
  responsable?: string | null;
  usuario?: string | null;
}

export interface FilaDeVersion extends VersionConPersona {
  // La clave del estado de aprobación (`guardada`, `en_aprobacion`, `devuelta`…), o null si no se pudo leer.
  estado: string | null;
  // Quién realizó el último movimiento de aprobación (`Nombre <login>`), si existe.
  por?: string | null;
  abierta: boolean;
  // Si se ofrece «Abrir»: no en una descartada, salvo que todas lo estén (`versionesOfrecidas`, la regla del proveedor).
  seAbre: boolean;
}


export interface OpcionDePersona {
  clave: string;
  nombre: string;
  etiqueta: string;
}

export { extraerPersona, type PersonaExtraida } from "../../comun/responsable";
import type { PersonaExtraida } from "../../comun/responsable";

export function personasDeVersion(fila: Pick<FilaDeVersion, "por" | "responsable" | "usuario">): PersonaExtraida[] {
  const lista: PersonaExtraida[] = [];
  const autor = extraerPersona(fila.responsable, fila.usuario);
  if (autor !== null) lista.push(autor);
  const por = extraerPersona(fila.por);
  if (por !== null && !lista.some((p) => p.clave === por.clave)) lista.push(por);
  return lista;
}

// Personas únicas presentes en las versiones ya cargadas, ordenadas por nombre para el filtro «Por persona».
export function listarPersonasDeVersiones(
  filas: readonly Pick<FilaDeVersion, "por" | "responsable" | "usuario">[],
): OpcionDePersona[] {
  const porClave = new Map<string, PersonaExtraida>();
  for (const fila of filas) {
    for (const p of personasDeVersion(fila)) {
      if (!porClave.has(p.clave)) porClave.set(p.clave, p);
    }
  }
  const unicas = [...porClave.values()].sort((a, b) => a.nombre.localeCompare(b.nombre, "es"));
  const conteos = new Map<string, number>();
  for (const p of unicas) conteos.set(p.nombre, (conteos.get(p.nombre) ?? 0) + 1);
  return unicas.map((p) => ({
    clave: p.clave,
    nombre: p.nombre,
    etiqueta: (conteos.get(p.nombre) ?? 0) > 1 && p.usuario !== null ? `${p.nombre} (${p.usuario})` : p.nombre,
  }));
}

export function filtrarVersionesPorPersona(filas: readonly FilaDeVersion[], clavePersona: string): FilaDeVersion[] {
  if (clavePersona === "") return [...filas];
  return filas.filter((f) => personasDeVersion(f).some((p) => p.clave === clavePersona));
}

export function textoDeConteoDeVersiones(visibles: number, total: number): string {
  const unidad = total === 1 ? "versión" : "versiones";
  return `${formatoEsVe(String(visibles))} de ${formatoEsVe(String(total))} ${unidad}`;
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
  return v.versiones.map((f) => {
    const aprobacion = estados?.[f.codigo];
    const por = aprobacion?.por ?? null;
    return {
      ...f,
      estado: aprobacion?.estado ?? null,
      ...(por !== null ? { por } : {}),
      abierta: abierta !== null && f.codigo === abierta,
      seAbre: ofrecidas.has(f.codigo),
    };
  });
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
