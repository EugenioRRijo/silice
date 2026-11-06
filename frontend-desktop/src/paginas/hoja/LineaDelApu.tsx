import { Button, Select, SelectItem } from "@carbon/react";
import { InlineNotification } from "../../comun/carbonEs";
import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { createPortal } from "react-dom";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { CampoConBusqueda } from "../../comun/CampoConBusqueda";
import type { GrupoDeResultados } from "../../comun/CampoConBusqueda";
import { CampoTexto } from "../../comun/CampoTexto";
import { mensajeDeError } from "../../comun/errores";
import { AYUDA_CIFRAS } from "../../indicadores/cifraEscrita";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { useFormularioSucio } from "../../shell/sucio";
import { useAtraparFoco } from "../../shell/useAtraparFoco";
import { CampoDeUnidad } from "../componer/CampoDeUnidad";
import { esBorradorAusente } from "./logica";
import type { Resumen } from "./logica";
import {
  TIPOS_DE_LINEA,
  RUBROS,
  campoDelErrorDeLinea,
  cuerpoDeInsumo,
  cuerpoDeLinea,
  grupoDelTipo,
  rutaDeInsumo,
  rutaDeInsumos,
  rutaDeLineas,
} from "./logicaApu";
import type { CampoDeLinea, InsumoCandidato, InsumosRespuesta, LineaApu, LineaNueva, TipoDeLinea } from "./logicaApu";
import { claseDeConflicto } from "./logicaSecciones";

const ID = "hoja-apu-linea";
const ID_INSUMO = `${ID}-insumo`;
const ID_DIALOGO = `${ID}-dialogo`;
const ID_DE_CAMPO: Record<CampoDeLinea, string> = {
  insumo: ID_INSUMO,
  unidad: `${ID}-unidad`,
  cantidad: `${ID}-cantidad`,
  precio: `${ID}-precio`,
  depreciacion: `${ID}-depreciacion`,
};

export const ELEGIR_UN_INSUMO = "Elija un insumo de la lista o escriba uno nuevo con «Insumo nuevo».";
export const ELEGIR_DE_LA_LISTA = "Elija un insumo de la lista de precios de la versión.";
const RECARGADO = "Ya se volvió a leer el borrador: puede agregar la línea otra vez.";
const RECARGADO_AL_CAMBIAR = "Ya se volvió a leer el borrador: puede cambiar el insumo otra vez.";
const AYUDA_INSUMO = "Busque en la lista de precios de la versión por una palabra de la descripción, por ejemplo «cemento».";
const AYUDA_DEPRECIACION = "La fracción del precio que cuesta un día de uso, mayor que 0 y hasta 1; por ejemplo 0,005.";

type Errores = Record<CampoDeLinea | "general", string | null>;
const SIN_ERRORES: Errores = { insumo: null, unidad: null, cantidad: null, precio: null, depreciacion: null, general: null };

// Carbon no liga el texto del error al campo inválido (solo la ayuda, y solo si es válido): se liga a mano.
function describirError(id: string, invalido: boolean): { "aria-describedby"?: string } {
  return invalido ? { "aria-describedby": `${id}-error-msg` } : {};
}

// El rótulo del precio de un insumo nuevo: el de un material o un equipo, el jornal o el precio a destajo.
function rotuloDelPrecio(tipo: TipoDeLinea, modalidad: LineaNueva["modalidad"], moneda: string): string {
  if (tipo !== "mano_obra") return `Precio (${moneda})`;
  return modalidad === "destajo" ? `Precio por unidad de la partida (${moneda})` : `Jornal diario (${moneda})`;
}

// Los insumos de la lista de la versión de un tipo, como grupo de resultados del buscador (`GET …/insumos`).
function buscadorDeInsumos(id: string, tipo: TipoDeLinea, moneda: string) {
  return (q: string, senal: AbortSignal, limite: number): Promise<GrupoDeResultados<InsumoCandidato>[]> =>
    pedir<InsumosRespuesta>(rutaDeInsumos(id, tipo, q, limite), { senal }).then((r) => [
      {
        rotulo: "Insumos de la lista de la versión",
        hayMas: r.hay_mas,
        opciones: r.insumos.map((i) => ({
          clave: `insumo:${i.codigo}`,
          principal: i.descripcion,
          secundaria: [i.codigo, i.unidad, `${formatoEsVe(i.precio.texto)} ${moneda}`].filter((s) => s !== ""),
          valor: i,
        })),
      },
    ]);
}

export interface LineaAgregada {
  resumen: Resumen;
  grupo: string;
  descripcion: string;
  cantidad: string;
}

// Los dos modos del diálogo: agregar una línea nueva o cambiar el insumo de una que ya está (su tipo y su lugar vienen fijos).
export type ModoDeLinea = { tipo: "agregar" } | { tipo: "cambiar"; linea: LineaApu };

interface Props {
  modo: ModoDeLinea;
  // El borrador y la partida cuyo APU se cambia.
  id: string;
  partida: string;
  moneda: string;
  // Dónde se pinta (fuera del resto de la página, que queda `inert`).
  anfitrion: HTMLElement;
  // El `rev` con que se manda: primero sale lo que la pestaña tenga por mandar.
  revActual: () => Promise<number>;
  // El servidor aceptó: su resumen y lo que la pestaña necesita para poner al día lo que se ve.
  alAceptar: (linea: LineaAgregada) => void;
  alCerrar: () => void;
  alAusente: () => void;
  // Vuelve a leer el borrador (su `rev`) y el APU, tras un 409 por `rev` viejo.
  alReleer: () => Promise<void>;
}

// Por qué existe (Tarea 8 del plan F4): «Agregar línea» (Tarea 26, diseño de montar un presupuesto §11 meta 5) y «Cambiar el
// insumo de una línea» (E7) eran dos formularios que pedían casi lo mismo; ahora son un solo diálogo con dos modos, y lo usa
// `EditorDeApu` en la pestaña APU y en el panel lateral. Agregar: un insumo de la lista de precios de la versión (con su
// precio) o uno nuevo con su precio tecleado. Cambiar: el tipo y la línea vienen fijos y solo se pide el insumo nuevo, de la
// lista de la versión; la línea conserva su cantidad. Lo escrito viaja tal cual y lo lee el servidor con la regla de las
// cifras; su error vuelve junto al campo que lo causó. Diálogo propio (como «Agregar partida»): foco atrapado, Esc cierra
// (primero la lista del buscador) y, mientras va la petición, no se cierra para no perder la respuesta. Pasa de 250 líneas
// porque es un formulario con dos modos que comparten estado, errores y foco; separarlos repetiría ese manejo.
export function LineaDelApu({ modo, id, partida, moneda, anfitrion, revActual, alAceptar, alCerrar, alAusente, alReleer }: Props) {
  const { alExpirar } = useAplicacion();
  const cambiando = modo.tipo === "cambiar";
  const caja = useRef<HTMLDivElement>(null);
  const atrapar = useAtraparFoco(caja);
  const idTitulo = useId();
  const [tipo, setTipo] = useState<TipoDeLinea>(modo.tipo === "cambiar" ? (RUBROS[modo.linea.grupo]?.tipo ?? "material") : "material");
  const [texto, setTexto] = useState("");
  const [elegido, setElegido] = useState<InsumoCandidato | null>(null);
  // La descripción de un insumo nuevo (elegido con «Insumo nuevo «X»»).
  const [nuevo, setNuevo] = useState<string | null>(null);
  const [unidad, setUnidad] = useState("");
  const [precio, setPrecio] = useState("");
  const [cantidad, setCantidad] = useState("");
  const [depreciacion, setDepreciacion] = useState("");
  const [modalidad, setModalidad] = useState<LineaNueva["modalidad"]>("jornal");
  const [errores, setErrores] = useState<Errores>(SIN_ERRORES);
  const [enviando, setEnviando] = useState(false);
  const buscar = useMemo(() => buscadorDeInsumos(id, tipo, moneda), [id, tipo, moneda]);
  // Adónde va el foco tras un error o al elegir un insumo nuevo: mientras va la petición los campos están deshabilitados.
  const focoPendiente = useRef<string | null>(null);

  // Lo escrito en un campo que se ve cuenta como trabajo sin guardar (también la modalidad elegida); lo que el tipo o el
  // insumo elegido oculta conserva su valor pero no ensucia el formulario.
  useFormularioSucio(
    "hoja",
    [
      texto,
      cantidad,
      nuevo !== null ? precio : "",
      nuevo !== null && tipo === "material" ? unidad : "",
      tipo === "equipo" ? depreciacion : "",
    ].some((t) => t.trim() !== "") ||
      (tipo === "mano_obra" && modalidad !== "jornal"),
  );

  useEffect(() => {
    document.getElementById(ID_INSUMO)?.focus();
  }, []);

  useEffect(() => {
    if (enviando || focoPendiente.current === null) return;
    const destino = focoPendiente.current;
    focoPendiente.current = null;
    (destino === ID_DIALOGO ? caja.current : document.getElementById(destino))?.focus();
  }, [enviando, errores, nuevo]);

  const cancelar = useCallback(() => {
    if (!enviando) alCerrar();
  }, [alCerrar, enviando]);

  const alTeclear = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      e.preventDefault();
      cancelar();
      return;
    }
    atrapar(e);
  };

  const limpiar = (campo: CampoDeLinea) => setErrores((previos) => ({ ...previos, [campo]: null }));

  const linea = (): LineaNueva => ({
    tipo,
    insumo: elegido?.codigo ?? "",
    descripcion: elegido === null ? (nuevo ?? "") : "",
    unidad: elegido === null && tipo === "material" ? unidad : "",
    cantidad,
    precio: elegido === null ? precio : "",
    depreciacion: tipo === "equipo" ? depreciacion : "",
    modalidad: tipo === "mano_obra" ? modalidad : "jornal",
  });

  async function aceptar(evento: FormEvent) {
    evento.preventDefault();
    if (enviando) return;
    if (elegido === null && (cambiando || nuevo === null)) {
      setErrores({ ...SIN_ERRORES, insumo: cambiando ? ELEGIR_DE_LA_LISTA : ELEGIR_UN_INSUMO });
      focoPendiente.current = ID_INSUMO;
      return;
    }
    setErrores(SIN_ERRORES);
    setEnviando(true);
    const escrita = linea();
    try {
      const rev = await revActual();
      const r =
        modo.tipo === "cambiar" && elegido !== null
          ? await pedir<{ rev: number; resumen: Resumen }>(rutaDeInsumo(id, partida), {
              metodo: "POST",
              cuerpo: cuerpoDeInsumo(rev, tipo, modo.linea.indice, elegido.codigo),
            })
          : await pedir<{ rev: number; resumen: Resumen }>(rutaDeLineas(id, partida), {
              metodo: "POST",
              cuerpo: cuerpoDeLinea(rev, escrita),
            });
      alAceptar({
        resumen: r.resumen,
        grupo: grupoDelTipo(tipo),
        descripcion: elegido?.descripcion ?? nuevo ?? "",
        cantidad,
      });
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) {
        alExpirar();
      } else if (esBorradorAusente(e)) {
        alCerrar();
        alAusente();
      } else if (e instanceof ErrorDeApi && e.estado === 422) {
        const campo = campoDelErrorDeLinea(e.detalle);
        setErrores({ ...SIN_ERRORES, [campo ?? "general"]: e.detalle });
        focoPendiente.current = campo === null ? ID_DIALOGO : ID_DE_CAMPO[campo];
      } else if (e instanceof ErrorDeApi && e.estado === 409 && claseDeConflicto(e.detalle) === "rev") {
        setErrores({ ...SIN_ERRORES, general: `${e.detalle} ${cambiando ? RECARGADO_AL_CAMBIAR : RECARGADO}` });
        focoPendiente.current = ID_DIALOGO;
        await alReleer();
      } else {
        // 404 (la partida ya no tiene APU), 409 (sin versión guardada), la base: van al aviso, tal cual.
        setErrores({ ...SIN_ERRORES, general: mensajeDeError(e) });
        focoPendiente.current = ID_DIALOGO;
      }
    } finally {
      setEnviando(false);
    }
  }

  const campoTexto = (campo: CampoDeLinea, rotulo: string, valor: string, cambiar: (t: string) => void, ayuda?: string) => (
    <CampoTexto
      id={ID_DE_CAMPO[campo]}
      labelText={rotulo}
      helperText={ayuda}
      size="md"
      autoComplete="off"
      maxLength={500}
      value={valor}
      invalid={errores[campo] !== null}
      invalidText={errores[campo] ?? ""}
      {...describirError(ID_DE_CAMPO[campo], errores[campo] !== null)}
      disabled={enviando}
      onChange={(e) => {
        cambiar(e.target.value);
        limpiar(campo);
      }}
    />
  );

  const unidadDeLaCantidad = elegido !== null && elegido.unidad !== "" ? ` (${elegido.unidad})` : "";

  return createPortal(
    <div className="silice-hoja__dialogo-fondo">
      <div
        ref={caja}
        id={ID_DIALOGO}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        tabIndex={-1}
        onKeyDown={alTeclear}
        className="silice-hoja__dialogo silice-hoja__dialogo--operacion"
      >
        <h2 id={idTitulo} className="cds--type-heading-compact-02">
          {modo.tipo === "cambiar" ? `Cambiar el insumo de ${modo.linea.descripcion}` : "Agregar una línea"}
        </h2>
        <p className="cds--type-body-compact-01">
          {modo.tipo === "cambiar"
            ? `Partida ${partida}, línea ${modo.linea.indice + 1} de ${RUBROS[modo.linea.grupo]?.enFrase ?? modo.linea.grupo}. Conserva su cantidad; el cambio es en la copia de esta versión.`
            : `Partida ${partida}. La línea se agrega en la copia de esta versión; el catálogo no cambia.`}
        </p>
        <form id={`${ID}-formulario`} className="silice-hoja__campos-operacion" noValidate onSubmit={(e) => void aceptar(e)}>
          {!cambiando && (
            <Select
              id={`${ID}-tipo`}
              labelText="Tipo de línea"
              size="md"
              value={tipo}
              disabled={enviando}
              onChange={(e) => {
                setTipo(e.target.value as TipoDeLinea);
                setTexto("");
                setElegido(null);
                setNuevo(null);
                setErrores(SIN_ERRORES);
              }}
            >
              {TIPOS_DE_LINEA.map((t) => (
                <SelectItem key={t.valor} value={t.valor} text={t.rotulo} />
              ))}
            </Select>
          )}
          <CampoConBusqueda<InsumoCandidato>
            id={ID_INSUMO}
            etiqueta="Insumo"
            ayuda={AYUDA_INSUMO}
            texto={texto}
            alCambiarTexto={(t) => {
              setTexto(t);
              setElegido(null);
              setNuevo(null);
              limpiar("insumo");
            }}
            buscar={buscar}
            alElegir={(opcion) => {
              setElegido(opcion.valor);
              setNuevo(null);
              setTexto(opcion.valor.descripcion);
              limpiar("insumo");
            }}
            valorPropio={
              cambiando
                ? undefined
                : {
                    rotulo: (t) => `Insumo nuevo «${t.trim()}»`,
                    alUsar: (t) => {
                      setNuevo(t.trim());
                      setElegido(null);
                      setTexto(t.trim());
                      limpiar("insumo");
                      focoPendiente.current = tipo === "material" ? ID_DE_CAMPO.unidad : ID_DE_CAMPO.precio;
                    },
                  }
            }
            vacio={{
              titulo: "¿No lo encuentra?",
              pasos: cambiando
                ? "Pruebe con otra palabra de la descripción: el insumo nuevo debe estar en la lista de precios de la versión."
                : "Pruebe con otra palabra de la descripción o use «Insumo nuevo» para escribir su precio.",
            }}
            alExpirar={alExpirar}
            invalido={errores.insumo !== null}
            textoInvalido={errores.insumo ?? undefined}
            deshabilitado={enviando}
            tamano="md"
          />
          {elegido !== null && (
            <p className="cds--type-helper-text-01">
              Precio de la lista de la versión: {formatoEsVe(elegido.precio.texto)} {moneda}
              {elegido.unidad !== "" ? ` por ${elegido.unidad}` : ""}
            </p>
          )}
          {nuevo !== null && tipo === "material" && (
            <CampoDeUnidad
              id={ID_DE_CAMPO.unidad}
              etiqueta="Unidad"
              ayuda="Elija una del catálogo o escriba la suya, por ejemplo m3, kg o saco."
              texto={unidad}
              alCambiar={(t) => {
                setUnidad(t);
                limpiar("unidad");
              }}
              alExpirar={alExpirar}
              invalido={errores.unidad !== null}
              textoInvalido={errores.unidad ?? undefined}
              deshabilitado={enviando}
              tamano="md"
            />
          )}
          {nuevo !== null && campoTexto("precio", rotuloDelPrecio(tipo, modalidad, moneda), precio, setPrecio, AYUDA_CIFRAS)}
          {!cambiando && tipo === "mano_obra" && (
            <Select
              id={`${ID}-modalidad`}
              labelText="Modalidad"
              size="md"
              value={modalidad}
              disabled={enviando}
              onChange={(e) => setModalidad(e.target.value === "destajo" ? "destajo" : "jornal")}
            >
              <SelectItem value="jornal" text="Jornal (por día, entre el rendimiento)" />
              <SelectItem value="destajo" text="Destajo (por unidad de la partida)" />
            </Select>
          )}
          {!cambiando && tipo === "equipo" && campoTexto("depreciacion", "Depreciación", depreciacion, setDepreciacion, AYUDA_DEPRECIACION)}
          {!cambiando && campoTexto("cantidad", `Cantidad${unidadDeLaCantidad}`, cantidad, setCantidad, AYUDA_CIFRAS)}
        </form>
        <p className="cds--type-helper-text-01" aria-live="polite">
          {enviando ? (cambiando ? "Cambiando el insumo en el borrador…" : "Agregando la línea al borrador…") : ""}
        </p>
        {errores.general !== null && (
          <InlineNotification
            kind="error"
            role="alert"
            lowContrast
            hideCloseButton
            title={cambiando ? "No se cambió el insumo" : "No se agregó la línea"}
            subtitle={errores.general}
          />
        )}
        <div className="silice-hoja__acciones">
          <Button kind="secondary" size="md" disabled={enviando} onClick={cancelar}>
            Cancelar
          </Button>
          <Button kind="primary" size="md" type="submit" form={`${ID}-formulario`} disabled={enviando}>
            {cambiando ? "Usar este insumo" : "Agregar al APU"}
          </Button>
        </div>
      </div>
    </div>,
    anfitrion,
  );
}
