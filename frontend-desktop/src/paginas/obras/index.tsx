import { AccesosDelModulo } from "../../shell/AccesosDelModulo";

// Inicio de «Presupuestos y obras». Por ahora, el mapa del modulo: sus pantallas por area. La mesa de control (cifras,
// obras y pendientes) se le agrega cuando la API las sirva; mientras no existan no se muestran (nada de cifras inventadas).
export default function PaginaObras() {
  return (
    <div className="silice-inicio silice-pagina">
      <h1 className="cds--type-heading-04">Inicio de presupuestos y obras</h1>
      <AccesosDelModulo modulo="obras" />
    </div>
  );
}
