import { useEffect, useReducer } from "react";
import type { CSSProperties } from "react";
import type { HallazgoLibroRespuesta } from "../api/tipos";
import type { Halo } from "./halos";
import type { HojaVisor } from "./hojaVisor";
import { IconoDeSeveridad } from "../severidad/IconoDeSeveridad";

interface Props {
  halos: Halo[];
  hallazgos: HallazgoLibroRespuesta[];
  visor: HojaVisor | null;
  // Posicion del hallazgo elegido en `hallazgos`, o null.
  seleccionado: number | null;
  onElegir: (indice: number) => void;
}

function etiquetaDe(halo: Halo, hallazgos: HallazgoLibroRespuesta[]): string {
  const celda = hallazgos[halo.indices[0]].celda;
  if (halo.indices.length === 1) return `${halo.estilo.texto} en ${celda}`;
  return `${halo.indices.length} hallazgos en ${celda}, el más grave: ${halo.estilo.texto}`;
}

// Capa DOM sobre el lienzo de la hoja (RS2-8). No pinta estilos dentro de la replica: cada halo es un contorno
// sin relleno (el valor de la celda se lee entero) mas una insignia con el icono de la severidad en una esquina.
// Sigue a la celda porque se vuelve a calcular cada vez que el visor avisa (desplazamiento, acercamiento,
// cambio de hoja o de tamano). Sin animacion.
export function CapaHalos({ halos, hallazgos, visor, seleccionado, onElegir }: Props) {
  const [, recalcular] = useReducer((n: number) => n + 1, 0);

  useEffect(() => {
    if (!visor) return;
    return visor.alCambiar(recalcular);
  }, [visor]);

  const area = visor?.area() ?? null;
  if (!visor || !area) return <div className="capa-halos" aria-hidden="true" />;

  const hoja = visor.hojaActiva();
  const estiloCapa: CSSProperties = { left: area.x, top: area.y, width: area.ancho, height: area.alto };

  return (
    <div className="capa-halos" style={estiloCapa}>
      {halos
        .filter((h) => h.hoja === hoja)
        .map((halo) => {
          const r = visor.rectanguloDe(halo);
          if (!r) return null;
          const elegido = seleccionado !== null && halo.indices.includes(seleccionado);
          const estilo = {
            left: r.x - area.x,
            top: r.y - area.y,
            width: r.ancho,
            height: r.alto,
            "--halo-color": `var(${halo.estilo.token})`,
          } as CSSProperties;
          return (
            <div
              key={halo.clave}
              className={[
                "halo",
                elegido ? "halo--elegido" : "",
                // El amarillo no alcanza 3:1 sobre el fondo claro: lleva un segundo contorno oscuro de 1 px.
                halo.estilo.token === "--silice-sev-advertencia" ? "halo--advertencia" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              style={estilo}
              aria-current={elegido ? "true" : undefined}
            >
              {/* Con nombre propio pero fuera del orden de Tab: la lista de hallazgos es el camino del teclado. */}
              <button
                type="button"
                tabIndex={-1}
                className="halo__insignia"
                aria-label={etiquetaDe(halo, hallazgos)}
                title={`${halo.estilo.texto}: ${hallazgos[halo.indices[0]].descripcion}`}
                onClick={() => onElegir(halo.indices[0])}
              >
                <span className="halo__icono" aria-hidden="true">
                  <IconoDeSeveridad nombre={halo.estilo.icono} size={12} />
                </span>
              </button>
            </div>
          );
        })}
    </div>
  );
}
