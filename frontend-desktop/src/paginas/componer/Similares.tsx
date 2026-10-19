import { Accordion, AccordionItem } from "@carbon/react";
import { TablaDensa } from "../../comun/TablaDensa";
import type { Similar } from "./cliente";
import { COLUMNAS, TIPOS, TITULOS } from "./tablas";

interface Props {
  similares: Similar[];
}

function tituloDe(s: Similar): string {
  const puntaje = Number(s.puntaje);
  const texto = Number.isFinite(puntaje) ? puntaje.toFixed(2) : String(s.puntaje);
  return `${texto} · ${s.codigo} · ${s.descripcion}`;
}

// Ayuda 1: partidas parecidas, de solo lectura. La persona copia a mano lo que le sirva; nada se llena solo.
export function Similares({ similares }: Props) {
  if (similares.length === 0) return null;
  return (
    <section className="silice-componer__bloque" aria-labelledby="componer-similares">
      <h2 id="componer-similares" className="cds--type-heading-03">
        Partidas similares del catálogo
      </h2>
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
                Rendimiento: {s.rendimiento} {s.unidad}/día
              </p>
            )}
            {s.tablas &&
              TIPOS.filter((t) => s.tablas![t].length > 0).map((t) => (
                <div key={t}>
                  <p className="cds--type-heading-compact-01">{TITULOS[t]}</p>
                  <TablaDensa
                    etiqueta={`${TITULOS[t]} de ${s.codigo}`}
                    columnas={COLUMNAS[t].map((c) => ({ clave: c.clave, titulo: c.titulo, numerica: c.numerica }))}
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
