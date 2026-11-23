import type { JSX } from "react";
import { useContext } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import { rutaDeObra } from "../../marco/secciones";
import { ComponerPartida } from "./ComponerPartida";
import type { PartidaCompuesta } from "./ComponerPartida";
import type { PasoSiguiente } from "./Guardar";

// Fuera de una obra, guardar termina aquí: la partida queda en el catálogo.
const sinMas = () => undefined;

// Lo que dice el éxito en la obra: la partida ya existe, pero todavía no suma en el presupuesto.
const AVISO_FUERA_DEL_PRESUPUESTO = "Todavía no está en el presupuesto de esta obra.";

// La pantalla «Componer una partida»: el h1 y la composición. `?codigo=X` trae el código de la partida (plan de montar, T4).
// Ficha de Componer (2026-11-23, lote 1). Eugenio: «acabo de componer una partida y me perdí». Dentro de una obra, la
// tarea no termina al guardar: termina con la partida en el presupuesto. Por eso el éxito ofrece ese paso como único
// botón principal, y lleva a Presupuesto › Partidas con «Agregar partida» abierto y la partida ya elegida.
export default function PaginaComponer(): JSX.Element {
  const [parametros] = useSearchParams();
  const obra = useContext(ContextoDeLaObra);
  const navegar = useNavigate();
  const pasoSiguiente =
    obra === null
      ? undefined
      : (partida: PartidaCompuesta): PasoSiguiente => ({
          aviso: AVISO_FUERA_DEL_PRESUPUESTO,
          boton: `Agregar ${partida.codigo} al presupuesto`,
          alPulsar: () => void navegar(rutaDeObra(obra.carpeta, obra.obraId, "presupuesto"), { state: { agregarPartida: partida } }),
        });
  return (
    <div className="silice-componer silice-pagina">
      <h1 className="cds--type-heading-04">Componer una partida</h1>
      <ComponerPartida
        codigoInicial={parametros.get("codigo") ?? ""}
        nivelDelTitulo={1}
        alGuardar={sinMas}
        pasoSiguiente={pasoSiguiente}
      />
    </div>
  );
}
