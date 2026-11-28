// Modelo y funciones puras de las notificaciones (lote C11, cara «Papel y resaltador»).

export type GravedadDeNotificacion = "listo" | "info" | "advertencia" | "error";

export interface EnlaceDeNotificacion {
  texto: string;
  ruta: string;
}

export interface Notificacion {
  id: string;
  gravedad: GravedadDeNotificacion;
  titulo: string;
  detalle?: string;
  enlace?: EnlaceDeNotificacion;
  creada: string;
  leida: boolean;
}

export interface NuevaNotificacion {
  id?: string;
  gravedad: GravedadDeNotificacion;
  titulo: string;
  detalle?: string;
  enlace?: EnlaceDeNotificacion;
  creada?: string;
  leida?: boolean;
}

export interface GrupoDeNotificaciones {
  etiqueta: string;
  items: Notificacion[];
}

export const DURACION_CONFIRMACION_MS = 180_000;
export const DIAS_DE_RETENCION = 30;

const RETENCION_MS = DIAS_DE_RETENCION * 24 * 60 * 60 * 1_000;
const MS_POR_DIA = 86_400_000;
const FECHA_SOLA_ISO = /^(\d{4})-(\d{2})-(\d{2})$/;

const PALABRA_DE_GRAVEDAD: Readonly<Record<GravedadDeNotificacion, string>> = {
  listo: "Listo",
  info: "Información",
  advertencia: "Advertencia",
  error: "Error",
};

export function gravedadEnPalabra(gravedad: GravedadDeNotificacion): string {
  return PALABRA_DE_GRAVEDAD[gravedad];
}

export function duracionDeNotificacion(gravedad: GravedadDeNotificacion): number | null {
  if (gravedad === "listo" || gravedad === "info") return DURACION_CONFIRMACION_MS;
  return null;
}

export function contarSinLeer(lista: readonly Notificacion[]): number {
  let total = 0;
  for (const item of lista) {
    if (!item.leida) total += 1;
  }
  return total;
}

export function marcarTodasComoLeidas(lista: readonly Notificacion[]): Notificacion[] {
  return lista.map((item) => (item.leida ? item : { ...item, leida: true }));
}

function instanteDe(iso: string): number {
  const soloFecha = FECHA_SOLA_ISO.exec(iso.trim());
  if (soloFecha) {
    return new Date(Number(soloFecha[1]), Number(soloFecha[2]) - 1, Number(soloFecha[3])).getTime();
  }
  return Date.parse(iso);
}

export function descartarVencidas(lista: readonly Notificacion[], ahora: Date = new Date()): Notificacion[] {
  const limite = ahora.getTime() - RETENCION_MS;
  return lista.filter((item) => {
    const t = instanteDe(item.creada);
    return Number.isFinite(t) && t >= limite;
  });
}

function partesDeDiaLocal(iso: string): { anio: number; mes: number; dia: number; indiceDia: number } | null {
  const soloFecha = FECHA_SOLA_ISO.exec(iso.trim());
  if (soloFecha) {
    const anio = Number(soloFecha[1]);
    const mes = Number(soloFecha[2]) - 1;
    const dia = Number(soloFecha[3]);
    return { anio, mes, dia, indiceDia: Math.floor(Date.UTC(anio, mes, dia) / MS_POR_DIA) };
  }
  const fecha = new Date(iso);
  if (Number.isNaN(fecha.getTime())) return null;
  const anio = fecha.getFullYear();
  const mes = fecha.getMonth();
  const dia = fecha.getDate();
  return { anio, mes, dia, indiceDia: Math.floor(Date.UTC(anio, mes, dia) / MS_POR_DIA) };
}

function etiquetaDeGrupo(iso: string, indiceHoy: number): string {
  const partes = partesDeDiaLocal(iso);
  if (partes === null) return iso;
  const diferencia = indiceHoy - partes.indiceDia;
  if (diferencia === 0) return "Hoy";
  if (diferencia === 1) return "Ayer";
  const dd = String(partes.dia).padStart(2, "0");
  const mm = String(partes.mes + 1).padStart(2, "0");
  const aaaa = String(partes.anio).padStart(4, "0");
  return `${dd}/${mm}/${aaaa}`;
}

export function ordenarPorFechaDescendente(lista: readonly Notificacion[]): Notificacion[] {
  return [...lista].sort((a, b) => instanteDe(b.creada) - instanteDe(a.creada));
}

export function agruparPorDia(
  lista: readonly Notificacion[],
  ahora: Date = new Date(),
): GrupoDeNotificaciones[] {
  const indiceHoy = Math.floor(
    Date.UTC(ahora.getFullYear(), ahora.getMonth(), ahora.getDate()) / MS_POR_DIA,
  );
  const ordenadas = ordenarPorFechaDescendente(lista);
  const grupos: GrupoDeNotificaciones[] = [];
  const porEtiqueta = new Map<string, GrupoDeNotificaciones>();

  for (const item of ordenadas) {
    const etiqueta = etiquetaDeGrupo(item.creada, indiceHoy);
    let grupo = porEtiqueta.get(etiqueta);
    if (grupo === undefined) {
      grupo = { etiqueta, items: [] };
      porEtiqueta.set(etiqueta, grupo);
      grupos.push(grupo);
    }
    grupo.items.push(item);
  }
  return grupos;
}

export function horaDeNotificacion(iso: string): string {
  if (FECHA_SOLA_ISO.test(iso.trim())) return "";
  const fecha = new Date(iso);
  if (Number.isNaN(fecha.getTime())) return "";
  const hh = String(fecha.getHours()).padStart(2, "0");
  const min = String(fecha.getMinutes()).padStart(2, "0");
  return `${hh}:${min}`;
}

function limpiarPuntoFinal(texto: string): string {
  return texto.trim().replace(/\.+$/, "");
}

// Arma el anuncio de lector de pantalla sin nombrar el botón Cerrar; si trae enlace añade «Acción disponible.».
export function textoDeAnuncio(
  notificacion: Pick<Notificacion, "gravedad" | "titulo" | "detalle" | "enlace">,
): string {
  const cabeza = `${gravedadEnPalabra(notificacion.gravedad)}: ${limpiarPuntoFinal(notificacion.titulo)}`;
  const partes = [cabeza];
  if (notificacion.detalle !== undefined && notificacion.detalle.trim() !== "") {
    partes.push(limpiarPuntoFinal(notificacion.detalle));
  }
  if (notificacion.enlace !== undefined) {
    return `${partes.join(". ")}. Acción disponible.`;
  }
  const cuerpo = partes.join(". ");
  return notificacion.detalle?.trim().endsWith(".") ? `${cuerpo}.` : cuerpo;
}

export function instanteActual(reloj?: () => Date): Date {
  return reloj ? reloj() : new Date();
}

export function hayDialogoModalAbierto(): boolean {
  if (typeof document === "undefined") return false;
  if (document.querySelector('[role="dialog"][aria-modal="true"], [role="alertdialog"][aria-modal="true"]') !== null) {
    return true;
  }
  const soportaPseudoModal =
    typeof window !== "undefined" && Boolean(window.CSS?.supports?.("selector(:modal)"));
  if (soportaPseudoModal) {
    return document.querySelector("dialog:modal") !== null;
  }
  return document.querySelector("dialog[open]") !== null;
}
