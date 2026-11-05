// La barra de pestañas de un espacio (Producción, Auditoría, Precios, Obra, Cuenta) y, con `nivel="subvista"`, el
// conmutador compacto de las vistas de una sección de la obra (plan F6, T3; diseño visual §1 y adenda A.3). Cada pestaña
// navega a su propia URL: es un enlace, no un panel local, así que la barra es un `nav` con `aria-current` y nunca un
// `tablist`. No pone encabezado: el único h1 de la pantalla lo pone la pantalla.
//
// Los enlaces de la barra están dentro del lienzo, que el marco no intercepta (Marco.alClicAntes): con cambios sin guardar
// preguntan ellos mismos, como cualquier enlace de una pantalla (useNavegarSeguro). Sin nada que perder, el enlace
// navega por sí solo (clic con Ctrl o Mayús, el botón del medio y el foco quedan como en cualquier enlace).
import type { MouseEvent } from "react";
import { Link } from "react-router";
import { esClicSimple, useNavegarSeguro } from "../shell/navegarSeguro";
import { paginaPorId, usable } from "../shell/rutas";
import { formulariosSucios } from "../shell/sucio";
import type { HerramientaDef } from "./espacios";
import "./BarraDeEspacio.scss";

export interface PestanaDeEspacio {
  id: string;
  titulo: string;
  ruta: string;
}

interface Propiedades {
  etiqueta: string;
  pestanas: readonly PestanaDeEspacio[];
  activa: string;
  nivel: "espacio" | "subvista";
}

export function BarraDeEspacio({ etiqueta, pestanas, activa, nivel }: Propiedades) {
  const navegarSeguro = useNavegarSeguro();
  function alPulsar(e: MouseEvent<HTMLAnchorElement>, ruta: string) {
    if (!esClicSimple(e)) return;
    if (formulariosSucios(ruta).length === 0) return;
    e.preventDefault();
    void navegarSeguro(ruta);
  }
  // Una sola vista (o ninguna) no se ofrece como elección: el conmutador de subvistas no se pinta (adenda A.1).
  if (nivel === "subvista" && pestanas.length <= 1) return null;
  const clase = nivel === "subvista" ? "silice-barra-espacio silice-barra-espacio--subvista" : "silice-barra-espacio";
  return (
    <nav aria-label={etiqueta} className={clase}>
      {pestanas.map((p) => (
        <Link
          key={p.id}
          to={p.ruta}
          onClick={(e) => alPulsar(e, p.ruta)}
          aria-current={p.id === activa ? "page" : undefined}
          className="silice-barra-espacio__pestana"
        >
          {p.titulo}
        </Link>
      ))}
    </nav>
  );
}

// Las pestañas que la cuenta puede usar, en el orden de la tabla: la misma regla que `primeraUsable` (permiso, modo
// entrega y módulos apagados, según `usable`). Una herramienta cuya pantalla no existe no se ofrece. `rutaDe` dice a
// dónde lleva cada una: quien monta la barra conoce la obra y la sección.
export function pestanasUsables(
  opciones: readonly HerramientaDef[],
  rutaDe: (herramienta: HerramientaDef) => string,
  acciones: readonly string[],
  modoEntrega: boolean,
  apagados: readonly string[],
): PestanaDeEspacio[] {
  const pestanas: PestanaDeEspacio[] = [];
  for (const opcion of opciones) {
    const pagina = paginaPorId(opcion.pagina);
    if (pagina === undefined || !usable(pagina, acciones, modoEntrega, apagados)) continue;
    pestanas.push({ id: opcion.id, titulo: opcion.titulo, ruta: rutaDe(opcion) });
  }
  return pestanas;
}
