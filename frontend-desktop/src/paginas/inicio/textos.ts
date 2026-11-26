// Los textos de Inicio › Resumen en un solo lugar (español llano, trato de usted, sin exclamaciones; cifras en es-VE).
import type { MonedaDeLaCartera } from "../../api/tipos";
import { centesimasEsVe, fechaEsVe, formatoEsVe } from "../../indicadores/formatoEsVe";

const cifra = (n: number) => formatoEsVe(String(n));

export function resumirTituloDeCartera(porMoneda: readonly MonedaDeLaCartera[] | null, totalObras: number | null): string {
  if (porMoneda === null || totalObras === null) return "Vista general";
  if (totalObras === 0 && porMoneda.length === 0) return "Sin obras en la cartera";
  if (porMoneda.length === 1) {
    const unica = porMoneda[0]!;
    const sustantivo = unica.obras === 1 ? "obra" : "obras";
    return `${cifra(unica.obras)} ${sustantivo} por ${centesimasEsVe(unica.total)} ${unica.moneda}`;
  }
  const sustantivo = totalObras === 1 ? "obra" : "obras";
  const montos = porMoneda.map((m) => `${centesimasEsVe(m.total)} ${m.moneda}`).join(" y ");
  return `${cifra(totalObras)} ${sustantivo} por ${montos}`;
}

export const TEXTOS = {
  tituloPorOmision: "Vista general",
  sobre: (hoyIso: string | null) => (hoyIso ? `Vista general · corte al ${fechaEsVe(hoyIso)}` : "Vista general"),
  subtitulo: "Presupuesto vigente frente a lo ejecutado por obra, problemas abiertos y datos cargados en la empresa",
  enEjecucion: (n: number) => (n === 1 ? "1 obra en ejecución" : `${cifra(n)} obras en ejecución`),
  sinProblemasAbiertos: "Sin problemas abiertos",
  cartera: {
    titulo: "La cartera de obras",
    ayudaTitulo: "Cómo se calcula el total",
    ayuda:
      "El total de cada obra es el de su línea base o, sin ella, el de su versión vigente. Cada moneda se suma por separado: Bs y USD nunca se mezclan.",
    cargando: "Cargando la cartera",
    error: "No se pudo leer la cartera",
    noDisponible: "La cartera aún no está disponible en esta instalación",
    noDisponibleQueHacer: "Pídale a quien administra Sílice que actualice el programa; mientras tanto, esta parte no se puede mostrar.",
    moneda: (moneda: string) => `Cartera en ${moneda}`,
    tituloDeMoneda: (moneda: string, total: string) => `Obras en ${moneda} · ${centesimasEsVe(total)} ${moneda}`,
    ejeMoneda: (moneda: string) => (moneda === "Bs" ? "Bolívares (Bs)" : moneda === "USD" ? "Dólares (USD)" : moneda),
    leyendaPresupuesto: "Presupuesto de la obra",
    leyendaEjecutado: "Ejecutado (avance físico)",
    verComoTabla: "Ver como tabla",
    tabla: (moneda: string) => `Presupuesto, avance y problemas abiertos de las obras en ${moneda}`,
    desplazar: (moneda: string) => `Obras de la cartera en ${moneda}: desplazar horizontalmente`,
    pieCartera: "Cartera",
    queMuestra:
      "Qué muestra: para cada obra, su presupuesto vigente (o de línea base) y la parte física ya ejecutada. Qué leer: la barra azul representa cuánto del presupuesto ya se ejecutó; cada moneda mantiene su propia escala y nunca se mezcla con otra.",
    omitidas: (n: number) =>
      n === 1
        ? "No se pudo leer 1 carpeta; sus obras no aparecen en la cartera."
        : `No se pudieron leer ${cifra(n)} carpetas; sus obras no aparecen en la cartera.`,
    vacio: {
      puedeCrear: {
        titulo: "Aún no hay obras",
        descripcion: "Cree la primera obra para armar su presupuesto y seguir su avance.",
        boton: "Crear la primera obra",
      },
      soloRevisa: {
        titulo: "No hay obras que su cuenta pueda ver",
        descripcion: "Cuando haya una obra registrada en las carpetas a las que tiene acceso, aparecerá aquí.",
      },
    },
  },
  avance: {
    titulo: "Avance de la cartera",
    etapasAria: "Obras de la cartera por etapa",
    verComoTabla: "Ver como tabla",
    tabla: "Obras de la cartera y su avance contra el plan",
    desplazar: "Obras de la cartera y su avance contra el plan: desplazar horizontalmente",
    obra: "Obra",
    estado: "Estado",
    presupuesto: (moneda: string) => `Presupuesto (${moneda})`,
    total: "Total",
    avance: "Avance ejecutado vs. plan",
    avanceReal: "Avance real",
    avancePlan: "Planificado",
    problemas: "Problemas abiertos",
    sinAvance: "Sin avance",
    sinVersion: "Sin versión",
    ningunProblema: "Ninguno",
    // Espacios duros (U+00A0) dentro de «Real 67,0 %» y de «Plan 76,7 %»: con letra Muy grande el «%» no cae solo.
    real: (real: string, plan: string) => `Real\u00a0${real}\u00a0% · Plan\u00a0${plan}\u00a0%`,
    ejecutadoPct: (real: string) => `${real}\u00a0%`,
    queMuestra:
      "Qué muestra: cuántas obras están en cada etapa y cómo va el avance físico real frente al planificado en las obras con seguimiento. Qué leer: cuando el avance real queda por debajo del planificado, la obra lleva atraso.",
  },
  bloquea: {
    titulo: "Problemas abiertos por obra",
    cargando: "Cargando los problemas abiertos",
    error: "No se pudieron leer los pendientes",
    ninguno: "Ninguna obra tiene problemas abiertos hoy.",
    tabla: "Problemas abiertos de cada obra, con su gravedad",
    suman: (resumen: string) => `Suman ${resumen}. Una obra con problemas que bloquean no puede cerrar su aprobación.`,
    irALaBandeja: (n: number) => `Ir a la bandeja de pendientes (${cifra(n)})`,
  },
  cargado: {
    titulo: "Lo que hay cargado",
    libros: {
      etiqueta: "Libros auditados",
      error: "No se pudo leer el historial de auditorías",
      sinDatos: "Sin libros auditados todavía",
      ir: "Ir a Auditoría",
    },
    lista: {
      etiqueta: "Lista de precios vigente",
      error: "No se pudo leer la lista de la carpeta",
      sinLista: "Sin lista vigente",
      sinDatos: "No hay lista de precios vigente en esta carpeta",
      ir: "Ver precios",
    },
    partidas: {
      etiqueta: "Partidas del catálogo",
      error: "No se pudieron leer las partidas del catálogo",
      sinDatos: "Sin partidas guardadas en esta carpeta",
      ir: "Ver el catálogo",
    },
    insumos: {
      etiqueta: "Insumos del catálogo",
      error: "No se pudieron leer los insumos del catálogo",
      sinDatos: "Sin insumos guardados en esta carpeta",
      todosVigentes: "Todos con precio vigente",
      ir: "Ver los insumos",
    },
    produccion: {
      etiqueta: "Producción de la arenera",
      error: "No se pudo leer la arenera",
      sinMateriales: "Aún no hay materiales registrados",
      todoBien: "Todo sobre el mínimo",
      ir: "Ver todas las existencias",
    },
  },
  auditorias: {
    titulo: "Últimas auditorías",
    ir: "Ir a Auditoría",
    // El vacío de «Últimas auditorías» cuando se usa desde vista-general.
    vacioEnLaVistaGeneral: "Para auditar un presupuesto, vaya a Auditoría: el resumen y los hallazgos quedarán aquí.",
  },
} as const;
