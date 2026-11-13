// Los textos de la sección Versiones (Tarea 6 del plan F4), en un solo lugar como los del Presupuesto (`hoja/textos.ts`).
// Por qué existe: la pantalla, la tabla, el aviso de la cadena y el panel los comparten, y las pruebas los fijan.

export const TEXTOS_DE_VERSIONES = {
  titulo: "Versiones",
  tabla: "Versiones de la obra",
  sinVersiones: "Esta obra aún no tiene versiones guardadas.",
  sinVersionesDescripcion:
    "La primera versión se guarda desde «Presupuesto», con «Guardar primera versión…», cuando la obra ya tiene partidas.",
  sinEstados: "No se pudo leer el estado de aprobación de las versiones.",
  abierta: "abierta",
  descartada: "descartada",
  vigente: "Sí",
  columnas: {
    version: "Versión",
    fecha: "Fecha",
    motivo: "Motivo",
    origen: "Sale de",
    cambios: "Cambios",
    estado: "Estado de aprobación",
    vigente: "Vigente",
    acciones: "Acciones",
  },
  abrir: "Abrir",
  abrirLa: (codigo: string) => `Abrir ${codigo}`,
  verCambios: "Ver cambios",
  verCambiosDe: (codigo: string) => `Ver cambios de ${codigo}`,
  registro: (codigo: string) => `Registro de cambios de la versión ${codigo}`,
  cadena: "Cadena de sellos",
  integra: "Integridad verificada",
  rota: (codigo: string | null) => (codigo === null ? "Se rompió la cadena de sellos" : `Se rompió en la versión ${codigo}`),
} as const;
