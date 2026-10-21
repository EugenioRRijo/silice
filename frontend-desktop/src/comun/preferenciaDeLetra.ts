// Tamaño de letra por presbicia (Eugenio, 2026-10-21). Tres tamaños que escalan la raíz del documento: todo el CSS propio y
// el de Carbon van en rem, así que texto, controles y espacios crecen juntos (como el zoom del navegador, que se respeta
// porque la raíz se expresa en porcentaje del tamaño del navegador).
//
// Es una preferencia de pantalla, no un dato de la obra: se guarda en localStorage (única excepción a RT-9, que protege
// libros, contraseñas y borradores). El almacenamiento puede faltar o lanzar (ventana privada, datos bloqueados): toda
// lectura y escritura va en try/catch y, sin él, la interfaz funciona con el tamaño normal.

export type TamanoDeLetra = "normal" | "grande" | "muy-grande";

export interface OpcionDeLetra {
  valor: TamanoDeLetra;
  rotulo: string;
  // Factor sobre el tamaño base de la raíz (116,6667 %: el cuerpo de 14 px de Carbon pasa a 16 px).
  escala: number;
}

export const TAMANOS_DE_LETRA: readonly OpcionDeLetra[] = [
  { valor: "normal", rotulo: "Normal", escala: 1 },
  { valor: "grande", rotulo: "Grande", escala: 1.25 },
  { valor: "muy-grande", rotulo: "Muy grande", escala: 1.5 },
];

export const CLAVE_TAMANO_LETRA = "silice.tamano-letra";
export const VARIABLE_ESCALA_LETRA = "--silice-escala-letra";

export function leerTamanoLetra(): TamanoDeLetra {
  try {
    const guardado = window.localStorage.getItem(CLAVE_TAMANO_LETRA);
    return TAMANOS_DE_LETRA.find((t) => t.valor === guardado)?.valor ?? "normal";
  } catch {
    return "normal";
  }
}

// El tamano que de verdad se ve: el que `aplicarTamanoLetra` dejo en la raiz (main.tsx lo fija antes de pintar y cada
// eleccion lo actualiza). Sin el, el guardado. Asi, con el almacenamiento bloqueado, el control que se monta despues
// (pantalla de entrada y luego shell) marca lo que se ve y no vuelve a «Normal».
export function tamanoAplicado(): TamanoDeLetra {
  const puesto = document.documentElement.dataset.siliceLetra;
  return TAMANOS_DE_LETRA.find((t) => t.valor === puesto)?.valor ?? leerTamanoLetra();
}

export function guardarTamanoLetra(tamano: TamanoDeLetra): void {
  try {
    window.localStorage.setItem(CLAVE_TAMANO_LETRA, tamano);
  } catch {
    // Sin almacenamiento la elección vale para esta pantalla y no se recuerda.
  }
}

// Fija la variable CSS de la raíz (la que lee `html { font-size }`) y marca el tamaño en un atributo para los ajustes de
// diseño que dependen de la escala.
export function aplicarTamanoLetra(tamano: TamanoDeLetra): void {
  const opcion = TAMANOS_DE_LETRA.find((t) => t.valor === tamano) ?? TAMANOS_DE_LETRA[0];
  const raiz = document.documentElement;
  raiz.style.setProperty(VARIABLE_ESCALA_LETRA, String(opcion.escala));
  raiz.dataset.siliceLetra = opcion.valor;
}
