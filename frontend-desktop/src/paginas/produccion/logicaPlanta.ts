// Lógica pura de «Receta de la planta» y «Costo por tonelada». La interfaz no calcula montos: costo por tonelada,
// totales y precios los manda el servidor y aquí solo se les da formato. Lo único que se suma es la masa de la receta,
// como aviso previo (el servidor la vuelve a comprobar y es la autoridad), y se suma con enteros sobre el texto, nunca
// con Number.
import { ErrorDeApi } from "../../api/cliente";
import { mensajeDeError } from "../../comun/errores";
import { MENSAJE_CIFRA, leerCifra } from "../../indicadores/cifraEscrita";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { SIN_DETALLE } from "./logica";

// La de `TOLERANCIA_MASA` en `produccion/fuentes.py` (suma de componentes en t por t de mezcla). Ninguna ruta la
// publica, así que se copia; `logicaPlanta.test.ts` compara la copia con el valor de Python.
export const TOLERANCIA_MASA = "0.02";

export const UNIDADES: readonly { valor: string; texto: string }[] = [
  { valor: "t", texto: "Toneladas (t)" },
  { valor: "l", texto: "Litros (l)" },
];
export const TIPOS: readonly { valor: string; texto: string }[] = [
  { valor: "propio", texto: "Propio (sale del inventario)" },
  { valor: "comprado", texto: "Comprado (precio de la lista)" },
];

export interface FilaDeComponente {
  codigo: string;
  cantidad: string; // lo que escribe la persona, con coma
  unidad: string;
  tipo: string;
}

// «0.94» -> (94n, 2): el entero y sus decimales.
function escalar(decimal: string, decimales: number): bigint {
  const [entera = "0", fraccion = ""] = decimal.split(".");
  return BigInt(entera + fraccion.padEnd(decimales, "0"));
}

function decimalesDe(decimal: string): number {
  return (decimal.split(".")[1] ?? "").length;
}

// El entero escalado a su decimal con punto, sin ceros de sobra: (990n, 3) -> «0.99».
function desescalar(valor: bigint, decimales: number): string {
  const texto = valor.toString().padStart(decimales + 1, "0");
  const entera = texto.slice(0, texto.length - decimales);
  const fraccion = texto.slice(texto.length - decimales).replace(/0+$/, "");
  return fraccion === "" ? entera : `${entera}.${fraccion}`;
}

const NO_NULA = /[1-9]/;

export interface SumaDeMasa {
  // La suma de las toneladas, en es-VE: «0,99».
  texto: string;
  // Todas las filas están completas y bien escritas: solo entonces la suma vale como aviso.
  completa: boolean;
  // Completa y a no más de la tolerancia de 1 t por t de mezcla.
  dentro: boolean;
}

// La masa de la receta: solo cuentan los componentes en toneladas (los litros, como el gasoil, no pesan en la mezcla).
export function sumaDeMasa(filas: readonly { cantidad: string; unidad: string }[]): SumaDeMasa {
  const cantidades: string[] = [];
  let completa = filas.length > 0;
  for (const fila of filas) {
    const lectura = leerCifra(fila.cantidad);
    if ("error" in lectura || lectura.valor.startsWith("-") || !NO_NULA.test(lectura.valor) || fila.unidad === "") {
      completa = false;
      continue;
    }
    if (fila.unidad === "t") cantidades.push(lectura.valor);
  }
  const escala = Math.max(decimalesDe(TOLERANCIA_MASA), ...cantidades.map(decimalesDe));
  const suma = cantidades.reduce((total, c) => total + escalar(c, escala), 0n);
  const uno = escalar("1", escala);
  const tolerancia = escalar(TOLERANCIA_MASA, escala);
  const distancia = suma > uno ? suma - uno : uno - suma;
  return {
    texto: formatoEsVe(desescalar(suma, escala)),
    completa,
    dentro: completa && distancia <= tolerancia,
  };
}

// «de 0,98 a 1,02»: 1 menos y 1 más la tolerancia.
export function rangoDeMasa(): [string, string] {
  const escala = decimalesDe(TOLERANCIA_MASA);
  const uno = escalar("1", escala);
  const tolerancia = escalar(TOLERANCIA_MASA, escala);
  return [formatoEsVe(desescalar(uno - tolerancia, escala)), formatoEsVe(desescalar(uno + tolerancia, escala))];
}

export interface ComponenteEnviado {
  codigo: string;
  cantidad_por_t: string;
  unidad: string;
  tipo: string;
}

export type LecturaDeComponentes = { componentes: ComponenteEnviado[] } | { error: string };

// Lo que escribe la persona al cuerpo de la API, o el primer problema dicho con el número de su fila. Son las mismas
// reglas de forma de `produccion/receta.py`; el servidor las vuelve a exigir.
export function armarComponentes(filas: readonly FilaDeComponente[]): LecturaDeComponentes {
  const componentes: ComponenteEnviado[] = [];
  for (const [i, fila] of filas.entries()) {
    const n = `Componente ${i + 1}`;
    const codigo = fila.codigo.trim();
    if (codigo === "") return { error: `${n}: escriba el código.` };
    if (fila.cantidad.trim() === "") return { error: `${n}: escriba la cantidad por tonelada.` };
    const lectura = leerCifra(fila.cantidad);
    if ("error" in lectura) return { error: `${n}: la cantidad está mal escrita. ${MENSAJE_CIFRA}` };
    if (lectura.valor.startsWith("-") || !NO_NULA.test(lectura.valor)) return { error: `${n}: la cantidad debe ser mayor que cero.` };
    if (fila.unidad === "") return { error: `${n}: elija la unidad.` };
    if (fila.tipo === "") return { error: `${n}: elija si es propio o comprado.` };
    if (fila.tipo === "propio" && fila.unidad !== "t") {
      return { error: `${n}: un componente propio sale del inventario y va en t.` };
    }
    componentes.push({ codigo, cantidad_por_t: lectura.valor, unidad: fila.unidad, tipo: fila.tipo });
  }
  const vistos = new Set<string>();
  for (const c of componentes) {
    if (vistos.has(c.codigo)) return { error: `El código ${c.codigo} está repetido.` };
    vistos.add(c.codigo);
  }
  return { componentes };
}

// Los textos que el servidor pone al publicar (`aplicacion/costo_propio.py`): el precio queda con esta fuente y la lista
// con este nombre.
export function fuenteDelPrecio(periodo: string, id: number): string {
  return `Producción, período ${periodo}, cálculo n.º ${id}`;
}

export function nombreDeLista(periodo: string, id: number): string {
  return `Costo propio ${periodo}, cálculo n.º ${id}`;
}

export interface DesgloseDeTasas {
  encabezado: string;
  faltan: string[];
  cierre: string;
}

const TASAS = /^(No hay tasa del BCV del mismo día para convertir a [A-Za-z]+:) (.+?)\. (Cárguela[^]*)$/;

// El rechazo por días sin tasa BCV nombra cada costo con su fecha, separados por «;»: aquí se parte para listarlos uno
// por renglón. Cualquier otro mensaje se devuelve como null y se muestra entero.
export function desgloseDeTasas(mensaje: string): DesgloseDeTasas | null {
  const m = TASAS.exec(mensaje);
  if (!m) return null;
  return { encabezado: m[1]!, faltan: m[2]!.split("; "), cierre: m[3]! };
}

// Lo que se le dice a la persona: el `detalle` en español del servidor tal cual; nunca un número de estado, el cuerpo
// técnico de una validación ni el nombre de un caso de uso.
export function mensajeDePlanta(error: unknown): string {
  if (!(error instanceof ErrorDeApi)) return mensajeDeError(error);
  if (error.estado === 403) return "Su cuenta no tiene permiso para esta acción.";
  if (SIN_DETALLE.test(error.detalle)) {
    if (error.estado === 422 || error.estado === 400) return "Revise los datos: alguno no es válido.";
    if (error.estado === 404) return "No se encontró lo que pedía. Actualice la pantalla.";
    return "El programa de Sílice no pudo completar la acción. Inténtelo de nuevo.";
  }
  return mensajeDeError(error);
}

// Publicar es de quien administra y exige su clave: un 403 aquí no es el genérico de «sin permiso».
export function mensajeAlPublicar(error: unknown): string {
  if (error instanceof ErrorDeApi && error.estado === 403) return "Solo un administrador con sesión puede publicar el costo propio.";
  return mensajeDePlanta(error);
}

// El servidor niega publicar si Administración no tiene la empresa: hay que mostrar el camino.
export function pideConfigurarEmpresa(error: unknown): boolean {
  return error instanceof ErrorDeApi && error.estado === 422 && error.detalle.startsWith("Configure la empresa");
}

export interface ResumenDeCalculo {
  agregados: string[];
  producido: [string, string][];
  totalCantera: string | null;
  totalPlanta: string | null;
}

function texto(valor: unknown): string | null {
  return typeof valor === "string" ? valor : null;
}

function objeto(valor: unknown): Record<string, unknown> {
  return valor !== null && typeof valor === "object" && !Array.isArray(valor) ? (valor as Record<string, unknown>) : {};
}

// Lo que se muestra de la instantánea que guardó el servidor; si trae otra forma, queda vacío en vez de romper.
export function resumenDeCalculo(instantanea: Record<string, unknown>): ResumenDeCalculo {
  const entradas = objeto(instantanea["entradas"]);
  const resultado = objeto(instantanea["resultado"]);
  const agregados = Array.isArray(entradas["agregados"]) ? entradas["agregados"].filter((a): a is string => typeof a === "string") : [];
  const producido = Object.entries(objeto(entradas["producido"])).flatMap(([codigo, t]): [string, string][] =>
    typeof t === "string" ? [[codigo, t]] : [],
  );
  return { agregados, producido, totalCantera: texto(resultado["total_cantera"]), totalPlanta: texto(resultado["total_planta"]) };
}
