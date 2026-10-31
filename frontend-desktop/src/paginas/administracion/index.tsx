import { Layer, Tab, TabList, TabPanel, TabPanels, Tabs } from "@carbon/react";
import { useState } from "react";
import type { ComponentType } from "react";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { useAplicacion } from "../../shell/contexto";
import Accesos from "./Accesos";
import AvisosDelTema from "./AvisosDelTema";
import Asistente from "./Asistente";
import CarpetasDeTrabajo, { tomarVueltaACarpetas } from "./CarpetasDeTrabajo";
import ClavesApi from "./ClavesApi";
import Cuentas from "./Cuentas";
import Empresa from "./Empresa";
import Especialidades from "./Especialidades";
import EmpresasRegistradas from "./EmpresasRegistradas";
import Instalacion from "./Instalacion";
import { PESTANAS } from "./logica";
import "./administracion.scss";

type IdDePestana = (typeof PESTANAS)[number]["id"];

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

// Plan de modulos, MOD-3b (diseno de modulos §7): «Carpetas de trabajo» se administra aqui, al final, para quien puede
// cambiar de carpeta (`cambiar_caso`). No es de la clasica: no esta en PESTANAS.
// Plan vial, Tarea 19: las especialidades de la instalacion se encienden y apagan aqui, para quien tiene `activar_modulos`.
const ESPECIALIDADES = { id: "especialidades", titulo: "Especialidades", Contenido: Especialidades };
const CARPETAS = { id: "carpetas", titulo: "Carpetas de trabajo", Contenido: CarpetasDeTrabajo };

// «Administracion» (UC-21): las siete pestañas de la clásica, todas migradas (la última, el Asistente de IA, en T6
// de la migración final; su panel de chat es otra pantalla), y las carpetas de trabajo.
// Solo se dibuja el contenido de la pestana elegida: al cambiar de pestana lo anterior se desmonta (y con el,
// cualquier contrasena escrita).
export default function PaginaAdministracion() {
  const { sesion } = useAplicacion();
  const puede = sesion.acciones.includes("administrar_cuentas");
  const pestanas = [
    ...PESTANAS.map((p) => ({ id: p.id, titulo: p.titulo, Contenido: CONTENIDOS[p.id] })),
    ...(sesion.acciones.includes("activar_modulos") ? [ESPECIALIDADES] : []),
    ...(sesion.acciones.includes("cambiar_caso") ? [CARPETAS] : []),
  ];
  // Tras abrir una carpeta desde su pestana la pagina se vuelve a montar: se vuelve a ella.
  const [activa, setActiva] = useState(() => {
    const vuelta = tomarVueltaACarpetas();
    const indice = pestanas.findIndex((p) => p.id === CARPETAS.id);
    return vuelta && indice >= 0 ? indice : 0;
  });
  return (
    <div className="silice-adm silice-pagina">
      <h1 className="cds--type-heading-04">Administración</h1>
      {!puede ? (
        <EstadoVacio titulo="Su cuenta no tiene permiso para administrar la instalación." />
      ) : (
        <Tabs selectedIndex={activa} onChange={({ selectedIndex }) => setActiva(selectedIndex)}>
          <TabList aria-label="Secciones de Administración" contained>
            {pestanas.map((p) => (
              <Tab key={p.id}>{p.titulo}</Tab>
            ))}
          </TabList>
          <TabPanels>
            {pestanas.map(({ id, Contenido }, i) => {
              // Un nivel de capa mas: los campos de texto toman `$field-02` y se distinguen del blanco de la pestana (VB-23).
              return (
                <TabPanel key={id}>
                  {i === activa && (
                    <Layer>
                      <Contenido />
                    </Layer>
                  )}
                </TabPanel>
              );
            })}
          </TabPanels>
        </Tabs>
      )}
    </div>
  );
}
