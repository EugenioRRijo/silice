import { Button } from "@carbon/react";
import { useCallback, useId, useState } from "react";
import { pedir } from "../../api/cliente";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { AvisoDeEdicion, AvisoDeEnvio } from "./AvisoDeEdicion";
import { CampoDeCelda } from "./CampoDeCelda";
import { Cifra } from "./Cifra";
import { EstadoDeFila } from "./EstadoDeFila";
import { TablaPaginada } from "./TablaPaginada";
import { VistaCarga } from "./VistaCarga";
import { clavesDeAuditoria, enteroDeDigitos, rotuloDeOrigen, rutaDeVista } from "./logica";
import type { Resumen, VistaPresupuesto } from "./logica";
import {
  FRASES_DE_RECHAZO,
  cambiarCantidad,
  cuerpoDeCantidades,
  rutaDeCantidades,
  sembrarCantidades,
  ubicarErrorDeCantidad,
} from "./logicaSecciones";
import type { EdicionDeCantidades } from "./logicaSecciones";
import { useEdicionDeSeccion } from "./useEdicionDeSeccion";

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
}

interface PropsContenido extends Props {
  vista: VistaPresupuesto;
  alRelectura: () => void;
}

const PENDIENTE = "Pendiente";

const idDeCantidad = (n: number | string) => `hoja-cantidades-${n}`;

function EditorDePresupuesto({ id, rev, vista, alAusente, alAceptar, alRecargarBorrador, alReabrir, alRelectura }: PropsContenido) {
  const { alExpirar } = useAplicacion();
  const idDelError = useId();
  const edicion = useEdicionDeSeccion<EdicionDeCantidades, number>({
    borrador: id,
    inicial: sembrarCantidades(vista.filas),
    rev,
    peticion: (r, cantidades) => ({ ruta: rutaDeCantidades(id), metodo: "PUT", cuerpo: cuerpoDeCantidades(r, cantidades) }),
    ubicar: ubicarErrorDeCantidad,
    frase: FRASES_DE_RECHAZO.cantidades,
    leerFresca: async () => sembrarCantidades((await pedir<VistaPresupuesto>(rutaDeVista(id, "presupuesto"))).filas),
    alAceptar,
    alRelectura,
    alRecargarBorrador,
    alAusente,
    alExpirar,
  });
  const { error } = edicion;
  const filaInvalida = error?.ubicacion ?? null;
  const mover = (desde: number, paso: 1 | -1) => document.getElementById(idDeCantidad(desde + paso))?.focus();

  return (
    <div className="silice-hoja__pestana">
      <p className="cds--type-body-compact-01">
        Las cantidades salen del espacio y los precios de la composición de cada partida. Aquí se edita la cantidad: una cantidad escrita
        a mano se marca en el Estado y puede volver a la calculada.
      </p>
      <p className="cds--type-helper-text-01">
        Decimales con punto, por ejemplo 2.5: la coma no se acepta. Los cambios se aplican al borrador cuando deja de escribir; no se
        guardan como versión hasta que lo pida.
      </p>
      <AvisoDeEnvio envio={edicion.envio} />
      {error !== null && <AvisoDeEdicion error={error} id={idDelError} alRecargar={() => void edicion.recargar()} alReabrir={alReabrir} />}
      <TablaPaginada
        etiqueta="Presupuesto"
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
            celda: (f) => {
              const n = enteroDeDigitos(f.n!);
              const clave = f.clave!;
              return (
                <div className="silice-hoja__cantidad">
                  <CampoDeCelda
                    id={idDeCantidad(f.n!)}
                    etiqueta={`Cantidad, Presupuesto fila ${f.n}`}
                    valor={edicion.estado.textos[clave] ?? f.cantidad!}
                    invalido={filaInvalida === n}
                    descripcionId={idDelError}
                    alCambiar={(texto) => edicion.cambiar((previo) => cambiarCantidad(previo, clave, texto))}
                    alRestaurar={() =>
                      edicion.cambiar((previo) => ({
                        ...previo,
                        textos: { ...previo.textos, [clave]: edicion.aceptado().textos[clave] ?? f.cantidad! },
                      }))
                    }
                    alMover={(paso) => mover(n, paso)}
                  />
                  {f.escrita === "si" && (
                    <>
                      <span className="cds--type-helper-text-01">(calculada: {formatoEsVe(f.calculada!)})</span>
                      <Button
                        kind="ghost"
                        size="sm"
                        aria-label={`Volver a la calculada, Presupuesto fila ${f.n}`}
                        onClick={() => edicion.cambiar((previo) => cambiarCantidad(previo, clave, f.calculada!))}
                      >
                        Volver a la calculada
                      </Button>
                    </>
                  )}
                </div>
              );
            },
          },
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
          n: String(i + 1),
          partida: f.partida,
          descripcion: f.descripcion,
          unidad: f.unidad,
          cantidad: f.cantidad,
          calculada: f.cantidad_calculada,
          escrita: f.escrita ? "si" : "no",
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

function ContenidoPresupuesto(props: PropsContenido) {
  if (props.vista.vacio_mensaje !== null) return <p className="cds--type-body-compact-01">{props.vista.vacio_mensaje}</p>;
  return <EditorDePresupuesto {...props} />;
}

// Pestaña «Presupuesto»: la cantidad de cada renglón se edita como texto (rebanada 3c-2) y se aplica al borrador del servidor.
export function PestanaPresupuesto(props: Props) {
  // Sube cada vez que hay que volver a leer la vista tras una edición: la anterior sigue a la vista mientras llega.
  const [lecturas, setLecturas] = useState(0);
  const alRelectura = useCallback(() => setLecturas((n) => n + 1), []);
  return (
    <VistaCarga<VistaPresupuesto> ruta={rutaDeVista(props.id, "presupuesto")} etiqueta="Presupuesto" alAusente={props.alAusente} recarga={lecturas}>
      {(vista) => <ContenidoPresupuesto {...props} vista={vista} alRelectura={alRelectura} />}
    </VistaCarga>
  );
}
