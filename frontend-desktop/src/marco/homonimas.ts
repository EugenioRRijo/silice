import { claveDeObra } from "../paginas/pendientes/logica";

interface ObraConCarpeta {
  carpeta: string | null;
  obra_id: number;
  obra: string;
  carpeta_titulo: string;
}

// D-F3-3: el árbol y la bandeja no agrupan por carpeta; solo cuando dos obras se llaman igual en carpetas distintas hace
// falta decir de cuál es cada una. Devuelve, por clave (carpeta y número, la de `claveDeObra`), el título de la carpeta
// de las obras que comparten nombre con otra de otra carpeta; las demás no salen. Compara sin mayúsculas, sin espacios de
// más y con la misma forma Unicode (NFC). Dos del mismo nombre en una misma carpeta no se marcan: la carpeta no las distinguiría.
export function obrasConMismoNombre(obras: readonly ObraConCarpeta[]): Map<string, string> {
  const porNombre = new Map<string, ObraConCarpeta[]>();
  for (const o of obras) {
    const nombre = o.obra.normalize("NFC").trim().replace(/\s+/g, " ").toLocaleLowerCase("es");
    porNombre.set(nombre, [...(porNombre.get(nombre) ?? []), o]);
  }
  const marcadas = new Map<string, string>();
  for (const grupo of porNombre.values()) {
    if (new Set(grupo.map((o) => o.carpeta)).size < 2) continue;
    for (const o of grupo) marcadas.set(claveDeObra(o.carpeta, o.obra_id), o.carpeta_titulo);
  }
  return marcadas;
}
