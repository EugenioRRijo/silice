import { DonutChart, LineChart, SimpleBarChart } from "@carbon/charts-react";
import "@carbon/charts-react/styles.css";

// Adaptador unico sobre Carbon Charts. Se carga perezosamente (`React.lazy`) para que el peso de la libreria solo se
// baje al abrir una pagina con graficos, y las pruebas lo reemplazan con `vi.mock` (jsdom no dibuja SVG de verdad).
export type TipoGrafico = "linea" | "anillo" | "barras";

interface Props {
  tipo: TipoGrafico;
  datos: object[];
  opciones: object;
}

/* eslint-disable @typescript-eslint/no-explicit-any */
// Los tipos de opciones de Carbon son muy anchos; las opciones se arman en cada pantalla.
export default function GraficoCarbon({ tipo, datos, opciones }: Props) {
  if (tipo === "linea") return <LineChart data={datos as any} options={opciones as any} />;
  if (tipo === "anillo") return <DonutChart data={datos as any} options={opciones as any} />;
  return <SimpleBarChart data={datos as any} options={opciones as any} />;
}
/* eslint-enable @typescript-eslint/no-explicit-any */
