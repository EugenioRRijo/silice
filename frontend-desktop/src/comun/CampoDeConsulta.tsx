import type { JSX } from "react";
import { CampoConBusqueda } from "./CampoConBusqueda";
import { buscadorDeConsulta } from "./consulta";
import type { TablaDeConsulta } from "./consulta";

interface Props {
  id: string;
  etiqueta: string;
  ayuda?: string;
  tabla: TablaDeConsulta;
  texto: string;
  alCambiarTexto: (texto: string) => void;
  alExpirar: () => void;
  invalido?: boolean;
  textoInvalido?: string;
}

const buscadores = new Map<TablaDeConsulta, ReturnType<typeof buscadorDeConsulta>>();

function buscadorDe(tabla: TablaDeConsulta) {
  let buscador = buscadores.get(tabla);
  if (buscador === undefined) {
    buscador = buscadorDeConsulta(tabla);
    buscadores.set(tabla, buscador);
  }
  return buscador;
}

// Un campo de texto con las sugerencias de una tabla (plan vial, Tarea 20). Lo elegido y lo escrito terminan igual en el
// campo: el texto es de la pagina, que lo valida; si el codigo no esta en la lista se puede usar tal cual, porque la
// tabla puede ir por detras de lo que la persona tiene en la mano. Sin componente propio de busqueda: es CampoConBusqueda.
export function CampoDeConsulta({
  id,
  etiqueta,
  ayuda,
  tabla,
  texto,
  alCambiarTexto,
  alExpirar,
  invalido,
  textoInvalido,
}: Props): JSX.Element {
  return (
    <CampoConBusqueda
      id={id}
      etiqueta={etiqueta}
      ayuda={ayuda}
      texto={texto}
      alCambiarTexto={alCambiarTexto}
      buscar={buscadorDe(tabla)}
      alElegir={(opcion) => alCambiarTexto(opcion.valor.valor)}
      valorPropio={{ rotulo: (t) => `Usar «${t.trim()}» tal cual`, alUsar: (t) => alCambiarTexto(t.trim()) }}
      vacio={{
        titulo: "¿No lo encuentra?",
        pasos: "Pruebe con otra palabra o con el código. Si no está en la lista, puede escribirlo tal cual.",
      }}
      alExpirar={alExpirar}
      invalido={invalido}
      textoInvalido={textoInvalido}
    />
  );
}
