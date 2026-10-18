import { useAplicacion } from "../../shell/contexto";
import { Visor } from "../../visor/Visor";

// «Libro de la empresa» (UC-25, RM-6): el visor de la sesion 2. Lo extiende la sesion 3, no la migracion.
export default function PaginaLibros() {
  const { alExpirar } = useAplicacion();
  return <Visor alExpirar={alExpirar} />;
}
