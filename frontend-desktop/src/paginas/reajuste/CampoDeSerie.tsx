import { useMemo } from "react";
import { CampoConBusqueda } from "../../comun/CampoConBusqueda";
import { buscadorDeSeries } from "./series";
import type { SerieDeIndice } from "./series";

interface Props {
  id: string;
  etiqueta: string;
  // Las series importadas, o null si no hay con que guiar (entonces el campo es de texto libre).
  series: SerieDeIndice[] | null;
  texto: string;
  alCambiarTexto: (texto: string) => void;
  alExpirar: () => void;
}

// El campo «Serie» de una fila de componentes: CampoConBusqueda en modo local, dentro de una celda (la lista va en un
// portal). Con la lista, solo vale una serie importada (el calculo rechaza las demas); sin ella, se puede escribir tal cual.
export function CampoDeSerie({ id, etiqueta, series, texto, alCambiarTexto, alExpirar }: Props) {
  const buscar = useMemo(() => buscadorDeSeries(series ?? []), [series]);
  return (
    <CampoConBusqueda
      id={id}
      etiqueta={etiqueta}
      etiquetaOculta
      conBorrar={false}
      texto={texto}
      alCambiarTexto={alCambiarTexto}
      buscar={buscar}
      alElegir={(opcion) => alCambiarTexto(opcion.valor.clave)}
      valorPropio={series === null ? { rotulo: (t) => `Usar «${t.trim()}» tal cual`, alUsar: (t) => alCambiarTexto(t.trim()) } : undefined}
      vacio={
        series === null
          ? { titulo: "La lista de series no está disponible.", pasos: "Escriba la clave y úsela tal cual." }
          : { titulo: "¿No la encuentra?", pasos: "Pruebe con otra palabra o con la clave. Las series se importan en «Índices del BCV»." }
      }
      minimoDeLetras={series === null ? 1 : 0}
      enCelda
      alExpirar={alExpirar}
    />
  );
}
