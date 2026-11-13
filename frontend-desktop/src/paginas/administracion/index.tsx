import { Layer } from "@carbon/react";
import type { ComponentType } from "react";
import { useParams } from "react-router";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { useAplicacion } from "../../shell/contexto";
import Accesos from "./Accesos";
import AvisosDelTema from "./AvisosDelTema";
import Asistente from "./Asistente";
import CarpetasDeTrabajo from "./CarpetasDeTrabajo";
import ClavesApi from "./ClavesApi";
import Cuentas from "./Cuentas";
import Empresa from "./Empresa";
import Especialidades from "./Especialidades";
import EmpresasRegistradas from "./EmpresasRegistradas";
import Instalacion from "./Instalacion";
import { PESTANAS, SECCIONES_DE_ADMINISTRACION } from "./logica";
import "./administracion.scss";

type IdDePestana = (typeof PESTANAS)[number]["id"];
type SeccionDeAdministracion = keyof typeof SECCIONES_DE_ADMINISTRACION;

// Los avisos de contraste del tema van encima de los datos de la empresa, no en cada pantalla.
function EmpresaConAvisos() {
  return (
    <>
      <AvisosDelTema />
      <Empresa />
    </>
  );
}

// Cada pestaña de la clásica con su componente; el tipo obliga a que ninguna quede sin el suyo.
const CONTENIDOS: Record<IdDePestana, ComponentType> = {
  cuentas: Cuentas,
  empresa: EmpresaConAvisos,
  registradas: EmpresasRegistradas,
  api: ClavesApi,
  asistente: Asistente,
  accesos: Accesos,
  instalacion: Instalacion,
};

// Lo que no es de las siete pestañas. Plan de modulos, MOD-3b (diseno de modulos §7): las carpetas se administran aqui, para
// quien las gestiona (`cambiar_caso`: crear y subir). Plan vial, Tarea 19: las especialidades de la instalacion se encienden
// y apagan aqui, para quien tiene `activar_modulos`.
interface Bloque {
  id: string;
  titulo: string;
  Contenido: ComponentType;
  // Los componentes que ya traen su propio h2 (casi todos) no llevan otro encima; los que no, se titulan aqui.
  conTitulo: boolean;
}

const ESPECIALIDADES: Bloque = { id: "especialidades", titulo: "Especialidades", Contenido: Especialidades, conTitulo: true };
const CARPETAS: Bloque = { id: "carpetas", titulo: "Carpetas", Contenido: CarpetasDeTrabajo, conTitulo: false };

// Los bloques de una seccion de la Cuenta, en el orden en que se apilan (contrato de rutas §3, diseno visual 2.4-E). Cada
// uno es una de las siete pestañas de antes; «Claves de API» no trae titulo y se lo pone esta pantalla.
function bloquesDe(seccion: SeccionDeAdministracion, acciones: readonly string[]): Bloque[] {
  if (seccion === "carpetas") return [CARPETAS];
  const deLaClasica = (id: IdDePestana): Bloque => {
    const pestana = PESTANAS.find((p) => p.id === id)!;
    return { id, titulo: pestana.titulo, Contenido: CONTENIDOS[id], conTitulo: id === "api" };
  };
  const bloques = SECCIONES_DE_ADMINISTRACION[seccion].map(deLaClasica);
  // «Especialidades» abre «sistema» solo para quien enciende y apaga especialidades.
  return seccion === "sistema" && acciones.includes("activar_modulos") ? [ESPECIALIDADES, ...bloques] : bloques;
}

function esDeAdministracion(seccion: string | undefined): seccion is SeccionDeAdministracion {
  return seccion !== undefined && Object.hasOwn(SECCIONES_DE_ADMINISTRACION, seccion);
}

// Lo que monta una seccion de administracion de la Cuenta (`/cuenta/:seccion`: cuentas, empresa, carpetas y sistema). El h1 y
// la barra de secciones los pone el marco (marco/EspacioDeCuenta); aqui solo el contenido, apilado, con la capa de nivel
// dos para que los campos de texto tomen `$field-02` y se distingan del blanco (VB-23). Cambiar de seccion desmonta lo
// anterior (y con ello cualquier contrasena escrita). El marco ya filtra el permiso (`administrar_cuentas`, y las carpetas
// ademas `cambiar_caso`); aqui se vuelve a comprobar, porque la API es quien manda pero esta pantalla tampoco ofrece lo que
// la cuenta no puede usar.
export default function PaginaAdministracion() {
  const { sesion } = useAplicacion();
  const { seccion } = useParams();
  if (!esDeAdministracion(seccion)) return null;
  const puede = sesion.acciones.includes("administrar_cuentas") && (seccion !== "carpetas" || sesion.acciones.includes("cambiar_caso"));
  return (
    <div className="silice-adm">
      {!puede ? (
        <EstadoVacio titulo="Su cuenta no tiene permiso para administrar la instalación." />
      ) : (
        <Layer className="silice-adm__capa">
          {bloquesDe(seccion, sesion.acciones).map(({ id, titulo, Contenido, conTitulo }) =>
            conTitulo ? (
              <section key={id} aria-labelledby={`adm-${id}-titulo`} className="silice-adm__bloque">
                <h2 id={`adm-${id}-titulo`} className="cds--type-heading-compact-02">
                  {titulo}
                </h2>
                <Contenido />
              </section>
            ) : (
              <Contenido key={id} />
            ),
          )}
        </Layer>
      )}
    </div>
  );
}
