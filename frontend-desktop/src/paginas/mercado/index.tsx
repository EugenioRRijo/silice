import { Tab, TabPanel, TabPanels, Tabs } from "@carbon/react";
import { TabList } from "../../comun/carbonEs";
import { useState } from "react";
import {
  CotizacionesDeLaObra,
  PantallaConDialogos,
} from "./CotizacionesDeLaObra";
import { EstudioDelLado } from "./EstudioDelLado";
import { HistoricoDePrecios } from "./HistoricoDePrecios";
import "./mercado.scss";

// «Estudio de mercado» (plan de montar un presupuesto, Tarea 15; diseno §5.1): dos pestanas, lo que la empresa compra
// (insumos) y lo que cobra (partidas). Cada una busca su insumo o partida, muestra las cifras del mercado que calcula la
// API, la propuesta con su razon y la tabla de observaciones, y deja usar un precio y anotar observaciones nuevas. La
// pagina no calcula nada: Silice propone y la persona decide. Desde la Tarea 13 del plan F4 gana el «Histórico de precios»
// y las «Cotizaciones de la obra» (antes pantalla propia y pestaña Precios de la Hoja). Esas dos se montan al elegirlas: no
// piden nada al servidor ni quitan nombres accesibles a las dos primeras mientras nadie las abre.
export default function PaginaMercado() {
  const [elegida, setElegida] = useState(0);
  return (
    <PantallaConDialogos>
      <section
        className="silice-mercado silice-pagina"
        aria-labelledby="mercado-titulo"
      >
        <h1 id="mercado-titulo" className="cds--type-heading-04">
          Estudio de mercado
        </h1>
        <p className="silice-mercado__nota cds--type-body-compact-01">
          Anote los precios que ve en el mercado y compárelos. Sílice calcula
          las cifras de los últimos días y propone un precio; usted decide cuál
          usar.
        </p>
        <Tabs onChange={({ selectedIndex }) => setElegida(selectedIndex)}>
          <TabList aria-label="Qué estudiar">
            <Tab>Lo que compramos</Tab>
            <Tab>Lo que cobramos</Tab>
            <Tab>Histórico de precios</Tab>
            <Tab>Cotizaciones de la obra</Tab>
          </TabList>
          <TabPanels>
            <TabPanel>
              <EstudioDelLado lado="compra" />
            </TabPanel>
            <TabPanel>
              <EstudioDelLado lado="cobro" />
            </TabPanel>
            <TabPanel>{elegida === 2 && <HistoricoDePrecios />}</TabPanel>
            <TabPanel>{elegida === 3 && <CotizacionesDeLaObra />}</TabPanel>
          </TabPanels>
        </Tabs>
      </section>
    </PantallaConDialogos>
  );
}
