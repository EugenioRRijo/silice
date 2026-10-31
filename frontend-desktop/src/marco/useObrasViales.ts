import { useContext, useEffect, useState } from "react";
import { obrasConTramos } from "../api/vial";
import { claveDeObra } from "../paginas/pendientes/logica";
import { ContextoAplicacion } from "../shell/contexto";

const NINGUNA: ReadonlySet<string> = new Set();

// Las obras de la carpeta abierta que ya tienen tramos viales guardados (`GET /v1/vial/obras`), como claves
// «carpeta|obra» (las del marco). Es lo que decide si una obra ofrece la sección «Tramos». `refresco` es cualquier valor
// que, al cambiar (otra obra, otra sección), vuelve a leer la lista. Sin `editar_hoja` no se pide (la API daría 403) y
// un fallo no avisa: la sección simplemente no se ofrece, y la pantalla sigue alcanzable por el buscador.
export function useObrasViales(carpetaActual: string | null, refresco: string): ReadonlySet<string> {
  const puedeEditar = useContext(ContextoAplicacion)?.sesion.acciones.includes("editar_hoja") ?? false;
  const [leidas, setLeidas] = useState<{ carpeta: string | null; ids: number[] } | null>(null);

  useEffect(() => {
    if (!puedeEditar) return;
    let vigente = true;
    obrasConTramos().then(
      (r) => {
        if (vigente && Array.isArray(r?.obras)) setLeidas({ carpeta: carpetaActual, ids: r.obras });
      },
      () => undefined,
    );
    return () => {
      vigente = false;
    };
  }, [puedeEditar, carpetaActual, refresco]);

  if (!puedeEditar || leidas === null || leidas.carpeta !== carpetaActual) return NINGUNA;
  return new Set(leidas.ids.map((id) => claveDeObra(carpetaActual, id)));
}
