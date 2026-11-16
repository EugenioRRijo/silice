// Lógica pura del botón «Descargar PDF» (RF-213, ola 2, línea 4, 2026-11-13).
import { RUTA_DE_BORRADORES } from "./logicaRetomar";

// Nombre de respaldo si el servidor no manda Content-Disposition (lo normal: presupuesto_{código}.pdf).
export const NOMBRE_PDF_POR_OMISION = "presupuesto_borrador.pdf";
// Nombre de respaldo al bajar el PDF de un solo APU desde la pestaña APU.
export const NOMBRE_PDF_APU_POR_OMISION = "apu_borrador.pdf";

// `GET /v1/hoja/borradores/{id}/pdf`: el presupuesto del borrador vivo y un APU por página. El id viene del servidor,
// pero se codifica igual. Con `partida`, pide solo ese APU (`?partida=…`).
export function rutaDelPdf(id: string, partida?: string): string {
  const base = `${RUTA_DE_BORRADORES}/${encodeURIComponent(id)}/pdf`;
  return partida ? `${base}?partida=${encodeURIComponent(partida)}` : base;
}
