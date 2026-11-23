import type { JSX } from "react";
import { useContext, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { pedir } from "../../api/cliente";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import { rutaDeObra } from "../../marco/secciones";
import { ContextoDeLaHoja } from "../hoja/ProveedorDeLaHoja";
import { ComponerPartida } from "./ComponerPartida";
import type { PartidaCompuesta } from "./ComponerPartida";
import type { PasoSiguiente } from "./Guardar";

// Lo que se sabe, tras guardar, de la partida en el presupuesto del borrador abierto: se está consultando, ya está, no
// está, o no se pudo saber (sin Hoja abierta o la consulta falló).
type EnElPresupuesto = "consultando" | "esta" | "no-esta" | "desconocido";

// La pantalla «Componer una partida»: el h1 y la composición. `?codigo=X` trae el código de la partida (plan de montar, T4).
//
// Ficha de Componer (2026-11-23, lote 1). Eugenio: «acabo de componer una partida y me perdí». Dentro de una obra, la
// tarea no termina al guardar: termina con la partida en el presupuesto. El éxito ofrece ese paso como único botón
// principal, y lleva a Presupuesto › Partidas con «Agregar partida» abierto y la partida ya elegida.
//
// Juez F2 (2026-11-23): el éxito no afirma lo que no sabe. Mira el presupuesto del borrador (la Hoja que comparte con
// Presupuesto) y si la versión se puede editar, y según eso el paso siguiente es agregarla, verla o ir a Versiones.
export default function PaginaComponer(): JSX.Element {
  const [parametros] = useSearchParams();
  const obra = useContext(ContextoDeLaObra);
  const hoja = useContext(ContextoDeLaHoja);
  const navegar = useNavigate();
  const [enElPresupuesto, setEnElPresupuesto] = useState<EnElPresupuesto>("desconocido");
  const borrador = hoja !== null && hoja.estado.estado === "listo" ? hoja.estado.borrador.id : null;

  // Fuera de una obra, guardar termina aquí (la partida queda en el catálogo). En la obra, se consulta el presupuesto.
  const alGuardar = (partida: PartidaCompuesta) => {
    if (obra === null || borrador === null) {
      setEnElPresupuesto("desconocido");
      return;
    }
    setEnElPresupuesto("consultando");
    pedir<{ filas: { partida: string }[] }>(`/v1/hoja/borradores/${borrador}/vistas/presupuesto`)
      .then((vista) => setEnElPresupuesto(vista.filas.some((f) => f.partida === partida.codigo) ? "esta" : "no-esta"))
      .catch(() => setEnElPresupuesto("desconocido"));
  };

  const pasoSiguiente =
    obra === null
      ? undefined
      : (partida: PartidaCompuesta): PasoSiguiente | null => {
          const presupuesto = rutaDeObra(obra.carpeta, obra.obraId, "presupuesto");
          if (hoja !== null && !hoja.puedeEditar) {
            return {
              aviso: "Esta versión del presupuesto no se puede editar: abra o cree una versión editable para agregarla.",
              boton: "Ir a Versiones",
              alPulsar: () => void navegar(rutaDeObra(obra.carpeta, obra.obraId, "versiones")),
            };
          }
          if (enElPresupuesto === "consultando") return null;
          if (enElPresupuesto === "esta") {
            return { aviso: "Ya está en el presupuesto de esta obra.", boton: "Ver el presupuesto", alPulsar: () => void navegar(presupuesto) };
          }
          return {
            aviso:
              enElPresupuesto === "no-esta"
                ? "Todavía no está en el presupuesto de esta obra."
                : "Si todavía no está en el presupuesto de esta obra, agréguela con su cantidad.",
            boton: `Agregar ${partida.codigo} al presupuesto`,
            alPulsar: () => void navegar(presupuesto, { state: { agregarPartida: partida } }),
          };
        };

  return (
    <div className="silice-componer silice-pagina">
      <h1 className="cds--type-heading-04">Componer una partida</h1>
      <ComponerPartida
        codigoInicial={parametros.get("codigo") ?? ""}
        nivelDelTitulo={1}
        alGuardar={alGuardar}
        pasoSiguiente={pasoSiguiente}
      />
    </div>
  );
}
