import { Add, ChevronDown, ChevronRight } from "@carbon/icons-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { Link, useMatch, useNavigate } from "react-router";
import { Pildora } from "../comun/Pildora";
import { contarPorObra } from "../paginas/pendientes/logica";
import { TEXTOS as TEXTOS_PENDIENTES } from "../paginas/pendientes/textos";
import { DialogoNuevaObra } from "../shell/obras/DialogoNuevaObra";
import type { DestinoDeNuevaObra } from "../shell/obras/DialogoNuevaObra";
import "./BarraLateral.scss";
import { obrasConMismoNombre } from "./homonimas";
import { abrirNuevaObra, cerrarNuevaObra, useNuevaObraAbierta } from "./nuevaObra";
import { obrasAlcanzables, useOferta } from "./oferta";
import {
  PATRON_DE_EMPRESA,
  RUTA_DE_PENDIENTES,
  rutaDeEmpresa,
  rutaDeObra,
  type SeccionId,
} from "./secciones";
import { useObras, type ObraDeCarpeta } from "./useObras";
import { usePendientes } from "./usePendientes";

interface Props {
  obraAbierta: { carpeta: string | null; obraId: number } | null;
  seccion: SeccionId | null;
}

const claveDe = (o: { carpeta: string | null; obra_id: number }) => `${o.carpeta ?? ""}|${o.obra_id}`;

// Barra lateral del marco nuevo: Pendientes, el árbol de Obras (la abierta, desplegada con sus secciones) y Empresa. Es
// un `tree` de WAI-ARIA: una sola parada de Tab, flechas para recorrer, derecha despliega e izquierda pliega. Sin
// títulos de grupo por carpeta (D-F3-3): las obras van por nombre y solo las de nombre repetido dicen su carpeta. Las
// píldoras de Pendientes y de cada obra salen de los pendientes que el marco ya cargó (`usePendientes`).
// Pasa de 250 líneas porque el árbol, su teclado y la ventana de Nueva obra comparten un mismo estado (qué está desplegado,
// qué fila tiene el foco); separarlos obligaría a subir ese estado sin quitar complejidad.
export function BarraLateral({ obraAbierta, seccion }: Props) {
  const { acciones, puedeCambiarDeCarpeta, oferta } = useOferta();
  const navegar = useNavigate();
  const base = useId();
  const { obras, carpetaActual, tituloActual, estado, recargar } = useObras();
  // Los contadores solo se pintan con la lectura lista y mayor que cero: cargando o con error no hay número (ni uno falso).
  const carga = usePendientes();
  const porObra = useMemo(() => contarPorObra(carga.estado === "listo" ? carga.pendientes : []), [carga]);
  const total = carga.estado === "listo" ? carga.pendientes.length : 0;
  const enPendientes = useMatch(RUTA_DE_PENDIENTES) !== null;
  const entradaActiva = useMatch(PATRON_DE_EMPRESA)?.params["entrada"] ?? null;
  // El diálogo lo puede pedir también la mesa (marco/nuevaObra); al irse la barra (salir de la sesión) se cierra.
  const nuevaAbierta = useNuevaObraAbierta();
  useEffect(() => cerrarNuevaObra, []);
  // Lo que la persona desplegó o plegó a mano; sin decisión, solo está desplegada la obra abierta.
  const [manual, setManual] = useState<Record<string, boolean>>({});
  const [foco, setFoco] = useState<string | null>(null);
  const arbol = useRef<HTMLUListElement>(null);

  const { secciones, entradas } = oferta;
  const puedeCrear = acciones.includes("editar_hoja");

  const visibles = useMemo(
    () => obrasAlcanzables(obras, carpetaActual, puedeCambiarDeCarpeta),
    [obras, carpetaActual, puedeCambiarDeCarpeta],
  );
  const carpetaDeHomonimas = useMemo(() => obrasConMismoNombre(visibles), [visibles]);
  // «Nueva obra» crea donde está la persona: en la carpeta de la obra abierta en la ruta o, sin obra, en la de la sesión.
  const carpetaDeCreacion = obraAbierta === null ? carpetaActual : obraAbierta.carpeta;
  // El título lo da el servidor: el de la carpeta de la sesión viene con la lista; el de otra, con sus obras.
  const tituloDeCreacion =
    carpetaDeCreacion === carpetaActual
      ? tituloActual
      : (obras.find((o) => o.carpeta === carpetaDeCreacion)?.carpeta_titulo ?? "");
  const destino: DestinoDeNuevaObra = {
    carpeta: carpetaDeCreacion,
    titulo: tituloDeCreacion,
    enOtraCarpeta: carpetaDeCreacion !== carpetaActual,
  };

  const claveAbierta = obraAbierta === null ? null : claveDe({ carpeta: obraAbierta.carpeta, obra_id: obraAbierta.obraId });
  const desplegada = (clave: string) => manual[clave] ?? clave === claveAbierta;
  const claveActiva = claveAbierta !== null && seccion !== null ? `${claveAbierta}|${seccion}` : claveAbierta;
  const idDe = (clave: string) => `${base}-${clave.replace(/[^A-Za-z0-9]/g, "_")}`;

  // Una sola parada de Tab: el último con foco, si sigue en pantalla, o el activo, o el primero.
  const clavesVisibles: string[] = [];
  for (const o of visibles) {
    const clave = claveDe(o);
    clavesVisibles.push(clave);
    if (desplegada(clave)) for (const s of secciones) clavesVisibles.push(`${clave}|${s.id}`);
  }
  const tabulable = [foco, claveActiva].find((c) => c !== null && clavesVisibles.includes(c)) ?? clavesVisibles[0] ?? null;

  function alTeclear(e: KeyboardEvent<HTMLUListElement>) {
    const actual = (e.target as HTMLElement).closest<HTMLElement>('[role="treeitem"]');
    if (!actual) return;
    const todas = [...(arbol.current?.querySelectorAll<HTMLElement>('[role="treeitem"]') ?? [])];
    const i = todas.indexOf(actual);
    const clave = actual.dataset["clave"] ?? "";
    const ir = (destino: HTMLElement | undefined) => {
      e.preventDefault();
      destino?.focus();
    };
    switch (e.key) {
      case "ArrowDown":
        return ir(todas[i + 1]);
      case "ArrowUp":
        return ir(todas[i - 1]);
      case "Home":
        return ir(todas[0]);
      case "End":
        return ir(todas[todas.length - 1]);
      case "ArrowRight": {
        const expandida = actual.getAttribute("aria-expanded");
        if (expandida === "false") {
          e.preventDefault();
          setManual((m) => ({ ...m, [clave]: true }));
        } else if (expandida === "true") ir(todas[i + 1]);
        return;
      }
      case "ArrowLeft": {
        if (actual.getAttribute("aria-expanded") === "true") {
          e.preventDefault();
          setManual((m) => ({ ...m, [clave]: false }));
        } else {
          const padre = actual.dataset["padre"];
          if (padre) ir(todas.find((f) => f.dataset["clave"] === padre));
        }
        return;
      }
    }
  }

  // Las obras son de nivel 1 y sus secciones de nivel 2; los niveles se dicen con aria-level, aria-setsize y aria-posinset.
  function filaDeObra(o: ObraDeCarpeta, tamano: number, posicion: number) {
    const nivel = 1;
    const clave = claveDe(o);
    const carpeta = carpetaDeHomonimas.get(clave);
    const cuenta = porObra.get(clave) ?? 0;
    // El nombre accesible dice lo mismo que se ve: la obra, su carpeta si hay homónima y cuántos pendientes tiene.
    const nombre = [o.obra, carpeta, cuenta > 0 ? TEXTOS_PENDIENTES.porHacer(cuenta) : undefined].filter(Boolean).join(", ");
    const abierta = desplegada(clave);
    const Chevron = abierta ? ChevronDown : ChevronRight;
    return (
      <li key={clave} role="none">
        <Link
          id={idDe(clave)}
          to={rutaDeObra(o.carpeta, o.obra_id, "resumen")}
          role="treeitem"
          aria-label={nombre === o.obra ? undefined : nombre}
          aria-expanded={abierta}
          aria-level={nivel}
          aria-setsize={tamano}
          aria-posinset={posicion}
          data-clave={clave}
          tabIndex={tabulable === clave ? 0 : -1}
          onFocus={() => setFoco(clave)}
          className="silice-marco-lateral__fila silice-marco-lateral__obra"
        >
          <Chevron size={16} aria-hidden="true" />
          <span className="silice-marco-lateral__nombre">
            {o.obra}
            {carpeta !== undefined && <span className="silice-marco-lateral__de-carpeta">{carpeta}</span>}
          </span>
          {cuenta > 0 && <Pildora valor={cuenta} />}
        </Link>
        {abierta && (
          <ul role="group" aria-labelledby={idDe(clave)} className="silice-marco-lateral__secciones">
            {secciones.map((s, i) => {
              const claveSeccion = `${clave}|${s.id}`;
              return (
                <li key={s.id} role="none">
                  <Link
                    to={rutaDeObra(o.carpeta, o.obra_id, s.id)}
                    role="treeitem"
                    aria-current={claveSeccion === claveActiva ? "page" : undefined}
                    aria-level={nivel + 1}
                    aria-setsize={secciones.length}
                    aria-posinset={i + 1}
                    data-clave={claveSeccion}
                    data-padre={clave}
                    tabIndex={tabulable === claveSeccion ? 0 : -1}
                    onFocus={() => setFoco(claveSeccion)}
                    className="silice-marco-lateral__fila silice-marco-lateral__seccion"
                  >
                    {s.titulo}
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </li>
    );
  }

  function zonaDeObras() {
    if (estado === "error") {
      return (
        <div className="silice-marco-lateral__aviso" role="alert">
          <p>No se pudieron cargar las obras</p>
          <button type="button" className="silice-marco-lateral__reintentar" onClick={recargar}>
            Reintentar
          </button>
        </div>
      );
    }
    // Sin nada que mostrar: mientras llega la primera lista (o una recarga de una lista vacía) se dice que carga; no se
    // pinta un árbol vacío. Con obras ya cargadas, una recarga conserva el árbol.
    if (visibles.length === 0) {
      return estado === "cargando" ? (
        <p className="silice-marco-lateral__aviso" role="status">
          Cargando obras…
        </p>
      ) : (
        <p className="silice-marco-lateral__aviso">Todavía no hay obras</p>
      );
    }
    return (
      <ul ref={arbol} role="tree" aria-label="Obras" className="silice-marco-lateral__arbol" onKeyDown={alTeclear}>
        {visibles.map((o, i) => filaDeObra(o, visibles.length, i + 1))}
      </ul>
    );
  }

  return (
    <aside className="silice-marco-lateral" aria-label="Barra lateral">
      <Link
        to={RUTA_DE_PENDIENTES}
        aria-current={enPendientes ? "page" : undefined}
        aria-label={total > 0 ? `Pendientes, ${TEXTOS_PENDIENTES.porHacer(total)}` : undefined}
        className="silice-marco-lateral__fila silice-marco-lateral__pendientes"
      >
        Pendientes
        {total > 0 && <Pildora valor={total} />}
      </Link>

      {/* Sin `leer_proyecto` la cuenta no ve obras: la zona no se pinta. */}
      {estado !== "sin_permiso" && (
        <div className="silice-marco-lateral__obras">
          <h2 className="silice-marco-lateral__titulo">Obras</h2>
          {puedeCrear && (
            <button type="button" className="silice-marco-boton-principal" onClick={abrirNuevaObra}>
              <Add size={20} aria-hidden="true" />
              Nueva obra
            </button>
          )}
          {zonaDeObras()}
        </div>
      )}

      <nav aria-label="Empresa" className="silice-marco-lateral__empresa">
        <h2 className="silice-marco-lateral__titulo">Empresa</h2>
        <ul>
          {entradas.map((e) => (
            <li key={e.id}>
              <Link
                to={rutaDeEmpresa(e.id)}
                aria-current={entradaActiva === e.id ? "page" : undefined}
                className="silice-marco-lateral__fila"
              >
                {e.titulo}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      <DialogoNuevaObra
        abierto={nuevaAbierta}
        alCerrar={cerrarNuevaObra}
        destino={destino}
        alCrear={(obra) => {
          cerrarNuevaObra();
          recargar();
          // El código lo da el servidor como texto; si no son dígitos no hay ruta a la obra nueva y se queda donde está.
          if (/^\d+$/.test(obra.codigo)) navegar(rutaDeObra(destino.carpeta, Number(obra.codigo), "resumen"));
        }}
      />
    </aside>
  );
}
