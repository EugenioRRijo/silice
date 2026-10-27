import { Add, ChevronDown, ChevronRight } from "@carbon/icons-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { Link, useMatch, useNavigate } from "react-router";
import { DialogoNuevaObra } from "../shell/obras/DialogoNuevaObra";
import type { DestinoDeNuevaObra } from "../shell/obras/DialogoNuevaObra";
import "./BarraLateral.scss";
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

interface Props {
  obraAbierta: { carpeta: string | null; obraId: number } | null;
  seccion: SeccionId | null;
}

const claveDe = (o: { carpeta: string | null; obra_id: number }) => `${o.carpeta ?? ""}|${o.obra_id}`;

interface Grupo {
  carpeta: string | null;
  titulo: string;
  obras: ObraDeCarpeta[];
}

function agruparPorCarpeta(obras: ObraDeCarpeta[]): Grupo[] {
  const grupos = new Map<string, Grupo>();
  for (const o of obras) {
    const clave = o.carpeta ?? "";
    const grupo = grupos.get(clave) ?? { carpeta: o.carpeta, titulo: o.carpeta_titulo, obras: [] };
    grupo.obras.push(o);
    grupos.set(clave, grupo);
  }
  return [...grupos.values()];
}

// Barra lateral del marco nuevo: Pendientes, el árbol de Obras (la abierta, desplegada con sus secciones) y Empresa. Es
// un `tree` de WAI-ARIA: una sola parada de Tab, flechas para recorrer, derecha despliega e izquierda pliega. Todavía no
// la monta marco/Marco (Tarea 8 del plan del marco). Los contadores llegan en F3.
// Pasa de 250 líneas porque el árbol, su teclado y la ventana de Nueva obra comparten un mismo estado (qué está desplegado,
// qué fila tiene el foco); separarlos obligaría a subir ese estado sin quitar complejidad.
export function BarraLateral({ obraAbierta, seccion }: Props) {
  const { acciones, puedeCambiarDeCarpeta, oferta } = useOferta();
  const navegar = useNavigate();
  const base = useId();
  const { obras, carpetaActual, estado, recargar } = useObras();
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
  const grupos = agruparPorCarpeta(visibles);
  // «Nueva obra» crea donde está la persona: en la carpeta de la obra abierta en la ruta o, sin obra, en la de la sesión.
  const carpetaDeCreacion = obraAbierta === null ? carpetaActual : obraAbierta.carpeta;
  const tituloDeCreacion =
    obras.find((o) => o.carpeta === carpetaDeCreacion)?.carpeta_titulo ??
    (carpetaDeCreacion === null ? "Carpeta de la empresa" : carpetaDeCreacion.replace(/\.db$/i, ""));
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

  function filaDeObra(o: ObraDeCarpeta) {
    const clave = claveDe(o);
    const abierta = desplegada(clave);
    const Chevron = abierta ? ChevronDown : ChevronRight;
    return (
      <li key={clave} role="none">
        <Link
          id={idDe(clave)}
          to={rutaDeObra(o.carpeta, o.obra_id, "resumen")}
          role="treeitem"
          aria-expanded={abierta}
          data-clave={clave}
          tabIndex={tabulable === clave ? 0 : -1}
          onFocus={() => setFoco(clave)}
          className="silice-marco-lateral__fila silice-marco-lateral__obra"
        >
          <Chevron size={16} aria-hidden="true" />
          {o.obra}
        </Link>
        {abierta && (
          <ul role="group" aria-labelledby={idDe(clave)} className="silice-marco-lateral__secciones">
            {secciones.map((s) => {
              const claveSeccion = `${clave}|${s.id}`;
              return (
                <li key={s.id} role="none">
                  <Link
                    to={rutaDeObra(o.carpeta, o.obra_id, s.id)}
                    role="treeitem"
                    aria-current={claveSeccion === claveActiva ? "page" : undefined}
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
    if (estado === "lista" && visibles.length === 0) {
      return <p className="silice-marco-lateral__aviso">Todavía no hay obras</p>;
    }
    return (
      <ul ref={arbol} role="tree" aria-label="Obras" className="silice-marco-lateral__arbol" onKeyDown={alTeclear}>
        {grupos.length > 1
          ? grupos.map((g) => {
              const idGrupo = idDe(`g|${g.carpeta ?? ""}`);
              return (
                <li key={g.carpeta ?? ""} role="none">
                  <span id={idGrupo} className="silice-marco-lateral__carpeta">
                    {g.titulo}
                  </span>
                  <ul role="group" aria-labelledby={idGrupo}>
                    {g.obras.map(filaDeObra)}
                  </ul>
                </li>
              );
            })
          : visibles.map(filaDeObra)}
      </ul>
    );
  }

  return (
    <aside className="silice-marco-lateral" aria-label="Barra lateral">
      <Link
        to={RUTA_DE_PENDIENTES}
        aria-current={enPendientes ? "page" : undefined}
        className="silice-marco-lateral__fila silice-marco-lateral__pendientes"
      >
        Pendientes
      </Link>

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
          navegar(rutaDeObra(destino.carpeta, Number(obra.codigo), "resumen"));
        }}
      />
    </aside>
  );
}
