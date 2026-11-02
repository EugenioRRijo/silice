import { Button, RadioButton, RadioButtonGroup } from "@carbon/react";
import { Search } from "../../comun/carbonEs";
import { Add } from "@carbon/icons-react";
import { useCallback, useEffect, useId, useState } from "react";
import { pedir } from "../../api/cliente";
import { TablaDensa } from "../../comun/TablaDensa";
import type { ColumnaDensa } from "../../comun/TablaDensa";
import { cifrasEnTextoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { ConfirmarQuitarLinea, DialogoAgregarLinea } from "./AgregarLineaApu";
import type { LineaAgregada } from "./AgregarLineaApu";
import { useFocoAlCerrar } from "./AgregarPartida";
import { AvisoDeEdicion, AvisoDeEnvio } from "./AvisoDeEdicion";
import { AyudaDePestana } from "./AyudaDePestana";
import { CambioDeInsumo } from "./CambioDeInsumo";
import { CampoDeCelda } from "./CampoDeCelda";
import { Cifra } from "./Cifra";
import { TablaPaginada } from "./TablaPaginada";
import { VistaCarga } from "./VistaCarga";
import { enteroDeDigitos, rutaDeVista } from "./logica";
import type { BaseAbierta, DetalleApu, GrupoApu, Resumen, VistaApu } from "./logica";
import {
  FRASE_DE_APU,
  RUBROS,
  cambiarCantidadDeLinea,
  cambiarRendimiento,
  conLineaAgregada,
  conLineaQuitada,
  cuerpoDeApu,
  rutaDeApu,
  rutaDeQuitarLinea,
  sembrarApu,
  textoDeEstado,
  ubicarErrorDeApu,
} from "./logicaApu";
import type { EdicionDeApu, UbicacionDeApu } from "./logicaApu";
import { useDialogoDeOperacion } from "./useDialogoDeOperacion";
import { useEdicionDeSeccion } from "./useEdicionDeSeccion";
import { usePuedeEditarLaHoja } from "./puedeEditar";

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
  // La base del borrador: con `solo_lectura` (o sin permiso de edición) no se pinta nada que escriba (F4 2b).
  base?: Pick<BaseAbierta, "solo_lectura">;
}

// Espera tras la última tecla antes de pedir la lista filtrada al servidor.
const PAUSA_DE_BUSQUEDA_MS = 300;
const NUMERICAS = new Set(["precio", "depreciacion", "sueldo"]);

const idDeCantidad = (rubro: string, n: number) => `hoja-apu-${rubro.replace(/\s+/g, "-")}-${n}`;
const idDeQuitar = (rubro: string, n: number) => `hoja-apu-quitar-${rubro.replace(/\s+/g, "-")}-${n}`;
const ID_AGREGAR_LINEA = "hoja-apu-agregar-linea";
const SIN_VERSION_GUARDADA = "Las líneas del APU se agregan y se quitan en una versión guardada.";

// La línea que la persona pidió quitar: espera su confirmación.
interface PorQuitar {
  grupo: string;
  indice: number;
  descripcion: string;
  boton: string;
}

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

// El APU de una partida: las cantidades de cada línea y el rendimiento se editan (se aplican al borrador del servidor tras
// la pausa de 400 ms); el cierre y los subtotales se vuelven a leer. A la derecha, los factores de la versión y el cierre.
function EditorDeApu({ id, rev, moneda, detalle, alAusente, alAceptar, alRecargarBorrador, alReabrir, alRelectura, base }: PropsEditor) {
  const { alExpirar } = useAplicacion();
  const puedeEditar = usePuedeEditarLaHoja(base ?? null);
  const idDelError = useId();
  const edicion = useEdicionDeSeccion<EdicionDeApu, UbicacionDeApu>({
    borrador: id,
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
  const { error, accionarEnOrden, esperarEnvios, resembrar, recargar } = edicion;
  const ubicacion = error?.ubicacion ?? null;
  // Agregar y quitar líneas (Tarea 26): solo en el borrador de una versión guardada.
  const conLineas = puedeEditar && !detalle.solo_lectura_insumos;
  const { abierto, anfitrion, abrir, cerrar, anclaDelBoton } = useDialogoDeOperacion();
  const enfocar = useFocoAlCerrar();
  const [porQuitar, setPorQuitar] = useState<PorQuitar | null>(null);
  // Mientras va la petición de quitar, la tabla no se edita: lo escrito tendría la forma del APU de antes.
  const [quitando, setQuitando] = useState(false);
  const [aviso, setAviso] = useState("");

  const alAgregada = useCallback(
    ({ resumen, grupo, descripcion, cantidad }: LineaAgregada) => {
      // La línea nueva va al final de su rubro: su cantidad entra en lo que se edita (lo demás se conserva).
      resembrar((escrito, yaAceptado) => ({
        estado: conLineaAgregada(escrito, grupo, cantidad),
        aceptado: conLineaAgregada(yaAceptado, grupo, cantidad),
      }));
      alAceptar(resumen);
      alRelectura();
      setAviso(`Se agregó «${descripcion}» a ${RUBROS[grupo]?.enFrase ?? grupo} de ${detalle.codigo}.`);
      cerrar(true);
    },
    [resembrar, alAceptar, alRelectura, cerrar, detalle.codigo],
  );

  const quitar = async () => {
    if (porQuitar === null) return;
    const { grupo, indice, descripcion, boton } = porQuitar;
    const tipo = RUBROS[grupo]!.tipo;
    setPorQuitar(null);
    setAviso("");
    setQuitando(true);
    try {
      // Primero sale lo escrito que espera la pausa; un error (409, 422) se dice en el aviso del APU, tal cual.
      const aceptado = await accionarEnOrden((r) => ({
        ruta: rutaDeQuitarLinea(id, detalle.codigo),
        metodo: "POST",
        cuerpo: { rev: r, tipo, indice },
        frase: "",
      }));
      if (aceptado !== null) {
        resembrar((escrito, yaAceptado) => ({
          estado: conLineaQuitada(escrito, grupo, indice),
          aceptado: conLineaQuitada(yaAceptado, grupo, indice),
        }));
        setAviso(`Se quitó «${descripcion}» de ${RUBROS[grupo]!.enFrase} de ${detalle.codigo}.`);
        enfocar(ID_AGREGAR_LINEA);
      } else {
        enfocar(boton);
      }
    } finally {
      setQuitando(false);
    }
  };

  return (
    <>
      <div className="silice-hoja__apu-centro">
        <h2 className="cds--type-heading-compact-02">
          {detalle.codigo} · {detalle.descripcion} · {detalle.unidad}
        </h2>
        <AvisoDeEnvio envio={edicion.envio} />
        {error !== null && (
          <AvisoDeEdicion error={error} id={idDelError} alRecargar={() => void recargar()} alReabrir={alReabrir} />
        )}
        <fieldset className="silice-hoja__sin-marco" disabled={quitando} aria-busy={quitando}>
          <legend className="cds--visually-hidden">Líneas y rendimiento del APU de {detalle.codigo}</legend>
          {detalle.grupos.map((g) => (
            <TablaDelRubro
              key={g.clave}
              grupo={g}
              moneda={moneda}
              edicion={edicion.estado}
              ubicacion={ubicacion}
              idDelError={idDelError}
              quitable={conLineas}
              soloLectura={!puedeEditar}
              alCambiar={(indice, texto) => edicion.cambiar((previo) => cambiarCantidadDeLinea(previo, g.clave, indice, texto))}
              alRestaurar={(indice) =>
                edicion.cambiar((previo) =>
                  cambiarCantidadDeLinea(previo, g.clave, indice, edicion.aceptado().cantidades[g.clave]?.[indice] ?? ""),
                )
              }
              alQuitar={(linea) => {
                setAviso("");
                setPorQuitar(linea);
              }}
            />
          ))}
          {puedeEditar && (
          <div className="silice-hoja__acciones">
            {conLineas ? (
              <Button
                id={ID_AGREGAR_LINEA}
                ref={anclaDelBoton}
                kind="tertiary"
                size="sm"
                renderIcon={Add}
                onClick={() => {
                  setAviso("");
                  abrir();
                }}
              >
                Agregar línea
              </Button>
            ) : (
              <p className="cds--type-helper-text-01">{SIN_VERSION_GUARDADA}</p>
            )}
          </div>
          )}
          <p className="cds--type-helper-text-01" role="status">
            {aviso}
          </p>
          <CampoDeCelda
            soloLectura={!puedeEditar}
            id="hoja-apu-rendimiento"
            etiqueta="Rendimiento (unidades por día)"
            etiquetaVisible
            valor={edicion.estado.rendimiento}
            invalido={ubicacion?.campo === "rendimiento"}
            descripcionId={idDelError}
            alCambiar={(texto) => edicion.cambiar((previo) => cambiarRendimiento(previo, texto))}
            alRestaurar={() => edicion.cambiar((previo) => cambiarRendimiento(previo, edicion.aceptado().rendimiento))}
          />
        </fieldset>
        {puedeEditar && (
          <CambioDeInsumo id={id} detalle={detalle} alCambiar={accionarEnOrden} alAusente={alAusente} alExpirar={alExpirar} />
        )}
        {porQuitar !== null && (
          <ConfirmarQuitarLinea
            partida={detalle.codigo}
            descripcion={porQuitar.descripcion}
            enFrase={RUBROS[porQuitar.grupo]?.enFrase ?? porQuitar.grupo}
            alQuitar={() => void quitar()}
            alCancelar={() => {
              enfocar(porQuitar.boton);
              setPorQuitar(null);
            }}
          />
        )}
        {abierto && anfitrion !== null && (
          <DialogoAgregarLinea
            id={id}
            partida={detalle.codigo}
            moneda={moneda}
            anfitrion={anfitrion}
            revActual={esperarEnvios}
            alAgregada={alAgregada}
            alCancelar={() => cerrar(true)}
            alAusente={alAusente}
            alReleer={recargar}
          />
        )}
      </div>
      <div className="silice-hoja__apu-cierre">
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
              // La nota la arma el servidor con punto decimal («FCAS 6 y bono 5.81», «15.0 %»): se lee en es-VE.
              nota: cifrasEnTextoEsVe(c.nota),
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
  const puedeEditar = usePuedeEditarLaHoja(props.base ?? null);
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
      {(vista, actualizando) => (
        <>
          <AyudaDePestana id="apu" puedeEditar={puedeEditar} />
          {vista.vacio_mensaje !== null ? (
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
        )}
        </>
      )}
    </VistaCarga>
  );
}
