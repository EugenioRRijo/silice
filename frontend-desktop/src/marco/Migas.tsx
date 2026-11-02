import { Fragment } from "react";
import { Link } from "react-router";

export interface Miga {
  texto: string;
  // Sin ruta: no es un enlace (la última, la pantalla donde se está).
  ruta?: string;
}

// El camino hasta la pantalla actual. La última miga es la página actual (aria-current); las anteriores, enlaces del
// enrutador. El «/» entre ellas es decorativo.
export function Migas({ migas }: { migas: Miga[] }) {
  const ultima = migas.length - 1;
  return (
    <nav aria-label="Ruta" className="silice-marco-barra__migas">
      <ol>
        {migas.map((miga, i) => (
          <Fragment key={`${i}-${miga.texto}`}>
            {i > 0 && (
              <li aria-hidden="true" className="silice-marco-barra__separador">
                /
              </li>
            )}
            <li>
              {i === ultima || miga.ruta === undefined ? (
                <span aria-current={i === ultima ? "page" : undefined} className="silice-marco-barra__miga-actual">
                  {miga.texto}
                </span>
              ) : (
                <Link to={miga.ruta}>{miga.texto}</Link>
              )}
            </li>
          </Fragment>
        ))}
      </ol>
    </nav>
  );
}
