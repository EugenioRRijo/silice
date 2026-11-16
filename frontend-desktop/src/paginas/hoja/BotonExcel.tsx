import { DescargaArchivo } from "../../comun/DescargaArchivo";
import { useAplicacion } from "../../shell/contexto";
import { BotonPdf } from "./BotonPdf";
import { NOMBRE_POR_OMISION, rutaDelExcel } from "./logicaExcel";
import "./excel.scss";

// «Descargar Excel» (3e-1): el servidor arma el libro del borrador vivo y propone el nombre (Content-Disposition). Si no se
// puede preparar, el aviso trae el detalle de la API tal cual («No se pudo preparar el Excel: …»). Va en la franja de acciones
// del Presupuesto, junto al botón del paso (`FranjaDelPresupuesto`): terciario, nunca el principal. En el mismo grupo va
// «Descargar PDF» (RF-213, `BotonPdf`), después del Excel.
export function BotonExcel({ id }: { id: string }) {
  const { alExpirar } = useAplicacion();
  return (
    <div className="silice-hoja__acciones" role="group" aria-label="Exportar la hoja">
      <DescargaArchivo
        ruta={rutaDelExcel(id)}
        etiqueta="Descargar Excel"
        nombrePorOmision={NOMBRE_POR_OMISION}
        alExpirar={alExpirar}
        kind="tertiary"
        size="md"
      />
      <BotonPdf id={id} />
    </div>
  );
}
