import { Button } from "@carbon/react";
import { useCallback, useContext, useId, useState } from "react";
import { Link, useInRouterContext } from "react-router";
import { pedir } from "../../api/cliente";
import { AvisoDeEdicion, AvisoDeEnvio } from "./AvisoDeEdicion";
import { AyudaDePestana } from "./AyudaDePestana";
import { TablaPaginada } from "./TablaPaginada";
import { TablaEditable } from "./TablaEditable";
import type { IrA } from "./TablaEditable";
import { Cifra } from "./Cifra";
import { VistaCarga } from "./VistaCarga";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import { rutaDeObra } from "../../marco/secciones";
import { useAplicacion } from "../../shell/contexto";
import {
  FRASE_DE_RECHAZO,
  cuerpoDeEdicionDelEspacio,
  nuevaClaveDeFila,
  rutaDeEspacio,
  rutaDeVista,
  sembrarTablas,
  ubicarError,
} from "./logica";
import type {
  BaseAbierta,
  FilaEditable,
  Resumen,
  TablasEditables,
  UbicacionDeError,
  VistaEspacio,
} from "./logica";
import { ENLACE_DESDE_EL_ESPACIO } from "../archivos/textos";
import { useEdicionDeSeccion } from "./useEdicionDeSeccion";
import { usePuedeEditarLaHoja } from "./puedeEditar";
import { unidadEscrita } from "../../comun/unidades";

interface Props {
  id: string;
  // El `rev` del borrador según la página.
  rev: number;
  alAusente: () => void;
  // El servidor aceptó una edición: su resumen pasa a la barra de estado de la página.
  alAceptar: (resumen: Resumen) => void;
  alRecargarBorrador: () => Promise<void>;
  // Descarta lo que se ve y abre otro borrador de la versión (cuando recargar no sirve).
  alReabrir: () => void;
  // La base del borrador: con `solo_lectura` (o sin permiso de edición) no se pinta nada que escriba (F4 2b).
  base?: Pick<BaseAbierta, "solo_lectura">;
}

interface PropsContenido extends Props {
  vista: VistaEspacio;
  alRelectura: () => void;
}

function ContenidoEspacio({
  id,
  rev,
  vista,
  alAusente,
  alAceptar,
  alRecargarBorrador,
  alReabrir,
  alRelectura,
  base,
}: PropsContenido) {
  const { alExpirar } = useAplicacion();
  const puedeEditar = usePuedeEditarLaHoja(base ?? null);
  // Dentro de una obra (y de un enrutador), el enlace a Archivos y planos, donde se importa el plano desde la Tarea 11 de F4.
  const obra = useContext(ContextoDeLaObra);
  const enRuta = useInRouterContext();
  const idDelError = useId();
  const [irA, setIrA] = useState<(IrA & { tabla: string }) | null>(null);
  const edicion = useEdicionDeSeccion<TablasEditables, UbicacionDeError>({
    borrador: id,
    inicial: sembrarTablas(vista.tablas, vista.filas, nuevaClaveDeFila),
    rev,
    peticion: (r, tablas) => ({
      ruta: rutaDeEspacio(id),
      metodo: "PUT",
      cuerpo: cuerpoDeEdicionDelEspacio(r, vista.tablas, tablas),
    }),
    ubicar: (detalle) => ubicarError(detalle, vista.tablas),
    frase: FRASE_DE_RECHAZO,
    leerFresca: async () => {
      const fresca = await pedir<VistaEspacio>(rutaDeVista(id, "espacio"));
      return sembrarTablas(fresca.tablas, fresca.filas, nuevaClaveDeFila);
    },
    alAceptar,
    alRelectura,
    alRecargarBorrador,
    alAusente,
    alExpirar,
  });
  const cambiarFilas = (tabla: string, filas: FilaEditable[]) =>
    edicion.cambiar((previo) => ({ ...previo, [tabla]: filas }));
  const valorAceptado = (
    tabla: string,
    filaClave: number,
    columna: string,
  ): string =>
    edicion.aceptado()[tabla]?.find((f) => f.clave === filaClave)?.valores[
      columna
    ] ?? "";
  const { error } = edicion;
  const ubicacion = error?.ubicacion ?? null;
  const rotuloDe = (clave: string) =>
    vista.tablas.find((t) => t.clave === clave)?.rotulo ?? clave;

  return (
    <div className="silice-hoja__pestana">
      <AyudaDePestana id="espacio" puedeEditar={puedeEditar} delServidor={vista.ayuda} />
      {puedeEditar && obra !== null && enRuta && (
        <p className="cds--type-body-compact-01">
          <Link className="cds--link" to={rutaDeObra(obra.carpeta, obra.obraId, "archivos")}>
            {ENLACE_DESDE_EL_ESPACIO}
          </Link>
        </p>
      )}
      <AvisoDeEnvio envio={edicion.envio} />
      {error !== null && (
        <AvisoDeEdicion
          error={error}
          id={idDelError}
          alRecargar={() => void edicion.recargar()}
          alReabrir={alReabrir}
        >
          {ubicacion !== null && (
            <Button
              kind="ghost"
              size="sm"
              onClick={() =>
                setIrA((previo) => ({
                  tabla: ubicacion.tabla,
                  fila: ubicacion.fila,
                  columna: ubicacion.columna,
                  vez: (previo?.vez ?? 0) + 1,
                }))
              }
            >
              {`Ir a la fila ${ubicacion.fila} de ${rotuloDe(ubicacion.tabla)}`}
            </Button>
          )}
        </AvisoDeEdicion>
      )}
      <div className="silice-hoja__tablas-espacio">
        {vista.tablas.map((t) => (
          <TablaEditable
            key={t.clave}
            tabla={t}
            filas={edicion.estado[t.clave] ?? []}
            estado={vista.estado}
            invalida={
              ubicacion !== null && ubicacion.tabla === t.clave
                ? { fila: ubicacion.fila, columna: ubicacion.columna }
                : null
            }
            idDelError={idDelError}
            irA={irA !== null && irA.tabla === t.clave ? irA : null}
            alCambiarFilas={(filas) => cambiarFilas(t.clave, filas)}
            valorAceptado={(filaClave, columna) =>
              valorAceptado(t.clave, filaClave, columna)
            }
            soloLectura={!puedeEditar}
          />
        ))}
      </div>
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
                celda: (f) => (
                  <Cifra
                    monto={{ texto: f.cantidad!, exacto: f.cantidad_exacto! }}
                  />
                ),
              },
              { clave: "origen", titulo: "Origen", ordenable: false },
            ]}
            filas={vista.derivadas.map((d, i) => ({
              id: `derivada-${i}`,
              partida: d.partida,
              descripcion: d.descripcion,
              unidad: unidadEscrita(d.unidad),
              cantidad: d.cantidad.texto,
              cantidad_exacto: d.cantidad.exacto,
              origen: d.origen,
            }))}
          />
        )}
      </section>
      {vista.pendientes > 0 && (
        <p className="cds--type-body-compact-01">
          {vista.pendientes} partida(s) no tienen composición en el catálogo del
          caso: quedan pendientes y no suman al total.
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
    <VistaCarga<VistaEspacio>
      ruta={rutaDeVista(props.id, "espacio")}
      etiqueta="Espacio y metrajes"
      alAusente={props.alAusente}
      recarga={lecturas}
    >
      {(vista) => (
        <ContenidoEspacio {...props} vista={vista} alRelectura={alRelectura} />
      )}
    </VistaCarga>
  );
}
