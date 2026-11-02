import { GestionCarpetas } from "../../shell/carpetas/GestionCarpetas";
import { useAplicacion } from "../../shell/contexto";

// Al abrir una carpeta el armazon vuelve a montar la pagina (pide sus datos a la carpeta nueva): Administracion vuelve
// a esta pestana en vez de caer en la primera. Solo en memoria (RT-9) y solo para el montaje siguiente.
let volverAEstaPestana = false;

export function tomarVueltaACarpetas(): boolean {
  const volver = volverAEstaPestana;
  volverAEstaPestana = false;
  return volver;
}

// Administracion › Carpetas de trabajo (diseno de modulos §7 y §12.2; BCP-5): la lista de la instalacion, crear, subir
// y, para quien arma, la demostracion. Abrir una pasa por el armazon: la misma confirmacion y el mismo aviso que
// «Cambiar carpeta…» de la barra.
export default function CarpetasDeTrabajo() {
  const { sesion, abrirCarpeta } = useAplicacion();
  const editaHoja = sesion.acciones.includes("editar_hoja");

  async function abrir(nombre: string, preparar?: () => Promise<string>): Promise<boolean> {
    if (!abrirCarpeta) return false;
    volverAEstaPestana = true;
    try {
      const abierta = await (preparar ? abrirCarpeta(nombre, preparar) : abrirCarpeta(nombre));
      if (!abierta) volverAEstaPestana = false;
      return abierta;
    } catch (e) {
      volverAEstaPestana = false;
      throw e;
    }
  }

  return (
    <div className="silice-adm__secciones">
      <GestionCarpetas alAbrir={abrir} conDemostracion={editaHoja} puedeDeclararMoneda={editaHoja} nivelDeTitulo={2} />
    </div>
  );
}
