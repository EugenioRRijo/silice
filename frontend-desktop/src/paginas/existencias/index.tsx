import { Tab, TabList, TabPanel, TabPanels, Tabs } from "@carbon/react";
import { useCallback, useMemo, useState } from "react";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { useAplicacion } from "../../shell/contexto";
import { SIN_PERMISO } from "./fallos";
import type { Reacciones } from "./fallos";
import { fechaIsoDe, hoyISO } from "./formato";
import { PestanaBandeja } from "./PestanaBandeja";
import { PestanaExistencias } from "./PestanaExistencias";
import { PestanaImportar } from "./PestanaImportar";
import { PestanaRegistrar } from "./PestanaRegistrar";
import type { ExistenciaRespuesta, MaterialRespuesta } from "./tipos";
import { useRecurso } from "./useRecurso";

const RUTA_EXISTENCIAS = "/v1/produccion/existencias";
const RUTA_MATERIALES = "/v1/produccion/materiales";

const EXISTENCIAS = 0;
const REGISTRAR = 1;
const IMPORTAR = 2;
const BANDEJA = 3;

// «Existencias de la arenera» (UC-28 y UC-29, sesion 4 de la ruta): cuanto hay y cuanto queda de cada material, el
// registro de entradas, despachos y conteos, la importacion del reporte de la bascula y la bandeja de pesajes
// sospechosos. La interfaz no calcula ninguna existencia: muestra lo que manda la API, y la API vuelve a exigir el
// permiso en cada ruta (la navegacion solo decide que se ve).
export default function PaginaExistencias() {
  const { alExpirar } = useAplicacion();
  const [pestana, setPestana] = useState(EXISTENCIAS);
  const [denegado, setDenegado] = useState(false);
  const [fecha, setFecha] = useState(() => hoyISO());
  const [versionExistencias, setVersionExistencias] = useState(0);
  const [versionMateriales, setVersionMateriales] = useState(0);

  const alDenegar = useCallback(() => setDenegado(true), []);
  const reacciones = useMemo<Reacciones>(() => ({ alExpirar, alDenegar }), [alExpirar, alDenegar]);

  const fechaConsulta = fechaIsoDe(fecha) || hoyISO();
  const existencias = useRecurso<ExistenciaRespuesta[]>(
    `${RUTA_EXISTENCIAS}?a_fecha=${fechaConsulta}`,
    versionExistencias,
    alExpirar,
    alDenegar,
  );
  const materiales = useRecurso<MaterialRespuesta[]>(RUTA_MATERIALES, versionMateriales, alExpirar, alDenegar);

  const recargarExistencias = useCallback(() => setVersionExistencias((n) => n + 1), []);
  const alCrearMaterial = useCallback(() => {
    setVersionMateriales((n) => n + 1);
    setVersionExistencias((n) => n + 1);
  }, []);

  if (denegado) {
    return (
      <div className="existencias">
        <h1 className="cds--type-heading-04">Existencias de la arenera</h1>
        <EstadoVacio
          titulo={SIN_PERMISO}
          descripcion="Pida a quien administra las cuentas que le dé el permiso de operar la arenera."
        />
      </div>
    );
  }

  return (
    <div className="existencias">
      <h1 className="cds--type-heading-04">Existencias de la arenera</h1>
      <Tabs selectedIndex={pestana} onChange={({ selectedIndex }) => setPestana(selectedIndex)}>
        <TabList aria-label="Secciones de la arenera">
          <Tab>Existencias</Tab>
          <Tab>Registrar</Tab>
          <Tab>Importar báscula</Tab>
          <Tab>Pesajes sospechosos</Tab>
        </TabList>
        <TabPanels>
          <TabPanel>
            {pestana === EXISTENCIAS && (
              <PestanaExistencias
                existencias={existencias}
                fecha={fecha}
                alCambiarFecha={setFecha}
                alReintentar={recargarExistencias}
                alCrearMaterial={() => setPestana(REGISTRAR)}
              />
            )}
          </TabPanel>
          <TabPanel>
            {pestana === REGISTRAR && (
              <PestanaRegistrar
                materiales={materiales}
                alRegistrar={recargarExistencias}
                alCrearMaterial={alCrearMaterial}
                reacciones={reacciones}
              />
            )}
          </TabPanel>
          <TabPanel>
            {pestana === IMPORTAR && (
              <PestanaImportar
                alImportar={recargarExistencias}
                alVerSospechosos={() => setPestana(BANDEJA)}
                reacciones={reacciones}
              />
            )}
          </TabPanel>
          <TabPanel>
            {pestana === BANDEJA && (
              <PestanaBandeja materiales={materiales} alResolver={recargarExistencias} reacciones={reacciones} />
            )}
          </TabPanel>
        </TabPanels>
      </Tabs>
    </div>
  );
}
