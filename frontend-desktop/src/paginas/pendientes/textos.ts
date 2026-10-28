// Los textos de la bandeja de Pendientes en un solo lugar (especificación, §6.4 «textos como datos»). Los fijos del plan
// de F3 (vacío y carpetas omitidas) van tal cual.
export const TEXTOS = {
  titulo: "Pendientes",
  porHacer: (n: number) => `${n} por hacer`,
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
    n === 1 ? "No se pudo leer 1 carpeta; sus pendientes no aparecen." : `No se pudieron leer ${n} carpetas; sus pendientes no aparecen.`,
  sinPermiso: "Su cuenta no puede dar este paso.",
} as const;
