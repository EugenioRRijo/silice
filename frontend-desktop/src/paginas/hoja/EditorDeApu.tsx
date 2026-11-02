import { Button } from "@carbon/react";
import { Add } from "@carbon/icons-react";
import { useCallback, useId, useState } from "react";
import type { JSX } from "react";
import { pedir } from "../../api/cliente";
import { TablaDensa } from "../../comun/TablaDensa";
import { cifrasEnTextoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { ConfirmarQuitarLinea } from "./ConfirmarQuitarLinea";
import { LineaDelApu } from "./LineaDelApu";
import type { LineaAgregada, ModoDeLinea } from "./LineaDelApu";
import { useFocoAlCerrar } from "./AgregarPartida";
import { AvisoDeEdicion, AvisoDeEnvio } from "./AvisoDeEdicion";
import { CampoDeCelda } from "./CampoDeCelda";
import { Cifra } from "./Cifra";
import { TablaDelRubro } from "./TablaDelRubro";
import { VistaCarga } from "./VistaCarga";
import { rutaDeVista } from "./logica";
import type { BaseAbierta, BorradorAbierto, DetalleApu, Resumen, VistaApu } from "./logica";
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
import type { EdicionDeApu, LineaApu, UbicacionDeApu } from "./logicaApu";
import { useHojaDeLaObra } from "./ProveedorDeLaHoja";
import { useDialogoDeOperacion } from "./useDialogoDeOperacion";
import { useEdicionDeSeccion } from "./useEdicionDeSeccion";
import { usePuedeEditarLaHoja } from "./puedeEditar";

// Por qué existe (Tarea 7 del plan F4): el mismo editor del APU sirve en la pestaña «Análisis de precio (APU)» y en el panel
// lateral que se abre desde el código de una fila de «Partidas». Es el cuerpo de la pestaña sin su lista de búsqueda: el
// título, las tablas por rubro (`TablaDelRubro`), el rendimiento, agregar y quitar líneas, cambiar un insumo, el cierre, las
// cifras y el estado de la partida. Sin `puedeEditar` (quien revisa, o un borrador de solo lectura) no pinta nada que
// escriba (Tarea 2b). Pasa de 250 líneas porque el editor es uno solo: sus estados (lo escrito, la línea por quitar, el
// diálogo de las líneas) se comparten entre las tablas, el rendimiento y los diálogos; desde la Tarea 8 agregar y cambiar insumo son el modo de un solo diálogo (`LineaDelApu`).

const ID_AGREGAR_LINEA = "hoja-apu-agregar-linea";
const SIN_VERSION_GUARDADA = "Las líneas del APU se agregan y se quitan en una versión guardada.";

export interface PropsDelDetalle {
  id: string;
  // El `rev` del borrador según la página.
  rev: number;
  moneda: string;
  detalle: DetalleApu;
  alAusente: () => void;
  // El servidor aceptó una edición: su resumen pasa a la barra de estado de la página.
  alAceptar: (resumen: Resumen) => void;
  alRecargarBorrador: () => Promise<void>;
  // Descarta lo que se ve y abre otro borrador de la versión (cuando recargar no sirve).
  alReabrir: () => void;
  // Vuelve a leer la vista del APU tras una edición (subtotales y cierre).
  alRelectura: () => void;
  // La base del borrador: con `solo_lectura` (o sin permiso de edición) no se pinta nada que escriba (F4 2b).
  base?: Pick<BaseAbierta, "solo_lectura">;
  // En el panel lateral el título es el del panel: el editor no repite el suyo.
  conTitulo?: boolean;
}

// El APU de una partida ya leída: las cantidades de cada línea y el rendimiento se editan (se aplican al borrador del
// servidor tras la pausa de 400 ms); el cierre y los subtotales se vuelven a leer. A la derecha, el cierre y las cifras. La
// pestaña APU lo usa con el detalle que ya trae su vista (la lista y la partida elegida llegan en una sola lectura).
export function EditorDelDetalle({
  id,
  rev,
  moneda,
  detalle,
  alAusente,
  alAceptar,
  alRecargarBorrador,
  alReabrir,
  alRelectura,
  base,
  conTitulo = true,
}: PropsDelDetalle) {
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
  const [porQuitar, setPorQuitar] = useState<LineaApu | null>(null);
  // Mientras va la petición de quitar, la tabla no se edita: lo escrito tendría la forma del APU de antes.
  const [quitando, setQuitando] = useState(false);
  const [aviso, setAviso] = useState("");

  const [modo, setModo] = useState<ModoDeLinea>({ tipo: "agregar" });

  const alAceptada = useCallback(
    ({ resumen, grupo, descripcion, cantidad }: LineaAgregada) => {
      if (modo.tipo === "cambiar") {
        // El insumo cambia y la línea conserva su cantidad: nada que resembrar; la vista se relee para el precio y el cierre.
        alAceptar(resumen);
        alRelectura();
        setAviso(`Insumo de la línea ${modo.linea.indice + 1} cambiado: ${descripcion}.`);
        cerrar(false);
        enfocar(modo.linea.boton);
        return;
      }
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
    [modo, resembrar, alAceptar, alRelectura, cerrar, enfocar, detalle.codigo],
  );

  // Cerrar sin cambios: «Agregar línea» devuelve el foco a su botón; «Cambiar», al de la línea que lo abrió.
  const alCerrarElDialogo = () => {
    if (modo.tipo === "cambiar") {
      cerrar(false);
      enfocar(modo.linea.boton);
    } else {
      cerrar(true);
    }
  };

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
        {conTitulo && (
          <h2 className="cds--type-heading-compact-02">
            {detalle.codigo} · {detalle.descripcion} · {detalle.unidad}
          </h2>
        )}
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
              alCambiarInsumo={(linea) => {
                setAviso("");
                setModo({ tipo: "cambiar", linea });
                abrir();
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
                  setModo({ tipo: "agregar" });
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
          <LineaDelApu
            modo={modo}
            id={id}
            partida={detalle.codigo}
            moneda={moneda}
            anfitrion={anfitrion}
            revActual={esperarEnvios}
            alAceptar={alAceptada}
            alCerrar={alCerrarElDialogo}
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

// El APU de `partida` en el borrador abierto, leído aquí: la forma con que lo abre el panel lateral de «Partidas». Si el
// servidor no la tiene entre las valoradas, su vista trae otra (la primera de la lista): entonces se dice, no se edita otra.
export function EditorDeApu({
  borrador,
  partida,
  alAceptar,
  alAusente,
}: {
  borrador: BorradorAbierto;
  partida: string;
  alAceptar: (r: Resumen) => void;
  alAusente: () => void;
}): JSX.Element {
  const { refrescar, reabrirNuevo } = useHojaDeLaObra();
  // Sube cada vez que hay que volver a leer la vista tras una edición: la anterior sigue a la vista mientras llega.
  const [lecturas, setLecturas] = useState(0);
  const alRelectura = useCallback(() => setLecturas((n) => n + 1), []);
  return (
    <VistaCarga<VistaApu> ruta={rutaDeVista(borrador.id, "apu", { partida })} etiqueta="APU" alAusente={alAusente} recarga={lecturas}>
      {(vista, actualizando) =>
        vista.detalle !== null && vista.detalle.codigo === partida ? (
          <div className="silice-hoja__apu-en-panel" aria-busy={actualizando}>
            <EditorDelDetalle
              id={borrador.id}
              rev={borrador.resumen.rev}
              moneda={borrador.resumen.moneda}
              base={borrador.base}
              detalle={vista.detalle}
              alAusente={alAusente}
              alAceptar={alAceptar}
              alRecargarBorrador={refrescar}
              alReabrir={reabrirNuevo}
              alRelectura={alRelectura}
              conTitulo={false}
            />
          </div>
        ) : (
          <p className="cds--type-body-compact-01">{vista.vacio_mensaje ?? `${partida} no tiene análisis de precio en este presupuesto.`}</p>
        )
      }
    </VistaCarga>
  );
}
