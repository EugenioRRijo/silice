import { useMemo } from "react";
import { CampoConBusqueda } from "./CampoConBusqueda";
import { buscadorDeUnidades } from "./unidadesDelCatalogo";
import type { UnidadUsada } from "./unidadesDelCatalogo";

interface Props {
  id: string;
  etiqueta: string;
  etiquetaOculta?: boolean; // en una celda: la columna ya la rotula
  ayuda?: string;
  texto: string;
  alCambiar: (texto: string) => void;
  alExpirar: () => void;
  enCelda?: boolean;
  invalido?: boolean;
  textoInvalido?: string;
  deshabilitado?: boolean;
  tamano?: "sm" | "md";
}

// AC4 (pedido de Eugenio del 2026-10-21): la unidad con sugerencias de las que ya usa el catalogo de la carpeta. Lo
// escrito queda tal cual (la pagina es duena del texto) y elegir pone la unidad canonica; una que no esta se usa tal
// cual. Con una letra ya sugiere: «m» es una unidad. Lo usan la cabecera y los materiales de Componer y el insumo nuevo
// de la Hoja; en una celda no lleva «Borrar» (una parada de Tab de mas por fila, como la descripcion).
export function CampoDeUnidad({
  id,
  etiqueta,
  etiquetaOculta = false,
  ayuda,
  texto,
  alCambiar,
  alExpirar,
  enCelda = false,
  invalido,
  textoInvalido,
  deshabilitado,
  tamano = "sm",
}: Props) {
  const buscar = useMemo(() => buscadorDeUnidades(), []);
  return (
    <CampoConBusqueda<UnidadUsada>
      id={id}
      etiqueta={etiqueta}
      etiquetaOculta={etiquetaOculta}
      ayuda={ayuda}
      texto={texto}
      alCambiarTexto={alCambiar}
      buscar={buscar}
      alElegir={(opcion) => alCambiar(opcion.valor.unidad)}
      valorPropio={{
        rotulo: (t) => `Usar «${t.trim()}» tal cual`,
        alUsar: (t) => alCambiar(t.trim()),
      }}
      vacio={{
        titulo: "¿No la encuentra?",
        pasos: "Pruebe con otra grafía (m3, kg, saco). Si no está en el catálogo, puede usarla tal cual.",
      }}
      minimoDeLetras={1}
      alExpirar={alExpirar}
      enCelda={enCelda}
      conBorrar={!enCelda}
      invalido={invalido}
      textoInvalido={textoInvalido}
      deshabilitado={deshabilitado}
      tamano={tamano}
    />
  );
}
