// Las tres peticiones que fijan la carpeta y la obra de la sesion en el servidor, en un solo lugar: las usan el armazon
// de hoy (shell/carpetas/useCarpetaDeTrabajo, shell/Shell) y el ruteo por obra del marco (marco/useObraDeLaRuta).
// Solo piden: preguntar antes de salir, avisar y recargar es cosa de quien las llama.
import { pedir } from "./cliente";
import type { CasoRespuesta } from "./tipos";

// `POST /v1/casos/actual`. Devuelve la carpeta que quedo abierta; si la API no la informa, la pedida.
export async function abrirCarpeta(nombre: string): Promise<CasoRespuesta> {
  const r = await pedir<Partial<CasoRespuesta> | null>("/v1/casos/actual", { metodo: "POST", cuerpo: { nombre } });
  return { nombre: typeof r?.nombre === "string" ? r.nombre : nombre, ruta_relativa: r?.ruta_relativa ?? "" };
}

// `DELETE /v1/casos/actual`: vuelve a la carpeta de la empresa (tambien olvida los borradores de la Hoja de la sesion).
export function volverALaCarpetaDeLaEmpresa(): Promise<CasoRespuesta> {
  return pedir<CasoRespuesta>("/v1/casos/actual", { metodo: "DELETE" });
}

// `PUT /v1/sesion/proyecto`: la obra (su `codigo`, el id como texto; null = ninguna) que la cuenta deja elegida.
export function recordarObra(codigo: string | null): Promise<void> {
  return pedir<void>("/v1/sesion/proyecto", { metodo: "PUT", cuerpo: { proyecto: codigo } });
}
