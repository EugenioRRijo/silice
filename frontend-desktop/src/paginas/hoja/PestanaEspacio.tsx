import { TablaPaginada } from "./TablaPaginada";
import type { ColumnaDensa } from "../../comun/TablaDensa";
import { Cifra } from "./Cifra";
import { EstadoDeFila } from "./EstadoDeFila";
import { VistaCarga } from "./VistaCarga";
import { filasDeTabla, rotuloDeOrigen, rutaDeVista, textoDeFilas } from "./logica";
import type { TablaEspacio, VistaEspacio } from "./logica";

interface Props {
  id: string;
  alAusente: () => void;
}

function TablaDelEspacio({ tabla, vista }: { tabla: TablaEspacio; vista: VistaEspacio }) {
  const filas = vista.filas[tabla.clave] ?? [];
  const columnas: ColumnaDensa[] = tabla.columnas.map((c) => ({ clave: `c_${c.clave}`, titulo: c.rotulo, ordenable: false }));
  if (tabla.con_estado) {
    columnas.push({
      clave: "estado",
      titulo: "Estado",
      ordenable: false,
      celda: (f) => (
        <EstadoDeFila
          estado={{ severidad: f.estado_severidad === "" ? null : f.estado_severidad!, texto: f.estado_texto! }}
          claves={f.estado_origen ? [f.estado_origen] : undefined}
          rotulo={f.estado_origen ? rotuloDeOrigen(f.estado_origen) : undefined}
        />
      ),
    });
  }
  return (
    <section className="silice-hoja__seccion">
      <div className="silice-hoja__titulo-tabla">
        <h3 className="cds--type-heading-compact-01">{tabla.rotulo}</h3>
        <span className="cds--type-helper-text-01">{textoDeFilas(filas.length)}</span>
      </div>
      <TablaPaginada
        etiqueta={tabla.rotulo}
        columnas={columnas}
        filas={filasDeTabla(tabla, filas, vista.estado)}
        vacio={{ titulo: "Sin filas" }}
        desplazable
      />
    </section>
  );
}

function ContenidoEspacio({ vista }: { vista: VistaEspacio }) {
  return (
    <div className="silice-hoja__pestana">
      <p className="cds--type-body-compact-01">{vista.ayuda}</p>
      {vista.tablas.map((t) => (
        <TablaDelEspacio key={t.clave} tabla={t} vista={vista} />
      ))}
      <section className="silice-hoja__seccion">
        <h2 className="cds--type-heading-compact-02">Cantidades derivadas</h2>
        {vista.vacio_mensaje !== null ? (
          <p className="cds--type-body-compact-01">{vista.vacio_mensaje}</p>
        ) : (
          <TablaPaginada
            etiqueta="Cantidades derivadas"
            desplazable
            columnas={[
              { clave: "partida", titulo: "Partida", ordenable: false },
              { clave: "descripcion", titulo: "Descripción", ordenable: false },
              { clave: "unidad", titulo: "Unidad", ordenable: false },
              {
                clave: "cantidad",
                titulo: "Cantidad",
                numerica: true,
                ordenable: false,
                celda: (f) => <Cifra monto={{ texto: f.cantidad!, exacto: f.cantidad_exacto! }} />,
              },
              { clave: "origen", titulo: "Origen", ordenable: false },
            ]}
            filas={vista.derivadas.map((d, i) => ({
              id: `derivada-${i}`,
              partida: d.partida,
              descripcion: d.descripcion,
              unidad: d.unidad,
              cantidad: d.cantidad.texto,
              cantidad_exacto: d.cantidad.exacto,
              origen: d.origen,
            }))}
          />
        )}
      </section>
      <p className="silice-hoja__total cds--type-heading-03">
        Total del presupuesto <Cifra monto={vista.total} unidad={vista.moneda} />
      </p>
      {vista.pendientes > 0 && (
        <p className="cds--type-body-compact-01">
          {vista.pendientes} partida(s) no tienen composición en el catálogo del caso: quedan pendientes y no suman al total.
        </p>
      )}
    </div>
  );
}

// Pestaña «Espacio y metrajes» en lectura (la edición llega en la rebanada 3c).
export function PestanaEspacio({ id, alAusente }: Props) {
  return (
    <VistaCarga<VistaEspacio> ruta={rutaDeVista(id, "espacio")} etiqueta="Espacio y metrajes" alAusente={alAusente}>
      {(vista) => <ContenidoEspacio vista={vista} />}
    </VistaCarga>
  );
}
