// Los textos de la Vista general en un solo lugar (español llano; los números van en es-VE, con punto de miles).
import { formatoEsVe } from "../../indicadores/formatoEsVe";

const cifra = (n: number) => formatoEsVe(String(n));

export const TEXTOS = {
  titulo: "Vista general",
  bloquea: {
    titulo: "Lo que requiere atención",
    cargando: "Cargando lo que requiere atención",
    error: "No se pudieron leer los pendientes",
    ninguno: "No tiene pendientes por hacer.",
    lista: "Lo que requiere atención, de lo más urgente a lo menos",
    irALaBandeja: (n: number) => `Ir a la bandeja de pendientes (${cifra(n)})`,
  },
  cartera: {
    titulo: "Cartera por moneda",
    cargando: "Cargando la cartera",
    error: "No se pudo leer la cartera",
    noDisponible: "La cartera aún no está disponible en esta instalación",
    moneda: (moneda: string) => `Cartera en ${moneda}`,
    tituloDeMoneda: (moneda: string) => `Obras en ${moneda}`,
    cifras: (moneda: string) => `Cifras de la cartera en ${moneda}`,
    total: "Total vigente",
    obras: "Obras",
    enEjecucion: "En ejecución",
    omitidas: (n: number) =>
      n === 1 ? "No se pudo leer 1 carpeta; sus obras no aparecen en la cartera." : `No se pudieron leer ${cifra(n)} carpetas; sus obras no aparecen en la cartera.`,
    vacio: {
      puedeCrear: { titulo: "Aún no hay obras", descripcion: "Cree la primera obra para armar su presupuesto y seguir su avance.", boton: "Nueva obra" },
      soloRevisa: {
        titulo: "No hay obras en esta carpeta",
        descripcion: "Cuando haya una obra registrada en las carpetas a las que tiene acceso, aparecerá aquí.",
      },
    },
  },
  avance: {
    titulo: "Obras y avance contra el plan",
    tabla: "Obras de la cartera y su avance contra el plan",
    obra: "Obra",
    estado: "Estado",
    total: "Total",
    avance: "Avance ejecutado vs. plan",
    sinAvance: "Sin avance",
    sinVersion: "Sin versión",
    real: (real: string, plan: string) => `Real ${real} % · Plan ${plan} %`,
  },
  auditorias: { titulo: "Últimas auditorías", ir: "Ir a Auditoría" },
} as const;
