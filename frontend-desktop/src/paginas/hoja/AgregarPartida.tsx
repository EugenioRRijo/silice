import { Button } from "@carbon/react";
import { InlineNotification } from "../../comun/carbonEs";
import { useCallback, useContext, useEffect, useId, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { createPortal } from "react-dom";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AreaTexto } from "../../comun/AreaTexto";
import { CampoConBusqueda } from "../../comun/CampoConBusqueda";
import { CampoTexto } from "../../comun/CampoTexto";
import { mensajeDeError } from "../../comun/errores";
import { buscadorDePartidas } from "../../comun/logicaBusqueda";
import type { PartidaHallada } from "../../comun/logicaBusqueda";
import { AYUDA_CIFRAS, MENSAJE_CIFRA_VACIA, leerCifra } from "../../indicadores/cifraEscrita";
import { useAplicacion } from "../../shell/contexto";
import { useFormularioSucio } from "../../shell/sucio";
import { useAtraparFoco } from "../../shell/useAtraparFoco";
import { pareceCodigo } from "../componer/codigo";
import type { PartidaCompuesta } from "../componer/ComponerPartida";
import { ComponerEnPanel } from "./ComponerEnPanel";
import type { PartidaPorComponer } from "./ComponerEnPanel";
import { ContextoDeDialogos } from "./ContextoDeDialogos";
import { DialogoDeVersion } from "./DialogoDeVersion";
import { campoDelErrorDePartida, cuerpoDeAgregarPartida, esBorradorAusente, rutaDeAgregarPartida } from "./logica";
import type { Resumen } from "./logica";
import { claseDeConflicto } from "./logicaSecciones";
import { Parecidas } from "./Parecidas";
import type { PartidaParecida } from "./Parecidas";

const ID_PARTIDA = "hoja-agregar-partida";
const ID_CANTIDAD = "hoja-agregar-cantidad";
const ID_CALCULO = "hoja-agregar-calculo";
const ID_NOTA = "hoja-agregar-nota";
const ID_DIALOGO = "hoja-agregar-dialogo";

export const ELEGIR_DE_LA_LISTA = "Elija la partida de la lista de sugerencias.";
const AYUDA_PARTIDA = "Busque por código o por una palabra de la descripción, por ejemplo «bloque».";
const PASOS_SIN_RESULTADO =
  "Pruebe con otra palabra, busque las parecidas con «Buscar parecidas» o compóngala con «Componer una partida nueva».";
const AYUDA_CALCULO = "Por ejemplo 6*3-2 o 2,5*4. Si lo escribe, Sílice puede verificar la cantidad.";
const CANTIDAD_DEL_CALCULO = "Si la deja vacía, Sílice la toma del resultado del cálculo al agregar.";
const AYUDA_NOTA = "Por ejemplo: 6 m × 35 m de muro, menos vanos.";
const RECARGADO = "Ya se volvió a leer el borrador: puede agregarla otra vez.";

interface PartidaAgregada {
  rev: number;
  resumen: Resumen;
  clave: string;
}

// La partida elegida: del catálogo, de las parecidas o recién compuesta. Sin unidad (una parecida sin desglose) la cantidad
// no dice en qué se mide.
type Elegida = Pick<PartidaHallada, "codigo" | "descripcion"> & { unidad: string | null };

const textoDeLaElegida = (p: Elegida) => (p.descripcion.trim() === "" ? p.codigo : `${p.codigo} · ${p.descripcion}`);

interface Errores {
  partida: string | null;
  cantidad: string | null;
  calculo: string | null;
  // Lo que no es de un campo (sin tasa, sin lista, `rev` viejo, la base): va en un aviso del diálogo.
  general: string | null;
}

const SIN_ERRORES: Errores = { partida: null, cantidad: null, calculo: null, general: null };

// Vacío según la regla de las cifras (recorta los mismos blancos que el servidor, `aplicacion/cifras.py`).
const estaVacio = (texto: string) => {
  const lectura = leerCifra(texto);
  return "error" in lectura && lectura.error === MENSAJE_CIFRA_VACIA;
};

// Carbon no liga el texto del error al campo inválido (solo la ayuda, y solo si es válido): se liga a mano.
function describirError(id: string, invalido: boolean): { "aria-describedby"?: string } {
  return invalido ? { "aria-describedby": `${id}-error-msg` } : {};
}

interface Props {
  // El borrador al que se agrega.
  id: string;
  // Dónde se pinta (fuera del resto de la página, que queda `inert`).
  anfitrion: HTMLElement;
  // El `rev` con que se manda: primero sale lo que la pestaña tenga por mandar.
  revActual: () => Promise<number>;
  alAgregada: (resumen: Resumen, codigo: string) => void;
  alCancelar: () => void;
  alAusente: () => void;
  // Vuelve a leer el borrador (su `rev`) y la vista, tras un 409 por `rev` viejo.
  alReleer: () => Promise<void>;
}

// «Agregar partida» (Tarea 11, diseño de montar un presupuesto §5.3 y §10): una partida del catálogo con su cantidad, el
// cálculo con que se midió (opcional) y una nota. Lo escrito viaja tal cual (`POST …/partidas` de la Tarea 9): la cantidad
// y el cálculo los interpreta el servidor con la regla de las cifras y su error vuelve junto al campo que lo causó. La
// interfaz no evalúa el cálculo: si la cantidad queda vacía, el servidor la toma del resultado. Diálogo propio (no el
// Modal de Carbon, como los demás de la Hoja): foco atrapado, Esc cierra (primero la lista del buscador, que se queda la
// tecla) y, mientras va la petición, no se cierra para no perder la respuesta.
//
// Puerta única (plan F4, Tarea 9): la partida se elige de tres maneras sin salir del diálogo: buscándola en el catálogo
// (el campo con sugerencias), con «Buscar parecidas» a lo escrito (`Parecidas`, baja 20) o componiéndola en el panel
// (`ComponerEnPanel`, baja 21). Mientras se compone, el diálogo espera oculto (un solo trabajo y un solo botón principal a
// la vista) y, al guardar, vuelve con la partida nueva elegida. El archivo pasa de 250 líneas porque junta los dos
// diálogos de las partidas del Presupuesto (agregar y quitar) y el foco que comparten al cerrarse.
export function DialogoAgregarPartida({ id, anfitrion, revActual, alAgregada, alCancelar, alAusente, alReleer }: Props) {
  const { alExpirar } = useAplicacion();
  const caja = useRef<HTMLDivElement>(null);
  const atrapar = useAtraparFoco(caja);
  const idTitulo = useId();
  const [texto, setTexto] = useState("");
  const [elegida, setElegida] = useState<Elegida | null>(null);
  // Con qué se compone una partida nueva en el panel (un código, o una descripción y el código por elegir), o null.
  const [componiendo, setComponiendo] = useState<PartidaPorComponer | null>(null);
  const [cantidad, setCantidad] = useState("");
  const [calculo, setCalculo] = useState("");
  const [nota, setNota] = useState("");
  const [calculoVisto, setCalculoVisto] = useState(false);
  const [errores, setErrores] = useState<Errores>(SIN_ERRORES);
  const [enviando, setEnviando] = useState(false);
  const [buscar] = useState(() => buscadorDePartidas());
  // Adónde va el foco tras un error: el campo, o la caja del diálogo si no es de un campo. Mientras va la petición los
  // campos y el botón están deshabilitados (no se pueden enfocar): se enfoca cuando vuelven.
  const focoPendiente = useRef<string | null>(null);

  // Lo escrito cuenta como trabajo sin guardar: salir de la obra con el diálogo abierto pregunta antes de perderlo.
  useFormularioSucio("hoja", cantidad.trim() !== "" || calculo.trim() !== "" || nota.trim() !== "");

  useEffect(() => {
    document.getElementById(ID_PARTIDA)?.focus();
  }, []);

  useEffect(() => {
    if (enviando || componiendo !== null || focoPendiente.current === null) return;
    const destino = focoPendiente.current;
    focoPendiente.current = null;
    (destino === ID_DIALOGO ? caja.current : document.getElementById(destino))?.focus();
  }, [enviando, errores, componiendo]);

  const cancelar = useCallback(() => {
    if (!enviando) alCancelar();
  }, [alCancelar, enviando]);

  const alTeclear = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      e.preventDefault();
      cancelar();
      return;
    }
    atrapar(e);
  };

  // Deja elegida una partida que no salió de la lista de sugerencias (una parecida o la recién compuesta) y lleva el foco
  // a `destino`. Cambiar los errores vuelve a pintar el diálogo, y su efecto mueve el foco.
  const elegirFueraDeLaLista = (partida: Elegida, destino: string) => {
    setElegida(partida);
    setTexto(textoDeLaElegida(partida));
    focoPendiente.current = destino;
    setErrores((previos) => ({ ...previos, partida: null }));
  };
  const usarParecida = (p: PartidaParecida) => elegirFueraDeLaLista(p, ID_CANTIDAD);
  const cerrarComponer = () => {
    focoPendiente.current = ID_PARTIDA;
    setComponiendo(null);
  };
  const alCompuesta = (p: PartidaCompuesta) => {
    elegirFueraDeLaLista({ ...p, unidad: p.unidad === "" ? null : p.unidad }, ID_PARTIDA);
    setComponiendo(null);
  };

  async function agregar(evento: FormEvent) {
    evento.preventDefault();
    if (enviando) return;
    if (elegida === null) {
      setErrores({ ...SIN_ERRORES, partida: ELEGIR_DE_LA_LISTA });
      focoPendiente.current = ID_PARTIDA;
      return;
    }
    // Sin cantidad ni cálculo no hay de dónde sacarla: se dice antes de mandar, con el texto del servidor (pasada del cierre
    // de F4, H7: Enter mandaba y solo el 422 lo decía). Con cálculo, la cantidad vacía la toma el servidor del resultado.
    if (estaVacio(cantidad) && estaVacio(calculo)) {
      setErrores({ ...SIN_ERRORES, cantidad: MENSAJE_CIFRA_VACIA });
      focoPendiente.current = ID_CANTIDAD;
      return;
    }
    setErrores(SIN_ERRORES);
    setEnviando(true);
    const escrito = { codigo: elegida.codigo, cantidad, calculo, nota };
    try {
      const rev = await revActual();
      const r = await pedir<PartidaAgregada>(rutaDeAgregarPartida(id), {
        metodo: "POST",
        cuerpo: cuerpoDeAgregarPartida(rev, escrito),
      });
      alAgregada(r.resumen, elegida.codigo);
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) {
        alExpirar();
      } else if (esBorradorAusente(e)) {
        alCancelar();
        alAusente();
      } else if (e instanceof ErrorDeApi && e.estado === 422) {
        const campo = campoDelErrorDePartida(e.detalle, escrito);
        setErrores({ ...SIN_ERRORES, ...(campo === null ? { general: e.detalle } : { [campo]: e.detalle }) });
        focoPendiente.current = campo === null ? ID_DIALOGO : campo === "calculo" ? ID_CALCULO : ID_CANTIDAD;
      } else if (e instanceof ErrorDeApi && e.estado === 404) {
        // La partida ya no está en el catálogo (el texto de la API dice que se componga primero).
        setErrores({ ...SIN_ERRORES, partida: e.detalle });
        focoPendiente.current = ID_PARTIDA;
      } else if (e instanceof ErrorDeApi && e.estado === 409 && claseDeConflicto(e.detalle) === "rev") {
        setErrores({ ...SIN_ERRORES, general: `${e.detalle} ${RECARGADO}` });
        focoPendiente.current = ID_DIALOGO;
        await alReleer();
      } else {
        setErrores({ ...SIN_ERRORES, general: mensajeDeError(e) });
        focoPendiente.current = ID_DIALOGO;
      }
    } finally {
      setEnviando(false);
    }
  }

  const unidad = elegida?.unidad ? ` (${elegida.unidad})` : "";
  const ayudaCantidad = calculoVisto && calculo.trim() !== "" && cantidad.trim() === "" ? `${CANTIDAD_DEL_CALCULO} ${AYUDA_CIFRAS}` : AYUDA_CIFRAS;

  return createPortal(
    <div className={componiendo === null ? "silice-hoja__dialogo-fondo" : "silice-hoja__dialogo-fondo silice-hoja__dialogo-fondo--con-panel"}>
      <div
        ref={caja}
        hidden={componiendo !== null}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        tabIndex={-1}
        onKeyDown={alTeclear}
        className="silice-hoja__dialogo silice-hoja__dialogo--operacion"
      >
        <h2 id={idTitulo} className="cds--type-heading-compact-02">
          Agregar partida
        </h2>
        <form id={`${ID_PARTIDA}-formulario`} className="silice-hoja__campos-operacion" noValidate onSubmit={(e) => void agregar(e)}>
          <CampoConBusqueda<PartidaHallada>
            id={ID_PARTIDA}
            etiqueta="Partida"
            ayuda={AYUDA_PARTIDA}
            texto={texto}
            alCambiarTexto={(t) => {
              setTexto(t);
              setElegida(null);
              setErrores((previos) => ({ ...previos, partida: null }));
            }}
            buscar={buscar}
            alElegir={(opcion) => {
              setElegida(opcion.valor);
              setTexto(`${opcion.valor.codigo} · ${opcion.valor.descripcion}`);
              setErrores((previos) => ({ ...previos, partida: null }));
            }}
            valorPropio={{
              // Pulido F5, Tarea 1: lo escrito solo se toma como código si lo parece («Z-99»); si no («excavación de
              // zanja»), es la descripción de la partida y el código se elige en el panel.
              rotulo: (t) =>
                pareceCodigo(t) ? `Componer una partida nueva con el código «${t}»` : `Componer una partida nueva con la descripción «${t}»`,
              alUsar: (t) => setComponiendo(pareceCodigo(t) ? { codigo: t, descripcion: "" } : { codigo: "", descripcion: t }),
            }}
            vacio={{ titulo: "¿No la encuentra?", pasos: PASOS_SIN_RESULTADO }}
            alExpirar={alExpirar}
            invalido={errores.partida !== null}
            textoInvalido={errores.partida ?? undefined}
            deshabilitado={enviando}
            tamano="md"
          />
          {/* Con una partida elegida el campo dice «código · descripción»: por parecido se busca su descripción (menor 5 de T9). */}
          <Parecidas
            descripcion={elegida !== null && elegida.descripcion.trim() !== "" ? elegida.descripcion : texto}
            alUsar={usarParecida}
            deshabilitado={enviando}
          />
          <CampoTexto
            id={ID_CANTIDAD}
            labelText={`Cantidad${unidad}`}
            helperText={ayudaCantidad}
            size="md"
            inputMode="decimal"
            autoComplete="off"
            maxLength={500}
            value={cantidad}
            invalid={errores.cantidad !== null}
            invalidText={errores.cantidad ?? ""}
            {...describirError(ID_CANTIDAD, errores.cantidad !== null)}
            disabled={enviando}
            onChange={(e) => {
              setCantidad(e.target.value);
              setErrores((previos) => ({ ...previos, cantidad: null }));
            }}
          />
          <CampoTexto
            id={ID_CALCULO}
            labelText="Cálculo (opcional)"
            helperText={AYUDA_CALCULO}
            size="md"
            autoComplete="off"
            maxLength={500}
            value={calculo}
            invalid={errores.calculo !== null}
            invalidText={errores.calculo ?? ""}
            {...describirError(ID_CALCULO, errores.calculo !== null)}
            disabled={enviando}
            onChange={(e) => {
              setCalculo(e.target.value);
              setErrores((previos) => ({ ...previos, calculo: null }));
            }}
            onBlur={() => setCalculoVisto(true)}
          />
          <AreaTexto
            id={ID_NOTA}
            labelText="Nota de medición (opcional)"
            helperText={AYUDA_NOTA}
            rows={2}
            maxLength={500}
            value={nota}
            disabled={enviando}
            onChange={(e) => setNota(e.target.value)}
          />
        </form>
        <p className="cds--type-helper-text-01" aria-live="polite">
          {enviando ? "Agregando la partida al borrador…" : ""}
        </p>
        {errores.general !== null && (
          <InlineNotification
            kind="error"
            role="alert"
            lowContrast
            hideCloseButton
            title="No se agregó la partida"
            subtitle={errores.general}
          />
        )}
        <div className="silice-hoja__acciones">
          <Button kind="secondary" size="md" disabled={enviando} onClick={cancelar}>
            Cancelar
          </Button>
          <Button kind="primary" size="md" type="submit" form={`${ID_PARTIDA}-formulario`} disabled={enviando}>
            Agregar al presupuesto
          </Button>
        </div>
      </div>
      <ComponerEnPanel partida={componiendo} alCerrar={cerrarComponer} alGuardar={alCompuesta} />
    </div>,
    anfitrion,
  );
}

interface PropsQuitar {
  partida: string;
  alQuitar: () => void;
  alCancelar: () => void;
}

// «Quitar» de una fila: la confirmación de siempre de la Hoja (`DialogoDeVersion`), pintada fuera de la página, que queda
// `inert` mientras está abierta.
export function ConfirmarQuitar({ partida, alQuitar, alCancelar }: PropsQuitar) {
  const { anfitrion, registrar } = useContext(ContextoDeDialogos);
  useEffect(() => {
    registrar(1);
    return () => registrar(-1);
  }, [registrar]);
  if (anfitrion === null) return null;
  return createPortal(
    <DialogoDeVersion
      titulo="Quitar partida"
      texto={`¿Quitar ${partida} del presupuesto? Lo puede descartar antes de guardar.`}
      textoConfirmar="Quitar"
      textoCancelar="Cancelar"
      alConfirmar={alQuitar}
      alCancelar={alCancelar}
    />,
    anfitrion,
  );
}

// Lleva el foco a un elemento cuando ya no queda ningún diálogo abierto: mientras lo hay, la página es `inert` y en un
// navegador real no se puede enfocar nada dentro (como `useDialogoDeOperacion`).
export function useFocoAlCerrar(): (id: string) => void {
  const { abiertos } = useContext(ContextoDeDialogos);
  const destino = useRef<string | null>(null);
  const [pedido, setPedido] = useState(0);
  useEffect(() => {
    if (destino.current === null || abiertos > 0) return;
    const elemento = document.getElementById(destino.current);
    destino.current = null;
    elemento?.focus();
  }, [abiertos, pedido]);
  return useCallback((id: string) => {
    destino.current = id;
    setPedido((n) => n + 1);
  }, []);
}
