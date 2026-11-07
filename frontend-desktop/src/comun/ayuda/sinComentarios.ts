// Quita los comentarios del código fuente antes de buscar en él los rótulos que la ayuda nombra (F7, A2): un rótulo que solo
// vive en un comentario o en un docstring no lo ve quien usa la interfaz. Es un recorrido por caracteres que respeta los
// textos (comillas simples, dobles y plantillas), de modo que `//` dentro de una URL o `#` dentro de un texto se conservan.
// Solo lo usan las pruebas.

export type Lenguaje = "ts" | "py";

export function sinComentarios(codigo: string, lenguaje: Lenguaje): string {
  return lenguaje === "ts" ? quitarDeTs(codigo) : quitarDePython(codigo);
}

function quitarDeTs(c: string): string {
  let fuera = "";
  let i = 0;
  while (i < c.length) {
    const ch = c[i]!;
    const par = c.slice(i, i + 2);
    if (par === "//") {
      while (i < c.length && c[i] !== "\n") i++;
    } else if (par === "/*") {
      const fin = c.indexOf("*/", i + 2);
      i = fin === -1 ? c.length : fin + 2;
      fuera += " ";
    } else if (ch === '"' || ch === "'" || ch === "`") {
      let j = i + 1;
      while (j < c.length && c[j] !== ch && (ch === "`" || c[j] !== "\n")) j += c[j] === "\\" ? 2 : 1;
      fuera += c.slice(i, j + 1);
      i = j + 1;
    } else {
      fuera += ch;
      i++;
    }
  }
  return fuera;
}

function quitarDePython(c: string): string {
  let fuera = "";
  let i = 0;
  while (i < c.length) {
    const ch = c[i]!;
    const triple = c.slice(i, i + 3);
    if (ch === "#") {
      while (i < c.length && c[i] !== "\n") i++;
    } else if (triple === '"""' || triple === "'''") {
      const fin = c.indexOf(triple, i + 3);
      const hasta = fin === -1 ? c.length : fin + 3;
      const inicioDeLinea = fuera.slice(fuera.lastIndexOf("\n") + 1);
      // Un texto de tres comillas que ocupa la línea entera, sin asignarse ni pasarse, es un docstring: se descarta.
      if (inicioDeLinea.trim() !== "") fuera += c.slice(i, hasta);
      i = hasta;
    } else if (ch === '"' || ch === "'") {
      let j = i + 1;
      while (j < c.length && c[j] !== ch && c[j] !== "\n") j += c[j] === "\\" ? 2 : 1;
      fuera += c.slice(i, j + 1);
      i = j + 1;
    } else {
      fuera += ch;
      i++;
    }
  }
  return fuera;
}
