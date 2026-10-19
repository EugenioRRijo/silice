import { Tab, TabList, TabPanel, TabPanels, Tabs } from "@carbon/react";
import { useState } from "react";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { useAplicacion } from "../../shell/contexto";
import { enlaceClasico, paginaPorId } from "../../shell/rutas";
import Accesos from "./Accesos";
import ClavesApi from "./ClavesApi";
import Cuentas from "./Cuentas";
import Empresa from "./Empresa";
import Instalacion from "./Instalacion";
import { PESTANAS } from "./logica";
import "./administracion.scss";

function EnLaClasica({ titulo }: { titulo: string }) {
  const { sesion } = useAplicacion();
  const pagina = paginaPorId("administracion");
  const enlace = pagina ? enlaceClasico(sesion.url_clasica, pagina) : null;
  return (
    <EstadoVacio
      titulo="En la interfaz clásica"
      descripcion={`«${titulo}» todavía se administra en la interfaz clásica de Sílice.`}
    >
      {enlace ? (
        <a href={enlace} target="_blank" rel="noopener noreferrer" className="cds--type-body-compact-01">
          Abrir «{titulo}» en la interfaz clásica (se abre en otra pestaña)
        </a>
      ) : (
        <p className="silice-adm__nota cds--type-body-compact-01">
          No se conoce la dirección de la interfaz clásica desde aquí: ábrala como lo hace siempre y entre en
          Administración, pestaña «{titulo}».
        </p>
      )}
    </EstadoVacio>
  );
}

function Contenido({ id, titulo }: { id: string; titulo: string }) {
  if (id === "cuentas") return <Cuentas />;
  if (id === "accesos") return <Accesos />;
  if (id === "empresa") return <Empresa />;
  if (id === "api") return <ClavesApi />;
  if (id === "instalacion") return <Instalacion />;
  return <EnLaClasica titulo={titulo} />;
}

// «Administracion» (UC-21): se migran Cuentas, Empresa y firma, Claves de API, Accesos e Instalacion; las demas siguen en la interfaz clasica.
// Solo se dibuja el contenido de la pestana elegida: al cambiar de pestana lo anterior se desmonta (y con el,
// cualquier contrasena escrita).
export default function PaginaAdministracion() {
  const { sesion } = useAplicacion();
  const [activa, setActiva] = useState(0);
  const puede = sesion.acciones.includes("administrar_cuentas");
  return (
    <div className="silice-adm">
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
            {PESTANAS.map((p, i) => (
              <TabPanel key={p.id}>{i === activa && <Contenido id={p.id} titulo={p.titulo} />}</TabPanel>
            ))}
          </TabPanels>
        </Tabs>
      )}
    </div>
  );
}
