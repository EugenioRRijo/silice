import { Close } from "@carbon/icons-react";
import { useState } from "react";
import type { KeyboardEvent } from "react";
import { CampoConBusqueda } from "./CampoConBusqueda";
import type { CampoConBusquedaProps, OpcionDeBusqueda } from "./CampoConBusqueda";
import "./SeleccionMultipleConBusqueda.scss";

// Seleccion multiple con busqueda en el servidor (AC3): un campo con busqueda que va agregando etiquetas quitables. Se
// construye por COMPOSICION sobre `CampoConBusqueda` (la lista, las flechas, la pausa, la carrera de peticiones, los
// errores y el 401 son los suyos) y no sobre el `FilterableMultiSelect` de Carbon, que descansa en el mismo downshift que
// el `ComboBox` ya descartado (diseno de autocompletado 2026-10-21, §4.1): lista plana sin grupos, region viva en ingles,
// texto propio que no controla la pagina y las elecciones como un contador, no como etiquetas que se quitan una a una.
//
// Lo propio de aqui: la lista de etiquetas, Retroceso (con el campo vacio quita la ultima), que Enter con algo escrito y
// ninguna opcion activa no envie el formulario de la pagina, el aviso de lo escrito sin elegir y los anuncios.
// NO hay «usar tal cual»: solo entra lo que viene de la lista. Lo elegido es un texto por opcion (`textoDe`); la pagina
// decide como se manda (`elegidos.join(", ")`). Los montos no pasan por aqui.
type PropsDelCampo<T> = Pick<
  CampoConBusquedaProps<T>,
  "id" | "etiqueta" | "buscar" | "vacio" | "alExpirar" | "minimoDeLetras" | "pausaMs" | "deshabilitado" | "tamano"
>;

export interface SeleccionMultipleConBusquedaProps<T> extends PropsDelCampo<T> {
  ayuda?: string; // bajo el campo mientras no haya nada escrito
  elegidos: string[]; // controlado por la pagina
  alCambiar: (elegidos: string[]) => void;
  textoDe: (opcion: OpcionDeBusqueda<T>) => string | null; // lo que se guarda al elegir; null: no se puede guardar
  rechazar?: (texto: string) => string | null; // el motivo por el que ese texto no puede entrar, o null
  nombreDeLaLista?: string; // nombre accesible de la lista de etiquetas ("Elegidos: " + etiqueta por omision)
}

const cuantos = (n: number) => (n === 0 ? "Ninguno elegido." : `${n} ${n === 1 ? "elegido" : "elegidos"}.`);

export function SeleccionMultipleConBusqueda<T>({
  ayuda,
  elegidos,
  alCambiar,
  textoDe,
  rechazar,
  nombreDeLaLista,
  ...campo
}: SeleccionMultipleConBusquedaProps<T>) {
  const { id, etiqueta, deshabilitado } = campo;
  const [texto, setTexto] = useState("");
  const [anuncio, setAnuncio] = useState("");
  const [motivo, setMotivo] = useState<string | null>(null);
  const escrito = texto.trim();

  function alElegir(opcion: OpcionDeBusqueda<T>) {
    setTexto("");
    const elegido = textoDe(opcion);
    if (elegido === null) return;
    const razon = rechazar?.(elegido) ?? null;
    setMotivo(razon);
    if (razon !== null) {
      setAnuncio(`No se agregó: ${razon}`);
      return;
    }
    if (elegidos.includes(elegido)) {
      setAnuncio(`${elegido} ya estaba en la lista.`);
      return;
    }
    alCambiar([...elegidos, elegido]);
    setAnuncio(`Agregado: ${elegido}. ${cuantos(elegidos.length + 1)}`);
  }

  function quitar(indice: number) {
    const quitado = elegidos[indice];
    if (quitado === undefined) return;
    alCambiar(elegidos.filter((_, i) => i !== indice));
    setMotivo(null);
    setAnuncio(`Quitado: ${quitado}. ${cuantos(elegidos.length - 1)}`);
  }

  // Los teclazos del campo suben hasta aqui despues de que `CampoConBusqueda` atendio los suyos.
  function alTeclear(e: KeyboardEvent<HTMLDivElement>) {
    if ((e.target as HTMLElement).id !== id) return;
    if (e.key === "Backspace" && texto === "" && elegidos.length > 0) {
      quitar(elegidos.length - 1);
      return;
    }
    // Enter con algo escrito que no se eligio: no es enviar el formulario de la pagina (sin texto, si lo es).
    if (e.key === "Enter" && !e.defaultPrevented && escrito !== "") e.preventDefault();
  }

  return (
    // El gestor de teclado va en la envoltura y solo atiende lo que nace en el campo (comprobado arriba).
    <div className="silice-seleccion" onKeyDown={alTeclear}>
      <CampoConBusqueda<T>
        {...campo}
        ayuda={escrito !== "" ? `Falta elegir «${escrito}» de la lista: así no se agrega.` : ayuda}
        texto={texto}
        alCambiarTexto={(valor) => {
          setTexto(valor);
          if (valor !== "") setMotivo(null);
        }}
        alElegir={alElegir}
        invalido={motivo !== null}
        textoInvalido={motivo ?? undefined}
        escLimpia={false}
      />
      {elegidos.length > 0 && (
        <ul className="silice-seleccion__lista" aria-label={nombreDeLaLista ?? `Elegidos: ${etiqueta}`}>
          {elegidos.map((elegido, i) => (
            <li key={elegido} className="silice-seleccion__etiqueta cds--type-label-02">
              <span className="silice-seleccion__texto">{elegido}</span>
              <button
                type="button"
                className="silice-seleccion__quitar"
                aria-label={`Quitar ${elegido}`}
                title={`Quitar ${elegido}`}
                disabled={deshabilitado}
                onClick={() => {
                  quitar(i);
                  document.getElementById(id)?.focus();
                }}
              >
                <Close aria-hidden="true" size={16} />
              </button>
            </li>
          ))}
        </ul>
      )}
      {anuncio !== "" && (
        <div role="status" aria-live="polite" aria-atomic="true" className="cds--visually-hidden">
          {anuncio}
        </div>
      )}
    </div>
  );
}
