// Los textos de la bandeja de Pendientes en un solo lugar (especificación, §6.4 «textos como datos»). Los fijos del plan
// de F3 (vacío y carpetas omitidas) van tal cual. Los números se escriben en es-VE (punto de miles).
import { formatoEsVe } from "../../indicadores/formatoEsVe";

const cifra = (n: number) => formatoEsVe(String(n));

export const TEXTOS = {
  titulo: "Pendientes",
  // Lo usa también la barra lateral (nombre accesible de Pendientes y de cada obra).
  porHacer: (n: number) => `${cifra(n)} por hacer`,
  // «2 bloquean · 2 avisos»: las mismas palabras que la urgencia de cada fila; un grupo en cero no se nombra.
  resumen: (bloquea: number, aviso: number) =>
    [
      bloquea > 0 ? (bloquea === 1 ? "1 bloquea" : `${cifra(bloquea)} bloquean`) : null,
      aviso > 0 ? (aviso === 1 ? "1 aviso" : `${cifra(aviso)} avisos`) : null,
    ]
      .filter((parte) => parte !== null)
      .join(" · "),
  lista: "Pendientes por hacer",
  detalle: "Detalle del pendiente",
  obra: "Obra",
  urgencia: "Urgencia",
  urgencias: { bloquea: "Bloquea", aviso: "Aviso" },
  cargando: "Cargando los pendientes",
  error: "No se pudieron leer los pendientes",
  reintentar: "Reintentar",
  vacio: "No tiene pendientes.",
  vacioExplica: "Cuando una obra necesite algo de usted, aparecerá aquí.",
  omitidas: (n: number) =>
    n === 1 ? "No se pudo leer 1 carpeta; sus pendientes no aparecen." : `No se pudieron leer ${cifra(n)} carpetas; sus pendientes no aparecen.`,
  sinPermiso: "Su cuenta no puede dar este paso.",
} as const;
