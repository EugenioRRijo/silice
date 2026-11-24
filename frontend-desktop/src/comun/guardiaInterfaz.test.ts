import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import ts from "typescript";
import { describe, expect, test } from "vitest";
import deuda from "./guardiaInterfaz.deuda.json";

// Guardia de interfaz (F3 del plan de interfaz, 2026-11-23). Eugenio: «vamos a hacer lo mismo que core y buscar una ui ux,
// front que sea amigable para el usuario y dejarlo guardado en una guardia en la CI». Vigila las reglas medibles de la
// skill `interfaz-silice` y de `docs/especificaciones/2026-11-23-norma-de-interfaz.md`:
//   - trato: la persona se trata de usted, nunca de tú;
//   - siglas: un rótulo no lleva una sigla suelta (primero la palabra, o la sigla con su explicación entre paréntesis);
//   - mayúsculas: el front no escribe «ERROR:», «ADVERTENCIA:»… (el ícono de la severidad ya lo dice);
//   - vacío: un `EstadoVacio` dice qué hacer (descripción o botón), no solo que no hay nada.
// Lee el código con el analizador de TypeScript: solo textos (no comentarios ni nombres de clase). Modo trinquete: lo que ya
// incumplía al nacer la guardia está en `guardiaInterfaz.deuda.json`; falla lo nuevo, y también una deuda que ya no se
// cumple (para que se borre). La deuda solo puede bajar. Una guardia no prueba que una pantalla sea buena: evita que
// vuelvan los errores que ya se saben medir (la gente juzga lo demás).

const SRC = join(__dirname, "..");

function archivos(dir: string): string[] {
  return readdirSync(dir).flatMap((nombre) => {
    const ruta = join(dir, nombre);
    if (statSync(ruta).isDirectory()) return archivos(ruta);
    const fuente = /\.tsx?$/.test(nombre) && !/\.(test|d)\.tsx?$/.test(nombre) && !nombre.startsWith("datosDePrueba");
    return fuente ? [ruta] : [];
  });
}

// Atributos y propiedades cuyo valor nunca se lee como texto.
const NO_VISIBLES = new Set(["className", "id", "key", "href", "to", "type", "kind", "size", "role", "src", "name", "htmlFor", "align"]);
// Rótulos de campo: atributos JSX `labelText`, `etiqueta` y `legend`, y la propiedad `titulo` de una columna de tabla
// (`{ clave, titulo }`). El `titulo` de un componente (por ejemplo de `EstadoVacio`) es una frase, no un rótulo.
const ROTULOS_JSX = new Set(["labelText", "etiqueta", "legend"]);
const ROTULOS_DE_COLUMNA = new Set(["titulo"]);

function esRotulo(nodo: ts.Node, nombre: string | null): boolean {
  if (nombre === null) return false;
  return ts.isJsxAttribute(nodo) ? ROTULOS_JSX.has(nombre) : ROTULOS_DE_COLUMNA.has(nombre);
}

interface Texto {
  texto: string;
  rotulo: boolean;
}

function nombreDe(nodo: ts.Node): string | null {
  if (ts.isJsxAttribute(nodo)) return nodo.name.getText();
  if (ts.isPropertyAssignment(nodo)) return nodo.name.getText().replace(/["']/g, "");
  return null;
}

// Los textos de un archivo: literales y texto JSX, con si son un rótulo. Un texto que parece código (sin espacios, una
// ruta, nombres de clase) no cuenta.
function textosDe(codigo: string, archivo = "x.tsx"): Texto[] {
  const tipo = archivo.endsWith("x") ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
  const fuente = ts.createSourceFile(archivo, codigo, ts.ScriptTarget.Latest, true, tipo);
  const hallados: Texto[] = [];
  const visitar = (nodo: ts.Node) => {
    if (ts.isImportDeclaration(nodo) || ts.isExportDeclaration(nodo)) return;
    let texto: string | null = null;
    if (ts.isJsxText(nodo)) texto = nodo.getText().replace(/\s+/g, " ").trim();
    else if (ts.isStringLiteral(nodo) || ts.isNoSubstitutionTemplateLiteral(nodo)) texto = nodo.text;
    else if (ts.isTemplateExpression(nodo)) texto = [nodo.head.text, ...nodo.templateSpans.map((s) => s.literal.text)].join("…");
    if (texto !== null && texto !== "") {
      let padre: ts.Node = nodo.parent;
      if (ts.isJsxExpression(padre)) padre = padre.parent;
      const nombre = nombreDe(padre);
      const pareceCodigo = !/\s/.test(texto) || /^\.{0,2}\//.test(texto) || /(^|\s)(cds|silice)-/.test(texto);
      if ((nombre === null || !NO_VISIBLES.has(nombre)) && !pareceCodigo) {
        hallados.push({ texto, rotulo: esRotulo(padre, nombre) });
      }
      if (!ts.isTemplateExpression(nodo)) return;
    }
    ts.forEachChild(nodo, visitar);
  };
  visitar(fuente);
  return hallados;
}

// `<EstadoVacio …/>` sin descripción ni contenido: dice que no hay nada, pero no qué hacer.
function vaciosSinPasoSiguiente(codigo: string): string[] {
  const fuente = ts.createSourceFile("x.tsx", codigo, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const hallados: string[] = [];
  const visitar = (nodo: ts.Node) => {
    if (ts.isJsxSelfClosingElement(nodo) && nodo.tagName.getText() === "EstadoVacio") {
      const atributos = nodo.attributes.properties.filter(ts.isJsxAttribute);
      if (!atributos.some((a) => a.name.getText() === "descripcion")) {
        const titulo = atributos.find((a) => a.name.getText() === "titulo");
        hallados.push(titulo?.initializer ? titulo.initializer.getText() : "<sin título>");
      }
    }
    ts.forEachChild(nodo, visitar);
  };
  visitar(fuente);
  return hallados;
}

// Marcas inequívocas de tú: pronombres, formas de segunda persona e imperativos irregulares. Límite declarado: el
// imperativo de tú de un verbo regular se escribe igual que la tercera persona («Crea una versión nueva» describe lo que
// hace un botón), así que no se puede distinguir sin leer la frase; «Empieza aquí» queda para la revisión humana.
const TU_IMPERATIVO = /(^|[.;:¿¡!?]\s+|«)(Haz|Pon|Ten|Ven|Sal|Di)\b/;
const TU_PALABRAS =
  /(^|[^\p{L}])((tú|ti|contigo|tienes|puedes|quieres|debes|necesitas|sabes|estás|eres|te falta)(?!\p{L})|tu (?=\p{Ll}))/iu;
// Siglas que no van solas en un rótulo. IVA y RIF quedan fuera: en Venezuela se leen como palabras (decisión del 2026-11-23).
const SIGLAS = /(^|[^\p{L}\d])(SPI|CPI|EAC|BAC|FCAS|PV|EV|AC|Km|R|P50|P80|AACE)(?![\p{L}\d])/u;
const SEVERIDAD_EN_MAYUSCULAS = /\b(ERROR|ADVERTENCIA|PENDIENTE|CRITICO|CRÍTICO|INFO):/;

function infracciones(texto: Texto): string[] {
  const reglas: string[] = [];
  if (TU_IMPERATIVO.test(texto.texto) || TU_PALABRAS.test(texto.texto)) reglas.push("trato");
  if (texto.rotulo && SIGLAS.test(texto.texto) && !texto.texto.includes("(")) reglas.push("siglas");
  if (SEVERIDAD_EN_MAYUSCULAS.test(texto.texto)) reglas.push("mayúsculas");
  return reglas;
}

function hallazgosDelFront(): string[] {
  const hallados = new Set<string>();
  for (const ruta of archivos(SRC)) {
    const codigo = readFileSync(ruta, "utf8");
    const archivo = relative(SRC, ruta).replaceAll("\\", "/");
    for (const t of textosDe(codigo, ruta)) {
      for (const regla of infracciones(t)) hallados.add(`${regla} | ${archivo} | ${t.texto.slice(0, 90)}`);
    }
    if (ruta.endsWith(".tsx")) {
      for (const titulo of vaciosSinPasoSiguiente(codigo)) hallados.add(`vacío | ${archivo} | ${titulo.slice(0, 90)}`);
    }
  }
  return [...hallados].sort();
}

describe("guardia de interfaz: el detector", () => {
  test("encuentra el tú y deja pasar el usted y lo impersonal", () => {
    const de = (texto: string) => infracciones({ texto, rotulo: false });
    expect(de("Te falta elegir la obra.")).toEqual(["trato"]);
    expect(de("Haz clic en «Guardar».")).toEqual(["trato"]);
    expect(de("Puedes cambiarlo después.")).toEqual(["trato"]);
    expect(de("Revise tu obra antes de enviarla.")).toEqual(["trato"]);
    expect(de("Escriba el código de la partida.")).toEqual([]);
    expect(de("El FCAS se escribe como fracción.")).toEqual([]);
    expect(de("Crea una versión nueva desde la guardada.")).toEqual([]);
  });

  test("una sigla suelta en un rótulo falla; con su explicación entre paréntesis, no", () => {
    const rotulo = (texto: string) => infracciones({ texto, rotulo: true });
    expect(rotulo("Límite de SPI")).toEqual(["siglas"]);
    expect(rotulo("Índice de plazo (SPI)")).toEqual([]);
    expect(rotulo("Precio con IVA")).toEqual([]);
    expect(infracciones({ texto: "El SPI mide el plazo", rotulo: false })).toEqual([]);
  });

  test("la severidad en mayúsculas escrita en el front falla", () => {
    expect(infracciones({ texto: "ERROR: no cuadra", rotulo: false })).toEqual(["mayúsculas"]);
  });

  test("lee textos y rótulos, no comentarios ni clases, y ve el vacío sin paso siguiente", () => {
    const codigo = `
      // Escribe esto: es un comentario y no cuenta.
      const a = <CampoTexto labelText="Límite de SPI" className="silice-x cds--type-body-01" />;
      const columnas = [{ clave: "eac", titulo: "EAC del sistema" }];
      const b = <p>Te falta elegir la obra.</p>;
      const c = <EstadoVacio titulo="No hay partidas." />;
      const d = <EstadoVacio titulo="No hay obras." descripcion="Cree una con «Nueva obra»." />;`;
    const textos = textosDe(codigo);
    expect(textos.filter((t) => t.rotulo).map((t) => t.texto)).toEqual(["Límite de SPI", "EAC del sistema"]);
    expect(textos.map((t) => t.texto)).not.toContain("silice-x cds--type-body-01");
    expect(textos.some((t) => t.texto.includes("comentario"))).toBe(false);
    expect(vaciosSinPasoSiguiente(codigo)).toEqual(['"No hay partidas."']);
  });
});

describe("guardia de interfaz: el front", () => {
  const hallados = hallazgosDelFront();
  const conocida = new Set<string>(deuda.conocida);

  test("ningún texto nuevo incumple la norma (lo que ya incumplía está en la deuda)", () => {
    expect(hallados.filter((h) => !conocida.has(h))).toEqual([]);
  });

  test("la deuda solo baja: lo arreglado se borra de guardiaInterfaz.deuda.json", () => {
    expect(deuda.conocida.filter((h) => !hallados.includes(h))).toEqual([]);
  });
});
