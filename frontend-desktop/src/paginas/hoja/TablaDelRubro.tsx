import { Button } from "@carbon/react";
import type { ColumnaDensa } from "../../comun/TablaDensa";
import { CampoDeCelda } from "./CampoDeCelda";
import { Cifra } from "./Cifra";
import { TablaPaginada } from "./TablaPaginada";
import { enteroDeDigitos } from "./logica";
import type { GrupoApu } from "./logica";
import type { EdicionDeApu, UbicacionDeApu } from "./logicaApu";

// Una tabla del APU por rubro (materiales, equipos, mano de obra) con su subtotal. Sale de `PestanaApu.tsx` en la Tarea 7
// del plan F4 junto con `EditorDeApu`, que la usa en la pestaña y en el panel lateral; aparte porque es una pieza con sus
// propias columnas y el editor ya es largo.

const NUMERICAS = new Set(["precio", "depreciacion", "sueldo"]);

const idDeCantidad = (rubro: string, n: number) => `hoja-apu-${rubro.replace(/\s+/g, "-")}-${n}`;
const idDeQuitar = (rubro: string, n: number) => `hoja-apu-quitar-${rubro.replace(/\s+/g, "-")}-${n}`;

// La línea que la persona pidió quitar: espera su confirmación.
export interface PorQuitar {
  grupo: string;
  indice: number;
  descripcion: string;
  boton: string;
}

export function TablaDelRubro({
  grupo,
  moneda,
  edicion,
  ubicacion,
  idDelError,
  quitable,
  soloLectura,
  alCambiar,
  alRestaurar,
  alQuitar,
}: {
  grupo: GrupoApu;
  moneda: string;
  edicion: EdicionDeApu;
  ubicacion: UbicacionDeApu | null;
  idDelError: string;
  // Las líneas se quitan solo en el borrador de una versión guardada (Tarea 26).
  quitable: boolean;
  // F4 2b: sin permiso de edición la cantidad de cada línea es texto.
  soloLectura: boolean;
  alCambiar: (indice: number, texto: string) => void;
  alRestaurar: (indice: number) => void;
  alQuitar: (linea: PorQuitar) => void;
}) {
  const mover = (desde: number, paso: 1 | -1) => document.getElementById(idDeCantidad(grupo.clave, desde + paso))?.focus();
  const columnas: ColumnaDensa[] = grupo.columnas.map((c) => {
    if (c.clave === "cantidad") {
      return {
        clave: c.clave,
        titulo: c.rotulo,
        ordenable: false,
        numerica: true,
        celda: (f) => {
          const n = enteroDeDigitos(f.n!);
          return (
            <CampoDeCelda
              soloLectura={soloLectura}
              id={idDeCantidad(grupo.clave, n)}
              etiqueta={`Cantidad, ${grupo.rotulo} fila ${n}`}
              valor={edicion.cantidades[grupo.clave]?.[n - 1] ?? f.cantidad!}
              invalido={ubicacion?.campo === "linea" && ubicacion.grupo === grupo.clave && ubicacion.fila === n}
              descripcionId={idDelError}
              alCambiar={(texto) => alCambiar(n - 1, texto)}
              alRestaurar={() => alRestaurar(n - 1)}
              alMover={(paso) => mover(n, paso)}
            />
          );
        },
      };
    }
    return {
      clave: c.clave,
      titulo: c.rotulo,
      ordenable: false,
      // Las filas del APU llegan escritas como en los campos (coma decimal y punto de miles: `texto_de_cifra` en
      // `filas_desde_composicion`); se muestran tal cual. Volver a formatearlas convertia «1.500» en «1,500» (B3).
      ...(NUMERICAS.has(c.clave) ? { numerica: true } : {}),
    };
  });
  if (quitable) {
    columnas.push({
      clave: "quitar",
      titulo: "Quitar",
      ordenable: false,
      celda: (f) => {
        const n = enteroDeDigitos(f.n!);
        const descripcion = f.descripcion ?? "";
        return (
          <Button
            id={idDeQuitar(grupo.clave, n)}
            kind="ghost"
            size="sm"
            aria-label={`Quitar ${descripcion}, ${grupo.rotulo} fila ${n}`}
            onClick={() => alQuitar({ grupo: grupo.clave, indice: n - 1, descripcion, boton: idDeQuitar(grupo.clave, n) })}
          >
            Quitar
          </Button>
        );
      },
    });
  }
  return (
    <section className="silice-hoja__seccion">
      <h3 className="cds--type-heading-compact-01">
        {grupo.rotulo} · {grupo.filas.length} línea(s)
      </h3>
      {grupo.filas.length === 0 ? (
        <p className="cds--type-body-compact-01">Sin líneas.</p>
      ) : (
        <TablaPaginada
          etiqueta={grupo.rotulo}
          desplazable
          columnas={columnas}
          filas={grupo.filas.map((f, i) => ({ ...f, id: `${grupo.clave}-${i}`, n: String(i + 1) }))}
        />
      )}
      <p className="cds--type-body-compact-01">
        <span>Subtotal de {grupo.rotulo.toLowerCase()}:</span> <Cifra monto={grupo.subtotal} unidad={moneda} />
      </p>
    </section>
  );
}
