import type { JSX } from "react";
import { useSearchParams } from "react-router";
import { ComponerPartida } from "./ComponerPartida";

// La partida guardada se dice en la propia composicion; la pantalla sola no lleva a ninguna parte (baja 21).
const sinMas = () => undefined;

// La pantalla «Componer una partida» (Ctrl+K, hasta que F5 la aloje en Precios y catalogo): el h1 y la composicion.
// `?codigo=X` trae el codigo de la partida (plan de montar, T4).
export default function PaginaComponer(): JSX.Element {
  const [parametros] = useSearchParams();
  return (
    <div className="silice-componer silice-pagina">
      <h1 className="cds--type-heading-04">Componer una partida</h1>
      <ComponerPartida codigoInicial={parametros.get("codigo") ?? ""} nivelDelTitulo={1} alGuardar={sinMas} />
    </div>
  );
}
