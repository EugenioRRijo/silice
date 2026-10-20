import { Button, InlineNotification } from "@carbon/react";
import { useCallback, useId, useState } from "react";
import { TablaPaginada } from "./TablaPaginada";
import { TablaEditable } from "./TablaEditable";
import type { IrA } from "./TablaEditable";
import { Cifra } from "./Cifra";
import { VistaCarga } from "./VistaCarga";
import { useAplicacion } from "../../shell/contexto";
import { rutaDeVista } from "./logica";
import type { Resumen, VistaEspacio } from "./logica";
import { useEdicionDelEspacio } from "./useEdicionDelEspacio";

interface Props {
  id: string;
  // El `rev` del borrador según la página.
  rev: number;
  alAusente: () => void;
  // El servidor aceptó una edición: su resumen pasa a la barra de estado de la página.
  alAceptar: (resumen: Resumen) => void;
  alRecargarBorrador: () => Promise<void>;
}

interface PropsContenido extends Props {
  vista: VistaEspacio;
  alRelectura: () => void;
}

function ContenidoEspacio({ id, rev, vista, alAusente, alAceptar, alRecargarBorrador, alRelectura }: PropsContenido) {
  const { alExpirar } = useAplicacion();
  const idDelError = useId();
  const [irA, setIrA] = useState<(IrA & { tabla: string }) | null>(null);
  const edicion = useEdicionDelEspacio({ id, vista, rev, alAceptar, alRelectura, alRecargarBorrador, alAusente, alExpirar });
  const { error } = edicion;
  const ubicacion = error?.ubicacion ?? null;
  const rotuloDe = (clave: string) => vista.tablas.find((t) => t.clave === clave)?.rotulo ?? clave;

  return (
    <div className="silice-hoja__pestana">
      <p className="cds--type-body-compact-01">{vista.ayuda}</p>
      <p className="cds--type-helper-text-01">
        Decimales con punto, por ejemplo 2.5: la coma no se acepta. Los cambios se aplican al borrador cuando deja de escribir; no se
        guardan como versión hasta que lo pida.
      </p>
      <p className="cds--type-helper-text-01" aria-live="polite">
        {edicion.envio === "quieto" ? "" : "Aplicando los cambios al borrador…"}
      </p>
      {error !== null && (
        <div id={idDelError} className="silice-hoja__aviso-edicion">
          <InlineNotification
            kind={error.tipo === "conflicto" ? "warning" : "error"}
            role="alert"
            lowContrast
            hideCloseButton
            title={error.tipo === "conflicto" ? "El borrador cambió" : "No se aplicó el cambio"}
            subtitle={error.mensaje}
          />
          {error.tipo === "conflicto" && (
            <Button kind="tertiary" size="sm" onClick={() => void edicion.recargar()}>
              Recargar el borrador
            </Button>
          )}
          {ubicacion !== null && (
            <Button
              kind="ghost"
              size="sm"
              onClick={() => setIrA((previo) => ({ tabla: ubicacion.tabla, fila: ubicacion.fila, columna: ubicacion.columna, vez: (previo?.vez ?? 0) + 1 }))}
            >
              {`Ir a la fila ${ubicacion.fila} de ${rotuloDe(ubicacion.tabla)}`}
            </Button>
          )}
        </div>
      )}
      {vista.tablas.map((t) => (
        <TablaEditable
          key={t.clave}
          tabla={t}
          filas={edicion.tablas[t.clave] ?? []}
          estado={vista.estado}
          invalida={ubicacion !== null && ubicacion.tabla === t.clave ? { fila: ubicacion.fila, columna: ubicacion.columna } : null}
          idDelError={idDelError}
          irA={irA !== null && irA.tabla === t.clave ? irA : null}
          alCambiarFilas={(filas) => edicion.cambiarFilas(t.clave, filas)}
          valorAceptado={(filaClave, columna) => edicion.valorAceptado(t.clave, filaClave, columna)}
        />
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

// Pestaña «Espacio y metrajes»: las cinco tablas se editan (rebanada 3c-1) y se aplican al borrador del servidor.
export function PestanaEspacio(props: Props) {
  // Sube cada vez que hay que volver a leer la vista tras una edición: la anterior sigue a la vista mientras llega.
  const [lecturas, setLecturas] = useState(0);
  const alRelectura = useCallback(() => setLecturas((n) => n + 1), []);
  return (
    <VistaCarga<VistaEspacio> ruta={rutaDeVista(props.id, "espacio")} etiqueta="Espacio y metrajes" alAusente={props.alAusente} recarga={lecturas}>
      {(vista) => <ContenidoEspacio {...props} vista={vista} alRelectura={alRelectura} />}
    </VistaCarga>
  );
}
