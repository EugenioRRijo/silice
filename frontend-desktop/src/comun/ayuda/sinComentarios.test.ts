import { describe, expect, test } from "vitest";
import { sinComentarios } from "./sinComentarios";

// F7 (revisión del árbitro, A2): el oráculo de la ayuda busca los rótulos en el código, y un rótulo que solo aparece en un
// comentario o en un docstring no existe para la persona. Estas pruebas fijan qué se quita antes de buscar. Oráculos a mano.

describe("sinComentarios en TypeScript", () => {
  test("quita los comentarios de línea y de bloque, también los de varias líneas", () => {
    const ts = 'const a = 1; // «Rótulo en comentario»\n/* «En bloque»\n   «y otra línea» */\nconst b = 2;';
    const fuera = sinComentarios(ts, "ts");
    expect(fuera).not.toContain("Rótulo en comentario");
    expect(fuera).not.toContain("En bloque");
    expect(fuera).not.toContain("y otra línea");
    expect(fuera).toContain("const a = 1;");
    expect(fuera).toContain("const b = 2;");
  });

  test("conserva lo que parece comentario pero está dentro de un texto", () => {
    const ts = 'const url = "https://ejemplo.test/a"; const t = `// «Rótulo en plantilla»`; const u = \'/* «Rótulo» */\';';
    const fuera = sinComentarios(ts, "ts");
    expect(fuera).toContain("https://ejemplo.test/a");
    expect(fuera).toContain("// «Rótulo en plantilla»");
    expect(fuera).toContain("/* «Rótulo» */");
  });

  test("conserva el texto de JSX y el de las etiquetas", () => {
    const tsx = '<Button kind="primary">Agregar partida</Button> {/* «Solo comentario» */}';
    const fuera = sinComentarios(tsx, "ts");
    expect(fuera).toContain("Agregar partida");
    expect(fuera).not.toContain("Solo comentario");
  });
});

describe("sinComentarios en Python", () => {
  test("quita los comentarios con # y los docstrings, pero no los textos", () => {
    const py = [
      '"""Docstring del módulo con «Rótulo de módulo»."""',
      "def f():",
      '    """Docstring de la función: «Rótulo de función»."""',
      '    mensaje = "Guardar # no es comentario"  # «Rótulo de comentario»',
      "    return mensaje",
    ].join("\n");
    const fuera = sinComentarios(py, "py");
    expect(fuera).not.toContain("Rótulo de módulo");
    expect(fuera).not.toContain("Rótulo de función");
    expect(fuera).not.toContain("Rótulo de comentario");
    expect(fuera).toContain("Guardar # no es comentario");
    expect(fuera).toContain("return mensaje");
  });

  test("un texto de varias líneas que se asigna no es un docstring y se conserva", () => {
    const py = 'TEXTO = """Línea uno\n«Rótulo en texto largo»"""\n';
    expect(sinComentarios(py, "py")).toContain("Rótulo en texto largo");
  });
});
