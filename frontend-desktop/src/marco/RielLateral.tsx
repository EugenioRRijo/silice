import { Folder, SidePanelClose, SidePanelOpen, ErrorFilled, WarningAltFilled } from "@carbon/icons-react";
import type { CarbonIconType } from "@carbon/icons-react";
import { useId, useLayoutEffect, useRef } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { Pildora } from "../comun/Pildora";
import { formatoEsVe } from "../indicadores/formatoEsVe";
import "./BarraLateral.scss";

// La barra lateral «riel de iconos» de la cara «Papel y resaltador» (elegida por Eugenio el 2026-11-26): un panel propio con
// su cabecera, sus opciones, el bloque «La obra en cifras» y la carpeta abierta al pie. Abierta mide 14,75 rem; reducida,
// 3,5 rem con solo iconos (el texto pasa a ser el nombre accesible y el title). No sabe de obras ni de permisos: quien la
// usa (BarraLateral) decide qué opciones y qué cifras se ofrecen.

export interface OpcionDeRiel {
  id: string;
  texto: string;
  icono: CarbonIconType;
  // Con `ruta` es un enlace; sin ella, un botón que llama a `alPulsar`.
  ruta?: string;
  alPulsar?: () => void;
  actual?: boolean;
  // Cuántas cosas esperan en esa opción (píldora; en la barra reducida, un número sobre el icono).
  cuenta?: number;
  // Lo que dice el contador en palabras («4 por hacer»): va en el nombre accesible, pues la píldora no se lee.
  detalle?: string;
  // Una letra en lugar del icono (la obra en la barra reducida: su inicial).
  inicial?: string;
}

export interface CifraDeRiel {
  id: string;
  // La cifra con su palabra («2 bloquean», «1 aviso»): la gravedad nunca va solo en color.
  texto: string;
  valor: number;
  gravedad: "error" | "advertencia";
  ruta: string;
}

export interface CifrasDeRiel {
  titulo: string;
  filas: readonly CifraDeRiel[];
  // Un renglón más debajo de las cifras (el avance), solo con la barra ampliada.
  extra?: ReactNode;
}

interface Props {
  // El nombre del lugar, en la cabecera de la barra ampliada.
  lugar: string;
  // Quien monta la barra decide si va reducida y la recuerda (el marco, en `silice_sidebar_collapsed`): el riel no guarda nada propio.
  reducida: boolean;
  alAlternar: () => void;
  // Las opciones que van ampliada y reducida.
  opciones: readonly OpcionDeRiel[];
  // El rótulo del grupo de arriba (ampliada).
  rotuloDeOpciones?: string;
  // Las que solo van como icono en la barra reducida (la ampliada las ofrece en su contenido propio).
  soloReducida?: readonly OpcionDeRiel[];
  grupoReducido?: { rotulo: string; opciones: readonly OpcionDeRiel[] };
  cifras?: CifrasDeRiel;
  carpeta?: { nombre: string; rutaDeCambio?: string };
  // El contenido propio de la barra ampliada (la lista de obras, los espacios): reducida no se pinta.
  children?: ReactNode;
  // Va dentro del `aside` en ambos estados (un diálogo).
  fuera?: ReactNode;
}

const ICONO_DE_GRAVEDAD = { error: ErrorFilled, advertencia: WarningAltFilled } as const;

function Opcion({ opcion, reducida }: { opcion: OpcionDeRiel; reducida: boolean }) {
  const { texto, icono: Icono, ruta, alPulsar, actual, cuenta, detalle, inicial } = opcion;
  const nombre = detalle === undefined ? texto : `${texto}, ${detalle}`;
  const comun = {
    "aria-label": reducida || detalle !== undefined ? nombre : undefined,
    title: reducida ? (detalle === undefined ? texto : `${texto} (${detalle})`) : undefined,
    className: `silice-marco-lateral__fila silice-marco-lateral__opcion${reducida ? " silice-marco-lateral__opcion--reducida" : ""}`,
  };
  const dentro = (
    <>
      <span className="silice-marco-lateral__icono">
        {inicial !== undefined ? (
          <span className="silice-marco-lateral__inicial" aria-hidden="true">
            {inicial}
          </span>
        ) : (
          <Icono size={16} aria-hidden="true" />
        )}
        {reducida && cuenta !== undefined && cuenta > 0 && (
          <span className="silice-marco-lateral__insignia" aria-hidden="true">
            {formatoEsVe(String(cuenta))}
          </span>
        )}
      </span>
      {!reducida && <span className="silice-marco-lateral__etiqueta">{texto}</span>}
      {!reducida && cuenta !== undefined && cuenta > 0 && <Pildora valor={cuenta} />}
    </>
  );
  if (ruta !== undefined) {
    return (
      <li>
        <Link to={ruta} aria-current={actual === true ? "page" : undefined} {...comun}>
          {dentro}
        </Link>
      </li>
    );
  }
  return (
    <li>
      <button type="button" onClick={alPulsar} {...comun}>
        {dentro}
      </button>
    </li>
  );
}

function ListaDeOpciones({ opciones, reducida, desplazable = false }: { opciones: readonly OpcionDeRiel[]; reducida: boolean; desplazable?: boolean }) {
  if (opciones.length === 0) return null;
  return (
    <ul className={`silice-marco-lateral__opciones${desplazable ? " silice-marco-lateral__opciones--desplazable" : ""}`}>
      {opciones.map((o) => (
        <Opcion key={o.id} opcion={o} reducida={reducida} />
      ))}
    </ul>
  );
}

function Cifras({ cifras, reducida }: { cifras: CifrasDeRiel; reducida: boolean }) {
  const id = useId();
  if (cifras.filas.length === 0 && (reducida || cifras.extra === undefined)) return null;
  if (reducida) {
    return (
      <ul aria-label={cifras.titulo} className="silice-marco-lateral__opciones silice-marco-lateral__cifras-reducidas">
        {cifras.filas.map((f) => {
          const Icono = ICONO_DE_GRAVEDAD[f.gravedad];
          return (
            <li key={f.id}>
              <Link
                to={f.ruta}
                aria-label={f.texto}
                title={f.texto}
                data-gravedad={f.gravedad}
                className="silice-marco-lateral__fila silice-marco-lateral__opcion silice-marco-lateral__opcion--reducida"
              >
                <span className="silice-marco-lateral__icono">
                  <Icono size={16} aria-hidden="true" />
                  <span className="silice-marco-lateral__insignia" aria-hidden="true">
                    {formatoEsVe(String(f.valor))}
                  </span>
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    );
  }
  return (
    <section aria-labelledby={id} className="silice-marco-lateral__cifras">
      <h2 id={id} className="silice-marco-lateral__cifras-titulo">
        {cifras.titulo}
      </h2>
      <ul>
        {cifras.filas.map((f) => {
          const Icono = ICONO_DE_GRAVEDAD[f.gravedad];
          return (
            <li key={f.id}>
              <Link to={f.ruta} data-gravedad={f.gravedad} className="silice-marco-lateral__cifra">
                <Icono size={16} aria-hidden="true" />
                <span>{f.texto}</span>
              </Link>
            </li>
          );
        })}
      </ul>
      {cifras.extra}
    </section>
  );
}

function Carpeta({ carpeta, reducida }: { carpeta: NonNullable<Props["carpeta"]>; reducida: boolean }) {
  const { nombre, rutaDeCambio } = carpeta;
  if (reducida) {
    const nombreCompleto = `Carpeta abierta: ${nombre}`;
    return (
      <div className="silice-marco-lateral__carpeta silice-marco-lateral__carpeta--reducida">
        {rutaDeCambio === undefined ? (
          <span role="img" aria-label={nombreCompleto} title={nombre} className="silice-marco-lateral__icono">
            <Folder size={16} aria-hidden="true" />
          </span>
        ) : (
          <Link
            to={rutaDeCambio}
            aria-label={`${nombreCompleto}. Cambiar`}
            title={nombre}
            className="silice-marco-lateral__fila silice-marco-lateral__opcion silice-marco-lateral__opcion--reducida"
          >
            <span className="silice-marco-lateral__icono">
              <Folder size={16} aria-hidden="true" />
            </span>
          </Link>
        )}
      </div>
    );
  }
  return (
    <div role="group" aria-label="Carpeta abierta" className="silice-marco-lateral__carpeta">
      <Folder size={16} aria-hidden="true" />
      <span className="silice-marco-lateral__carpeta-nombre">
        <span className="silice-marco-lateral__carpeta-rotulo" aria-hidden="true">
          Carpeta abierta
        </span>
        {nombre}
      </span>
      {rutaDeCambio !== undefined && <Link to={rutaDeCambio}>Cambiar</Link>}
    </div>
  );
}

export function RielLateral({
  lugar,
  rotuloDeOpciones,
  reducida,
  alAlternar,
  opciones,
  soloReducida = [],
  grupoReducido,
  cifras,
  carpeta,
  children,
  fuera,
}: Props) {
  // Reducir o ampliar monta una rama y desmonta la otra: el enlace enfocado (o la obra, con Ctrl+B) desaparece y el foco caería
  // en el cuerpo del documento. Si se perdió, pasa al botón (WCAG 2.4.3); si lo tiene otro control, no se toca. El botón
  // siempre es el mismo elemento, así que pulsarlo no pierde el foco.
  const boton = useRef<HTMLButtonElement>(null);
  const reducidaAntes = useRef(reducida);
  useLayoutEffect(() => {
    if (reducidaAntes.current === reducida) return;
    reducidaAntes.current = reducida;
    const activo = document.activeElement;
    if (activo === null || activo === document.body) boton.current?.focus();
  }, [reducida]);

  return (
    <aside
      className={`silice-marco-lateral silice-marco-lateral--riel${reducida ? " silice-marco-lateral--colapsada" : ""}`}
      data-collapsed={reducida ? "true" : "false"}
      aria-label="Barra lateral"
    >
      <div className="silice-marco-lateral__cabecera">
        {!reducida && <span className="silice-marco-lateral__lugar">{lugar}</span>}
        <button
          ref={boton}
          type="button"
          className="silice-marco-lateral__plegar"
          onClick={alAlternar}
          aria-label={reducida ? "Ampliar la barra" : "Reducir a iconos"}
          aria-expanded={!reducida}
          title={reducida ? "Ampliar la barra (Ctrl+B)" : "Reducir a iconos (Ctrl+B)"}
        >
          {reducida ? <SidePanelOpen size={16} aria-hidden="true" /> : <SidePanelClose size={16} aria-hidden="true" />}
        </button>
      </div>

      <nav aria-label="Obras y espacios" className="silice-marco-lateral__nav">
        {!reducida && rotuloDeOpciones !== undefined && <span className="silice-marco-lateral__rotulo">{rotuloDeOpciones}</span>}
        <ListaDeOpciones opciones={opciones} reducida={reducida} />
        {reducida ? (
          <>
            {grupoReducido !== undefined && grupoReducido.opciones.length > 0 && (
              <nav aria-label={grupoReducido.rotulo} className="silice-marco-lateral__grupo-reducido">
                <ListaDeOpciones opciones={grupoReducido.opciones} reducida />
              </nav>
            )}
            <ListaDeOpciones opciones={soloReducida} reducida desplazable />
          </>
        ) : (
          children
        )}
      </nav>

      {cifras !== undefined && <Cifras cifras={cifras} reducida={reducida} />}
      {carpeta !== undefined && <Carpeta carpeta={carpeta} reducida={reducida} />}
      {fuera}
    </aside>
  );
}
