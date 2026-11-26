import {
  Add,
  Calculator,
  Catalog,
  ChartLine,
  Dashboard,
  Document,
  DocumentView,
  Folder,
  Home,
  Industry,
  Meter,
  Policy,
  Renew,
  Roadmap,
  Send,
  Table,
  Task,
  Time,
  Upload,
  WarningAlt,
} from "@carbon/icons-react";
import type { CarbonIconType } from "@carbon/icons-react";

// La barra lateral «riel de iconos» (cara «Papel y resaltador»): lo que no es dibujo. Puro y sin React, probado aparte.

// La barra reducida se recuerda en una sola clave, la del marco (`silice_sidebar_collapsed`, useWorkspaceLayout): aquí no hay almacenamiento.

// Los iconos de 16 px de cada opción, los de `iconos.json` de la especificación en su equivalente de Carbon
// (tabla, calculadora, ruta, subir, línea, alerta, firma, medidor, ciclo, escudo, ramas, reloj, enviar, carpeta…).
const ICONOS: Readonly<Record<string, CarbonIconType>> = {
  "vista-general": Dashboard,
  "nueva-obra": Add,
  carpeta: Folder,
  resumen: Home,
  presupuesto: Table,
  componer: Calculator,
  tramos: Roadmap,
  archivos: Upload,
  mercado: ChartLine,
  problemas: WarningAlt,
  aprobaciones: Task,
  control: Meter,
  reajuste: Renew,
  riesgo: Policy,
  versiones: Time,
  entregar: Send,
  // Los tres espacios de «Costos y producción».
  auditoria: DocumentView,
  precios: Catalog,
  produccion: Industry,
};

// Un id que no se conoce lleva el icono de documento: nunca queda una opción sin icono.
export function iconoDeOpcion(id: string): CarbonIconType {
  return ICONOS[id] ?? Document;
}
