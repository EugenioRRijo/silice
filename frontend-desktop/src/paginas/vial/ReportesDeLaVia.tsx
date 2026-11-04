import { DescargaArchivo } from "../../comun/DescargaArchivo";

// Los reportes de la vía en Excel (`GET /v1/vial/reportes/{tipo}`): el servidor arma cada libro con una portada que dice
// de dónde sale cada cifra y propone el nombre del archivo. La pantalla solo pide el de la obra y la versión que se ven.
export const REPORTES_DE_LA_VIA = [
  { tipo: "computos", etiqueta: "Cómputos por tramo" },
  { tipo: "apu", etiqueta: "APU con origen y conciliación" },
  { tipo: "resumen", etiqueta: "Resumen con IVA" },
] as const;

export function rutaDeReporteVial(tipo: string, proyecto: string, version: string): string {
  const consulta = new URLSearchParams({ proyecto, version });
  return `/v1/vial/reportes/${encodeURIComponent(tipo)}?${consulta.toString()}`;
}

interface Props {
  proyecto: string;
  version: string;
  alExpirar: () => void;
}

export function ReportesDeLaVia({ proyecto, version, alExpirar }: Props) {
  return (
    <section aria-label="Reportes de la vía" className="vial-reportes">
      <h2 className="cds--type-heading-compact-02">Reportes en Excel</h2>
      <p className="vial-nota cds--type-body-compact-01">
        Cada libro empieza con una portada que dice de dónde sale cada cifra.
      </p>
      <div className="vial-reportes__botones">
        {REPORTES_DE_LA_VIA.map((r) => (
          <DescargaArchivo
            key={r.tipo}
            ruta={rutaDeReporteVial(r.tipo, proyecto, version)}
            etiqueta={r.etiqueta}
            nombrePorOmision={`${r.tipo}.xlsx`}
            alExpirar={alExpirar}
            kind="tertiary"
            size="sm"
          />
        ))}
      </div>
    </section>
  );
}
