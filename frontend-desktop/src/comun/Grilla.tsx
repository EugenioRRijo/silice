import { useLayoutEffect, useRef, useState } from "react";
import type { KeyboardEvent, MouseEvent, ReactNode } from "react";
import "./Grilla.scss";
import { estadoInicialDeGrilla, eventoDesdeTecla, siguiente } from "./logicaGrilla";
import type { EstadoDeGrilla, EventoDeGrilla, TransicionDeGrilla } from "./logicaGrilla";

// Grilla de celdas con teclado de hoja de cálculo (lote B1-2b). Guía `spatial-navigation` de Google: <table role="grid">,
// una sola parada de Tab (tabindex itinerante), flechas solo dentro de la grilla, sin preventDefault donde no se mueve
// nada, sin interceptar con modificadores o eventos ya prevenidos, y el campo de edición se queda sus propias teclas.
// Las reglas de movimiento y edición son de la máquina pura de logicaGrilla.ts; aquí solo se traducen a DOM.
// Guías `responsive-table` (cabeceras sticky, @container) y `single-line-overflow` (overflow hidden): ver Grilla.scss.
// No importa de paginas/ (comun/arquitectura.test.ts): lo que se dibuja y lo que se guarda lo decide quien la usa.

export interface ColumnaDeGrilla<F> {
  readonly clave: string;
  readonly titulo: string;
  // El texto de la celda: lo que se ve, lo que se edita y lo que lee la lectora de pantalla.
  readonly valor: (fila: F) => string;
  // Contenido propio en lugar del texto (un ícono con su palabra, un botón). Si lo hay, la celda no se edita.
  readonly render?: ((fila: F) => ReactNode) | undefined;
  // Cifras: a la derecha y tabulares.
  readonly numerica?: boolean | undefined;
  // Se edita con F2, Enter o escribiendo, solo si la grilla recibe alEditar.
  readonly editable?: boolean | undefined;
}

export interface PropiedadesDeGrilla<F> {
  readonly etiqueta: string;
  readonly columnas: readonly ColumnaDeGrilla<F>[];
  readonly filas: readonly F[];
  readonly idDeFila: (fila: F) => string;
  // Se llama al confirmar una edición con un valor distinto del original.
  readonly alEditar?: ((idDeFila: string, clave: string, valor: string) => void) | undefined;
  // Se llama cuando la persona cambia de celda activa (no al montar).
  readonly alActivar?: ((idDeFila: string, clave: string) => void) | undefined;
  readonly filaElegida?: string | null | undefined;
  // Abrir la fila (su inspector): Enter sobre una celda que no se edita, o doble clic en una celda que nada dentro atendió.
  // Recibe la celda para que quien abre sepa a dónde devolver el foco al cerrar.
  readonly alAbrir?: ((idDeFila: string, clave: string, celda: HTMLElement) => void) | undefined;
  // Filas de pie (tr con su td), dentro de un tfoot.
  readonly pie?: ReactNode;
}

function acotar(estado: EstadoDeGrilla, filas: number, columnas: number): EstadoDeGrilla {
  const fila = Math.max(0, Math.min(estado.activa.fila, filas - 1));
  const columna = Math.max(0, Math.min(estado.activa.columna, columnas - 1));
  if (fila === estado.activa.fila && columna === estado.activa.columna) {
    return estado;
  }
  return { ...estado, activa: { fila, columna } };
}

export function Grilla<F>({
  etiqueta,
  columnas,
  filas,
  idDeFila,
  alEditar,
  alActivar,
  filaElegida,
  alAbrir,
  pie,
}: PropiedadesDeGrilla<F>) {
  const [estadoCrudo, setEstado] = useState<EstadoDeGrilla>(() => estadoInicialDeGrilla());
  const tabla = useRef<HTMLTableElement>(null);
  const pedirFoco = useRef(false);
  const hayCeldas = filas.length > 0 && columnas.length > 0;
  const estado = hayCeldas ? acotar(estadoCrudo, filas.length, columnas.length) : estadoCrudo;

  // El foco se mueve después de pintar: la celda destino (o su campo) ya existe con su tabindex.
  useLayoutEffect(() => {
    if (!pedirFoco.current) {
      return;
    }
    pedirFoco.current = false;
    const celda = tabla.current?.querySelector<HTMLElement>(
      `[data-celda][data-fila="${estado.activa.fila}"][data-columna="${estado.activa.columna}"]`,
    );
    const destino =
      estado.modo === "editar"
        ? celda?.querySelector<HTMLInputElement>("input[data-campo-de-celda]")
        : celda;
    if (!destino) {
      return;
    }
    destino.focus();
    if (destino instanceof HTMLInputElement) {
      destino.setSelectionRange(destino.value.length, destino.value.length);
    }
    destino.scrollIntoView?.({ block: "nearest", inline: "nearest" });
  });

  function editable(fila: number, columna: number): boolean {
    const c = columnas[columna];
    return alEditar !== undefined && c !== undefined && c.editable === true && c.render === undefined && fila < filas.length;
  }

  function valorEditable(fila: number, columna: number): string | null {
    const f = filas[fila];
    const c = columnas[columna];
    return f !== undefined && c !== undefined && editable(fila, columna) ? c.valor(f) : null;
  }

  function aplicar(evento: EventoDeGrilla, transicion: TransicionDeGrilla) {
    const { activa } = estado;
    const cambioDeCelda =
      transicion.activa.fila !== activa.fila || transicion.activa.columna !== activa.columna;
    const cambioDeModo = transicion.estado.modo !== estado.modo;
    if ((cambioDeCelda || cambioDeModo) && evento.tipo !== "activar" && evento.tipo !== "cambiar") {
      pedirFoco.current = true;
    }
    // En Tab el foco vuelve a la celda antes de que el navegador ejecute su Tab: React vacía las actualizaciones de un
    // evento discreto de teclado al terminar el manejador, y el efecto de diseño mueve el foco en ese vaciado.
    setEstado(transicion.estado);
    const edicion = transicion.edicion;
    if (edicion?.tipo === "confirmar" && estado.modo === "editar" && edicion.valor !== estado.valorOriginal) {
      const f = filas[edicion.celda.fila];
      const c = columnas[edicion.celda.columna];
      if (f !== undefined && c !== undefined) {
        alEditar?.(idDeFila(f), c.clave, edicion.valor);
      }
    }
    if (cambioDeCelda) {
      const f = filas[transicion.activa.fila];
      const c = columnas[transicion.activa.columna];
      if (f !== undefined && c !== undefined) {
        alActivar?.(idDeFila(f), c.clave);
      }
    }
  }

  function despachar(evento: EventoDeGrilla): TransicionDeGrilla {
    const transicion = siguiente(estado, evento);
    aplicar(evento, transicion);
    return transicion;
  }

  function alTecla(e: KeyboardEvent<HTMLTableElement>) {
    if (!hayCeldas) {
      return;
    }
    const objetivo = e.target as HTMLElement;
    const enCampo = objetivo.hasAttribute("data-campo-de-celda");
    // Solo se actúa si lo enfocado es una celda o el campo de edición; un control de la celda se queda con sus teclas.
    if (!enCampo && !objetivo.hasAttribute("data-celda")) {
      return;
    }
    // Dentro del campo solo se atienden Enter, Esc y Tab; flechas, Inicio, Fin y letras son del campo.
    if (enCampo && e.key !== "Enter" && e.key !== "Escape" && e.key !== "Tab") {
      return;
    }
    const evento = eventoDesdeTecla(
      {
        key: e.key,
        ctrlKey: e.ctrlKey,
        altKey: e.altKey,
        metaKey: e.metaKey,
        shiftKey: e.shiftKey,
        isComposing: e.nativeEvent.isComposing,
        defaultPrevented: e.defaultPrevented,
      },
      {
        filas: filas.length,
        columnas: columnas.length,
        valorCelda: valorEditable(estado.activa.fila, estado.activa.columna),
      },
    );
    if (evento === null) {
      return;
    }
    // Enter sobre una celda que no se edita: la fila se abre (la máquina no hace nada con ella).
    if (
      evento.tipo === "enter" &&
      alAbrir !== undefined &&
      !enCampo &&
      estado.modo === "navegar" &&
      valorEditable(estado.activa.fila, estado.activa.columna) === null
    ) {
      const f = filas[estado.activa.fila];
      const c = columnas[estado.activa.columna];
      if (f !== undefined && c !== undefined) {
        e.preventDefault();
        alAbrir(idDeFila(f), c.clave, objetivo);
        return;
      }
    }
    const transicion = despachar(evento);
    if (transicion.consumir) {
      e.preventDefault();
    }
  }

  return (
    <div className="silice-grilla">
      <table ref={tabla} role="grid" aria-label={etiqueta} className="silice-grilla__tabla" onKeyDown={alTecla}>
        <thead>
          <tr>
            {columnas.map((c, j) => (
              <th
                key={c.clave}
                scope="col"
                className={[
                  "silice-grilla__cabecera",
                  j === 0 ? "silice-grilla__celda--fija" : "",
                  c.numerica ? "silice-grilla__celda--numerica" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                {c.titulo}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filas.map((f, i) => {
            const id = idDeFila(f);
            const elegida = filaElegida === id;
            return (
              <tr
                key={id}
                aria-selected={elegida}
                className={elegida ? "silice-grilla__fila silice-grilla__fila--elegida" : "silice-grilla__fila"}
              >
                {columnas.map((c, j) => {
                  const esActiva = estado.activa.fila === i && estado.activa.columna === j;
                  const editando = esActiva && estado.modo === "editar";
                  const propiedades = {
                    "data-celda": "",
                    "data-fila": i,
                    "data-columna": j,
                    tabIndex: esActiva && !editando ? 0 : -1,
                    className: [
                      "silice-grilla__celda",
                      j === 0 ? "silice-grilla__celda--fija" : "",
                      c.numerica ? "silice-grilla__celda--numerica" : "",
                    ]
                      .filter(Boolean)
                      .join(" "),
                    onDoubleClick:
                      alAbrir === undefined
                        ? undefined
                        : (e: MouseEvent<HTMLElement>) => {
                            if (!e.defaultPrevented) alAbrir(id, c.clave, e.currentTarget);
                          },
                    onFocus: (e: { target: EventTarget; currentTarget: EventTarget }) => {
                      if (e.target === e.currentTarget) {
                        despachar({
                          tipo: "activar",
                          celda: { fila: i, columna: j },
                          filas: filas.length,
                          columnas: columnas.length,
                        });
                      }
                    },
                  };
                  const contenido: ReactNode = editando ? (
                    <input
                      data-campo-de-celda=""
                      className="silice-grilla__campo"
                      type="text"
                      aria-label={`${c.titulo}, ${columnas[0]?.valor(f) ?? ""}`}
                      value={estado.modo === "editar" ? estado.borrador : ""}
                      onChange={(e) => despachar({ tipo: "cambiar", valor: e.target.value })}
                    />
                  ) : c.render ? (
                    c.render(f)
                  ) : (
                    c.valor(f)
                  );
                  return j === 0 ? (
                    <th key={c.clave} scope="row" role="rowheader" {...propiedades}>
                      {contenido}
                    </th>
                  ) : (
                    <td key={c.clave} role="gridcell" {...propiedades}>
                      {contenido}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
        {pie ? <tfoot>{pie}</tfoot> : null}
      </table>
    </div>
  );
}
