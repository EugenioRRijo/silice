import { Close, WarningFilled } from "@carbon/icons-react";
import { Fragment, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { KeyboardEvent, MouseEvent } from "react";
import { createPortal } from "react-dom";
import { CampoTexto } from "./CampoTexto";
import { EstadoVacio } from "./EstadoVacio";
import {
  ESPERA_DE_BUSCANDO_MS,
  LARGO_MAXIMO,
  LIMITE_AMPLIADO,
  LIMITE_INICIAL,
  MINIMO_DE_LETRAS,
  PAUSA_MS,
  RETARDO_DEL_ANUNCIO_MS,
  entradasDeLaLista,
  esAborto,
  limiteDelGrupo,
  mensajeDeError,
  moverActiva,
  textoDelMinimo,
  textoDelResultado,
  tramosResaltados,
} from "./logicaBusqueda";
import type { Entrada, GrupoDeResultados, OpcionDeBusqueda } from "./logicaBusqueda";
import "./CampoConBusqueda.scss";

export type { GrupoDeResultados, OpcionDeBusqueda } from "./logicaBusqueda";

// Campo con busqueda (combobox con lista, ARIA 1.2; diseno de autocompletado 2026-10-21 §3). Es un selector con
// busqueda, no un cuadro que adivina: lo escrito es una busqueda y lo que queda en el campo lo decide la PAGINA (`texto`
// es suyo). Entrega la opcion elegida con `alElegir` y no guarda nada por su cuenta. Propio y no el ComboBox de Carbon
// (§4.1): ese guarda su propio texto, elige sin navegar, restaura lo escrito al salir y deja una region viva vacia.
//
// El modo local del diseno (`opciones` ya cargadas, filtradas en el navegador) no se construye aqui: lo trae el plan de
// autocompletado. Montos: `secundaria` llega ya como texto formateado por el padre; aqui no se calcula nada.
export interface CampoConBusquedaProps<T> {
  id: string;
  etiqueta: string; // visible siempre, en lenguaje llano
  ayuda?: string; // helperText bajo el campo, con ejemplo
  texto: string; // el texto del campo: lo controla la pagina
  alCambiarTexto: (texto: string) => void;
  buscar: (q: string, senal: AbortSignal, limitePorGrupo: number) => Promise<GrupoDeResultados<T>[]>;
  alElegir: (opcion: OpcionDeBusqueda<T>) => void;
  valorPropio?: {
    rotulo: (texto: string) => string; // "Crear una partida nueva con el código «LB-06»"
    alUsar: (texto: string) => void;
  };
  vacio: { titulo: string; pasos: string }; // "¿No la encuentra?" + que hacer (§3.5)
  minimoDeLetras?: number; // 2 por omision
  alSalir?: () => void; // onBlur del campo: la pagina decide que significa lo escrito
  pausaMs?: number; // 300
  limiteInicial?: number; // 8 por grupo; «Ver más resultados» pide 20
  enCelda?: boolean; // la lista va en un portal con position: fixed (una celda recorta un menu absoluto)
  alExpirar: () => void; // 401
  invalido?: boolean;
  textoInvalido?: string;
  deshabilitado?: boolean;
  soloLectura?: boolean;
  tamano?: "sm" | "md";
}

const SIN_RESULTADO_AUN = "Las sugerencias aparecen bajo el campo al dejar de escribir.";

export function CampoConBusqueda<T>({
  id,
  etiqueta,
  ayuda,
  texto,
  alCambiarTexto,
  buscar,
  alElegir,
  valorPropio,
  vacio,
  minimoDeLetras = MINIMO_DE_LETRAS,
  alSalir,
  pausaMs = PAUSA_MS,
  limiteInicial = LIMITE_INICIAL,
  enCelda = false,
  alExpirar,
  invalido = false,
  textoInvalido,
  deshabilitado = false,
  soloLectura = false,
  tamano = "sm",
}: CampoConBusquedaProps<T>) {
  const [grupos, setGrupos] = useState<GrupoDeResultados<T>[] | null>(null);
  const [buscado, setBuscado] = useState(""); // el texto de los resultados que se ven
  const [ampliados, setAmpliados] = useState<ReadonlySet<number>>(() => new Set());
  const [error, setError] = useState<string | null>(null);
  const [abierta, setAbierta] = useState(false);
  const [activa, setActiva] = useState<number | null>(null);
  const [anuncio, setAnuncio] = useState("");
  const [conFoco, setConFoco] = useState(false);

  const pausa = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const esperaDelAnuncio = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const esperaDeBuscando = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const controlador = useRef<AbortController | null>(null);
  const turno = useRef(0);
  const elegido = useRef(false); // el texto actual salio de elegir (Esc con la lista cerrada lo limpia)
  const enfocado = useRef(false);
  const panel = useRef<HTMLDivElement>(null);

  const idLista = `${id}-lista`;
  const idEstado = `${id}-estado`;
  const idOpcion = (indice: number) => `${id}-opcion-${indice}`;
  const recortado = texto.trim();
  const corto = recortado.length < minimoDeLetras;
  const conPropio = valorPropio !== undefined && recortado !== "";
  const entradas: Entrada<T>[] = grupos ? entradasDeLaLista(grupos, ampliados, limiteInicial, conPropio) : [];
  const listaVisible = abierta && entradas.length > 0;
  const sinResultados = grupos !== null && error === null && grupos.every((g) => g.opciones.length === 0);
  const panelVisible = abierta && (listaVisible || error !== null || sinResultados);
  const regionVisible = conFoco || abierta;
  const textoDeEstado = corto ? textoDelMinimo(minimoDeLetras) : anuncio || SIN_RESULTADO_AUN;

  // Ninguna peticion ni temporizador sobrevive al campo.
  useEffect(() => {
    const temporizadores = [pausa, esperaDelAnuncio, esperaDeBuscando];
    const peticion = controlador;
    return () => {
      for (const t of temporizadores) clearTimeout(t.current);
      peticion.current?.abort();
    };
  }, []);

  // La opcion activa se desplaza a la vista (§3.6).
  useEffect(() => {
    if (activa === null || !listaVisible) return;
    document.getElementById(`${id}-opcion-${activa}`)?.scrollIntoView?.({ block: "nearest" });
  }, [activa, listaVisible, id]);

  // En una celda la lista va en un portal con position: fixed bajo el campo, y se recoloca al desplazar o al cambiar
  // el tamano de la ventana (§3.7). Se escribe en el estilo del panel: medir no es estado de React.
  useLayoutEffect(() => {
    if (!enCelda || !panelVisible) return;
    const colocar = () => {
      const campo = document.getElementById(id);
      const destino = panel.current;
      if (!campo || !destino) return;
      const caja = campo.getBoundingClientRect();
      destino.style.top = `${caja.bottom}px`;
      destino.style.left = `${caja.left}px`;
      destino.style.minWidth = `${caja.width}px`;
    };
    colocar();
    window.addEventListener("scroll", colocar, true);
    window.addEventListener("resize", colocar);
    return () => {
      window.removeEventListener("scroll", colocar, true);
      window.removeEventListener("resize", colocar);
    };
  }, [enCelda, panelVisible, id]);

  function anunciar(mensaje: string) {
    clearTimeout(esperaDelAnuncio.current);
    esperaDelAnuncio.current = setTimeout(() => setAnuncio(mensaje), RETARDO_DEL_ANUNCIO_MS);
  }

  // Corta lo pendiente: la pausa, la peticion en vuelo y su respuesta (por turno, aunque no se haya podido abortar).
  function cancelar() {
    clearTimeout(pausa.current);
    clearTimeout(esperaDeBuscando.current);
    controlador.current?.abort();
    controlador.current = null;
    turno.current += 1;
  }

  function cerrar() {
    setAbierta(false);
    setActiva(null);
  }

  // `ampliar`: el grupo cuyo «Ver más resultados» se eligio y la posicion de esa opcion en la lista.
  function lanzar(q: string, limite: number, ampliar: { grupo: number; posicion: number } | null) {
    cancelar();
    const propio = new AbortController();
    controlador.current = propio;
    const mio = turno.current;
    esperaDeBuscando.current = setTimeout(() => {
      if (turno.current === mio) setAnuncio("Buscando…");
    }, ESPERA_DE_BUSCANDO_MS);
    let respuesta: Promise<GrupoDeResultados<T>[]>;
    try {
      respuesta = buscar(q, propio.signal, limite);
    } catch (e) {
      respuesta = Promise.reject(e);
    }
    const previos = grupos ?? [];
    respuesta.then(
      (nuevos) => {
        if (mio !== turno.current) return; // respuesta de una busqueda vieja
        clearTimeout(esperaDeBuscando.current);
        controlador.current = null;
        setError(null);
        setBuscado(q);
        setAbierta(enfocado.current);
        if (ampliar === null) {
          setGrupos(nuevos);
          setAmpliados(new Set());
          setActiva(null);
          const cuenta = entradasDeLaLista(nuevos, new Set(), limiteInicial, false).filter((e) => e.tipo === "opcion").length;
          anunciar(textoDelResultado(cuenta, q));
          return;
        }
        // Solo cambia el grupo ampliado; la primera opcion nueva queda activa donde estaba «Ver más resultados».
        const anterior = previos[ampliar.grupo];
        const reemplazo = nuevos.find((g) => g.rotulo === anterior?.rotulo) ?? nuevos[ampliar.grupo] ?? anterior;
        setGrupos(previos.map((g, i) => (i === ampliar.grupo ? reemplazo : g)));
        setAmpliados((antes) => new Set(antes).add(ampliar.grupo));
        const visibles = Math.min(reemplazo.opciones.length, LIMITE_AMPLIADO);
        const habia = Math.min(anterior?.opciones.length ?? 0, limiteDelGrupo(ampliar.grupo, ampliados, limiteInicial));
        setActiva(visibles > habia ? ampliar.posicion : null);
        anunciar(`Se muestran ${visibles} resultados`);
      },
      (e: unknown) => {
        if (mio !== turno.current || esAborto(e)) return;
        clearTimeout(esperaDeBuscando.current);
        controlador.current = null;
        const mensaje = mensajeDeError(e);
        if (mensaje === null) {
          cerrar();
          alExpirar();
          return;
        }
        setError(mensaje);
        setGrupos([]);
        setAmpliados(new Set());
        setBuscado(q);
        setActiva(null);
        setAbierta(enfocado.current);
        anunciar(`No se pudo buscar: ${mensaje}`);
      },
    );
  }

  function alEscribir(valor: string) {
    elegido.current = false;
    alCambiarTexto(valor);
    cancelar();
    setActiva(null);
    const q = valor.trim();
    if (q.length < minimoDeLetras) {
      setGrupos(null);
      setError(null);
      setAbierta(false);
      setAnuncio("");
      return;
    }
    pausa.current = setTimeout(() => lanzar(q, limiteInicial, null), pausaMs);
  }

  // Abre lo que ya hay para este texto; si no hay nada (o es de otro texto), busca ya, sin pausa. Devuelve si abrio.
  function abrir(): boolean {
    if (corto || deshabilitado || soloLectura) return false;
    if (grupos === null || buscado !== recortado) {
      lanzar(recortado, limiteInicial, null);
      return false;
    }
    setAbierta(true);
    return true;
  }

  function limpiar() {
    elegido.current = false;
    cancelar();
    alCambiarTexto("");
    setGrupos(null);
    setError(null);
    setAnuncio("");
    cerrar();
  }

  function usar(entrada: Entrada<T>, posicion: number) {
    if (entrada.tipo === "ver_mas") {
      lanzar(buscado, LIMITE_AMPLIADO, { grupo: entrada.grupo, posicion });
      return;
    }
    cancelar();
    elegido.current = true;
    cerrar();
    if (entrada.tipo === "opcion") alElegir(entrada.opcion);
    else valorPropio?.alUsar(recortado);
  }

  function alTeclear(e: KeyboardEvent<HTMLInputElement>) {
    const total = entradas.length;
    switch (e.key) {
      case "ArrowDown":
      case "ArrowUp": {
        e.preventDefault();
        if (e.altKey) {
          if (!abierta) abrir();
          return;
        }
        if (!abierta) {
          if (abrir()) setActiva(moverActiva(null, e.key, total));
          return;
        }
        setActiva(moverActiva(activa, e.key, total));
        return;
      }
      case "PageDown":
      case "PageUp":
        if (!listaVisible) return;
        e.preventDefault();
        setActiva(moverActiva(activa, e.key, total));
        return;
      case "Home":
      case "End":
        setActiva(null); // el cursor va al texto del campo, no a la lista
        return;
      case "Enter":
        if (listaVisible && activa !== null && entradas[activa]) {
          e.preventDefault(); // elegir no envia el formulario
          usar(entradas[activa], activa);
        }
        return;
      case "Escape":
        if (abierta) {
          e.preventDefault();
          e.stopPropagation(); // dentro de un dialogo, Esc cierra primero la lista
          cerrar();
          return;
        }
        if (elegido.current && texto !== "") {
          e.preventDefault();
          e.stopPropagation();
          limpiar();
        }
        return;
      case "Tab":
        cerrar();
        return;
    }
  }

  const sinMoverElFoco = (e: MouseEvent) => e.preventDefault();

  const describe = [invalido ? `${id}-error-msg` : ayuda ? `${id}-helper-text` : null, regionVisible ? idEstado : null]
    .filter(Boolean)
    .join(" ");

  function opcionDeLaLista(entrada: Entrada<T>, posicion: number, enGrupo: number) {
    const clases = ["silice-busqueda__opcion"];
    if (posicion === activa) clases.push("silice-busqueda__opcion--activa");
    const comun = {
      id: idOpcion(posicion),
      role: "option",
      "aria-selected": posicion === activa,
      onMouseDown: sinMoverElFoco,
      onClick: () => usar(entrada, posicion),
    } as const;
    if (entrada.tipo === "ver_mas") {
      return (
        <div key={`ver_mas:${enGrupo}`} {...comun} className={[...clases, "silice-busqueda__ver-mas"].join(" ")}>
          Ver más resultados
        </div>
      );
    }
    if (entrada.tipo === "propio") {
      return (
        <div key="propio" {...comun} className={[...clases, "silice-busqueda__propio"].join(" ")}>
          {valorPropio?.rotulo(recortado)}
        </div>
      );
    }
    const { opcion } = entrada;
    const grupo = grupos?.[enGrupo];
    const conMas = grupo?.hayMas ? { "aria-setsize": -1, "aria-posinset": grupo.opciones.indexOf(opcion) + 1 } : {};
    return (
      <div key={opcion.clave} {...comun} {...conMas} className={clases.join(" ")}>
        <span className="silice-busqueda__principal">
          {tramosResaltados(opcion.principal, buscado).map((t, i) =>
            t.resaltado ? <strong key={i}>{t.texto}</strong> : <Fragment key={i}>{t.texto}</Fragment>,
          )}
        </span>
        {opcion.secundaria.length > 0 && (
          <span className="silice-busqueda__secundaria">
            {opcion.secundaria.map((parte, i) => (
              <Fragment key={i}>
                {i > 0 && " · "}
                {i === 0 ? <span className="silice-busqueda__codigo">{parte}</span> : parte}
              </Fragment>
            ))}
          </span>
        )}
      </div>
    );
  }

  // Las entradas con su posicion en la lista, repartidas por grupo; el valor propio va fuera de los grupos, al final.
  const conPosicion = entradas.map((entrada, posicion) => ({ entrada, posicion }));
  const varios = (grupos?.length ?? 0) > 1;
  const contenidoDePanel = panelVisible && (
    <div
      ref={panel}
      className={`silice-busqueda__panel${enCelda ? " silice-busqueda__panel--en-celda" : ""}`}
      style={enCelda ? { position: "fixed" } : undefined}
    >
      {error !== null && (
        <p className="silice-busqueda__error cds--type-body-compact-01">
          <WarningFilled aria-hidden="true" className="silice-busqueda__icono-error" />
          {error}
        </p>
      )}
      {sinResultados && (
        <EstadoVacio titulo={`No encontramos «${buscado}».`} descripcion={`${vacio.titulo} ${vacio.pasos}`} />
      )}
      {listaVisible && (
        <div role="listbox" id={idLista} aria-label={etiqueta} className="silice-busqueda__lista">
          {grupos?.map((g, indice) => {
            const suyas = conPosicion.filter((c) => c.entrada.tipo !== "propio" && c.entrada.grupo === indice);
            if (suyas.length === 0) return null;
            const idRotulo = `${id}-grupo-${indice}`;
            return (
              <div key={`${indice}:${g.rotulo}`} role="group" aria-labelledby={idRotulo}>
                <div id={idRotulo} role="presentation" className="silice-busqueda__rotulo cds--type-label-01">
                  {g.rotulo}
                </div>
                {suyas.map((c) => opcionDeLaLista(c.entrada, c.posicion, indice))}
              </div>
            );
          })}
          {conPosicion.filter((c) => c.entrada.tipo === "propio").map((c) => opcionDeLaLista(c.entrada, c.posicion, -1))}
        </div>
      )}
      {grupos?.map((g, indice) =>
        g.hayMas && limiteDelGrupo(indice, ampliados, limiteInicial) >= LIMITE_AMPLIADO ? (
          <p key={`mas:${indice}`} className="silice-busqueda__nota cds--type-label-01">
            {varios
              ? `Hay más resultados en «${g.rotulo}»: escriba más letras para acotar.`
              : "Hay más resultados: escriba más letras para acotar."}
          </p>
        ) : null,
      )}
      {grupos?.map((g, indice) =>
        g.aviso ? (
          <p key={`aviso:${indice}`} className="silice-busqueda__nota cds--type-label-01">
            {g.aviso}
          </p>
        ) : null,
      )}
    </div>
  );

  return (
    <div className={`silice-busqueda${enCelda ? " silice-busqueda--en-celda" : ""}`}>
      <div className="silice-busqueda__campo">
        <CampoTexto
          id={id}
          labelText={etiqueta}
          helperText={ayuda}
          value={texto}
          size={tamano}
          maxLength={LARGO_MAXIMO}
          autoComplete="off"
          invalid={invalido}
          invalidText={textoInvalido}
          disabled={deshabilitado}
          readOnly={soloLectura}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={listaVisible}
          aria-controls={listaVisible ? idLista : undefined}
          aria-activedescendant={listaVisible && activa !== null ? idOpcion(activa) : undefined}
          aria-describedby={describe || undefined}
          onChange={(e) => alEscribir(e.target.value)}
          onKeyDown={alTeclear}
          onFocus={() => {
            enfocado.current = true;
            setConFoco(true);
          }}
          onBlur={() => {
            enfocado.current = false;
            setConFoco(false);
            cerrar();
            alSalir?.();
          }}
        />
        {texto !== "" && !deshabilitado && !soloLectura && (
          <button
            type="button"
            className="silice-busqueda__borrar cds--btn cds--btn--ghost cds--btn--sm cds--btn--icon-only"
            aria-label="Borrar"
            title="Borrar"
            onMouseDown={sinMoverElFoco}
            onClick={() => {
              limpiar();
              document.getElementById(id)?.focus();
            }}
          >
            <Close aria-hidden="true" />
          </button>
        )}
      </div>
      {regionVisible && (
        <div id={idEstado} role="status" aria-live="polite" aria-atomic="true" className="cds--visually-hidden">
          {textoDeEstado}
        </div>
      )}
      {contenidoDePanel && (enCelda ? createPortal(contenidoDePanel, document.body) : contenidoDePanel)}
    </div>
  );
}
