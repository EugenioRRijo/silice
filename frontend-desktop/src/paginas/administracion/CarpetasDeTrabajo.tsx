import { GestionCarpetas } from "../../shell/carpetas/GestionCarpetas";
import { useAplicacion } from "../../shell/contexto";

// Cuenta › Carpetas (diseno de modulos §7 y §12.2; BCP-5; F6, T6): la lista de la instalacion, crear, subir y, para quien
// arma, la demostracion. La seccion es de quien gestiona carpetas (`cambiar_caso`: crear y subir). Abrir una exige ademas
// `abrir_carpeta` (arma y administra tienen las dos; quien revisa solo esa, y abre desde la barra y el buscador). Abrir una pasa
// por el armazon: la misma confirmacion y el mismo aviso que «Cambiar carpeta…» de la barra. Al abrir una carpeta el armazon
// vuelve a montar la pantalla, que sigue en /cuenta/carpetas: ya no hay pestaña que recordar.
export default function CarpetasDeTrabajo() {
  const { sesion, abrirCarpeta } = useAplicacion();
  const editaHoja = sesion.acciones.includes("editar_hoja");

  async function abrir(nombre: string, preparar?: () => Promise<string>): Promise<boolean> {
    if (!abrirCarpeta) return false;
    return preparar ? abrirCarpeta(nombre, preparar) : abrirCarpeta(nombre);
  }

  return (
    <div className="silice-adm__secciones">
      <GestionCarpetas alAbrir={abrir} conDemostracion={editaHoja} puedeDeclararMoneda={editaHoja} nivelDeTitulo={2} />
    </div>
  );
}
