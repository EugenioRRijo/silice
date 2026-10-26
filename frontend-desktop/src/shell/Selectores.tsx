import type { ProyectoRespuesta } from "../api/tipos";

// Rotulos de la carpeta de trabajo y de la obra (plan de modulos, MOD-3b). Los selectores «Carpeta de trabajo» y
// «Proyecto» de la barra se retiraron: los reemplazan el selector de obra (`SelectorObra`) y el dialogo de carpetas.

// La carpeta de trabajo (el caso en la API) se muestra sin la extension de la base de datos.
export function nombreDeCarpeta(nombre: string): string {
  return nombre.endsWith(".db") ? nombre.slice(0, -3) : nombre;
}

// La obra (el proyecto en la API) se elige por su nombre: el codigo es un numero interno y solo se agrega si dos obras se
// llaman igual (VB-20). Una obra sin version guardada lo dice (BCP-6 §5.2, F11), salvo en el boton de la barra, que
// solo nombra la obra (`conVersion` falso).
export function rotuloDeProyecto(p: ProyectoRespuesta, todos: readonly ProyectoRespuesta[], conVersion = true): string {
  const nombre = todos.filter((q) => q.nombre === p.nombre).length > 1 ? `${p.nombre} (${p.codigo})` : p.nombre;
  return conVersion && p.version_vigente === null ? `${nombre} (sin versión guardada)` : nombre;
}
