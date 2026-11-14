import { Accordion, AccordionItem } from "@carbon/react";
import { TablaDensa } from "../../comun/TablaDensa";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import type { Similar } from "./cliente";
import { COLUMNAS, TIPOS, TITULOS } from "./tablas";
import { unidadEscrita } from "../../comun/unidades";

interface Props {
  similares: Similar[];
  // El nivel de su titulo: h2 en la pantalla, h3 en el panel de «Agregar partida» (plan F4, Tarea 9).
  nivel?: 2 | 3;
}

function tituloDe(s: Similar): string {
  const puntaje = Number(s.puntaje);
  const texto = Number.isFinite(puntaje) ? puntaje.toFixed(2) : String(s.puntaje);
  return `${formatoEsVe(texto)} · ${s.codigo} · ${s.descripcion}`;
}

// Ayuda 1: partidas parecidas, de solo lectura. La persona copia a mano lo que le sirva; nada se llena solo.
export function Similares({ similares, nivel = 2 }: Props) {
  if (similares.length === 0) return null;
  const Titulo = `h${nivel}` as const;
  return (
    <section className="silice-componer__bloque" aria-labelledby="componer-similares">
      <Titulo id="componer-similares" className="cds--type-heading-compact-02">
        Partidas similares del catálogo
      </Titulo>
      <p className="silice-componer__nota cds--type-body-compact-01">
        Sugerencias de solo lectura: copie a mano lo que le sirva en las tablas de abajo; el sistema no llena nada por
        su cuenta.
      </p>
      <Accordion size="sm">
        {similares.map((s) => (
          <AccordionItem key={s.codigo} title={tituloDe(s)}>
            {s.aviso && <p className="cds--type-body-compact-01">{s.aviso}</p>}
            {s.tablas && s.rendimiento !== null && (
              <p className="cds--type-body-compact-01">
                Rendimiento: {formatoEsVe(s.rendimiento)} {unidadEscrita(s.unidad ?? "")}/día
              </p>
            )}
            {s.tablas &&
              TIPOS.filter((t) => s.tablas![t].length > 0).map((t) => (
                <div key={t}>
                  <p className="cds--type-heading-compact-01">{TITULOS[t]}</p>
                  <TablaDensa
                    etiqueta={`${TITULOS[t]} de ${s.codigo}`}
                    // Las celdas llegan escritas en es-VE («1.500,5»), que `compararDecimales` no lee: sin orden.
                    columnas={COLUMNAS[t].map((c) => ({
                      clave: c.clave,
                      titulo: c.titulo,
                      numerica: c.numerica,
                      ordenable: false,
                    }))}
                    filas={s.tablas![t].map((f, i) => ({ id: `${s.codigo}-${t}-${i}`, ...f }))}
                  />
                </div>
              ))}
          </AccordionItem>
        ))}
      </Accordion>
    </section>
  );
}
