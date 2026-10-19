import { Tab, TabList, TabPanel, TabPanels, Tabs } from "@carbon/react";
import { useAplicacion } from "../../shell/contexto";
import { PestanaExcelExterno } from "./ExcelExterno";
import { PestanaPaquete } from "./Paquete";
import "./revisar.scss";

// «Revisar un paquete» (UC-23; RF-86, RF-87): las dos pestañas de ui/paginas/revisar.py. Quien revisa sube el
// .silice que recibió y ve lo que dice la API: verificacion (firma, integridad y cadena), reauditoria en memoria,
// diferencias, quien cambio que, los Excel regenerados aqui y el dictamen.
export default function PaginaRevisar() {
  const { alExpirar } = useAplicacion();
  return (
    <div className="silice-revisar silice-pagina">
      <h1 className="cds--type-heading-04">Revisar un paquete</h1>
      <Tabs>
        <TabList aria-label="Qué revisar" contained>
          <Tab>Paquete .silice</Tab>
          <Tab>Presupuesto en Excel</Tab>
        </TabList>
        <TabPanels>
          <TabPanel>
            <PestanaPaquete alExpirar={alExpirar} />
          </TabPanel>
          <TabPanel>
            <PestanaExcelExterno alExpirar={alExpirar} />
          </TabPanel>
        </TabPanels>
      </Tabs>
    </div>
  );
}
