import { DonutChart, LineChart, SimpleBarChart } from "@carbon/charts-react";
import type { BarChartOptions, ChartTabularData, DonutChartOptions, LineChartOptions } from "@carbon/charts-react";
import "@carbon/charts-react/styles.css";
import { fusionarOpciones, opcionesBase, useModoEfectivo } from "./paletaGraficos";

// Adaptador unico sobre Carbon Charts. Se carga perezosamente (`React.lazy`) para que el peso de la libreria solo se
// baje al abrir una pagina con graficos, y las pruebas lo reemplazan con `vi.mock` (jsdom no dibuja SVG de verdad).
// Cada grafico parte de las opciones base de Silice (tema segun el modo de color, sin barra de herramientas, leyenda con
// dos o mas series, cifras en es-VE) y lo que manda la pantalla las completa o las cambia.
export type TipoGrafico = "linea" | "anillo" | "barras";

type Props =
  | { tipo: "linea"; datos: ChartTabularData; opciones: LineChartOptions }
  | { tipo: "anillo"; datos: ChartTabularData; opciones: DonutChartOptions }
  | { tipo: "barras"; datos: ChartTabularData; opciones: BarChartOptions };

function numeroDeSeries(datos: ChartTabularData): number {
  return new Set(datos.map((d) => String((d as { group?: unknown }).group))).size;
}

export default function GraficoCarbon(props: Props) {
  const modo = useModoEfectivo();
  const series = numeroDeSeries(props.datos);
  if (props.tipo === "linea") {
    return <LineChart data={props.datos} options={fusionarOpciones(opcionesBase(modo, { series }), props.opciones)} />;
  }
  if (props.tipo === "anillo") {
    return <DonutChart data={props.datos} options={fusionarOpciones(opcionesBase(modo, { series, ejes: false }), props.opciones)} />;
  }
  return <SimpleBarChart data={props.datos} options={fusionarOpciones(opcionesBase(modo, { series }), props.opciones)} />;
}
