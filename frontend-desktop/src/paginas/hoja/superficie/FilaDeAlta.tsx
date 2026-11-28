import { Button } from "@carbon/react";
import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import type { FormEvent, JSX } from "react";
import { ErrorDeApi, pedir } from "../../../api/cliente";
import { useAnunciar } from "../../../comun/Anunciador";
import { AreaTexto } from "../../../comun/AreaTexto";
import { CampoConBusqueda } from "../../../comun/CampoConBusqueda";
import { CampoDeCifra } from "../../../comun/CampoDeCifra";
import { CampoTexto } from "../../../comun/CampoTexto";
import { InlineNotification } from "../../../comun/carbonEs";
import { mensajeDeError } from "../../../comun/errores";
import { buscadorDePartidas } from "../../../comun/logicaBusqueda";
import type { PartidaHallada } from "../../../comun/logicaBusqueda";
import { useFocoEnPrimerError } from "../../../comun/useFocoEnPrimerError";
import { useAplicacion } from "../../../shell/contexto";
import { useFormularioSucio } from "../../../shell/sucio";
import type { PartidaCompuesta } from "../../componer/ComponerPartida";
import type { PartidaPorComponer } from "../ComponerEnPanel";
import { Parecidas } from "../Parecidas";
import { cuerpoDeAgregarPartida, esBorradorAusente, rutaDeAgregarPartida } from "../logica";
import { claseDeConflicto } from "../logicaSecciones";
import {
  AYUDA_CALCULO,
  AYUDA_NOTA,
  AYUDA_PARTIDA,
  PASOS_SIN_RESULTADO,
  SIN_ERRORES,
  anuncioDePartidaAgregada,
  ayudaDeCantidad,
  descripcionParaParecidas,
  estadoInicialDeAlta,
  estaVacioCifra,
  etiquetaDeCantidad,
  leerPartidaAgregada,
  resumenDeCalculoYNota,
  rotuloCrearPartida,
  siguiente,
  solicitudDeCreacion,
} from "./altaDePartida";
import type {
  ErroresDeAlta,
  EstadoDeAlta,
  EventoDeAlta,
  PartidaAgregadaRespuesta,
  ResultadoDePartidaAgregada,
  TransicionDeAlta,
} from "./altaDePartida";
import "./filaDeAlta.scss";

// Fila de alta en línea bajo la grilla del Presupuesto (lote B1-8, ficha-b1 §1.6 a §1.10).
// Guías `forms` (no deshabilitar el botón para validar; sí al enviar para evitar doble POST),
// `validate-input-after-interaction` (CampoDeCifra valida al salir) y `accessible-error-announcement`
// (useFocoEnPrimerError mueve el foco al primer campo inválido al fallar).

export interface PropiedadesDeFilaDeAlta {
  readonly borradorId: string;
  readonly revActual: () => Promise<number>;
  readonly alAgregada: (agregada: ResultadoDePartidaAgregada) => void;
  readonly alAusente: () => void;
  readonly alReleer: () => Promise<void>;
  readonly alCrearPartida?: ((partida: PartidaPorComponer) => void) | undefined;
  readonly partidaInicial?: PartidaCompuesta | null | undefined;
  readonly alConsumirPartidaInicial?: (() => void) | undefined;
  readonly solicitudDeFocoEnPartida?: number | undefined;
  readonly dominio?: string | undefined;
}

/** Fila en línea para buscar o crear una partida, indicar su cantidad (o cálculo y nota) y agregarla al borrador. */
export function FilaDeAlta({
  borradorId,
  revActual,
  alAgregada,
  alAusente,
  alReleer,
  alCrearPartida,
  partidaInicial = null,
  alConsumirPartidaInicial,
  solicitudDeFocoEnPartida,
  dominio,
}: PropiedadesDeFilaDeAlta): JSX.Element {
  const { alExpirar } = useAplicacion();
  const anunciar = useAnunciar();
  const enfocarPrimerError = useFocoEnPrimerError();
  const buscar = useMemo(() => buscadorDePartidas(dominio), [dominio]);

  const idBase = useId();
  const idTitulo = `${idBase}-titulo`;
  const idPartida = `${idBase}-partida`;
  const idCantidad = `${idBase}-cantidad`;
  const idCalculo = `${idBase}-calculo`;
  const idNota = `${idBase}-nota`;

  const [estado, setEstado] = useState<EstadoDeAlta>(() => estadoInicialDeAlta(partidaInicial));
  const [prevBorradorId, setPrevBorradorId] = useState(borradorId);
  const [inicialAplicado, setInicialAplicado] = useState<PartidaCompuesta | null>(partidaInicial);
  const estadoRef = useRef<EstadoDeAlta>(estado);
  const [focoCantidad, setFocoCantidad] = useState(0);

  if (borradorId !== prevBorradorId) {
    setPrevBorradorId(borradorId);
    setInicialAplicado(partidaInicial);
    setEstado(estadoInicialDeAlta(partidaInicial));
  } else if (partidaInicial !== inicialAplicado) {
    setInicialAplicado(partidaInicial);
    if (partidaInicial !== null) {
      setEstado((actual) => siguiente(actual, { tipo: "fijarPartidaInicial", partida: partidaInicial }).estado);
    }
  }

  const refPartida = useRef<HTMLInputElement | null>(null);
  const asignarContenedorPartida = useCallback((nodo: HTMLDivElement | null) => {
    refPartida.current = nodo?.querySelector<HTMLInputElement>('input[role="combobox"]') ?? null;
  }, []);
  const refCantidad = useRef<HTMLInputElement>(null);
  const refCalculo = useRef<HTMLInputElement>(null);
  const refGeneral = useRef<HTMLDivElement>(null);

  const montado = useRef(true);
  const envioEnCurso = useRef(0);
  const ultimoEnfocado = useRef<PartidaCompuesta | null>(null);

  useEffect(() => {
    estadoRef.current = estado;
  }, [estado]);

  const despachar = useCallback((evento: EventoDeAlta): TransicionDeAlta => {
    const transicion = siguiente(estadoRef.current, evento);
    estadoRef.current = transicion.estado;
    setEstado(transicion.estado);
    return transicion;
  }, []);

  const aplicarFocoDeError = useCallback(
    (errores: ErroresDeAlta) => {
      enfocarPrimerError([
        { error: errores.partida, ref: refPartida },
        { error: errores.cantidad, ref: refCantidad },
        { error: errores.calculo, ref: refCalculo },
        { error: errores.general, ref: refGeneral },
      ]);
    },
    [enfocarPrimerError],
  );

  useFormularioSucio(
    "hoja",
    estado.cantidad.trim() !== "" || estado.calculo.trim() !== "" || estado.nota.trim() !== "",
  );

  useEffect(() => {
    montado.current = true;
    return () => {
      montado.current = false;
    };
  }, []);

  useEffect(() => {
    envioEnCurso.current += 1;
  }, [borradorId]);

  // Al llegar desde Componer o tras guardar en el inspector de creación: enfoca Cantidad una vez por partida recibida.
  useEffect(() => {
    if (partidaInicial === null) {
      ultimoEnfocado.current = null;
      return;
    }
    if (ultimoEnfocado.current === partidaInicial) return;
    ultimoEnfocado.current = partidaInicial;
    refCantidad.current?.focus();
    alConsumirPartidaInicial?.();
  }, [partidaInicial, alConsumirPartidaInicial]);

  useEffect(() => {
    if (focoCantidad === 0) return;
    refCantidad.current?.focus();
  }, [focoCantidad]);

  useEffect(() => {
    if (solicitudDeFocoEnPartida === undefined || solicitudDeFocoEnPartida === 0) return;
    refPartida.current?.focus();
    refPartida.current?.scrollIntoView?.({ block: "nearest", inline: "nearest" });
  }, [solicitudDeFocoEnPartida]);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const transicion = despachar({ tipo: "enviar" });
    if (transicion.efecto === null) return;
    if (transicion.efecto.tipo === "enfocarErrores") {
      if (transicion.estado.fase === "error") aplicarFocoDeError(transicion.estado.errores);
      return;
    }
    if (transicion.efecto.tipo !== "postPartida") return;

    const escrito = transicion.efecto.partida;
    const turno = ++envioEnCurso.current;
    try {
      const rev = await revActual();
      if (!montado.current || turno !== envioEnCurso.current) return;
      const respuesta = await pedir<PartidaAgregadaRespuesta>(rutaDeAgregarPartida(borradorId), {
        metodo: "POST",
        cuerpo: cuerpoDeAgregarPartida(rev, escrito),
        leer: leerPartidaAgregada,
      });
      if (!montado.current || turno !== envioEnCurso.current) return;
      despachar({ tipo: "exito" });
      anunciar(anuncioDePartidaAgregada(escrito.codigo, respuesta.resumen, respuesta.aviso));
      alAgregada({
        rev: respuesta.rev,
        resumen: respuesta.resumen,
        clave: respuesta.clave,
        codigo: escrito.codigo,
        aviso: respuesta.aviso,
      });
    } catch (e) {
      if (!montado.current || turno !== envioEnCurso.current) return;
      if (e instanceof ErrorDeApi && e.estado === 401) {
        despachar({ tipo: "abortadoPorSesionOBorrador" });
        alExpirar();
        return;
      }
      if (esBorradorAusente(e)) {
        despachar({ tipo: "abortadoPorSesionOBorrador" });
        alAusente();
        return;
      }
      if (e instanceof ErrorDeApi && e.estado === 422) {
        const fallo = despachar({ tipo: "rechazo422", detalle: e.detalle });
        if (fallo.estado.fase === "error") aplicarFocoDeError(fallo.estado.errores);
        return;
      }
      if (e instanceof ErrorDeApi && e.estado === 404) {
        const fallo = despachar({ tipo: "fueraDeCatalogo", detalle: e.detalle });
        if (fallo.estado.fase === "error") aplicarFocoDeError(fallo.estado.errores);
        return;
      }
      if (e instanceof ErrorDeApi && e.estado === 409 && claseDeConflicto(e.detalle) === "rev") {
        const fallo = despachar({ tipo: "conflictoRev", detalle: e.detalle });
        if (fallo.estado.fase === "error") aplicarFocoDeError(fallo.estado.errores);
        await alReleer();
        return;
      }
      const fallo = despachar({ tipo: "falloGeneral", mensaje: mensajeDeError(e) });
      if (fallo.estado.fase === "error") aplicarFocoDeError(fallo.estado.errores);
    }
  }

  const enviando = estado.fase === "enviando";
  const errores = estado.fase === "error" ? estado.errores : SIN_ERRORES;
  const textoParecidas = descripcionParaParecidas(estado.elegida, estado.texto);
  const mostrarParecidas = textoParecidas.trim() !== "";

  return (
    <section className="silice-fila-alta">
      <h2 id={idTitulo} className="cds--visually-hidden cds--type-heading-compact-02">
        Agregar partida al presupuesto
      </h2>
      <form
        className="silice-fila-alta__formulario"
        aria-labelledby={idTitulo}
        method="post"
        noValidate
        onSubmit={(e) => void enviar(e)}
      >
        <div className="silice-fila-alta__principal">
          <div ref={asignarContenedorPartida} className="silice-fila-alta__partida">
            <CampoConBusqueda<PartidaHallada>
              key={`partida-${estado.reinicios}`}
              id={idPartida}
              etiqueta="Partida"
              ayuda={AYUDA_PARTIDA}
              texto={estado.texto}
              alCambiarTexto={(texto) => despachar({ tipo: "cambiarTextoPartida", texto })}
              buscar={buscar}
              alElegir={(opcion) => {
                despachar({
                  tipo: "elegirPartida",
                  partida: {
                    codigo: opcion.valor.codigo,
                    descripcion: opcion.valor.descripcion,
                    unidad: opcion.valor.unidad === "" ? null : opcion.valor.unidad,
                  },
                });
              }}
              valorPropio={
                alCrearPartida !== undefined
                  ? {
                      rotulo: rotuloCrearPartida,
                      alUsar: (texto) => alCrearPartida(solicitudDeCreacion(texto)),
                      esEleccion: false,
                    }
                  : undefined
              }
              vacio={{ titulo: "¿No la encuentra?", pasos: PASOS_SIN_RESULTADO }}
              alExpirar={alExpirar}
              invalido={errores.partida !== null}
              textoInvalido={errores.partida ?? undefined}
              deshabilitado={enviando}
              tamano="md"
            />
          </div>
          <div className="silice-fila-alta__cantidad">
            <CampoDeCifra
              key={`cantidad-${estado.reinicios}`}
              ref={refCantidad}
              id={idCantidad}
              size="md"
              labelText={etiquetaDeCantidad(estado.elegida)}
              helperText={ayudaDeCantidad(estado.calculoVisto, estado.calculo, estado.cantidad)}
              value={estado.cantidad}
              obligatorio={estaVacioCifra(estado.calculo)}
              validar={() => errores.cantidad}
              mostrarError={errores.cantidad !== null}
              disabled={enviando}
              onChange={(valor) => despachar({ tipo: "cambiarCantidad", valor })}
            />
          </div>
          <div className="silice-fila-alta__accion">
            <Button kind="tertiary" size="md" type="submit" disabled={enviando} aria-busy={enviando}>
              Agregar al presupuesto
            </Button>
            {enviando && (
              <span className="silice-fila-alta__enviando cds--type-helper-text-01">
                <progress aria-label="Agregando partida" className="silice-fila-alta__progreso" />
                Agregando…
              </span>
            )}
          </div>
        </div>

        <details
          className="silice-fila-alta__pliegue"
          open={estado.pliegueAbierto}
          onToggle={(e) => despachar({ tipo: "alternarPliegue", abierto: e.currentTarget.open })}
        >
          <summary className="cds--type-body-compact-01">
            {resumenDeCalculoYNota(estado.calculo, estado.nota)}
          </summary>
          <div className="silice-fila-alta__opcionales">
            <CampoTexto
              id={idCalculo}
              ref={refCalculo}
              labelText="Cálculo (opcional)"
              helperText={AYUDA_CALCULO}
              size="md"
              autoComplete="off"
              maxLength={500}
              value={estado.calculo}
              invalid={errores.calculo !== null}
              invalidText={errores.calculo ?? ""}
              {...(errores.calculo !== null ? { "aria-describedby": `${idCalculo}-error-msg` } : {})}
              disabled={enviando}
              onChange={(e) => despachar({ tipo: "cambiarCalculo", valor: e.target.value })}
              onBlur={() => despachar({ tipo: "verCalculo" })}
            />
            <AreaTexto
              id={idNota}
              labelText="Nota de medición (opcional)"
              helperText={AYUDA_NOTA}
              rows={2}
              maxLength={500}
              value={estado.nota}
              disabled={enviando}
              onChange={(e) => despachar({ tipo: "cambiarNota", valor: e.target.value })}
            />
          </div>
        </details>
      </form>

      {errores.general !== null && (
        <div ref={refGeneral} tabIndex={-1} className="silice-fila-alta__error-general">
          <InlineNotification
            kind="error"
            role="alert"
            lowContrast
            hideCloseButton
            title="Error al agregar la partida"
            subtitle={errores.general}
          />
        </div>
      )}

      {mostrarParecidas && (
        <div className="silice-fila-alta__parecidas">
          <Parecidas
            key={`parecidas-${estado.reinicios}`}
            descripcion={textoParecidas}
            alUsar={(partida) => {
              const transicion = despachar({ tipo: "elegirPartida", partida, enfocarCantidad: true });
              if (transicion.efecto?.tipo === "enfocarCantidad") {
                setFocoCantidad((n) => n + 1);
              }
            }}
            deshabilitado={enviando}
          />
        </div>
      )}
    </section>
  );
}
