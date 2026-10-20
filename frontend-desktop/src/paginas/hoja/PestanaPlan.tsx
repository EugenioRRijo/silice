import { CurvaPlanAvance, periodoLegible } from "../../comun/CurvaPlanAvance";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { Cifra } from "./Cifra";
import { TablaPaginada } from "./TablaPaginada";
import { VistaCarga } from "./VistaCarga";
import { rutaDeVista } from "./logica";
import type { VistaPlan } from "./logica";

interface Props {
  id: string;
  alAusente: () => void;
}

function ContenidoPlan({ vista }: { vista: VistaPlan }) {
  if (!vista.hay_plan) return <p className="cds--type-body-compact-01">{vista.mensaje}</p>;
  return (
    <div className="silice-hoja__pestana">
      <p className="cds--type-body-compact-01">
        Cada partida se reparte entre los períodos y cada fila suma 1. Los montos, los acumulados y los porcentajes se
        calculan.
      </p>
      <TablaPaginada
        etiqueta="Plan de trabajo"
        desplazable
        columnas={[
          { clave: "partida", titulo: "Partida", ordenable: false },
          ...vista.etiquetas.map((e, i) => ({
            clave: `e${i}`,
            titulo: periodoLegible(e),
            numerica: true,
            ordenable: false,
            presentar: formatoEsVe,
          })),
        ]}
        filas={vista.filas.map((f, i) => ({
          id: `plan-${i}`,
          partida: f.partida,
          ...Object.fromEntries(vista.etiquetas.map((e, j) => [`e${j}`, f.valores[e] ?? ""])),
        }))}
      />
      <section className="silice-hoja__seccion">
        <h2 className="cds--type-heading-compact-02">Curva de inversión</h2>
        <CurvaPlanAvance
          titulo="Curva de inversión"
          unidad={vista.moneda}
          series={[
            {
              nombre: "Acumulado",
              rol: "plan",
              puntos: vista.curva.map((p) => ({ periodo: p.periodo, valor: p.acumulado.texto })),
            },
          ]}
        />
        <TablaPaginada
          etiqueta="Curva de inversión: montos"
          columnas={[
            { clave: "periodo", titulo: "Período", ordenable: false },
            {
              clave: "monto",
              titulo: "Monto",
              numerica: true,
              ordenable: false,
              celda: (f) => <Cifra monto={{ texto: f.monto!, exacto: f.monto_exacto! }} />,
            },
            {
              clave: "acumulado",
              titulo: "Acumulado",
              numerica: true,
              ordenable: false,
              celda: (f) => <Cifra monto={{ texto: f.acumulado!, exacto: f.acumulado_exacto! }} />,
            },
            {
              clave: "porcentaje",
              titulo: "% acumulado",
              numerica: true,
              ordenable: false,
              celda: (f) => <Cifra monto={{ texto: f.porcentaje!, exacto: f.porcentaje_exacto! }} />,
            },
          ]}
          filas={vista.curva.map((p, i) => ({
            id: `curva-${i}`,
            periodo: periodoLegible(p.periodo),
            monto: p.monto.texto,
            monto_exacto: p.monto.exacto,
            acumulado: p.acumulado.texto,
            acumulado_exacto: p.acumulado.exacto,
            porcentaje: p.porcentaje.texto,
            porcentaje_exacto: p.porcentaje.exacto,
          }))}
        />
      </section>
    </div>
  );
}

// Pestaña «Plan y curva» en lectura (crear el plan secuencial y editar el reparto llegan en la rebanada 3c).
export function PestanaPlan({ id, alAusente }: Props) {
  return (
    <VistaCarga<VistaPlan> ruta={rutaDeVista(id, "plan")} etiqueta="Plan y curva" alAusente={alAusente}>
      {(vista) => <ContenidoPlan vista={vista} />}
    </VistaCarga>
  );
}
