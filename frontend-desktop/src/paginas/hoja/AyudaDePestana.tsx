import type { JSX, ReactNode } from "react";
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
//
// Con `herramientas` (cabecera compacta, 2026-11-05) la ayuda forma una barra de una sola fila con lo que la pestaña pone
// sobre su tabla: las herramientas (p. ej. «Agregar partida»), el aviso de las cifras y «¿Qué es esto?», en ese orden de
// lectura y de tabulación. Envuelve con letra grande y, abierto, el panel de la ayuda queda bajo la fila (`hoja.scss`).
// `herramientas={null}` pide la barra sin herramientas (quien solo revisa).
export function AyudaDePestana({
  id,
  puedeEditar,
  delServidor,
  extra = [],
  herramientas,
}: {
  id: PestanaId;
  puedeEditar: boolean;
  delServidor?: string;
  // Párrafos que la vista añade al final (Tarea 5b: la fuente de la alícuota del IVA, que llega del servidor).
  extra?: string[];
  herramientas?: ReactNode;
}): JSX.Element {
  const ayuda = AYUDAS[id];
  const parrafos: string[] = [delServidor ?? ayuda.general, puedeEditar ? ayuda.alEditar : "", ...extra].filter((t) => t !== "");
  const titulo = PESTANAS.find((p) => p.id === id)!.titulo;
  const queEsEsto = (
    <QueEsEsto titulo={titulo}>
      {parrafos.map((t, i) => (
        <p key={i}>{t}</p>
      ))}
    </QueEsEsto>
  );
  const cifras = puedeEditar && ayuda.cifras && <p className="silice-hoja__herramientas-aviso cds--type-helper-text-01">{AYUDA_CIFRAS}</p>;
  if (herramientas !== undefined) {
    return (
      <div role="group" aria-label={`Herramientas de ${titulo}`} className="silice-hoja__herramientas">
        {herramientas}
        {cifras}
        {queEsEsto}
      </div>
    );
  }
  return (
    <>
      {queEsEsto}
      {puedeEditar && ayuda.cifras && <p className="cds--type-helper-text-01">{AYUDA_CIFRAS}</p>}
    </>
  );
}
