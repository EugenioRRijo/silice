import { Button } from "@carbon/react";
import { Add } from "@carbon/icons-react";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { pedir } from "../../api/cliente";
import { unidadEscrita } from "../../comun/unidades";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { ConfirmarQuitar, DialogoAgregarPartida, useFocoAlCerrar } from "./AgregarPartida";
import { AvisoDeEdicion, AvisoDeEnvio } from "./AvisoDeEdicion";
import { AyudaDePestana } from "./AyudaDePestana";
import { CampoDeCelda } from "./CampoDeCelda";
import { Cifra } from "./Cifra";
import { EstadoDeFila } from "./EstadoDeFila";
import { IvaDelPresupuesto, parrafosDeAyudaDelIva } from "./IvaDelPresupuesto";
import { useObjetivosDeMercado } from "./ObjetivoDeMercado";
import { PanelDeApu } from "./PanelDeApu";
import type { PartidaDelPanel } from "./PanelDeApu";
import { useHojaDeLaObra } from "./ProveedorDeLaHoja";
import type { FilaDensa } from "../../comun/TablaDensa";
import { TablaPaginada } from "./TablaPaginada";
import { VistaCarga } from "./VistaCarga";
import { esFilaAfectada } from "./pasoDelPresupuesto";
import { clavesDeAuditoria, comoSeMidio, enteroDeDigitos, rutaDeQuitarPartida, rutaDeVista } from "./logica";
import { rotuloDeOrigen } from "../../comun/rotuloDeOrigen";
import type { BaseAbierta, FilaPresupuesto, Resumen, VistaPresupuesto } from "./logica";
import {
  FRASES_DE_RECHAZO,
  cambiarCantidad,
  cuerpoDeCantidades,
  resembrarCantidades,
  rutaDeCantidades,
  sembrarCantidades,
  ubicarErrorDeCantidad,
} from "./logicaSecciones";
import type { EdicionDeCantidades } from "./logicaSecciones";
import { useDialogoDeOperacion } from "./useDialogoDeOperacion";
import { useEdicionDeSeccion } from "./useEdicionDeSeccion";
import { usePuedeEditarLaHoja } from "./puedeEditar";

// La pestaña «Partidas» del Presupuesto. Pasa de 250 líneas (≈470) porque junta tres capas que comparten el motor de
// edición y el foco: la tabla editable de cantidades (`EditorDePresupuesto`, con `useEdicionDeSeccion`), el contenido con
// los diálogos de agregar y quitar partida (`ContenidoPresupuesto`, que devuelve el foco a «Agregar partida» o a la fila) y
// el panel lateral del APU (`PestanaPresupuesto`, Tarea 7). Partirla pasaría el motor, la espera y el foco por props entre
// tres archivos sin quitar líneas (menores 3 de la Tarea 7 y 5 de la Tarea 5, cierre de F4).

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
  // La franja del Presupuesto pidió «Agregar la primera partida» (Tarea 5 del plan F4): la pestaña abre su diálogo en
  // cuanto tiene la vista y avisa que lo atendió (así volver a la pestaña no lo abre otra vez).
  pedirAgregar?: boolean;
  alAtenderAgregar?: () => void;
}

interface PropsContenido extends Props {
  vista: VistaPresupuesto;
  alRelectura: () => void;
  // Tarea 7 del plan F4: el código de una fila abre su APU en el panel lateral.
  alAbrirApu: (p: PartidaDelPanel) => void;
}

interface PropsEditor extends PropsContenido {
  // El editor le da a la pestaña cómo esperar lo que tiene por mandar (antes de agregar una partida).
  registrarEspera: (esperar: (() => Promise<number>) | null) => void;
  // Se quitó la partida `codigo`: la pestaña lo dice y lleva el foco a «Agregar partida».
  alQuitada: (codigo: string) => void;
  // Lleva el foco a un elemento cuando ya no queda ningún diálogo abierto.
  enfocar: (id: string) => void;
  // F4 2b: sin permiso, la cantidad es texto y no hay «Volver a la calculada» ni «Quitar».
  puedeEditar: boolean;
}

const PENDIENTE = "Pendiente";
// Sin partidas no se pinta el IVA ni su ayuda (Tarea 5b): una sola regla para la sección y para «¿Qué es esto?».
const llevaIva = (vista: VistaPresupuesto) => vista.filas.length > 0;
const ID_AGREGAR = "hoja-agregar-partida-boton";

const idDeCantidad = (n: number | string) => `hoja-cantidades-${n}`;
const idDeQuitar = (n: number | string) => `hoja-quitar-${n}`;

// «Cómo se midió»: el cálculo (en Plex Mono, como se escribió) y la nota; sin ninguno, de dónde sale la cantidad.
function Medicion({ fila }: { fila: Pick<FilaPresupuesto, "quitable" | "calculo" | "nota" | "de_tramo"> }) {
  const { calculo, nota, texto } = comoSeMidio(fila);
  return (
    <div className="silice-hoja__medicion">
      {calculo !== null && (
        <span>
          <span className="cds--visually-hidden">Cálculo: </span>
          <span className="silice-codigo">{calculo}</span>
        </span>
      )}
      {nota !== null && <span className="cds--type-helper-text-01">{nota}</span>}
      {texto !== null && <span className="cds--type-helper-text-01">{texto}</span>}
    </div>
  );
}

function EditorDePresupuesto({
  id,
  rev,
  vista,
  alAusente,
  alAceptar,
  alRecargarBorrador,
  alReabrir,
  alRelectura,
  registrarEspera,
  alQuitada,
  enfocar,
  puedeEditar,
  alAbrirApu,
}: PropsEditor) {
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
  const { error, esperarEnvios, accionarEnOrden, resembrar } = edicion;
  // Tarea 16: el objetivo de mercado de cada partida y su margen (lo calcula la API) junto al precio unitario.
  const objetivos = useObjetivosDeMercado(vista.filas, vista.moneda);
  const filaInvalida = error?.ubicacion ?? null;
  const mover = (desde: number, paso: 1 | -1) => document.getElementById(idDeCantidad(desde + paso))?.focus();
  // La fila que la persona pidió quitar: espera su confirmación.
  const [porQuitar, setPorQuitar] = useState<{ clave: string; partida: string; boton: string } | null>(null);

  useEffect(() => {
    registrarEspera(esperarEnvios);
    return () => registrarEspera(null);
  }, [registrarEspera, esperarEnvios]);

  // Se agregó o se quitó un renglón: se vuelve a sembrar conservando lo escrito y no aceptado de las demás filas (y su
  // aviso). Volver a montar el editor lo perdía.
  const claves = vista.filas.map((f) => f.clave).join("\n");
  const sembradas = useRef(claves);
  useEffect(() => {
    if (sembradas.current === claves) return;
    sembradas.current = claves;
    resembrar((estado, aceptado) => resembrarCantidades(vista.filas, estado, aceptado));
  }, [claves, vista.filas, resembrar]);

  const quitar = async () => {
    if (porQuitar === null) return;
    const { clave, partida, boton } = porQuitar;
    setPorQuitar(null);
    // Primero sale lo escrito que espera la pausa; un error (409, 422) se dice en el aviso de la sección, tal cual.
    const aceptado = await accionarEnOrden((r) => ({
      ruta: rutaDeQuitarPartida(id),
      metodo: "POST",
      cuerpo: { rev: r, clave },
      frase: "",
    }));
    if (aceptado !== null) alQuitada(partida);
    else enfocar(boton);
  };

  return (
    <>
      <AvisoDeEnvio envio={edicion.envio} />
      {error !== null && <AvisoDeEdicion error={error} id={idDelError} alRecargar={() => void edicion.recargar()} alReabrir={alReabrir} />}
      <TablaPaginada
        etiqueta="Presupuesto"
        desplazable
        // Tarea 5 del plan F4: el renglón con un hallazgo crítico, de error o de advertencia lleva el fondo de precaución; la
        // severidad sigue dicha en palabra en su Estado (el color nunca va solo).
        claseDeFila={(f) => (esFilaAfectada(f.estado_severidad || null) ? "silice-fila--afectada" : undefined)}
        columnas={[
          {
            clave: "partida",
            titulo: "Partida",
            ordenable: false,
            // El código no se parte en líneas («C-000.000.001» salía en dos). Con precio, abre su APU en el panel (Tarea 7;
            // también para quien revisa: es lectura). Sin precio no hay APU que abrir (el servidor daría el de otra partida).
            celda: (f) =>
              f.pu_texto === "" ? (
                <span className="silice-hoja__codigo">{f.partida}</span>
              ) : (
                <Button
                  kind="ghost"
                  size="sm"
                  aria-label={`Abrir el APU de ${f.partida}`}
                  onClick={() => alAbrirApu({ partida: f.partida!, descripcion: f.descripcion ?? "", unidad: f.unidad ?? "" })}
                >
                  <span className="silice-hoja__codigo">{f.partida}</span>
                </Button>
              ),
          },
          { clave: "descripcion", titulo: "Descripción", ordenable: false },
          { clave: "unidad", titulo: "Unidad", ordenable: false, celda: (f) => unidadEscrita(f.unidad ?? "") },
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
                    soloLectura={!puedeEditar}
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
                      {puedeEditar && (
                      <Button
                        kind="ghost"
                        size="sm"
                        aria-label={`Volver a la calculada, Presupuesto fila ${f.n}`}
                        onClick={() => edicion.cambiar((previo) => cambiarCantidad(previo, clave, f.calculada!))}
                      >
                        Volver a la calculada
                      </Button>
                      )}
                    </>
                  )}
                </div>
              );
            },
          },
          {
            clave: "medicion",
            titulo: "Cómo se midió",
            ordenable: false,
            celda: (f) => <Medicion fila={{ quitable: f.quitable === "si", calculo: f.calculo || null, nota: f.nota || null, de_tramo: f.de_tramo === "si" }} />,
          },
          {
            clave: "pu",
            titulo: "Precio unitario",
            numerica: true,
            ordenable: false,
            celda: (f) => (f.pu_texto === "" ? PENDIENTE : <Cifra monto={{ texto: f.pu_texto!, exacto: f.pu_exacto! }} />),
          },
          objetivos.columna,
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
          ...(puedeEditar ? [{
            clave: "quitar",
            titulo: "Quitar",
            ordenable: false,
            // Solo los renglones de la versión; los del espacio se cambian en «Espacio y metrajes».
            celda: (f: FilaDensa) =>
              f.quitable === "si" ? (
                <Button
                  id={idDeQuitar(f.n!)}
                  kind="ghost"
                  size="sm"
                  aria-label={`Quitar ${f.partida}, Presupuesto fila ${f.n}`}
                  onClick={() => setPorQuitar({ clave: f.clave!, partida: f.partida!, boton: idDeQuitar(f.n!) })}
                >
                  Quitar
                </Button>
              ) : (
                ""
              ),
          }] : []),
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
          quitable: f.quitable ? "si" : "no",
          de_tramo: f.de_tramo === true ? "si" : "no",
          calculo: f.calculo ?? "",
          nota: f.nota ?? "",
        }))}
      />
      {objetivos.aviso}
      <p className="silice-hoja__total cds--type-heading-03">
        Total del presupuesto <Cifra monto={vista.total} unidad={vista.moneda} />
      </p>
      {llevaIva(vista) && <IvaDelPresupuesto impuestos={vista.impuestos} moneda={vista.moneda} />}
      {porQuitar !== null && (
        <ConfirmarQuitar
          partida={porQuitar.partida}
          alQuitar={() => void quitar()}
          alCancelar={() => {
            enfocar(porQuitar.boton);
            setPorQuitar(null);
          }}
        />
      )}
    </>
  );
}

// La pestaña: la barra de herramientas (su explicación y «Agregar partida», también con el presupuesto vacío) y la tabla.
function ContenidoPresupuesto(props: PropsContenido) {
  const { id, rev, vista, alAceptar, alRelectura, alAusente, alRecargarBorrador, pedirAgregar, alAtenderAgregar } = props;
  const puedeEditar = usePuedeEditarLaHoja(props.base ?? null);
  const { abierto, anfitrion, abrir, cerrar, anclaDelBoton } = useDialogoDeOperacion();
  // El pedido de la franja (Tarea 5) se atiende una vez: se abre el diálogo, que es el mismo de «Agregar partida».
  useEffect(() => {
    if (!pedirAgregar) return;
    alAtenderAgregar?.();
    if (puedeEditar) abrir();
  }, [pedirAgregar, alAtenderAgregar, puedeEditar, abrir]);
  const enfocar = useFocoAlCerrar();
  const [aviso, setAviso] = useState("");
  // Con el editor montado, el `rev` sale de él (después de lo que tenga por mandar); sin renglones, de la página.
  const espera = useRef<(() => Promise<number>) | null>(null);
  const revDeLaPagina = useRef(rev);
  useEffect(() => {
    revDeLaPagina.current = rev;
  });
  const registrarEspera = useCallback((esperar: (() => Promise<number>) | null) => {
    espera.current = esperar;
  }, []);
  const revActual = useCallback(async () => (espera.current !== null ? espera.current() : revDeLaPagina.current), []);
  const alAgregada = useCallback(
    (resumen: Resumen, codigo: string) => {
      alAceptar(resumen);
      alRelectura();
      setAviso(`Se agregó ${codigo} al presupuesto.`);
      cerrar(true);
    },
    [alAceptar, alRelectura, cerrar],
  );
  const alQuitada = useCallback(
    (codigo: string) => {
      setAviso(`Se quitó ${codigo} del presupuesto.`);
      enfocar(ID_AGREGAR);
    },
    [enfocar],
  );
  // Tras un 409 por `rev` viejo: el borrador y la vista, para que la tabla no quede vieja si la persona cancela.
  const releer = useCallback(async () => {
    await alRecargarBorrador();
    alRelectura();
  }, [alRecargarBorrador, alRelectura]);

  return (
    <div className="silice-hoja__pestana">
      {/* Barra de herramientas sobre la tabla (cabecera compacta): agregar, cómo se escriben las cifras y «¿Qué es esto?». */}
      <AyudaDePestana
        id="partidas"
        puedeEditar={puedeEditar}
        extra={llevaIva(vista) ? parrafosDeAyudaDelIva(vista.impuestos) : []}
        herramientas={
          puedeEditar ? (
            <Button
              id={ID_AGREGAR}
              ref={anclaDelBoton}
              kind="tertiary"
              size="sm"
              renderIcon={Add}
              onClick={() => {
                setAviso("");
                abrir();
              }}
            >
              Agregar partida
            </Button>
          ) : null
        }
      />
      <p className="silice-hoja__region-viva cds--type-helper-text-01" role="status">
        {aviso}
      </p>
      {vista.vacio_mensaje !== null ? (
        <p className="cds--type-body-compact-01">{vista.vacio_mensaje}</p>
      ) : (
        <EditorDePresupuesto
          {...props}
          registrarEspera={registrarEspera}
          alQuitada={alQuitada}
          enfocar={enfocar}
          puedeEditar={puedeEditar}
        />
      )}
      {abierto && anfitrion !== null && (
        <DialogoAgregarPartida
          id={id}
          anfitrion={anfitrion}
          revActual={revActual}
          alAgregada={alAgregada}
          alCancelar={() => cerrar(true)}
          alAusente={alAusente}
          alReleer={releer}
        />
      )}
    </div>
  );
}

// Pestaña «Presupuesto»: la cantidad de cada renglón se edita como texto (rebanada 3c-2) y se aplica al borrador del servidor;
// las partidas del catálogo se agregan y se quitan (Tarea 11).
export function PestanaPresupuesto(props: Props) {
  // Sube cada vez que hay que volver a leer la vista tras una edición: la anterior sigue a la vista mientras llega.
  const [lecturas, setLecturas] = useState(0);
  const alRelectura = useCallback(() => setLecturas((n) => n + 1), []);
  // Tarea 7 del plan F4: el APU de una partida en el panel lateral, junto a la tabla. La partida queda elegida en el
  // proveedor, así que la pestaña APU la muestra; una edición en el panel vuelve a leer la tabla (su total cambia).
  const { elegirPartida } = useHojaDeLaObra();
  const [enPanel, setEnPanel] = useState<PartidaDelPanel | null>(null);
  const alAbrirApu = useCallback(
    (p: PartidaDelPanel) => {
      elegirPartida(p.partida);
      setEnPanel(p);
    },
    [elegirPartida],
  );
  const { alAceptar } = props;
  const alAceptarDelApu = useCallback(
    (r: Resumen) => {
      alAceptar(r);
      alRelectura();
    },
    [alAceptar, alRelectura],
  );
  return (
    <div className={enPanel === null ? undefined : "silice-con-panel"}>
      <VistaCarga<VistaPresupuesto> ruta={rutaDeVista(props.id, "presupuesto")} etiqueta="Presupuesto" alAusente={props.alAusente} recarga={lecturas}>
        {(vista) => <ContenidoPresupuesto {...props} vista={vista} alRelectura={alRelectura} alAbrirApu={alAbrirApu} />}
      </VistaCarga>
      <PanelDeApu abierta={enPanel} alCerrar={() => setEnPanel(null)} alAceptar={alAceptarDelApu} />
    </div>
  );
}
