import { unidadEscrita } from "../../comun/unidades";

// N4 de la tanda: ¿lo que hay en un campo de la cabecera es lo mismo que pone la partida del catálogo, a ojos del
// servidor? La descripción se compara sin los espacios de borde y la unidad, además, sin mayúsculas y por la grafía con que
// la pantalla la escribe (`unidadEscrita`: «m3» se lee «m³», «dia» se lee «día»), como `motivo_para_no_reemplazar`
// (`aplicacion/composicion.py`, que usa `unidades_equivalentes` del núcleo). La tabla completa de alias vive solo en el
// núcleo (NORMAS §2.1): una grafía que la pantalla no escribe distinto («mts» frente a «m») sigue dando el aviso, que
// solo informa.
function unidadComparable(unidad: string): string {
  const limpia = unidad.trim().toLowerCase();
  return unidadEscrita(limpia);
}

export function mismoDatoDeCabecera(campo: "descripcion" | "unidad", actual: string, nuevo: string): boolean {
  if (campo === "descripcion") return actual.trim() === nuevo.trim();
  return unidadComparable(actual) === unidadComparable(nuevo);
}
