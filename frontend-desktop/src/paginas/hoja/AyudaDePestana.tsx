import type { JSX } from "react";
import { QueEsEsto } from "../../comun/QueEsEsto";
import { AYUDA_CIFRAS } from "../../indicadores/cifraEscrita";
import { PESTANAS } from "./logica";
import type { PestanaId } from "./logica";
import { AYUDAS } from "./textos";

// Por qué existe (Tarea 4 del plan F4): las siete pestañas con ayuda la pintan igual, tras «¿Qué es esto?» y con el título
// de su pestaña como nombre de la región. Evita repetir en cada una el reparto entre lo que ve todo el mundo y lo que solo
// sirve a quien edita. `delServidor` es lo que la vista trae consigo (Espacio). Desde la Tarea 5 (menor de la 4, decisión
// 8), cómo se escriben las cifras (coma decimal) queda a la vista para quien edita: es lo que más se confunde al escribir y
// no debe esconderse tras un clic. Quien revisa no escribe cifras y no la ve.
export function AyudaDePestana({
  id,
  puedeEditar,
  delServidor,
  extra = [],
}: {
  id: PestanaId;
  puedeEditar: boolean;
  delServidor?: string;
  // Párrafos que la vista añade al final (Tarea 5b: la fuente de la alícuota del IVA, que llega del servidor).
  extra?: string[];
}): JSX.Element {
  const ayuda = AYUDAS[id];
  const parrafos: string[] = [delServidor ?? ayuda.general, puedeEditar ? ayuda.alEditar : "", ...extra].filter((t) => t !== "");
  const titulo = PESTANAS.find((p) => p.id === id)!.titulo;
  return (
    <>
      <QueEsEsto titulo={titulo}>
        {parrafos.map((t, i) => (
          <p key={i}>{t}</p>
        ))}
      </QueEsEsto>
      {puedeEditar && ayuda.cifras && <p className="cds--type-helper-text-01">{AYUDA_CIFRAS}</p>}
    </>
  );
}
