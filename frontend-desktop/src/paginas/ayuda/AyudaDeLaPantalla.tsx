import { Fragment } from "react";
import { QueEsEsto } from "../../comun/QueEsEsto";
import { EnlaceDeAyuda } from "./EnlaceDeAyuda";
import { rutaDeTema } from "./temas";
import { AYUDA_DE_PANTALLAS, guiaPorId, terminoPorId } from "./textos";
import "./ayuda.scss";

// El «¿Qué es esto?» de una pantalla de la obra o de un espacio (F7, tarea A1). Es el mismo `QueEsEsto` plegado de las
// pestañas del Presupuesto (no un tercer patrón): el marco lo pone encima de la pantalla, tras la barra de vistas, así que
// una sola pieza cubre todas sin tocar cada pantalla. Dice para qué sirve y cuándo usarla y enlaza su guía y los términos
// del glosario que la pantalla usa sin explicar. Una pantalla sin texto (el Presupuesto, cuyas pestañas ya traen el suyo) no
// pinta nada.
export function AyudaDeLaPantalla({ pagina }: { pagina: string }) {
  const ayuda = Object.hasOwn(AYUDA_DE_PANTALLAS, pagina) ? AYUDA_DE_PANTALLAS[pagina] : undefined;
  if (ayuda === undefined) return null;
  const terminos = ayuda.terminos ?? [];
  return (
    <div className="silice-ayuda-de-pantalla">
      <QueEsEsto titulo={ayuda.titulo}>
        {ayuda.parrafos.map((p) => (
          <p key={p}>{p}</p>
        ))}
        {(ayuda.guia !== undefined || terminos.length > 0) && (
          <p className="silice-ayuda-de-pantalla__enlaces">
            {ayuda.guia !== undefined && (
              <EnlaceDeAyuda a={rutaDeTema(`guia-${ayuda.guia}`)}>{`Guía «${guiaPorId(ayuda.guia).titulo}»`}</EnlaceDeAyuda>
            )}
            {ayuda.guia !== undefined && terminos.length > 0 && " · "}
            {terminos.length > 0 && "En el glosario: "}
            {terminos.map((id, i) => (
              <Fragment key={id}>
                {i > 0 && ", "}
                <EnlaceDeAyuda a={rutaDeTema(`glosario-${id}`)}>{terminoPorId(id).termino}</EnlaceDeAyuda>
              </Fragment>
            ))}
          </p>
        )}
      </QueEsEsto>
    </div>
  );
}
