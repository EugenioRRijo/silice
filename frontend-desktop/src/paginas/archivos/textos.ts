// Los textos de «Archivos y planos» (Tarea 11 del plan F4), con las palabras de quien arma el presupuesto. Los del flujo
// del plano siguen en `logicaPlano.ts` y los del cómputo en `logicaComputo.ts`, que los comparten con sus pruebas.
export const TEXTOS = {
  titulo: "Archivos y planos",
  subir: "Subir plano o cómputo",
  // Con la especialidad «edificación» apagada no hay planos: la misma puerta solo carga el cómputo (Tarea 12).
  cargarComputo: "Cargar cómputo",
  // Va tras «Te falta:» en la franja (pregunta abierta 3 del plan: solo si se pidió describir el espacio y sigue vacío).
  falta: "subir el plano o describir el espacio",
  registro: "Registro de importaciones",
  vacio: "Todavía no se ha importado ningún archivo en esta obra.",
  falloDelRegistro: "No se pudo leer el registro de importaciones",
  verInforme: (archivo: string) => `Ver el informe de ${archivo}`,
  informe: (archivo: string) => `Informe de la importación de ${archivo}`,
  // Lo que el panel aclara: el informe completo es el del diálogo, mientras se importa.
  informeGuardado: "Es el resumen que guardó el registro. El informe detallado se ve al importar el archivo.",
  describir: "Describir el espacio a mano",
  // Con borradores sin guardar que esperan una decisión (retomarlos o descartarlos), no se abre ninguno aquí.
  conOfertas: "Esta obra tiene cambios sin guardar que esperan su decisión. Retómelos o descártelos en Presupuesto para subir un archivo.",
  irAPresupuesto: "Ir a Presupuesto",
  borradorAusente: "El borrador ya no está",
  falloDelBorrador: "No se pudo abrir el borrador",
  abrirDeNuevo: "Abrir de nuevo",
  sinObra: "Elija una obra",
  cerrar: "Cerrar",
} as const;

// El enlace que deja la pestaña «Espacio y metrajes» donde estaba el bloque del plano.
export const ENLACE_DESDE_EL_ESPACIO = "Importar un plano en Archivos y planos";
