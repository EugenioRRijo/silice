import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { SelectorCaso, SelectorProyecto } from "./Selectores";

const PROYECTOS = [
  { codigo: "P-01", nombre: "Clínica Norte con un nombre larguísimo que se recorta", version_vigente: 3, actualizado: null },
  { codigo: "P-02", nombre: "Galpón", version_vigente: null, actualizado: null },
];

// Con la letra grande el selector se acota (min(13rem, 18vw)) y el nombre del proyecto se recorta con puntos suspensivos:
// el nombre completo queda en el título.
describe("SelectorProyecto", () => {
  test("el título del selector trae el nombre completo del proyecto elegido", () => {
    render(<SelectorProyecto proyectos={PROYECTOS} elegido="P-01" alElegir={() => {}} />);
    expect(screen.getByRole("combobox", { name: "Proyecto" })).toHaveAttribute("title", PROYECTOS[0].nombre);
  });

  // Carbon fija el título solo al montar y al cambiar con el selector: si el proyecto cambia desde fuera, hay que dárselo.
  test("el título sigue al proyecto elegido cuando este cambia desde fuera", () => {
    const { rerender } = render(<SelectorProyecto proyectos={PROYECTOS} elegido="P-01" alElegir={() => {}} />);
    rerender(<SelectorProyecto proyectos={PROYECTOS} elegido="P-02" alElegir={() => {}} />);
    expect(screen.getByRole("combobox", { name: "Proyecto" })).toHaveAttribute("title", "Galpón");
  });

  test("sin proyecto elegido el título dice «Sin proyecto»", () => {
    render(<SelectorProyecto proyectos={PROYECTOS} elegido={null} alElegir={() => {}} />);
    expect(screen.getByRole("combobox", { name: "Proyecto" })).toHaveAttribute("title", "Sin proyecto");
  });
});

describe("SelectorCaso", () => {
  test("el rótulo dice «Carpeta de trabajo», no «Caso»", () => {
    const caso = { nombre: "demo.db", ruta_relativa: "data/demo.db" } as never;
    render(<SelectorCaso casos={{ actual: caso, casos: [caso] }} puedeCambiar ocupado={false} alElegir={() => {}} />);
    expect(screen.getByRole("combobox", { name: "Carpeta de trabajo" })).toBeInTheDocument();
    expect(screen.queryByText(/\bcaso\b/i)).toBeNull();
  });
});

// D1 del recorrido funcional (bitacora 2026-10-25-recorrido-funcional.md): si la carpeta abierta no viene en la lista, el
// Select caia en la primera opcion, mostraba una carpeta que no era la de la sesion y elegirla no hacia nada.
describe("SelectorCaso, carpeta abierta fuera de la lista", () => {
  test("muestra la carpeta abierta aunque no esté en la lista, y elegir otra llama alElegir con su nombre real", async () => {
    const usuario = userEvent.setup();
    const alElegir = vi.fn();
    const actual = { nombre: "silice.db", ruta_relativa: "data/silice.db" } as never;
    const demo = { nombre: "demo.db", ruta_relativa: "data/demo.db" } as never;
    render(<SelectorCaso casos={{ actual, casos: [demo] }} puedeCambiar ocupado={false} alElegir={alElegir} />);
    const selector = screen.getByRole("combobox", { name: "Carpeta de trabajo" });
    expect(selector).toHaveValue("silice.db");
    expect((selector as HTMLSelectElement).selectedOptions[0].textContent).toBe("silice");
    expect(screen.getAllByRole("option").map((o) => o.textContent)).toEqual(["silice", "demo"]);
    await usuario.selectOptions(selector, "demo.db");
    expect(alElegir).toHaveBeenCalledWith("demo.db");
  });

  test("con la carpeta abierta en la lista no la repite", () => {
    const a = { nombre: "demo.db", ruta_relativa: "data/demo.db" } as never;
    const b = { nombre: "obra.db", ruta_relativa: "data/obra.db" } as never;
    render(<SelectorCaso casos={{ actual: b, casos: [a, b] }} puedeCambiar ocupado={false} alElegir={() => {}} />);
    expect(screen.getAllByRole("option").map((o) => o.textContent)).toEqual(["demo", "obra"]);
    expect(screen.getByRole("combobox", { name: "Carpeta de trabajo" })).toHaveValue("obra.db");
  });
});

describe("SelectorCaso, extensión", () => {
  test("las opciones se ven sin .db y conservan el nombre real como valor", () => {
    const a = { nombre: "demo.db", ruta_relativa: "data/demo.db" } as never;
    const b = { nombre: "obra.v2.db", ruta_relativa: "data/obra.v2.db" } as never;
    render(<SelectorCaso casos={{ actual: a, casos: [a, b] }} puedeCambiar ocupado={false} alElegir={() => {}} />);
    const opciones = screen.getAllByRole("option");
    expect(opciones.map((o) => o.textContent)).toEqual(["demo", "obra.v2"]);
    expect(opciones.map((o) => (o as HTMLOptionElement).value)).toEqual(["demo.db", "obra.v2.db"]);
  });
});

// El pie «Sesión de …» del menú lateral pasó a la capa: lo prueban MenuEnCapa.test.tsx («con nombre muestra la sesion al pie;
// sin nombre no», «sin nombre no hay pie de sesion») y Shell.test.tsx («la capa trae al pie quién tiene la sesión»).
