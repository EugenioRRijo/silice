import { InlineLoading, InlineNotification } from "@carbon/react";
import { useRef, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { DescargaArchivo } from "../../comun/DescargaArchivo";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import { TablaDensa } from "../../comun/TablaDensa";
import { COLUMNAS_HALLAZGOS } from "./logica";
import { Dato } from "./piezas";
import type { ExcelExterno } from "./tipos";

type Estado =
  | { tipo: "ninguno" }
  | { tipo: "auditando" }
  | { tipo: "error"; error: unknown }
  | { tipo: "listo"; resultado: ExcelExterno };

// Pestaña «Presupuesto en Excel» (UC-05; ui/paginas/revisar.py `_excel_externo`): la plantilla del formato y un
// presupuesto de otra herramienta auditado en memoria. Nada se guarda; siempre «no verificado».
export function PestanaExcelExterno({ alExpirar }: { alExpirar: () => void }) {
  const [estado, setEstado] = useState<Estado>({ tipo: "ninguno" });
  const consulta = useRef(0);

  async function auditar(archivo: File) {
    const numero = ++consulta.current;
    setEstado({ tipo: "auditando" });
    const cuerpo = new FormData();
    cuerpo.append("presupuesto", archivo);
    try {
      const resultado = await pedir<ExcelExterno>("/v1/revision/excel-externo", { metodo: "POST", cuerpo });
      if (numero === consulta.current) setEstado({ tipo: "listo", resultado });
    } catch (error) {
      if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
      if (numero === consulta.current) setEstado({ tipo: "error", error });
    }
  }

  return (
    <div className="silice-revisar__pestana">
      <DescargaArchivo
        ruta="/v1/revision/plantilla"
        etiqueta="Descargar la plantilla del formato"
        nombrePorOmision="plantilla-presupuesto.xlsx"
        alExpirar={alExpirar}
        size="sm"
      />
      <SubidaArchivo
        id="revisar-excel"
        etiqueta="Suelte aquí el presupuesto en Excel (.xlsx), o haga clic para elegirlo"
        extensiones={[".xlsx"]}
        deshabilitada={estado.tipo === "auditando"}
        alElegir={(archivo) => void auditar(archivo)}
      />
      {estado.tipo === "auditando" && <InlineLoading description="Auditando el presupuesto…" />}
      {estado.tipo === "error" && <AvisoError error={estado.error} titulo="No se pudo auditar el presupuesto" />}
      {estado.tipo === "listo" && (
        <>
          <InlineNotification kind="warning" title="" subtitle={estado.resultado.aviso} lowContrast hideCloseButton />
          <dl className="silice-revisar__datos">
            <Dato rotulo="Total" texto={estado.resultado.total_texto} exacto={estado.resultado.total} />
          </dl>
          <TablaDensa
            etiqueta="Hallazgos del presupuesto en Excel"
            columnas={COLUMNAS_HALLAZGOS}
            filas={estado.resultado.hallazgos.map((h, i) => ({ id: String(i), ...h }))}
            vacio={{ titulo: "Sin hallazgos." }}
          />
        </>
      )}
    </div>
  );
}
