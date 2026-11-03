import { Tab, TabPanel, TabPanels, Tabs } from "@carbon/react";
import { TabList } from "../../comun/carbonEs";
import { useState } from "react";
import type { ReactNode } from "react";
import { useAplicacion } from "../../shell/contexto";
import {
  CotizacionesDeLaObra,
  PantallaConDialogos,
} from "./CotizacionesDeLaObra";
import { EstudioDelLado } from "./EstudioDelLado";
import { HistoricoDePrecios } from "./HistoricoDePrecios";
import "./mercado.scss";

interface Pestana {
  titulo: string;
  // Las que anotan observaciones y usan precios: solo con `editar_hoja` (la API exige lo mismo para su estudio).
  escribe: boolean;
  // Si el panel solo se monta al elegir la pestaña.
  alElegir: boolean;
  contenido: ReactNode;
}

const PESTANAS: readonly Pestana[] = [
  { titulo: "Lo que compramos", escribe: true, alElegir: false, contenido: <EstudioDelLado lado="compra" /> },
  { titulo: "Lo que cobramos", escribe: true, alElegir: false, contenido: <EstudioDelLado lado="cobro" /> },
  { titulo: "Histórico de precios", escribe: false, alElegir: true, contenido: <HistoricoDePrecios /> },
  { titulo: "Cotizaciones de la obra", escribe: false, alElegir: true, contenido: <CotizacionesDeLaObra /> },
];

// «Estudio de mercado» (plan de montar un presupuesto, Tarea 15; diseno §5.1): dos pestanas, lo que la empresa compra
// (insumos) y lo que cobra (partidas). Cada una busca su insumo o partida, muestra las cifras del mercado que calcula la
// API, la propuesta con su razon y la tabla de observaciones, y deja usar un precio y anotar observaciones nuevas. La
// pagina no calcula nada: Silice propone y la persona decide. Desde la Tarea 13 del plan F4 gana el «Histórico de precios»
// y las «Cotizaciones de la obra» (antes pantalla propia y pestaña Precios de la Hoja). Esas dos se montan al elegirlas: no
// piden nada al servidor ni quitan nombres accesibles a las dos primeras mientras nadie las abre.
// Ronda 2 de la Tarea 13: quien solo revisa (`leer_proyecto` sin `editar_hoja`) entra a leer; las dos primeras pestañas
// anotan y usan precios y no se le pintan (regla de la Tarea 2b: no se deshabilita, no se pinta). Las cotizaciones se le
// muestran sin «Registrar» ni «Retirar» (`CotizacionesDeLaObra`).
export default function PaginaMercado() {
  const { sesion } = useAplicacion();
  const edita = sesion.acciones.includes("editar_hoja");
  const pestanas = PESTANAS.filter((p) => edita || !p.escribe);
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
          {edita
            ? "Anote los precios que ve en el mercado y compárelos. Sílice calcula las cifras de los últimos días y propone un precio; usted decide cuál usar."
            : "Vea cómo cambiaron los precios de los insumos y las cotizaciones de la obra."}
        </p>
        <Tabs onChange={({ selectedIndex }) => setElegida(selectedIndex)}>
          <TabList aria-label="Qué estudiar">
            {pestanas.map((p) => (
              <Tab key={p.titulo}>{p.titulo}</Tab>
            ))}
          </TabList>
          <TabPanels>
            {pestanas.map((p, i) => (
              <TabPanel key={p.titulo}>{(!p.alElegir || elegida === i) && p.contenido}</TabPanel>
            ))}
          </TabPanels>
        </Tabs>
      </section>
    </PantallaConDialogos>
  );
}
