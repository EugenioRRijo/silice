import type { JSX } from "react";
import { QueEsEsto } from "../../comun/QueEsEsto";
import { PESTANAS } from "./logica";
import type { PestanaId } from "./logica";
import { AYUDAS } from "./textos";

// Por qué existe (Tarea 4 del plan F4): las siete pestañas con ayuda la pintan igual, tras «¿Qué es esto?» y con el título
// de su pestaña como nombre de la región. Evita repetir en cada una el reparto entre lo que ve todo el mundo y lo que solo
// sirve a quien edita. `delServidor` es lo que la vista trae consigo (Espacio).
export function AyudaDePestana({
  id,
  puedeEditar,
  delServidor,
}: {
  id: Exclude<PestanaId, "trazabilidad">;
  puedeEditar: boolean;
  delServidor?: string;
}): JSX.Element {
  const ayuda = AYUDAS[id];
  const parrafos: string[] = [delServidor ?? ayuda.general, puedeEditar ? ayuda.alEditar : ""].filter((t) => t !== "");
  const titulo = PESTANAS.find((p) => p.id === id)!.titulo;
  return (
    <QueEsEsto titulo={titulo}>
      {parrafos.map((t, i) => (
        <p key={i}>{t}</p>
      ))}
    </QueEsEsto>
  );
}
