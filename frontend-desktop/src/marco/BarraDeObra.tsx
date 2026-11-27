// La barra del lugar dentro de una obra (especificación 2026-11-26, «Cara Papel y resaltador»), en dos filas. Fila 1: a la
// izquierda el nombre de la obra, que es un enlace a su Portada; en medio las tres herramientas (Presupuestar, Auditar y
// Anticipar), que agrupan las secciones de siempre sin cambiar ninguna ruta; a la derecha el menú de versión y la acción
// principal de la pantalla. Fila 2: las opciones de la herramienta activa como pestañas secundarias (OPCIONES_DE_HERRAMIENTA).
// Todo es un enlace con `aria-current`, nunca un `tablist` (navega por URL). Con cambios sin guardar los enlaces
// preguntan antes de salir, como los de BarraDeEspacio (useNavegarSeguro).
import { MenuButton, MenuItem } from "@carbon/react";
import type { MouseEvent, ReactNode } from "react";
import { Link } from "react-router";
import { esClicSimple, useNavegarSeguro } from "../shell/navegarSeguro";
import { formulariosSucios } from "../shell/sucio";
import { HERRAMIENTAS_DE_OBRA, OPCIONES_DE_HERRAMIENTA, herramientaDe, opcionActual, primeraRutaDe, rutaDeOpcion } from "./herramientas";
import { rutaDeObra } from "./secciones";
import type { SeccionId } from "./secciones";
import "./BarraDeObra.scss";

interface Props {
  carpeta: string | null;
  obraId: number;
  nombre: string;
  // Dónde está la persona ahora: sirve para marcar la herramienta y la opción actuales.
  seccion: SeccionId;
  subvista?: string;
  // Las secciones que la cuenta puede usar; sin ella se ofrecen todas. Una herramienta u opción sin ninguna no se pinta.
  usables?: readonly SeccionId[];
  // La acción principal de la pantalla (guardar, entregar…), a la derecha del menú de versión.
  accion?: ReactNode;
}

interface OpcionDeVersion {
  titulo: string;
  ruta: string;
  // La sección que la cuenta necesita poder usar para que la opción se ofrezca.
  seccion: SeccionId;
}

export function BarraDeObra({ carpeta, obraId, nombre, seccion, subvista, usables, accion }: Props) {
  const navegarSeguro = useNavegarSeguro();
  const actual = herramientaDe(seccion, subvista);
  const alPulsar = (e: MouseEvent<HTMLAnchorElement>, ruta: string) => {
    if (!esClicSimple(e) || formulariosSucios(ruta).length === 0) return;
    e.preventDefault();
    void navegarSeguro(ruta);
  };

  const portada = rutaDeObra(carpeta, obraId, "resumen");
  const herramientas = HERRAMIENTAS_DE_OBRA.flatMap((h) => {
    const ruta = primeraRutaDe(h.id, carpeta, obraId, usables);
    return ruta === null ? [] : [{ id: h.id, titulo: h.titulo, ruta }];
  });
  const opcionesDeVersion: OpcionDeVersion[] = (
    [
    { titulo: "Versiones", ruta: rutaDeObra(carpeta, obraId, "versiones"), seccion: "versiones" },
    { titulo: "Pedir aprobación", ruta: rutaDeObra(carpeta, obraId, "aprobaciones"), seccion: "aprobaciones" },
    { titulo: "Entregar al cliente", ruta: rutaDeObra(carpeta, obraId, "aprobaciones", "entregar"), seccion: "aprobaciones" },
    ] satisfies OpcionDeVersion[]
  ).filter((o) => usables === undefined || usables.includes(o.seccion));

  // La segunda fila: en Versiones (que no es una herramienta) no hay.
  const opciones =
    actual === "versiones" ? [] : OPCIONES_DE_HERRAMIENTA[actual].filter((o) => usables === undefined || usables.includes(o.seccion));
  const abierta = opcionActual(actual, seccion, subvista);
  const tituloDeLaFila = actual === "portada" ? "la portada" : (HERRAMIENTAS_DE_OBRA.find((h) => h.id === actual)?.titulo ?? "");

  return (
    <div className="silice-barra-obra">
      <div className="silice-barra-obra__fila">
        <Link
          to={portada}
          onClick={(e) => alPulsar(e, portada)}
          aria-current={actual === "portada" ? "page" : undefined}
          className="silice-barra-obra__nombre"
        >
          <span className="silice-barra-obra__titulo">{nombre}</span>
          <span className="silice-barra-obra__linea">Portada de la obra</span>
        </Link>

        <nav aria-label="Herramientas de la obra" className="silice-barra-obra__herramientas">
          {herramientas.map((h) => (
            <Link
              key={h.id}
              to={h.ruta}
              onClick={(e) => alPulsar(e, h.ruta)}
              aria-current={actual === h.id ? "page" : undefined}
              className="silice-barra-obra__herramienta"
            >
              {h.titulo}
            </Link>
          ))}
        </nav>

        <div className="silice-barra-obra__acciones">
          {opcionesDeVersion.length > 0 && (
            <MenuButton label="Versión" kind="ghost" size="sm" menuAlignment="bottom-end" className="silice-barra-obra__version">
              {opcionesDeVersion.map((o) => (
                <MenuItem key={o.titulo} label={o.titulo} onClick={() => void navegarSeguro(o.ruta)} />
              ))}
            </MenuButton>
          )}
          {accion}
        </div>
      </div>

      {opciones.length > 0 && (
        <nav aria-label={`Opciones de ${tituloDeLaFila}`} className="silice-barra-obra__opciones">
          {opciones.map((o) => {
            const ruta = rutaDeOpcion(o, carpeta, obraId);
            return (
              <Link
                key={o.id}
                to={ruta}
                onClick={(e) => alPulsar(e, ruta)}
                aria-current={abierta?.id === o.id ? "page" : undefined}
                className="silice-barra-obra__opcion"
              >
                {o.titulo}
              </Link>
            );
          })}
        </nav>
      )}
    </div>
  );
}
