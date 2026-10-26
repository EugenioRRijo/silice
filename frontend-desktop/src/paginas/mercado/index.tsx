import { Tab, TabList, TabPanel, TabPanels, Tabs } from "@carbon/react";
import { EstudioDelLado } from "./EstudioDelLado";
import "./mercado.scss";

// «Estudio de mercado» (plan de montar un presupuesto, Tarea 15; diseno §5.1): dos pestanas, lo que la empresa compra
// (insumos) y lo que cobra (partidas). Cada una busca su insumo o partida, muestra las cifras del mercado que calcula la
// API, la propuesta con su razon y la tabla de observaciones, y deja usar un precio y anotar observaciones nuevas. La
// pagina no calcula nada: Silice propone y la persona decide.
export default function PaginaMercado() {
  return (
    <section className="silice-mercado silice-pagina" aria-labelledby="mercado-titulo">
      <h1 id="mercado-titulo" className="cds--type-heading-04">
        Estudio de mercado
      </h1>
      <p className="silice-mercado__nota cds--type-body-compact-01">
        Anote los precios que ve en el mercado y compárelos. Sílice calcula las cifras de los últimos días y propone un
        precio; usted decide cuál usar.
      </p>
      <Tabs>
        <TabList aria-label="Qué estudiar">
          <Tab>Lo que compramos</Tab>
          <Tab>Lo que cobramos</Tab>
        </TabList>
        <TabPanels>
          <TabPanel>
            <EstudioDelLado lado="compra" />
          </TabPanel>
          <TabPanel>
            <EstudioDelLado lado="cobro" />
          </TabPanel>
        </TabPanels>
      </Tabs>
    </section>
  );
}
