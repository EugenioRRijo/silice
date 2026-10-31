import { Button, InlineNotification, SkeletonText } from "@carbon/react";
import { WarningAltFilled, WarningFilled } from "@carbon/icons-react";
import { useId, useMemo, useState } from "react";
import type { KeyboardEvent } from "react";
import type { PendienteDeObra } from "../../api/tipos";
import { AvisoError } from "../../comun/AvisoError";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { obrasConMismoNombre } from "../../marco/homonimas";
import type { ObraDeCarpeta } from "../../marco/useObras";
import { usePendientes } from "../../marco/usePendientes";
import { useAplicacion } from "../../shell/contexto";
import { paginaPorId, usable } from "../../shell/rutas";
import "./Bandeja.scss";
import { claveDeObra, contarUrgencias, destinoDelPendiente, indiceTrasTecla, paginaQueAbre } from "./logica";
import { TEXTOS } from "./textos";

interface Props {
  // Abre la sección del pendiente pasando por la confirmación de salida del marco (`irSeguro` de Marco.tsx): formularios
  // sin guardar y, si la obra está en otra carpeta, los borradores de la Hoja que el cambio de carpeta perdería (foco 3).
  alAbrir: (ruta: string) => void;
  // Las obras que el marco ya cargó: de ahí sale la carpeta de las obras que se llaman igual (D-F3-3). Una obra que no
  // esté en la lista no muestra carpeta.
  obras?: readonly ObraDeCarpeta[];
}

// La carpeta de una obra, solo si otra obra de otra carpeta se llama igual (la misma regla que el árbol de la barra).
type CarpetaDe = (p: PendienteDeObra) => string | undefined;

// La bandeja de Pendientes (rediseño F3, Tarea 2; especificación §2.2 y §8 bis): lo que piden las obras de todas las
// carpetas, en el orden que da la API (lo que bloquea primero), con el detalle del elegido y el botón para hacerlo. Los
// datos los pide el marco (`usePendientes`), que los vuelve a pedir cada vez que se entra aquí.
export function Bandeja({ alAbrir, obras = [] }: Props) {
  const carga = usePendientes();
  const homonimas = useMemo(() => obrasConMismoNombre(obras), [obras]);
  const carpetaDe: CarpetaDe = (p) => homonimas.get(claveDeObra(p.carpeta, p.obra_id));
  const total = carga.estado === "listo" ? carga.pendientes.length : 0;
  return (
    <div className="silice-pagina silice-bandeja">
      <div className="silice-bandeja__cabecera">
        <h1 className="cds--type-heading-04">{TEXTOS.titulo}</h1>
      </div>
      {carga.estado === "cargando" && (
        <div className="silice-bandeja__cargando" role="status" aria-busy="true" aria-label={TEXTOS.cargando}>
          <SkeletonText paragraph lineCount={4} />
        </div>
      )}
      {carga.estado === "error" && (
        <div className="silice-bandeja__error">
          <AvisoError error={carga.mensaje} titulo={TEXTOS.error} />
          <Button kind="tertiary" size="sm" onClick={carga.recargar}>
            {TEXTOS.reintentar}
          </Button>
        </div>
      )}
      {carga.estado === "listo" && carga.carpetasOmitidas > 0 && (
        <InlineNotification
          className="silice-bandeja__aviso"
          kind="warning"
          title={TEXTOS.omitidas(carga.carpetasOmitidas)}
          lowContrast
          hideCloseButton
        />
      )}
      {carga.estado === "listo" &&
        (total === 0 ? (
          <EstadoVacio titulo={TEXTOS.vacio} descripcion={TEXTOS.vacioExplica} />
        ) : (
          <ListaYDetalle pendientes={carga.pendientes} alAbrir={alAbrir} carpetaDe={carpetaDe} />
        ))}
    </div>
  );
}

// Patrón listbox de WAI-ARIA con `aria-activedescendant`: el foco se queda en la lista y las flechas eligen. El primero
// queda elegido al llegar (y al llegar una lista nueva).
function ListaYDetalle({
  pendientes,
  alAbrir,
  carpetaDe,
}: {
  pendientes: PendienteDeObra[];
  alAbrir: Props["alAbrir"];
  carpetaDe: CarpetaDe;
}) {
  const base = useId();
  const [elegido, setElegido] = useState(0);
  const [deLaLista, setDeLaLista] = useState(pendientes);
  if (deLaLista !== pendientes) {
    setDeLaLista(pendientes);
    setElegido(0);
  }
  const idDe = (i: number) => `${base}-pendiente-${i}`;
  const { bloquea, aviso } = contarUrgencias(pendientes);
  const actual = Math.min(elegido, pendientes.length - 1);

  const alTeclear = (e: KeyboardEvent<HTMLUListElement>) => {
    const siguiente = indiceTrasTecla(e.key, actual, pendientes.length);
    if (siguiente === null) return;
    e.preventDefault();
    setElegido(siguiente);
    // jsdom no lo tiene; en el navegador deja a la vista el elegido dentro de la columna.
    document.getElementById(idDe(siguiente))?.scrollIntoView?.({ block: "nearest" });
  };

  return (
    <div className="silice-bandeja__rejilla">
      <div className="silice-bandeja__lista">
        <p className="silice-bandeja__resumen cds--type-label-01">{TEXTOS.resumen(bloquea, aviso)}</p>
        <ul
          className="silice-bandeja__opciones"
          role="listbox"
          aria-label={TEXTOS.lista}
          tabIndex={0}
          aria-activedescendant={idDe(actual)}
          onKeyDown={alTeclear}
        >
          {pendientes.map((p, i) => (
            <li
              key={idDe(i)}
              id={idDe(i)}
              className="silice-bandeja__opcion"
              role="option"
              aria-selected={i === actual}
              onClick={() => setElegido(i)}
            >
              <span className="silice-bandeja__texto">{p.texto}</span>
              <span className="silice-bandeja__pie">
                <NombreDeObra pendiente={p} carpetaDe={carpetaDe} />
                <Urgencia valor={p.urgencia} />
              </span>
            </li>
          ))}
        </ul>
      </div>
      <Detalle pendiente={pendientes[actual]} alAbrir={alAbrir} carpetaDe={carpetaDe} />
    </div>
  );
}

// Qué pasó, de qué obra y el botón para hacerlo: el único botón principal de la pantalla. Si la cuenta no puede usar la
// pantalla a la que lleva, no se ofrece (la API la rechazaría): se dice por qué (foco 1).
function Detalle({
  pendiente: p,
  alAbrir,
  carpetaDe,
}: {
  pendiente: PendienteDeObra;
  alAbrir: Props["alAbrir"];
  carpetaDe: CarpetaDe;
}) {
  const { sesion, modulosApagados } = useAplicacion();
  const pagina = paginaPorId(paginaQueAbre(p));
  const puede = pagina !== undefined && usable(pagina, sesion.acciones, sesion.modo_entrega, modulosApagados);
  return (
    <section className="silice-bandeja__detalle" aria-label={TEXTOS.detalle}>
      <h2 className="cds--type-heading-compact-02">{p.texto}</h2>
      <dl className="silice-bandeja__datos cds--type-body-compact-01">
        <dt>{TEXTOS.obra}</dt>
        <dd>
          <NombreDeObra pendiente={p} carpetaDe={carpetaDe} />
        </dd>
        <dt>{TEXTOS.urgencia}</dt>
        <dd>
          <Urgencia valor={p.urgencia} />
        </dd>
      </dl>
      <div>
        {puede ? (
          <Button kind="primary" size="md" onClick={() => alAbrir(destinoDelPendiente(p))}>
            {p.accion.texto}
          </Button>
        ) : (
          <p className="cds--type-body-compact-01">{TEXTOS.sinPermiso}</p>
        )}
      </div>
    </section>
  );
}

// La urgencia en palabras con su ícono (el color nunca va solo): los de error y advertencia de la severidad (DESIGN.md).
function Urgencia({ valor }: { valor: PendienteDeObra["urgencia"] }) {
  const bloquea = valor === "bloquea";
  const Icono = bloquea ? WarningFilled : WarningAltFilled;
  return (
    <span className={`silice-bandeja__urgencia silice-sev silice-sev--${bloquea ? "error" : "advertencia"}`}>
      <Icono size={16} className="silice-sev__icono" aria-hidden="true" />
      {TEXTOS.urgencias[valor]}
    </span>
  );
}

// El nombre de la obra y, si hay otra con el mismo nombre en otra carpeta, la suya en letra secundaria.
function NombreDeObra({ pendiente: p, carpetaDe }: { pendiente: PendienteDeObra; carpetaDe: CarpetaDe }) {
  const carpeta = carpetaDe(p);
  return (
    <span className="silice-bandeja__obra">
      {p.obra}
      {carpeta !== undefined && <span className="silice-bandeja__carpeta"> · {carpeta}</span>}
    </span>
  );
}
