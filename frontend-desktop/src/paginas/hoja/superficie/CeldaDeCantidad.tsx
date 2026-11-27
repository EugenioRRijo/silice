import { useEffect, useId, useRef, useState } from "react";
import type { FocusEvent, JSX, KeyboardEvent } from "react";
import { CampoDeCifra } from "../../../comun/CampoDeCifra";
import { leerCifra } from "../../../indicadores/cifraEscrita";
import { accionEnCampo, aperturaPorTecla, textoDeRechazoDeCelda } from "./logicaDeCantidad";
import "./celdaDeCantidad.scss";

// La celda de cantidad de la grilla del Presupuesto (lote B1-5, ficha-b1 §1.6 y §1.10 pruebas 5 y 6).
// En reposo es solo el texto: ni un campo por fila (hasta 500, S5) ni una parada de Tab de más; la grilla sigue con su única
// parada. Se abre con F2, Enter, un carácter imprimible o doble clic, y entonces es un `CampoDeCifra` pequeño con su
// etiqueta oculta (guía `forms`: `inputmode="decimal"`, etiqueta asociada). Cada tecla pasa por `alCambiar` y la pausa y el
// envío con su `rev` son del motor de la sección (`useEdicionDeSeccion`, ver `useCantidadesDeLaSuperficie`); aquí solo se
// decide qué se ve y a dónde va el foco.
// Como en Excel: Enter confirma y baja, Tab confirma y sigue, Esc restaura, y salir con el foco (un clic en otro lugar)
// confirma lo escrito. Dentro del campo las flechas, Inicio, Fin y las letras son del campo: la grilla no las ve.
// Guías `validate-input-after-interaction` y `accessible-error-announcement`: un valor mal escrito se marca al salir del
// campo, con texto y no solo con color, y su error se anuncia una vez (lo hace `CampoDeCifra`). Un rechazo del servidor
// (un 422) deja lo escrito tal cual, mantiene el campo a la vista con el texto de lo que hay que corregir y se limpia en
// cuanto la persona cambia el texto.

export interface PropiedadesDeCeldaDeCantidad {
  // El nombre accesible del campo («Cantidad, EXC-01»): la cabecera da la columna y esto da la fila. Va oculto.
  readonly etiqueta: string;
  // El texto de la cantidad (con coma decimal): lo escrito por la persona o lo que mandó el servidor.
  readonly valor: string;
  // Sin permiso de edición la celda es su texto: no se abre.
  readonly soloLectura?: boolean | undefined;
  // El rechazo del servidor a esta celda (su 422). Un objeto nuevo por cada rechazo, aunque repita el mensaje.
  readonly rechazo?: { readonly mensaje: string } | null | undefined;
  readonly alCambiar: (texto: string) => void;
  // Esc: devuelve el texto a lo último que aceptó el servidor.
  readonly alRestaurar: () => void;
  // Enter, Tab o salir del campo: lo escrito se manda sin esperar la pausa.
  readonly alConfirmar: () => void;
}

const SELECTOR_DE_CELDA = "[data-celda]";

// La celda de la fila de abajo en la misma columna, o null en la última fila.
function celdaDeAbajo(celda: HTMLElement | null): HTMLElement | null {
  const columna = celda?.dataset["columna"];
  const fila = celda?.closest("tr")?.nextElementSibling;
  if (columna === undefined || !fila) return null;
  return fila.querySelector<HTMLElement>(`${SELECTOR_DE_CELDA}[data-columna="${columna}"]`);
}

export function CeldaDeCantidad({
  etiqueta,
  valor,
  soloLectura = false,
  rechazo = null,
  alCambiar,
  alRestaurar,
  alConfirmar,
}: PropiedadesDeCeldaDeCantidad): JSX.Element {
  const id = useId();
  const raiz = useRef<HTMLDivElement>(null);
  const campo = useRef<HTMLInputElement>(null);
  const [abierta, setAbierta] = useState(false);
  // Lo leen los manejadores sin esperar a pintar (Enter cierra y el foco sale en el mismo evento).
  const abiertaAhora = useRef(false);
  // El rechazo con el texto que había cuando llegó: si la persona cambia el texto, el rechazo ya no es de este valor.
  const [visto, setVisto] = useState<{ rechazo: { readonly mensaje: string }; texto: string } | null>(null);
  if (rechazo !== (visto?.rechazo ?? null)) setVisto(rechazo === null ? null : { rechazo, texto: valor });
  const rechazoVigente = visto !== null && visto.rechazo === rechazo && visto.texto === valor ? visto.rechazo : null;
  const textoDelRechazo = rechazoVigente === null ? null : textoDeRechazoDeCelda(rechazoVigente.mensaje);
  const mal = "error" in leerCifra(valor);
  // Lo escrito mal o rechazado no se esconde: el campo sigue a la vista con su error hasta que se corrija.
  const editor = !soloLectura && (abierta || mal || rechazoVigente !== null);

  const abrir = (texto: string | null) => {
    if (abiertaAhora.current) return;
    abiertaAhora.current = true;
    setAbierta(true);
    if (texto !== null) alCambiar(texto);
  };
  const cerrar = () => {
    abiertaAhora.current = false;
    setAbierta(false);
  };

  // La celda de la grilla (el `td` que contiene a esta) recibe F2, Enter y los caracteres cuando tiene el foco: la grilla no
  // edita celdas con contenido propio, así que la apertura se escucha aquí. Va con el último `abrir` sin volver a escuchar.
  const abrirAhora = useRef(abrir);
  useEffect(() => {
    abrirAhora.current = abrir;
  });
  useEffect(() => {
    const celda = raiz.current?.closest<HTMLElement>(SELECTOR_DE_CELDA);
    if (!celda || soloLectura) return;
    const alTeclear = (e: globalThis.KeyboardEvent) => {
      if (e.target !== celda) return;
      const apertura = aperturaPorTecla({
        key: e.key,
        ctrlKey: e.ctrlKey,
        altKey: e.altKey,
        metaKey: e.metaKey,
        shiftKey: e.shiftKey,
        isComposing: e.isComposing,
        defaultPrevented: e.defaultPrevented,
      });
      if (apertura === null) return;
      e.preventDefault();
      abrirAhora.current(apertura.texto);
    };
    celda.addEventListener("keydown", alTeclear);
    return () => celda.removeEventListener("keydown", alTeclear);
  }, [soloLectura]);

  // Al abrirse, el foco entra al campo con el cursor al final.
  useEffect(() => {
    if (!abierta) return;
    const entrada = campo.current;
    if (!entrada) return;
    entrada.focus();
    entrada.setSelectionRange(entrada.value.length, entrada.value.length);
  }, [abierta]);

  const celdaDeLaGrilla = () => raiz.current?.closest<HTMLElement>(SELECTOR_DE_CELDA) ?? null;

  const alTeclearEnElCampo = (e: KeyboardEvent<HTMLDivElement>) => {
    const accion = accionEnCampo({
      key: e.key,
      ctrlKey: e.ctrlKey,
      altKey: e.altKey,
      metaKey: e.metaKey,
      shiftKey: e.shiftKey,
      isComposing: e.nativeEvent.isComposing,
      defaultPrevented: e.defaultPrevented,
    });
    if (accion === null) return;
    const celda = celdaDeLaGrilla();
    cerrar();
    if (accion === "restaurar") {
      // Esc no sale del campo hacia quien cierra paneles: solo cancela la edición.
      e.preventDefault();
      e.stopPropagation();
      alRestaurar();
      celda?.focus();
      return;
    }
    alConfirmar();
    if (accion === "confirmar-y-bajar") {
      e.preventDefault();
      (celdaDeAbajo(celda) ?? celda)?.focus();
    } else {
      // Tab: el foco vuelve a la celda antes de que el navegador ejecute su Tab, para que siga desde ella y no desde el aire.
      celda?.focus();
    }
  };

  // Entrar al campo que ya estaba a la vista (el rechazado, el mal escrito) cuenta como abrirlo.
  const alEntrarAlCampo = () => {
    if (!abiertaAhora.current) {
      abiertaAhora.current = true;
      setAbierta(true);
    }
  };

  // Como en Excel, salir del campo con la edición abierta (un clic en otro lugar) confirma lo escrito.
  const alSalirDelCampo = (e: FocusEvent<HTMLDivElement>) => {
    if (!abiertaAhora.current) return;
    if (e.relatedTarget instanceof Node && e.currentTarget.contains(e.relatedTarget)) return;
    cerrar();
    alConfirmar();
  };

  return (
    <div ref={raiz} className="silice-celda-cantidad">
      {editor ? (
        <div
          className="silice-celda-cantidad__campo"
          onKeyDown={alTeclearEnElCampo}
          onFocus={alEntrarAlCampo}
          onBlur={alSalirDelCampo}
        >
          <CampoDeCifra
            id={id}
            ref={campo}
            labelText={etiqueta}
            hideLabel
            size="sm"
            obligatorio
            value={valor}
            onChange={alCambiar}
            mostrarError={textoDelRechazo !== null}
            validar={textoDelRechazo === null ? undefined : () => textoDelRechazo}
          />
        </div>
      ) : (
        <span
          className="silice-celda-cantidad__valor"
          onDoubleClick={
            soloLectura
              ? undefined
              : (e) => {
                  // La celda lo atendió: la grilla no abre además el inspector de la fila.
                  e.preventDefault();
                  abrir(null);
                }
          }
        >
          {valor}
        </span>
      )}
    </div>
  );
}
