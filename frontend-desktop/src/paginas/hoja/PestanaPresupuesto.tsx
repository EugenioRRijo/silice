import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { Cifra } from "./Cifra";
import { EstadoDeFila } from "./EstadoDeFila";
import { TablaPaginada } from "./TablaPaginada";
import { VistaCarga } from "./VistaCarga";
import { clavesDeAuditoria, rotuloDeOrigen, rutaDeVista } from "./logica";
import type { VistaPresupuesto } from "./logica";

interface Props {
  id: string;
  alAusente: () => void;
}

const PENDIENTE = "Pendiente";

function ContenidoPresupuesto({ vista }: { vista: VistaPresupuesto }) {
  if (vista.vacio_mensaje !== null) return <p className="cds--type-body-compact-01">{vista.vacio_mensaje}</p>;
  return (
    <div className="silice-hoja__pestana">
      <p className="cds--type-body-compact-01">
        Las cantidades salen del espacio y los precios de la composición de cada partida. Una cantidad escrita a mano se
        marca en el Estado.
      </p>
      <TablaPaginada
        etiqueta="Presupuesto"
        desplazable
        columnas={[
          { clave: "partida", titulo: "Partida", ordenable: false },
          { clave: "descripcion", titulo: "Descripción", ordenable: false },
          { clave: "unidad", titulo: "Unidad", ordenable: false },
          { clave: "cantidad", titulo: "Cantidad", numerica: true, ordenable: false },
          {
            clave: "pu",
            titulo: "Precio unitario",
            numerica: true,
            ordenable: false,
            celda: (f) => (f.pu_texto === "" ? PENDIENTE : <Cifra monto={{ texto: f.pu_texto!, exacto: f.pu_exacto! }} />),
          },
          {
            clave: "total",
            titulo: "Total",
            numerica: true,
            ordenable: false,
            celda: (f) =>
              f.total_texto === "" ? PENDIENTE : <Cifra monto={{ texto: f.total_texto!, exacto: f.total_exacto! }} />,
          },
          {
            clave: "estado",
            titulo: "Estado",
            ordenable: false,
            celda: (f) => (
              <EstadoDeFila
                estado={{ severidad: f.estado_severidad === "" ? null : f.estado_severidad!, texto: f.estado_texto! }}
                claves={clavesDeAuditoria(f.clave!)}
                rotulo={rotuloDeOrigen(f.clave!)}
              />
            ),
          },
        ]}
        filas={vista.filas.map((f, i) => ({
          id: `renglon-${i}`,
          clave: f.clave,
          partida: f.partida,
          descripcion: f.descripcion,
          unidad: f.unidad,
          cantidad: f.escrita
            ? `${formatoEsVe(f.cantidad)} (calculada: ${formatoEsVe(f.cantidad_calculada)})`
            : formatoEsVe(f.cantidad),
          pu_texto: f.pu?.texto ?? "",
          pu_exacto: f.pu?.exacto ?? "",
          total_texto: f.total?.texto ?? "",
          total_exacto: f.total?.exacto ?? "",
          estado_severidad: f.estado.severidad ?? "",
          estado_texto: f.estado.texto,
        }))}
      />
      <p className="silice-hoja__total cds--type-heading-03">
        Total del presupuesto <Cifra monto={vista.total} unidad={vista.moneda} />
      </p>
    </div>
  );
}

// Pestaña «Presupuesto» en lectura (la cantidad editable llega en la rebanada 3c).
export function PestanaPresupuesto({ id, alAusente }: Props) {
  return (
    <VistaCarga<VistaPresupuesto> ruta={rutaDeVista(id, "presupuesto")} etiqueta="Presupuesto" alAusente={alAusente}>
      {(vista) => <ContenidoPresupuesto vista={vista} />}
    </VistaCarga>
  );
}
