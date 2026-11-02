import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Pildora } from "./Pildora";

describe("Pildora", () => {
  it("muestra el número y se oculta a los lectores de pantalla (el nombre accesible lo dice el enlace)", () => {
    render(<Pildora valor={4} />);
    const p = screen.getByText("4");
    expect(p).toHaveClass("silice-pildora");
    expect(p).toHaveAttribute("aria-hidden", "true");
  });
});

describe("Pildora: formato es-VE", () => {
  it("escribe el número con punto de miles", () => {
    render(<Pildora valor={1234} />);
    expect(screen.getByText("1.234")).toHaveClass("silice-pildora");
  });
});

// jsdom no calcula CSS: la regla se lee del fuente (como marco/estilosMarco.test.ts).
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const estilos = () => nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/comun/Pildora.scss`, "utf-8");

describe("Pildora: colores propios del contador", () => {
  const regla = () => /\.silice-pildora\s*\{([^}]*)\}/.exec(estilos())?.[1] ?? "";

  it("pinta el número y un contorno de 1 px del color del número sobre el fondo del contador", () => {
    expect(regla()).toMatch(/background-color:\s*var\(--silice-contador-fondo\)/);
    expect(regla()).toMatch(/(^|[\s;])color:\s*var\(--silice-contador-numero\)/);
    expect(regla()).toMatch(/border:\s*1px solid var\(--silice-contador-numero\)/);
  });

  it("deja de usar el acento y el marco", () => {
    expect(estilos()).not.toMatch(/var\(--silice-(acento|marco)\)/);
    expect(estilos()).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });
});
