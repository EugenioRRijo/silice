import type { GridOptions, LegendOptions, ScaleTypes, ToolbarOptions, TooltipOptions } from "@carbon/charts";
import { useEffect, useState } from "react";
import { formatoEsVe } from "../indicadores/formatoEsVe";
import { useModoDeColor } from "./modoDeColor";
import type { ModoEfectivo } from "./modoDeColor";

// Paleta de los graficos, validada con el script de la skill de graficos sobre las superficies de Silice. Tres colores de
// serie (azul, aguamarina y naranja) y dos neutros; nunca el morado (reservado para los atipicos) ni los colores de
// gravedad, que son de las alertas y no de una serie. La aguamarina en claro queda bajo 3:1 contra el papel: siempre va con
// rotulo directo o con su tabla. El naranja solo entra como tercera serie.
// Carbon Charts trae su propia paleta categorica (con morado), por eso se pasa siempre una escala.
export type SlotDeColor = "serie1" | "serie2" | "serie3" | "neutro" | "neutro2";

export const ORDEN_DE_SLOTS: readonly SlotDeColor[] = ["serie1", "serie2", "serie3", "neutro", "neutro2"];

const PASOS: Record<ModoEfectivo, Record<SlotDeColor, string>> = {
  claro: { serie1: "#2A78D6", serie2: "#1BAF7A", serie3: "#EB6834", neutro: "#9A9184", neutro2: "#6B655B" },
  oscuro: { serie1: "#3987E5", serie2: "#199E70", serie3: "#D95926", neutro: "#8A847A", neutro2: "#B3ADA2" },
};

// Los pasos de color de un modo, por nombre de lugar en la paleta.
export function coloresDeSerie(modo: ModoEfectivo): Record<SlotDeColor, string> {
  return { ...PASOS[modo] };
}

// Los colores del modo claro en orden (para los lugares que solo necesitan la lista).
export const PALETA_GRAFICOS: readonly string[] = ORDEN_DE_SLOTS.map((s) => PASOS.claro[s]);

// El lugar de la paleta de cada grupo. Con `catalogo` (todos los grupos posibles, en un orden fijo) un grupo conserva su
// color aunque un filtro quite a los demas; sin el, el color sale del orden en que llegan. Pasada la paleta, vuelve al inicio.
export function slotsPorGrupo(grupos: readonly string[], catalogo: readonly string[] = grupos): Record<string, SlotDeColor> {
  const slots: Record<string, SlotDeColor> = {};
  grupos.forEach((g, i) => {
    const lugar = catalogo.indexOf(g);
    slots[g] = ORDEN_DE_SLOTS[(lugar >= 0 ? lugar : catalogo.length + i) % ORDEN_DE_SLOTS.length]!;
  });
  return slots;
}

// El lugar de cada serie de una curva por su rol: lo real es la serie 1, lo gastado la 2, el pronostico la 3 y el plan
// es neutro. Es fijo por rol (no por cuantas series vengan), asi el color no cambia cuando una serie falta. Una segunda
// serie del mismo rol toma el neutro oscuro para no repetir el de la primera.
const SLOT_DE_ROL: Record<"plan" | "real" | "gastado" | "pronostico", SlotDeColor> = {
  plan: "neutro",
  real: "serie1",
  gastado: "serie2",
  pronostico: "serie3",
};

export function slotsPorRol(series: readonly { nombre: string; rol: "plan" | "real" | "gastado" | "pronostico" }[]): Record<string, SlotDeColor> {
  const slots: Record<string, SlotDeColor> = {};
  const usados = new Set<SlotDeColor>();
  for (const s of series) {
    const slot = SLOT_DE_ROL[s.rol];
    slots[s.nombre] = usados.has(slot) ? "neutro2" : slot;
    usados.add(slot);
  }
  return slots;
}

// `color.scale` de Carbon Charts a partir de los lugares ya decididos.
export function escalaDeColor(modo: ModoEfectivo, slots: Readonly<Record<string, SlotDeColor>>): { scale: Record<string, string> } {
  const scale: Record<string, string> = {};
  for (const [nombre, slot] of Object.entries(slots)) scale[nombre] = PASOS[modo][slot];
  return { scale };
}

// Numero de un eje o de un tooltip a es-VE, solo por operaciones de cadena sobre su representacion decimal.
export function formatoNumeroEsVe(valor: unknown): string {
  return formatoEsVe(String(valor));
}

// La única conversión de una cifra del servidor a número del front: el alto de una barra o la posición de un punto. La
// cifra que se lee (etiquetas, globo, tabla) sigue siendo el texto del servidor; esto no se muestra ni se suma. Solo el
// decimal con punto de la API («1234.50»); cualquier otro texto da NaN y no se dibuja.
const DECIMAL_DE_LA_API = /^-?\d+(\.\d+)?$/;
export function valorParaDibujar(cifra: string): number {
  return DECIMAL_DE_LA_API.test(cifra) ? Number(cifra) : Number.NaN;
}

// Carbon tipa `scaleType` con su enum (`ScaleTypes`), que solo existe como valor dentro de la libreria: importarlo aqui
// traeria toda la libreria al paquete principal y rompe la carga perezosa de los graficos. Se pasa el mismo texto.
export const ESCALA_DE_ETIQUETAS = "labels" as unknown as ScaleTypes;

export interface OpcionesBase {
  theme: string;
  toolbar: ToolbarOptions;
  legend: LegendOptions;
  tooltip: TooltipOptions;
  grid?: GridOptions;
  color?: { scale: Record<string, string> };
}

interface ConfigBase {
  // Lugar de color de cada serie por su nombre (fijo: no cambia con un filtro).
  colores?: Readonly<Record<string, SlotDeColor>>;
  // Cuantas series dibuja el grafico: la leyenda va con dos o mas (una sola la repetiria el titulo).
  series?: number;
  // Falso en los graficos sin ejes (el anillo): sin cuadricula.
  ejes?: boolean;
}

// Lo comun a todos los graficos de Silice: tema segun el modo, sin barra de herramientas (su boton va dentro de un
// role="button", sus rotulos estan en ingles y cada grafico tiene su tabla), cuadricula solo horizontal y de una linea
// fina, leyenda con dos o mas series, y un globo con las cifras en coma decimal y punto de miles.
export function opcionesBase(modo: ModoEfectivo, config: ConfigBase = {}): OpcionesBase {
  const { colores, series, ejes = true } = config;
  const base: OpcionesBase = {
    theme: modo === "oscuro" ? "g100" : "white",
    toolbar: { enabled: false },
    legend: { enabled: series === undefined ? true : series >= 2, position: "bottom" },
    tooltip: { valueFormatter: formatoNumeroEsVe },
  };
  if (ejes) base.grid = { x: { enabled: false }, y: { enabled: true } };
  if (colores) base.color = escalaDeColor(modo, colores);
  return base;
}

type Plano = Record<string, unknown>;
const esPlano = (v: unknown): v is Plano => typeof v === "object" && v !== null && Object.getPrototypeOf(v) === Object.prototype;

// Mezcla las opciones propias de un grafico sobre las de base: lo propio manda y los objetos se mezclan por dentro (la
// leyenda propia no borra la posicion de la base). No toca ninguna de las dos.
export function fusionarOpciones<T extends object>(base: object, propias: T): T {
  const salida: Plano = { ...base };
  for (const [clave, valor] of Object.entries(propias)) {
    const previo = salida[clave];
    salida[clave] = esPlano(previo) && esPlano(valor) ? fusionarOpciones(previo, valor) : valor;
  }
  return salida as unknown as T;
}

function modoAplicado(): ModoEfectivo | null {
  const aplicado = document.documentElement.dataset.modo;
  return aplicado === "claro" || aplicado === "oscuro" ? aplicado : null;
}

// El modo que rige ahora (claro u oscuro): el elegido, o el del sistema si la persona dejo «como el sistema». Cada uso de
// `useModoDeColor` guarda su propio estado y un cambio hecho en otro lugar de la misma pestana no lo avisa, por eso se
// mira ademas el atributo `data-modo` de <html>, que el selector de modo siempre actualiza.
export function useModoEfectivo(): ModoEfectivo {
  const { modo, delSistema } = useModoDeColor();
  const [aplicado, setAplicado] = useState<ModoEfectivo | null>(modoAplicado);
  useEffect(() => {
    const observador = new MutationObserver(() => setAplicado(modoAplicado()));
    observador.observe(document.documentElement, { attributes: true, attributeFilter: ["data-modo"] });
    return () => observador.disconnect();
  }, []);
  return aplicado ?? (modo === "sistema" ? delSistema : modo);
}
