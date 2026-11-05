import { useMemo } from "react";
import { CampoConBusqueda } from "../../comun/CampoConBusqueda";
import { buscadorDePartidasDelContrato, partidaDelContrato } from "./partidasDelContrato";
import type { PartidaDelContrato } from "./partidasDelContrato";

interface Props {
  id: string;
  etiqueta: string;
  ayuda?: string;
  // Las partidas del contrato, o null si no hay con que guiar (entonces el campo es de texto libre).
  partidas: PartidaDelContrato[] | null;
  // true: solo vale una partida del contrato (una valuacion mide lo contratado) y no se ofrece usar otro codigo «tal
  // cual». false: se puede dejar cualquiera, p. ej. el costo real, que es opcional y puede ser un gasto general.
  soloDelContrato: boolean;
  texto: string;
  alCambiarTexto: (texto: string) => void;
  alExpirar: () => void;
  invalido?: boolean;
  textoInvalido?: string;
  // La lista va en un portal con position: fixed (la celda de una tabla recorta un menu absoluto).
  enCelda?: boolean;
  etiquetaOculta?: boolean;
  conBorrar?: boolean;
  tamano?: "sm" | "md";
}

// Un campo de codigo de partida con las del contrato de esa obra (CampoConBusqueda en modo local). Lo elegido y lo escrito
// terminan igual en el campo: el texto es de la pagina, que lo valida. Fuera de una celda, bajo el campo queda la
// descripcion y la unidad de lo elegido, para medir en la unidad correcta. Al salir del campo, un codigo escrito completo
// se deja con la forma del contrato («ob-a» -> «OB-A»).
export function CampoDePartida({
  id,
  etiqueta,
  ayuda,
  partidas,
  soloDelContrato,
  texto,
  alCambiarTexto,
  alExpirar,
  invalido,
  textoInvalido,
  enCelda = false,
  etiquetaOculta = enCelda,
  conBorrar = !enCelda,
  tamano,
}: Props) {
  const buscar = useMemo(() => buscadorDePartidasDelContrato(partidas ?? []), [partidas]);
  const cerrada = soloDelContrato && partidas !== null;
  const elegida = partidas ? partidaDelContrato(partidas, texto) : null;
  const ayudaViva = !enCelda && elegida ? `${elegida.descripcion} · ${elegida.unidad}` : enCelda ? undefined : ayuda;
  return (
    <CampoConBusqueda
      id={id}
      etiqueta={etiqueta}
      etiquetaOculta={etiquetaOculta}
      conBorrar={conBorrar}
      ayuda={ayudaViva}
      texto={texto}
      alCambiarTexto={alCambiarTexto}
      buscar={buscar}
      alElegir={(opcion) => alCambiarTexto(opcion.valor.codigo)}
      valorPropio={cerrada ? undefined : { rotulo: (t) => `Usar «${t.trim()}» tal cual`, alUsar: (t) => alCambiarTexto(t.trim()) }}
      vacio={
        partidas === null
          ? { titulo: "La lista de partidas del contrato no está disponible.", pasos: "Escriba el código y úselo tal cual." }
          : {
              titulo: "¿No la encuentra?",
              pasos: cerrada
                ? "Pruebe con otra palabra o con el código. Solo se pueden usar partidas del contrato."
                : "Pruebe con otra palabra o con el código. Si no está en la lista, puede escribirlo tal cual.",
            }
      }
      // Con la lista, el campo vacio ya ofrece todas; sin ella no hay nada que buscar hasta que se escribe algo.
      minimoDeLetras={partidas === null ? 1 : 0}
      alSalir={() => {
        if (elegida && elegida.codigo !== texto) alCambiarTexto(elegida.codigo);
      }}
      enCelda={enCelda}
      alExpirar={alExpirar}
      invalido={invalido}
      textoInvalido={textoInvalido}
      tamano={tamano}
    />
  );
}
