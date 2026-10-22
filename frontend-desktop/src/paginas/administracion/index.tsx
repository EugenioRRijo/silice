import { Layer, Tab, TabList, TabPanel, TabPanels, Tabs } from "@carbon/react";
import { useState } from "react";
import type { ComponentType } from "react";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { useAplicacion } from "../../shell/contexto";
import Accesos from "./Accesos";
import Asistente from "./Asistente";
import ClavesApi from "./ClavesApi";
import Cuentas from "./Cuentas";
import Empresa from "./Empresa";
import EmpresasRegistradas from "./EmpresasRegistradas";
import Instalacion from "./Instalacion";
import { PESTANAS } from "./logica";
import "./administracion.scss";

type IdDePestana = (typeof PESTANAS)[number]["id"];

// Cada pestaña de la clásica con su componente; el tipo obliga a que ninguna quede sin el suyo.
const CONTENIDOS: Record<IdDePestana, ComponentType> = {
  cuentas: Cuentas,
  empresa: Empresa,
  registradas: EmpresasRegistradas,
  api: ClavesApi,
  asistente: Asistente,
  accesos: Accesos,
  instalacion: Instalacion,
};

// «Administracion» (UC-21): las siete pestañas de la clásica, todas migradas (la última, el Asistente de IA, en T6
// de la migración final; su panel de chat es otra pantalla).
// Solo se dibuja el contenido de la pestana elegida: al cambiar de pestana lo anterior se desmonta (y con el,
// cualquier contrasena escrita).
export default function PaginaAdministracion() {
  const { sesion } = useAplicacion();
  const [activa, setActiva] = useState(0);
  const puede = sesion.acciones.includes("administrar_cuentas");
  return (
    <div className="silice-adm silice-pagina">
      <h1 className="cds--type-heading-04">Administración</h1>
      {!puede ? (
        <EstadoVacio titulo="Su cuenta no tiene permiso para administrar la instalación." />
      ) : (
        <Tabs selectedIndex={activa} onChange={({ selectedIndex }) => setActiva(selectedIndex)}>
          <TabList aria-label="Secciones de Administración" contained>
            {PESTANAS.map((p) => (
              <Tab key={p.id}>{p.titulo}</Tab>
            ))}
          </TabList>
          <TabPanels>
            {PESTANAS.map((p, i) => {
              const Contenido = CONTENIDOS[p.id];
              // Un nivel de capa mas: los campos de texto toman `$field-02` y se distinguen del blanco de la pestana (VB-23).
              return (
                <TabPanel key={p.id}>
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
