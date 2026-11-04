// La ruta a la que lleva cada pantalla (plan F6, Tarea 1). Quien enlaza a una pantalla (recorridos guiados, buscador,
// pendientes, botones de las pantallas) pide aquí su ruta y no la escribe: cuando las pantallas cambien de sitio (T4 y T5)
// se cambia este lugar y quien llama no se entera. Hoy devuelve la ruta que ya abre cada pantalla.
import { PAGINAS, paginaPorId, rutaDe } from "../shell/rutas";
import { ENTRADAS_DE_EMPRESA, RUTA_DE_PENDIENTES, SECCIONES_DE_OBRA, rutaDeEmpresa, rutaDeObra } from "./secciones";

export interface ObraDeLaRuta {
  carpeta: string | null;
  obraId: number;
}

// `paginaId` es el id de la pantalla en `shell/rutas.ts`. Una sección de obra va a la ruta de la obra dada; sin obra, a su
// dirección corta (`/<id>`), que redirige a la obra de la sesión. Una entrada de Empresa va a `/empresa/<entrada>`. Las
// demás, a `/<id>`. Un id que no es pantalla da null.
export function rutaCanonica(paginaId: string, obra?: ObraDeLaRuta): string | null {
  const pagina = paginaPorId(paginaId, PAGINAS);
  if (pagina === undefined) return null;
  const seccion = SECCIONES_DE_OBRA.find((s) => s.pagina === paginaId);
  if (seccion !== undefined && obra !== undefined) return rutaDeObra(obra.carpeta, obra.obraId, seccion.id);
  if (seccion !== undefined) return rutaDe(pagina);
  const entrada = ENTRADAS_DE_EMPRESA.find((e) => e.pagina === paginaId);
  if (entrada !== undefined) return rutaDeEmpresa(entrada.id);
  return rutaDe(pagina);
}

// Para los enlaces cuya pantalla es una constante del código: si el id no existiera, el enlace no queda muerto, lleva a
// Pendientes (la prueba de `rutaCanonica` y la de cada enlace vigilan que no pase).
export function rutaOPendientes(paginaId: string, obra?: ObraDeLaRuta): string {
  return rutaCanonica(paginaId, obra) ?? RUTA_DE_PENDIENTES;
}
