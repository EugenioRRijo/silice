import { useAplicacion } from "../../shell/contexto";
import { Visor } from "../../visor/Visor";

// «Libro de la empresa» (UC-25, RM-6): el visor de la sesion 2. Lo extiende la sesion 3, no la migracion.
// Sus controles (fecha de devolucion, Cambiar libro) van en el cuerpo de la pagina, no en la ranura de la cabecera (V-24).
export default function PaginaLibros() {
  const { alExpirar, almacenDelLibro, crearHojaVisor } = useAplicacion();
  return (
    <div className="silice-pagina-libro">
      <h1 className="cds--type-heading-04">Libro de la empresa</h1>
      <p className="cds--type-body-compact-01">
        Compare el Excel original con el recálculo de Sílice y revise cada celda marcada
      </p>
      <Visor
        alExpirar={alExpirar}
        almacen={almacenDelLibro}
        crearHoja={crearHojaVisor}
      />
    </div>
  );
}
