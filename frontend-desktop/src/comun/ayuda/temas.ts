import { rutaDeCuenta } from "../../marco/espacios";

// Cada parte de la Ayuda se puede enlazar (`#/cuenta/ayuda?tema=…`): el «¿Qué es esto?» de una pantalla lleva a su guía o a
// un término del glosario, y «Empieza aquí» a sus guías. Con el enrutador de hash no sirve un ancla (`#glosario` cambiaría
// la ruta), así que la Ayuda lee `tema` y pasa el foco al elemento `ayuda-<tema>`. Los recorridos guiados ya tienen el suyo
// (`ayuda-recorridos`, en `marco/RecorridosGuiados.tsx`).
export function rutaDeTema(tema: string): string {
  return `${rutaDeCuenta("ayuda")}?tema=${tema}`;
}

export function idDeTema(tema: string): string {
  return `ayuda-${tema}`;
}
