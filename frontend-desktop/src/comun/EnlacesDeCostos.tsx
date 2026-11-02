import type { JSX } from "react";
import { Link } from "react-router";

// Los dos enlaces de costos que cuelgan de Existencias y de Inicio de producción. Solo se pintan si la persona puede
// registrar costos; «Receta de la planta» lleva su propia condición en cada pantalla.
export function EnlacesDeCostos(): JSX.Element {
  return (
    <p className="cds--type-body-compact-01">
      <Link className="cds--link" to="/costos">
        Costos del período
      </Link>{" "}
      ·{" "}
      <Link className="cds--link" to="/costo_tonelada">
        Costo por tonelada
      </Link>
    </p>
  );
}
