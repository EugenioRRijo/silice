import { DescargaArchivo } from "../../comun/DescargaArchivo";
import { useAplicacion } from "../../shell/contexto";
import { NOMBRE_PDF_POR_OMISION, rutaDelPdf } from "./logicaPdf";

// «Descargar PDF» (RF-213): el servidor arma el PDF del borrador vivo (encabezado, partidas, subtotal, IVA, total y un APU
// por página) y propone el nombre. La interfaz no calcula ni formatea nada del PDF. Terciario, como «Descargar Excel».
export function BotonPdf({ id }: { id: string }) {
  const { alExpirar } = useAplicacion();
  return (
    <DescargaArchivo
      ruta={rutaDelPdf(id)}
      etiqueta="Descargar PDF"
      nombrePorOmision={NOMBRE_PDF_POR_OMISION}
      alExpirar={alExpirar}
      kind="tertiary"
      size="md"
    />
  );
}
