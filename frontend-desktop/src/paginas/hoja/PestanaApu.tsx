import { RadioButton, RadioButtonGroup, Search } from "@carbon/react";
import { useCallback, useEffect, useId, useState } from "react";
import { pedir } from "../../api/cliente";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa } from "../../comun/TablaDensa";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { AvisoDeEdicion, AvisoDeEnvio } from "./AvisoDeEdicion";
import { CambioDeInsumo } from "./CambioDeInsumo";
import { CampoDeCelda } from "./CampoDeCelda";
import { Cifra } from "./Cifra";
import { FactoresDeLaVersion } from "./PestanaParametros";
import { TablaPaginada } from "./TablaPaginada";
import { VistaCarga } from "./VistaCarga";
import { enteroDeDigitos, rutaDeVista } from "./logica";
import type { DetalleApu, GrupoApu, Resumen, VistaApu } from "./logica";
import {
  FRASE_DE_APU,
  cambiarCantidadDeLinea,
  cambiarRendimiento,
  cuerpoDeApu,
  rutaDeApu,
  sembrarApu,
  textoDeEstado,
  ubicarErrorDeApu,
} from "./logicaApu";
import type { EdicionDeApu, UbicacionDeApu } from "./logicaApu";
import { useEdicionDeSeccion } from "./useEdicionDeSeccion";

interface Props {
  id: string;
  // El `rev` del borrador según la página.
  rev: number;
  moneda: string;
  alAusente: () => void;
  // El servidor aceptó una edición: su resumen pasa a la barra de estado de la página.
  alAceptar: (resumen: Resumen) => void;
  alRecargarBorrador: () => Promise<void>;
  // Descarta lo que se ve y abre otro borrador de la versión (cuando recargar no sirve).
  alReabrir: () => void;
}

// Espera tras la última tecla antes de pedir la lista filtrada al servidor.
const PAUSA_DE_BUSQUEDA_MS = 300;
const NUMERICAS = new Set(["precio", "depreciacion", "sueldo"]);

const idDeCantidad = (rubro: string, n: number) => `hoja-apu-${rubro.replace(/\s+/g, "-")}-${n}`;

interface PropsEditor extends Props {
  detalle: DetalleApu;
  alRelectura: () => void;
}

function TablaDelRubro({
  grupo,
  moneda,
  edicion,
  ubicacion,
  idDelError,
  alCambiar,
  alRestaurar,
}: {
  grupo: GrupoApu;
  moneda: string;
  edicion: EdicionDeApu;
  ubicacion: UbicacionDeApu | null;
  idDelError: string;
  alCambiar: (indice: number, texto: string) => void;
  alRestaurar: (indice: number) => void;
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
      ...(NUMERICAS.has(c.clave) ? { numerica: true, presentar: formatoEsVe } : {}),
    };
  });
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

// El APU de una partida: las cantidades de cada línea y el rendimiento se editan (se aplican al borrador del servidor tras
// la pausa de 400 ms); el cierre y los subtotales se vuelven a leer. A la derecha, los factores de la versión y el cierre.
function EditorDeApu({ id, rev, moneda, detalle, alAusente, alAceptar, alRecargarBorrador, alReabrir, alRelectura }: PropsEditor) {
  const { alExpirar } = useAplicacion();
  const idDelError = useId();
  const edicion = useEdicionDeSeccion<EdicionDeApu, UbicacionDeApu>({
    inicial: sembrarApu(detalle),
    rev,
    peticion: (r, apu) => ({ ruta: rutaDeApu(id, detalle.codigo), metodo: "PUT", cuerpo: cuerpoDeApu(r, apu) }),
    ubicar: ubicarErrorDeApu,
    frase: FRASE_DE_APU,
    leerFresca: async () => {
      const vista = await pedir<VistaApu>(rutaDeVista(id, "apu", { partida: detalle.codigo }));
      return sembrarApu(vista.detalle ?? detalle);
    },
    alAceptar,
    alRelectura,
    alRecargarBorrador,
    alAusente,
    alExpirar,
  });
  const { error } = edicion;
  const ubicacion = error?.ubicacion ?? null;

  return (
    <>
      <div className="silice-hoja__apu-centro">
        <h2 className="cds--type-heading-compact-02">
          {detalle.codigo} · {detalle.descripcion} · {detalle.unidad}
        </h2>
        <p className="cds--type-helper-text-01">
          Se edita la cantidad de cada línea y el rendimiento, en la copia de esta versión: el catálogo no cambia. Decimales con
          punto, por ejemplo 2.5: la coma no se acepta. Los cambios se aplican al borrador cuando deja de escribir; no se guardan
          como versión hasta que lo pida.
        </p>
        <AvisoDeEnvio envio={edicion.envio} />
        {error !== null && (
          <AvisoDeEdicion error={error} id={idDelError} alRecargar={() => void edicion.recargar()} alReabrir={alReabrir} />
        )}
        {detalle.grupos.map((g) => (
          <TablaDelRubro
            key={g.clave}
            grupo={g}
            moneda={moneda}
            edicion={edicion.estado}
            ubicacion={ubicacion}
            idDelError={idDelError}
            alCambiar={(indice, texto) => edicion.cambiar((previo) => cambiarCantidadDeLinea(previo, g.clave, indice, texto))}
            alRestaurar={(indice) =>
              edicion.cambiar((previo) =>
                cambiarCantidadDeLinea(previo, g.clave, indice, edicion.aceptado().cantidades[g.clave]?.[indice] ?? ""),
              )
            }
          />
        ))}
        <CampoDeCelda
          id="hoja-apu-rendimiento"
          etiqueta="Rendimiento (unidades por día)"
          etiquetaVisible
          valor={edicion.estado.rendimiento}
          invalido={ubicacion?.campo === "rendimiento"}
          descripcionId={idDelError}
          alCambiar={(texto) => edicion.cambiar((previo) => cambiarRendimiento(previo, texto))}
          alRestaurar={() => edicion.cambiar((previo) => cambiarRendimiento(previo, edicion.aceptado().rendimiento))}
        />
        <CambioDeInsumo
          id={id}
          detalle={detalle}
          alCambiar={edicion.accionarEnOrden}
          alAusente={alAusente}
          alExpirar={alExpirar}
        />
      </div>
      <div className="silice-hoja__apu-cierre">
        <section className="silice-hoja__seccion">
          <h3 className="cds--type-heading-compact-01">Factores de la versión</h3>
          <FactoresDeLaVersion
            id={id}
            rev={rev}
            moneda={moneda}
            alAusente={alAusente}
            alAceptar={alAceptar}
            alRecargarBorrador={alRecargarBorrador}
            alReabrir={alReabrir}
            alCambiar={alRelectura}
          />
        </section>
        <section className="silice-hoja__seccion">
          <h3 className="cds--type-heading-compact-01">Cierre de partida</h3>
          <TablaDensa
            etiqueta="Cierre de partida"
            columnas={[
              { clave: "concepto", titulo: "Concepto", ordenable: false },
              {
                clave: "monto",
                titulo: "Monto",
                numerica: true,
                ordenable: false,
                celda: (f) => <Cifra monto={{ texto: f.monto!, exacto: f.monto_exacto! }} unidad={moneda} />,
              },
              { clave: "nota", titulo: "Nota", ordenable: false },
            ]}
            filas={detalle.cierre.map((c, i) => ({
              id: `cierre-${i}`,
              concepto: c.concepto,
              monto: c.monto.texto,
              monto_exacto: c.monto.exacto,
              nota: c.nota,
            }))}
          />
        </section>
        <dl className="silice-hoja__metricas">
          {(
            [
              ["Materiales", detalle.metricas.materiales],
              ["Equipos", detalle.metricas.equipos],
              ["Mano de obra", detalle.metricas.mano_obra],
              ["Precio unitario", detalle.metricas.precio_unitario],
            ] as const
          ).map(([rotulo, monto]) => (
            <div key={rotulo}>
              <dt className="cds--type-helper-text-01">{rotulo}</dt>
              <dd className="cds--type-heading-compact-02">
                <Cifra monto={monto} unidad={moneda} />
              </dd>
            </div>
          ))}
        </dl>
        {detalle.estados.length > 0 && (
          <section className="silice-hoja__seccion">
            <h3 className="cds--type-heading-compact-01">Estado de la partida</h3>
            {detalle.estados.map((e) => (
              <p key={e} className="cds--type-helper-text-01">
                {textoDeEstado(e)}
              </p>
            ))}
          </section>
        )}
      </div>
    </>
  );
}

// Pestaña «APU»: lista con buscador (lo filtra el servidor), tres rubros editables, factores y cierre de la partida
// (rebanada 3c-3). Cada edición recalcula en el servidor; la pestaña vuelve a leer su vista.
export function PestanaApu(props: Props) {
  const [escrito, setEscrito] = useState("");
  const [buscar, setBuscar] = useState("");
  const [partida, setPartida] = useState<string | undefined>(undefined);
  // Sube cada vez que hay que volver a leer la vista tras una edición: la anterior sigue a la vista mientras llega.
  const [lecturas, setLecturas] = useState(0);
  const alRelectura = useCallback(() => setLecturas((n) => n + 1), []);

  useEffect(() => {
    const espera = setTimeout(() => setBuscar(escrito.trim()), PAUSA_DE_BUSQUEDA_MS);
    return () => clearTimeout(espera);
  }, [escrito]);

  return (
    <VistaCarga<VistaApu>
      ruta={rutaDeVista(props.id, "apu", { partida, buscar })}
      etiqueta="APU"
      alAusente={props.alAusente}
      recarga={lecturas}
    >
      {(vista, actualizando) =>
        vista.vacio_mensaje !== null ? (
          <p className="cds--type-body-compact-01">{vista.vacio_mensaje}</p>
        ) : (
          <div className="silice-hoja__apu" aria-busy={actualizando}>
            <div className="silice-hoja__apu-lista">
              <Search
                size="sm"
                labelText="Buscar partida"
                placeholder="Código o descripción"
                value={escrito}
                onChange={(e: { target: { value: string } }) => setEscrito(e.target.value)}
              />
              {vista.sin_coincidencias && (
                <p className="cds--type-helper-text-01">Ninguna partida coincide; se muestran todas.</p>
              )}
              <RadioButtonGroup
                legendText="Partidas"
                name="partida-apu"
                orientation="vertical"
                valueSelected={vista.seleccionada ?? undefined}
                onChange={(valor) => setPartida(String(valor))}
              >
                {vista.partidas.map((p) => (
                  <RadioButton key={p.codigo} id={`apu-${p.codigo}`} value={p.codigo} labelText={`${p.codigo} · ${p.descripcion}`} />
                ))}
              </RadioButtonGroup>
            </div>
            {vista.detalle !== null && (
              <EditorDeApu key={vista.detalle.codigo} {...props} detalle={vista.detalle} alRelectura={alRelectura} />
            )}
          </div>
        )
      }
    </VistaCarga>
  );
}
