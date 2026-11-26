import { Children, Fragment, isValidElement, useEffect, useId, useRef } from "react";
import type { JSX, ReactNode } from "react";
import "./Dialogo.scss";

export interface PropsDeDialogo {
  abierto: boolean;
  titulo: string;
  alCerrar: () => void;
  children: ReactNode;
  pie?: ReactNode;
  enviando?: boolean;
  destructivo?: boolean;
  id?: string;
}

const SELECTOR_ENFOCABLE =
  'a[href], area[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"]):not([disabled])';

const SELECTOR_CAMPO =
  'input:not([disabled]):not([type="hidden"]):not([type="button"]):not([type="submit"]):not([type="reset"]), select:not([disabled]), textarea:not([disabled])';

function esElementoVisible(elemento: HTMLElement, raiz: HTMLElement): boolean {
  for (let nodo: HTMLElement | null = elemento; nodo !== null && nodo !== raiz; nodo = nodo.parentElement) {
    if (nodo.hasAttribute("hidden") || getComputedStyle(nodo).display === "none") return false;
  }
  return true;
}

function resolverMarcadoExplicito(contenedor: HTMLElement, raiz: HTMLElement): HTMLElement | null {
  const marcados = contenedor.querySelectorAll<HTMLElement>("[autofocus], [data-autofocus]");
  for (const nodo of marcados) {
    if (nodo.getAttribute("data-autofocus") === "false") continue;
    if (nodo.matches(SELECTOR_ENFOCABLE) && esElementoVisible(nodo, raiz)) {
      return nodo;
    }
    const interno = nodo.querySelector<HTMLElement>(SELECTOR_ENFOCABLE);
    if (interno !== null && esElementoVisible(interno, raiz)) {
      return interno;
    }
  }
  return null;
}

function encontrarBotonCancelar(pie: HTMLElement | null, dialogo: HTMLElement): HTMLElement | null {
  const ambito = pie ?? dialogo;
  const botones = ambito.querySelectorAll<HTMLButtonElement>("button:not([disabled])");
  for (const boton of botones) {
    if (!esElementoVisible(boton, dialogo)) continue;
    const nombre = (boton.getAttribute("aria-label") ?? boton.textContent ?? "").trim();
    if (/^cancelar$/i.test(nombre)) return boton;
  }
  const secundario = ambito.querySelector<HTMLButtonElement>("button.cds--btn--secondary:not([disabled])");
  if (secundario !== null && esElementoVisible(secundario, dialogo)) return secundario;
  return null;
}

function encontrarPrimerCampo(cuerpo: HTMLElement | null, dialogo: HTMLElement): HTMLElement | null {
  if (cuerpo === null) return null;
  const campos = cuerpo.querySelectorAll<HTMLElement>(SELECTOR_CAMPO);
  for (const campo of campos) {
    if (esElementoVisible(campo, dialogo)) return campo;
  }
  return null;
}

function elegirObjetivoInicial(
  dialogo: HTMLDialogElement,
  cuerpo: HTMLElement | null,
  pie: HTMLElement | null,
  destructivo: boolean,
): HTMLElement | null {
  if (destructivo) {
    return encontrarBotonCancelar(pie, dialogo) ?? resolverMarcadoExplicito(dialogo, dialogo);
  }
  return resolverMarcadoExplicito(dialogo, dialogo) ?? encontrarPrimerCampo(cuerpo, dialogo);
}

function limpiarAutofocus(registro: { current: HTMLElement | null }): void {
  if (registro.current !== null) {
    registro.current.removeAttribute("autofocus");
    registro.current = null;
  }
}

function aplicarAutofocusInicial(
  dialogo: HTMLDialogElement,
  cuerpo: HTMLElement | null,
  pie: HTMLElement | null,
  destructivo: boolean,
  registro: { current: HTMLElement | null },
): void {
  limpiarAutofocus(registro);
  const objetivo = elegirObjetivoInicial(dialogo, cuerpo, pie, destructivo);
  if (objetivo !== null && !objetivo.hasAttribute("autofocus")) {
    objetivo.setAttribute("autofocus", "");
    registro.current = objetivo;
  }
}

function extraerNodosDelPie(nodo: ReactNode): ReactNode[] {
  const lista = Children.toArray(nodo);
  if (lista.length === 1 && isValidElement<{ children?: ReactNode }>(lista[0]) && lista[0].type === Fragment) {
    return extraerNodosDelPie(lista[0].props.children);
  }
  return lista;
}

function pesoEnPieDeModal(nodo: ReactNode): number {
  if (!isValidElement<{ kind?: string }>(nodo)) return 0;
  const tipo = nodo.props.kind;
  if (tipo === "primary" || tipo === "danger" || tipo === "danger--primary") return 1;
  return 0;
}

function ordenarPieDeModal(pie: ReactNode): ReactNode[] {
  const nodos = extraerNodosDelPie(pie);
  return [...nodos].sort((a, b) => pesoEnPieDeModal(a) - pesoEnPieDeModal(b));
}

/**
 * Diálogo modal común sobre el elemento nativo `<dialog>` y `showModal()`.
 *
 * No usa el `Modal` de Carbon: su archivo incluye una URL externa que `npm run dist` rechaza (RNF-22).
 * Tampoco añade `role="dialog"`, `aria-modal`, trampa de foco, `inert` manual, manejador de `Escape` ni código
 * para devolver el foco al cerrar: el navegador resuelve todo eso en la capa superior al abrir con `showModal()`
 * y cerrar con `close()`.
 *
 * **Cómo se decide y cómo se marca el foco inicial:**
 * - Por omisión, antes de llamar a `showModal()`, `Dialogo` asigna el atributo HTML `autofocus` al primer campo
 *   habilitado del contenido (`input`, `select` o `textarea`).
 * - Si `destructivo` es `true`, el atributo `autofocus` se coloca en el botón «Cancelar» para evitar confirmar
 *   por accidente una acción irreversible.
 * - Si quien usa `Dialogo` necesita elegir otro control inicial, marca ese campo o botón (o su contenedor) con
 *   `data-autofocus` (por ejemplo `<CampoTexto data-autofocus ... />`). En JSX no debe usarse `autoFocus` de React,
 *   porque React ejecuta `.focus()` durante el montaje antes de `showModal()` —alterando el elemento previo al que
 *   el navegador devuelve el foco al cerrar— y no escribe el atributo HTML `autofocus` que lee `showModal()`.
 */
export function Dialogo({
  abierto,
  titulo,
  alCerrar,
  children,
  pie,
  enviando = false,
  destructivo = false,
  id,
}: PropsDeDialogo): JSX.Element {
  const idTitulo = useId();
  const refDialogo = useRef<HTMLDialogElement>(null);
  const refCuerpo = useRef<HTMLDivElement>(null);
  const refPie = useRef<HTMLDivElement>(null);
  const cerradoNotificado = useRef(false);
  const autofocusPuesto = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const dialogo = refDialogo.current;
    if (dialogo === null) return;

    const alCancelarEvento = (evento: Event) => {
      if (enviando) {
        evento.preventDefault();
        return;
      }
      if (cerradoNotificado.current) return;
      cerradoNotificado.current = true;
      alCerrar();
    };

    const alCerrarEvento = () => {
      limpiarAutofocus(autofocusPuesto);
      if (cerradoNotificado.current) return;
      cerradoNotificado.current = true;
      alCerrar();
    };

    dialogo.addEventListener("cancel", alCancelarEvento);
    dialogo.addEventListener("close", alCerrarEvento);
    return () => {
      dialogo.removeEventListener("cancel", alCancelarEvento);
      dialogo.removeEventListener("close", alCerrarEvento);
    };
  }, [alCerrar, enviando]);

  useEffect(() => {
    const dialogo = refDialogo.current;
    if (dialogo === null) return;

    if (abierto) {
      if (!dialogo.open) {
        cerradoNotificado.current = false;
        aplicarAutofocusInicial(dialogo, refCuerpo.current, refPie.current, destructivo, autofocusPuesto);
        dialogo.showModal();
      }
    } else if (dialogo.open) {
      cerradoNotificado.current = true;
      limpiarAutofocus(autofocusPuesto);
      dialogo.close();
    }
  }, [abierto, destructivo]);

  useEffect(() => {
    const dialogo = refDialogo.current;
    return () => {
      if (dialogo !== null && dialogo.open) {
        dialogo.close();
      }
    };
  }, []);

  const nodosPie = pie !== undefined && pie !== null ? ordenarPieDeModal(pie) : [];
  const clases = destructivo ? "silice-dialogo silice-dialogo--destructivo" : "silice-dialogo";

  return (
    <dialog ref={refDialogo} id={id} aria-labelledby={idTitulo} className={clases}>
      {abierto && (
        <>
          <div className="silice-dialogo__cabecera">
            <h2 id={idTitulo} className="silice-dialogo__titulo cds--type-heading-compact-02">
              {titulo}
            </h2>
          </div>
          <div ref={refCuerpo} className="silice-dialogo__cuerpo">
            {children}
          </div>
          {nodosPie.length > 0 && (
            <div ref={refPie} className="silice-dialogo__pie">
              {nodosPie}
            </div>
          )}
        </>
      )}
    </dialog>
  );
}
