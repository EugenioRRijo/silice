// Texto que se ve en la celda, a partir del valor guardado (texto decimal, fecha ISO, TRUE/FALSE o texto) y del
// codigo de formato de Excel. Subconjunto: General, 0, 0.00 (cualquier cantidad de decimales), #,##0 y #,##0.00,
// porcentajes (0%, 0.00%) y fechas con d, m y a. Cualquier otro codigo se muestra con el valor tal como llega:
// una cifra puede verse menos bonita, pero nunca se esconde ni se altera.
//
// El redondeo se hace sobre el texto con BigInt, sin pasar por float, y la mitad se redondea hacia afuera de
// cero como Excel (2.5 -> 3, -2.675 -> -2.68). Los separadores son los del codigo del libro (coma de miles,
// punto decimal), los mismos con que la API manda los montos; los regionales (es-VE) quedan diferidos.

const NUMERO = /^(-?)(0|[1-9][0-9]*)(?:\.([0-9]+))?$/;
const FECHA = /^([0-9]{4})-([0-9]{2})-([0-9]{2})(?:[T ].*)?$/;
const FORMATO_NUMERICO = /^(#,##)?0(?:\.(0+))?(%)?$/;
const FORMATO_FECHA = /^(?:[dmy]{1,4})(?:[/\-. ](?:[dmy]{1,4})){2}$/i;

// Formato corto de fecha de Excel (numero 14): en Excel se ve segun la region. Aqui, dia/mes/anio.
const FECHA_CORTA_DE_EXCEL = "mm-dd-yy";

interface Decimal {
  negativo: boolean;
  entera: string;
  fraccion: string;
}

function leer(texto: string): Decimal | null {
  const m = NUMERO.exec(texto);
  if (!m) return null;
  const fraccion = m[3] ?? "";
  const esCero = /^0*$/.test(m[2] + fraccion);
  return { negativo: m[1] === "-" && !esCero, entera: m[2], fraccion };
}

// Corre la coma decimal dos lugares a la derecha (para porcentajes) sin pasar por numero.
function porCien(d: Decimal): Decimal {
  const fraccion = d.fraccion.padEnd(2, "0");
  const entera = (d.entera + fraccion.slice(0, 2)).replace(/^0+(?=[0-9])/, "");
  return { ...d, entera, fraccion: fraccion.slice(2) };
}

function redondear(d: Decimal, decimales: number): Decimal {
  if (d.fraccion.length <= decimales) return { ...d, fraccion: d.fraccion.padEnd(decimales, "0") };
  const sobran = d.fraccion.length - decimales;
  const divisor = 10n ** BigInt(sobran);
  const total = BigInt(d.entera + d.fraccion);
  let cociente = total / divisor;
  if ((total % divisor) * 2n >= divisor) cociente += 1n;
  const digitos = cociente.toString().padStart(decimales + 1, "0");
  return {
    ...d,
    entera: digitos.slice(0, digitos.length - decimales),
    fraccion: digitos.slice(digitos.length - decimales),
  };
}

function conMiles(entera: string): string {
  return entera.replace(/\B(?=([0-9]{3})+(?![0-9]))/g, ",");
}

function armar(d: Decimal, miles: boolean): string {
  const entera = miles ? conMiles(d.entera) : d.entera;
  return `${d.negativo ? "-" : ""}${entera}${d.fraccion ? `.${d.fraccion}` : ""}`;
}

function formatearFecha(valor: string, codigo: string): string {
  const m = FECHA.exec(valor);
  if (!m) return valor;
  const [, anio, mes, dia] = m;
  if (codigo === FECHA_CORTA_DE_EXCEL) return `${dia}/${mes}/${anio}`;
  // Una sola pasada, de izquierda a derecha, para que el "m" de "mm" no se confunda con otro.
  return codigo.replace(/y{1,4}|m{1,4}|d{1,4}/gi, (parte) => {
    const letra = parte[0].toLowerCase();
    if (letra === "y") return parte.length <= 2 ? anio.slice(2) : anio;
    if (letra === "m") return parte.length === 1 ? String(Number(mes)) : mes;
    return parte.length === 1 ? String(Number(dia)) : dia;
  });
}

export function formatearMostrado(valor: string, formato: string): string {
  const codigo = formato.trim();

  if (FORMATO_FECHA.test(codigo)) return formatearFecha(valor, codigo);

  const numero = leer(valor);
  if (!numero) return valor; // texto, booleano o fecha con otro formato: tal como llega

  if (codigo === "General" || codigo === "") {
    return armar({ ...numero, fraccion: numero.fraccion.replace(/0+$/, "") }, false);
  }

  const m = FORMATO_NUMERICO.exec(codigo);
  if (!m) return valor;
  const [, miles, ceros, porcentaje] = m;
  const base = porcentaje ? porCien(numero) : numero;
  return armar(redondear(base, ceros?.length ?? 0), miles !== undefined) + (porcentaje ? "%" : "");
}

export type TipoDeValor = "numero" | "fecha" | "booleano" | "texto";

// Excel alinea por tipo cuando la alineacion es General: numeros y fechas a la derecha, booleanos al centro,
// texto a la izquierda. El contrato lleva el valor como texto sin su tipo, asi que se deduce de la forma del
// texto (un codigo "007" se trata como texto; un texto "100" guardado como cadena se tomaria por numero: limite
// declarado, ver el ruling RS2.4-3).
export function tipoDeValor(valor: string): TipoDeValor {
  if (NUMERO.test(valor)) return "numero";
  if (FECHA.test(valor)) return "fecha";
  if (valor === "TRUE" || valor === "FALSE") return "booleano";
  return "texto";
}
