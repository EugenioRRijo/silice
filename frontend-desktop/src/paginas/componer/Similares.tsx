import { Accordion, AccordionItem, Button } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import { TablaDensa } from "../../comun/TablaDensa";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import type { Similar } from "./cliente";
import { COLUMNAS, TIPOS, TITULOS } from "./tablas";
import { unidadEscrita } from "../../comun/unidades";

interface Props {
  similares: Similar[];
  // El nivel de su titulo: h2 en la pantalla, h3 en el panel de «Agregar partida» (plan F4, Tarea 9).
  nivel?: 2 | 3;
  // «Empezar desde esta» (decisión de Eugenio, 2026-11-23): copia sus insumos y su rendimiento a la composición. Sin él,
  // la lista es de solo lectura.
  alEmpezarDesde?: (similar: Similar) => void;
  // Ya hay insumos o rendimiento escritos: empezar desde una parecida los reemplaza, así que antes se pregunta.
  conAlgoEscrito?: boolean;
}

function tituloDe(s: Similar): string {
  const puntaje = Number(s.puntaje);
  const texto = Number.isFinite(puntaje) ? puntaje.toFixed(2) : String(s.puntaje);
  return `${s.codigo} · ${s.descripcion} (similitud ${formatoEsVe(texto)})`;
}

// Ayuda 1: partidas parecidas del catálogo. Con «Empezar desde» la persona copia sus insumos y su rendimiento y luego los
// ajusta (decisión de Eugenio, 2026-11-23: quien no domina el oficio no copia tres tablas a mano). Nada se llena sin que
// lo pulse, nada se guarda hasta «Guardar composición» y, si ya escribió algo, se pregunta antes de reemplazarlo.
export function Similares({ similares, nivel = 2, alEmpezarDesde, conAlgoEscrito = false }: Props) {
  // La parecida que espera confirmación para reemplazar lo escrito, o null.
  const [porConfirmar, setPorConfirmar] = useState<Similar | null>(null);
  const cancelar = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (porConfirmar !== null) cancelar.current?.focus();
  }, [porConfirmar]);
  if (similares.length === 0) return null;
  const Titulo = `h${nivel}` as const;
  const empezar = (s: Similar) => {
    if (conAlgoEscrito) {
      setPorConfirmar(s);
      return;
    }
    alEmpezarDesde?.(s);
  };
  return (
    <section className="silice-componer__bloque" aria-labelledby="componer-similares">
      <Titulo id="componer-similares" className="cds--type-heading-compact-02">
        Partidas similares del catálogo
      </Titulo>
      <p className="silice-componer__nota cds--type-body-compact-01">
        {alEmpezarDesde === undefined
          ? "Sugerencias de solo lectura: copie a mano lo que le sirva en las tablas de abajo; el sistema no llena nada por su cuenta."
          : "Puede empezar desde una de ellas: copia sus insumos y su rendimiento, y luego los ajusta. Nada se guarda hasta «Guardar composición»."}
      </p>
      <Accordion size="sm">
        {similares.map((s) => (
          <AccordionItem key={s.codigo} title={tituloDe(s)}>
            {s.aviso && <p className="cds--type-body-compact-01">{s.aviso}</p>}
            {s.tablas && alEmpezarDesde !== undefined && (
              <Button kind="tertiary" size="sm" onClick={() => empezar(s)}>
                {`Empezar desde ${s.codigo}`}
              </Button>
            )}
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
      {porConfirmar !== null && (
        <div role="alert" className="silice-componer__reemplazo">
          <p className="cds--type-body-compact-01">
            {`Se reemplazarán los insumos y el rendimiento que ya escribió por los de ${porConfirmar.codigo}.`}
          </p>
          <div className="silice-componer__acciones">
            <Button ref={cancelar} kind="secondary" size="sm" onClick={() => setPorConfirmar(null)}>
              Cancelar
            </Button>
            <Button
              kind="danger--tertiary"
              size="sm"
              onClick={() => {
                alEmpezarDesde?.(porConfirmar);
                setPorConfirmar(null);
              }}
            >
              {`Reemplazar por los de ${porConfirmar.codigo}`}
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}
