import { Tab, TabPanel, TabPanels, Tabs } from "@carbon/react";
import { TabList } from "../../comun/carbonEs";
import { useCallback, useState } from "react";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { EstadoVacio } from "../../comun/EstadoVacio";
import { useAplicacion } from "../../shell/contexto";
import { PestanaLineaBase } from "./PestanaLineaBase";
import { PestanaProcura } from "./PestanaProcura";
import { PestanaValuaciones } from "./PestanaValuaciones";
import { AlertasYReproyeccion, BarraDeCorte, Recuperacion, ValorGanado } from "./PestanasDeResultados";
import { FILTROS_INICIALES, PESTANAS, consultaDeCalculo, errorDeCarga, useCargaSuave } from "./logica";
import type { Calculo, Filtros, Pestana } from "./logica";
import "./control.scss";

// Las tres pestañas de resultados comparten un solo calculo al corte (UC-20 1 a 3: se calcula siempre). Se eligen por
// su nombre, no por su lugar: «Procura» (Tarea 24) entro entre Valuaciones y los resultados.
function Resultados({
  proyecto,
  pestana,
  clave,
  alCambiar,
}: {
  proyecto: string;
  pestana: Pestana;
  clave: number;
  alCambiar: () => void;
}) {
  const { alExpirar, sesion } = useAplicacion();
  const [filtros, setFiltros] = useState<Filtros>(FILTROS_INICIALES);
  const ruta = `${consultaDeCalculo(proyecto, filtros)}&n=${clave}`;
  const carga = useCargaSuave<Calculo>(ruta, alExpirar);
  const [versiones, setVersiones] = useState<string[]>([]);
  const [ultima, setUltima] = useState<Calculo | null>(null);
  if (carga.estado === "listo" && carga.datos !== ultima) {
    setUltima(carga.datos);
    setVersiones(carga.datos.versiones_revaloradas);
  }

  const barra = <BarraDeCorte filtros={filtros} versiones={versiones} alAplicar={setFiltros} />;
  if (carga.estado === "cargando") return <EsqueletoPagina etiqueta="Calculando el control" />;
  if (carga.estado === "error") return <>{barra}<AvisoError error={carga.error} titulo="No se pudo calcular el control" /></>;
  if (carga.estado !== "listo") return <AvisoError error={errorDeCarga(carga)} titulo="No se pudo calcular el control" />;
  const calculo = carga.datos;
  if (calculo.estado === "sin_linea_base") {
    return <EstadoVacio titulo="Declare primero la línea base de control" descripcion="Se hace en la pestaña «Línea base»." />;
  }
  if (calculo.estado === "sin_valuaciones") {
    return <EstadoVacio titulo="Registre la primera valuación para ver el control" descripcion="Se hace en la pestaña «Valuaciones»." />;
  }
  return (
    <>
      {barra}
      {pestana === "Valor ganado" && <ValorGanado calculo={calculo} />}
      {pestana === "Alertas y reproyección" && <AlertasYReproyeccion calculo={calculo} />}
      {pestana === "Recuperación" && (
        <Recuperacion
          proyecto={proyecto}
          filtros={filtros}
          calculo={calculo}
          puedeDecidir={sesion.acciones.includes("decidir_recuperacion")}
          alDecidir={alCambiar}
        />
      )}
    </>
  );
}

// Control de obra (UC-19, UC-20, MP-7): seis pestañas sobre la linea base del proyecto elegido en la cabecera.
// Exige `control_de_obra`; elegir una opcion de recuperacion exige ademas `decidir_recuperacion`.
export default function PaginaControl() {
  const { proyecto } = useAplicacion();
  const [pestana, setPestana] = useState(0);
  const [clave, setClave] = useState(0);
  const cambiar = useCallback(() => setClave((n) => n + 1), []);

  return (
    <div className="silice-control silice-pagina">
      <h1 className="cds--type-heading-04">Control de obra</h1>
      {proyecto === null ? (
        <EstadoVacio titulo="Elija un proyecto" descripcion="Abra un proyecto en la cabecera para controlar su obra." />
      ) : (
        <Tabs key={proyecto} selectedIndex={pestana} onChange={({ selectedIndex }) => setPestana(selectedIndex)}>
          <TabList aria-label="Secciones del control de obra" contained>
            {PESTANAS.map((p) => (
              <Tab key={p}>{p}</Tab>
            ))}
          </TabList>
          <TabPanels>
            {PESTANAS.map((p, i) => (
              <TabPanel key={p}>
                {i !== pestana ? null : p === "Línea base" ? (
                  <PestanaLineaBase proyecto={proyecto} clave={clave} alCambiar={cambiar} />
                ) : p === "Valuaciones" ? (
                  <PestanaValuaciones proyecto={proyecto} clave={clave} alCambiar={cambiar} />
                ) : p === "Procura" ? (
                  <PestanaProcura proyecto={proyecto} clave={clave} alCambiar={cambiar} />
                ) : (
                  <Resultados proyecto={proyecto} pestana={p} clave={clave} alCambiar={cambiar} />
                )}
              </TabPanel>
            ))}
          </TabPanels>
        </Tabs>
      )}
    </div>
  );
}
