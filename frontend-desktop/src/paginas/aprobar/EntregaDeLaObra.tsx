import { useId } from "react";
import { Link } from "react-router";
import { useAplicacion } from "../../shell/contexto";
import { paginaPorId, rutaDe, usable } from "../../shell/rutas";

// Tanda 2 del pulido F5, Tarea 6: el pendiente «Entregar» (una versión aprobada y sin entregar) llega a Aprobaciones de su
// obra, porque la ruta de la obra es la que cambia de carpeta y fija la obra; la pantalla «Entregar paquete» no es sección
// de la obra y antes solo se abría con Ctrl+K. Este bloque lleva a ella, con la obra ya elegida, a la cuenta que puede usarla
// (`entregar_paquete`, la misma regla del árbol y del buscador); a las demás no se les pinta.
export function EntregaDeLaObra() {
  const { sesion, modulosApagados } = useAplicacion();
  const titulo = useId();
  const pagina = paginaPorId("entregar");
  if (pagina === undefined || !usable(pagina, sesion.acciones, sesion.modo_entrega, modulosApagados)) return null;
  return (
    <section className="silice-aprobar__entrega" aria-labelledby={titulo}>
      <h2 id={titulo} className="cds--type-heading-compact-02">
        Entregar al cliente
      </h2>
      <p className="cds--type-body-compact-01">Una versión aprobada se entrega al cliente en un paquete .silice.</p>
      <Link className="cds--link" to={rutaDe(pagina)}>
        Entregar paquete
      </Link>
    </section>
  );
}
