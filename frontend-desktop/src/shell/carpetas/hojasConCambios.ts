import { ErrorDeApi, pedir } from "../../api/cliente";
import type { ProyectoRespuesta } from "../../api/tipos";

// «Hoja de {obra}» por cada borrador de esta sesion con cambios (`GET /v1/hoja/borradores`): lo que se perderia al
// cambiar de carpeta (`caso_web.olvidar`). Un 403 o un fallo cuentan como ninguno (no se puede saber); un 401 sigue hacia
// arriba (la sesion vencio). Lo comparten el cambio de carpeta del armazon y «Nueva obra» en otra carpeta.
export async function hojasConCambios(obras: readonly Pick<ProyectoRespuesta, "codigo" | "nombre">[] | null | undefined): Promise<string[]> {
  try {
    const r = await pedir<{ borradores?: { proyecto: string; cambios: number }[] }>("/v1/hoja/borradores");
    const lista = Array.isArray(r?.borradores) ? r.borradores : [];
    const nombre = (p: string) => obras?.find((o) => o.codigo === p || o.nombre === p)?.nombre ?? p;
    return [...new Set(lista.filter((b) => b.cambios > 0).map((b) => `Hoja de ${nombre(b.proyecto)}`))];
  } catch (e) {
    if (e instanceof ErrorDeApi && e.estado === 401) throw e;
    return [];
  }
}
