// Lógica pura del botón «Descargar Excel» (rebanada 3e-1, ruta X1 del diseño §4.1).
import { RUTA_DE_BORRADORES } from "./logicaRetomar";

// Nombre de respaldo si el servidor no manda Content-Disposition (lo normal es que lo mande: hoja_{código}.xlsx).
export const NOMBRE_POR_OMISION = "hoja_borrador.xlsx";

// X1: `GET /v1/hoja/borradores/{id}/excel`. El id viene del servidor, pero se codifica igual.
export function rutaDelExcel(id: string): string {
  return `${RUTA_DE_BORRADORES}/${encodeURIComponent(id)}/excel`;
}
