// Lógica pura de «Producir mezcla», del reparto por pesos y de las constancias de la Tarea 4b. La interfaz no calcula
// costos: lo único que multiplica o suma es lo que anuncia antes de registrar (lo que consumirá una producción, la suma de
// los porcentajes), y lo hace con enteros sobre el texto, nunca con Number. El servidor vuelve a calcular y es la autoridad.
import type { ComponenteDeReceta } from "../../api/produccionPlanta";
import { decimalesDe, desescalar, escalar } from "./logicaPlanta";

// «0.94» por «2.5» = «2.35», exacto y sin ceros de sobra.
export function multiplicar(a: string, b: string): string {
  const da = decimalesDe(a);
  const db = decimalesDe(b);
  const producto = escalar(a, da) * escalar(b, db);
  return desescalar(producto, da + db);
}

export interface Consumo {
  codigo: string;
  toneladas: string;
}

// Lo que sale del inventario al producir: solo los componentes propios (los comprados vienen de la lista de precios y los
// litros no pesan). Es lo mismo que registra `produccion/receta.py`; aquí es un aviso previo.
export function consumosDeLaReceta(componentes: readonly ComponenteDeReceta[], toneladas: string): Consumo[] {
  return componentes
    .filter((c) => c.tipo === "propio")
    .map((c) => ({ codigo: c.codigo, toneladas: multiplicar(c.cantidad_por_t, toneladas) }));
}

// «75» (por ciento) -> «0.75» (la fracción que espera la API): se corre la coma dos lugares, sin dividir.
export function porcentajeAFraccion(porcentaje: string): string {
  const decimales = decimalesDe(porcentaje) + 2;
  return desescalar(escalar(porcentaje, decimalesDe(porcentaje)), decimales);
}

// La suma exacta de porcentajes escritos como decimales con punto.
export function sumaDePorcentajes(porcentajes: readonly string[]): string {
  const escala = Math.max(0, ...porcentajes.map(decimalesDe));
  return desescalar(
    porcentajes.reduce((total, p) => total + escalar(p, escala), 0n),
    escala,
  );
}

// «2026-02» -> «2026-02-28»: el día con que se pregunta qué receta rige al cierre del mes.
export function ultimoDiaDelMes(periodo: string): string {
  const [anio = "0", mes = "0"] = periodo.split("-");
  const dia = new Date(Date.UTC(Number(anio), Number(mes), 0)).getUTCDate();
  return `${periodo}-${String(dia).padStart(2, "0")}`;
}

export interface DatoDelMesAnterior {
  centro: string;
  total: string;
  calculo: number;
  periodo: string;
  tasa: { valor: string; fecha: string } | null;
}
export interface DatoQuePasa {
  centro: string;
  total: string;
}
export interface DatoDeOtroCalculo {
  codigo: string;
  costo: string;
  calculo: number;
  periodo: string;
}
export interface Constancias {
  vieneDelMesAnterior: DatoDelMesAnterior[];
  pasaAlMesSiguiente: DatoQuePasa[];
  deOtroCalculo: DatoDeOtroCalculo[];
}

function objeto(valor: unknown): Record<string, unknown> {
  return valor !== null && typeof valor === "object" && !Array.isArray(valor) ? (valor as Record<string, unknown>) : {};
}
function texto(valor: unknown): string | null {
  return typeof valor === "string" ? valor : null;
}
function entero(valor: unknown): number | null {
  return typeof valor === "number" && Number.isInteger(valor) ? valor : null;
}

// Lo que la versión 2 de la instantánea añade (`aplicacion/costo_propio.py`). Un cálculo de la versión 1 no trae estas
// claves y queda vacío; una forma inesperada se ignora en vez de romper la pantalla.
export function constanciasDe(instantanea: Record<string, unknown>): Constancias {
  const entradas = objeto(instantanea["entradas"]);
  const resultado = objeto(instantanea["resultado"]);
  const vieneDelMesAnterior = Object.entries(objeto(entradas["viene_del_mes_anterior"])).flatMap(([centro, dato]): DatoDelMesAnterior[] => {
    const d = objeto(dato);
    const total = texto(d["total"]);
    const calculo = entero(d["calculo"]);
    const periodo = texto(d["periodo"]);
    if (total === null || calculo === null || periodo === null) return [];
    const t = objeto(d["tasa"]);
    const valor = texto(t["valor"]);
    const fecha = texto(t["fecha"]);
    return [{ centro, total, calculo, periodo, tasa: valor !== null && fecha !== null ? { valor, fecha } : null }];
  });
  const pasaAlMesSiguiente = Object.entries(objeto(resultado["pasa_al_mes_siguiente"])).flatMap(([centro, dato]): DatoQuePasa[] => {
    const total = texto(objeto(dato)["total"]);
    return total === null ? [] : [{ centro, total }];
  });
  const deOtroCalculo = Object.entries(objeto(entradas["de_otro_calculo"])).flatMap(([codigo, dato]): DatoDeOtroCalculo[] => {
    const d = objeto(dato);
    const costo = texto(d["costo"]);
    const calculo = entero(d["calculo"]);
    const periodo = texto(d["periodo"]);
    return costo === null || calculo === null || periodo === null ? [] : [{ codigo, costo, calculo, periodo }];
  });
  return { vieneDelMesAnterior, pasaAlMesSiguiente, deOtroCalculo };
}
