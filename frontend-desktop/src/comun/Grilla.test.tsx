import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { Grilla } from "./Grilla";
import type { ColumnaDeGrilla } from "./Grilla";

// Lote B1-2b de la ficha de B1 (§4) y guías de Google `spatial-navigation`, `responsive-table` y `single-line-overflow`.
// Datos ficticios. La máquina de estados vive en logicaGrilla.ts (B1-2a); aquí se prueba el componente que la usa.

interface Fila {
  id: string;
  partida: string;
  descripcion: string;
  cantidad: string;
  total: string;
}

const FILAS: Fila[] = [
  { id: "a", partida: "EXC-01", descripcion: "Excavación manual", cantidad: "10,5", total: "1.050,00" },
  { id: "b", partida: "REL-02", descripcion: "Relleno compactado", cantidad: "20", total: "2.000,00" },
  { id: "c", partida: "ACA-03", descripcion: "Acarreo de material", cantidad: "30", total: "3.000,00" },
];

const COLUMNAS: ColumnaDeGrilla<Fila>[] = [
  { clave: "partida", titulo: "Partida", valor: (f) => f.partida },
  { clave: "descripcion", titulo: "Descripción", valor: (f) => f.descripcion },
  { clave: "cantidad", titulo: "Cantidad", valor: (f) => f.cantidad, numerica: true, editable: true },
  { clave: "total", titulo: "Total", valor: (f) => f.total, numerica: true },
];

function montar(extra: Partial<Parameters<typeof Grilla<Fila>>[0]> = {}) {
  const alEditar = vi.fn();
  const utilidades = render(
    <div>
      <button type="button">antes</button>
      <Grilla<Fila>
        etiqueta="Partidas"
        columnas={COLUMNAS}
        filas={FILAS}
        idDeFila={(f) => f.id}
        alEditar={alEditar}
        {...extra}
      />
      <button type="button">despues</button>
    </div>,
  );
  return { alEditar, ...utilidades };
}

const celda = (nombre: string) => screen.getByRole("gridcell", { name: nombre });
const tabindexes = () =>
  [...document.querySelectorAll<HTMLElement>("[data-celda]")].map((c) => c.getAttribute("tabindex"));

let acercar: ReturnType<typeof vi.fn>;
beforeEach(() => {
  acercar = vi.fn();
  Element.prototype.scrollIntoView = acercar as unknown as typeof Element.prototype.scrollIntoView;
});
afterEach(() => {
  delete (Element.prototype as { scrollIntoView?: unknown }).scrollIntoView;
});

describe("semántica de la tabla", () => {
  test("es una table role=grid con nombre, th scope=col por columna y th scope=row en la primera columna", () => {
    montar();
    const grilla = screen.getByRole("grid", { name: "Partidas" });
    expect(grilla.tagName).toBe("TABLE");
    const cabeceras = within(grilla).getAllByRole("columnheader");
    expect(cabeceras.map((c) => c.textContent)).toEqual(["Partida", "Descripción", "Cantidad", "Total"]);
    for (const c of cabeceras) {
      expect(c.tagName).toBe("TH");
      expect(c.getAttribute("scope")).toBe("col");
    }
    const filas = within(grilla).getAllByRole("rowheader");
    expect(filas.map((c) => c.textContent)).toEqual(["EXC-01", "REL-02", "ACA-03"]);
    for (const c of filas) {
      expect(c.tagName).toBe("TH");
      expect(c.getAttribute("scope")).toBe("row");
    }
    expect(within(grilla).getAllByRole("gridcell")).toHaveLength(9);
  });

  test("las cifras van a la derecha, y el pie se dibuja en un tfoot", () => {
    montar({ pie: <tr><td>Total sin IVA</td></tr> });
    expect(celda("10,5").classList.contains("silice-grilla__celda--numerica")).toBe(true);
    expect(celda("Relleno compactado").classList.contains("silice-grilla__celda--numerica")).toBe(false);
    const pie = screen.getByText("Total sin IVA").closest("tfoot");
    expect(pie).not.toBeNull();
  });

  test("la fila elegida lleva aria-selected y su clase", () => {
    montar({ filaElegida: "b" });
    const filaB = screen.getByText("REL-02").closest("tr");
    expect(filaB?.getAttribute("aria-selected")).toBe("true");
    expect(filaB?.classList.contains("silice-grilla__fila--elegida")).toBe(true);
    expect(screen.getByText("EXC-01").closest("tr")?.getAttribute("aria-selected")).toBe("false");
  });
});

describe("una sola parada de Tab con tabindex itinerante", () => {
  test("una celda con tabindex 0 y el resto con -1", () => {
    montar();
    const t = tabindexes();
    expect(t.filter((x) => x === "0")).toHaveLength(1);
    expect(t.filter((x) => x === "-1")).toHaveLength(11);
    expect(t[0]).toBe("0");
  });

  test("Tab entra a la celda activa y el siguiente Tab sale de la grilla", async () => {
    const u = userEvent.setup();
    montar();
    await u.tab();
    await u.tab();
    expect(document.activeElement).toBe(screen.getByText("EXC-01"));
    await u.tab();
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "despues" }));
  });

  test("al moverse con flechas el tabindex 0 viaja con el foco", async () => {
    const u = userEvent.setup();
    montar();
    await u.tab();
    await u.tab();
    await u.keyboard("{ArrowRight}{ArrowDown}");
    expect(document.activeElement).toBe(celda("Relleno compactado"));
    const t = tabindexes();
    expect(t.filter((x) => x === "0")).toHaveLength(1);
    expect(celda("Relleno compactado").getAttribute("tabindex")).toBe("0");
    expect(screen.getByText("EXC-01").getAttribute("tabindex")).toBe("-1");
  });

  test("hacer clic en una celda la vuelve la activa", async () => {
    const u = userEvent.setup();
    montar();
    await u.click(celda("3.000,00"));
    expect(celda("3.000,00").getAttribute("tabindex")).toBe("0");
    expect(tabindexes().filter((x) => x === "0")).toHaveLength(1);
  });

  test("una grilla sin filas no tiene ninguna parada de Tab", () => {
    montar({ filas: [] });
    expect(document.querySelectorAll("[data-celda]")).toHaveLength(0);
  });

  test("si las filas se reducen, la celda activa queda dentro de la grilla", async () => {
    const u = userEvent.setup();
    const { rerender, alEditar } = montar();
    await u.click(celda("3.000,00"));
    rerender(
      <div>
        <button type="button">antes</button>
        <Grilla<Fila>
          etiqueta="Partidas"
          columnas={COLUMNAS}
          filas={FILAS.slice(0, 1)}
          idDeFila={(f) => f.id}
          alEditar={alEditar}
        />
        <button type="button">despues</button>
      </div>,
    );
    expect(tabindexes().filter((x) => x === "0")).toHaveLength(1);
    expect(celda("1.050,00").getAttribute("tabindex")).toBe("0");
  });
});

describe("flechas: no se previene lo que no se consume", () => {
  test("una flecha que mueve la celda llama a preventDefault; la del borde, no", async () => {
    const u = userEvent.setup();
    montar();
    await u.tab();
    await u.tab();
    const inicio = screen.getByText("EXC-01");
    expect(fireEvent.keyDown(inicio, { key: "ArrowLeft" })).toBe(true);
    expect(fireEvent.keyDown(inicio, { key: "ArrowUp" })).toBe(true);
    expect(document.activeElement).toBe(inicio);
    expect(fireEvent.keyDown(inicio, { key: "ArrowRight" })).toBe(false);
    expect(document.activeElement).toBe(celda("Excavación manual"));
  });

  test("en el último borde tampoco se previene ni se mueve", async () => {
    const u = userEvent.setup();
    montar();
    await u.click(celda("3.000,00"));
    expect(fireEvent.keyDown(celda("3.000,00"), { key: "ArrowDown" })).toBe(true);
    expect(fireEvent.keyDown(celda("3.000,00"), { key: "ArrowRight" })).toBe(true);
    expect(document.activeElement).toBe(celda("3.000,00"));
  });

  test("con Ctrl, Alt o Meta no se intercepta nada", async () => {
    const u = userEvent.setup();
    montar();
    await u.tab();
    await u.tab();
    const inicio = screen.getByText("EXC-01");
    for (const mod of [{ ctrlKey: true }, { altKey: true }, { metaKey: true }]) {
      expect(fireEvent.keyDown(inicio, { key: "ArrowRight", ...mod })).toBe(true);
    }
    expect(document.activeElement).toBe(inicio);
  });

  test("si el evento ya venía prevenido, no se intercepta", async () => {
    const u = userEvent.setup();
    montar();
    await u.tab();
    await u.tab();
    const inicio = screen.getByText("EXC-01");
    const tabla = screen.getByRole("grid");
    tabla.addEventListener("keydown", (e) => e.preventDefault());
    fireEvent.keyDown(inicio, { key: "ArrowRight" });
    expect(document.activeElement).toBe(inicio);
  });

  test("Tab nunca se previene en navegación", async () => {
    const u = userEvent.setup();
    montar();
    await u.tab();
    await u.tab();
    expect(fireEvent.keyDown(screen.getByText("EXC-01"), { key: "Tab" })).toBe(true);
  });

  test("Inicio y Fin saltan a los extremos de la fila", async () => {
    const u = userEvent.setup();
    montar();
    await u.click(celda("Relleno compactado"));
    await u.keyboard("{End}");
    expect(document.activeElement).toBe(celda("2.000,00"));
    await u.keyboard("{Home}");
    expect(document.activeElement).toBe(screen.getByText("REL-02"));
  });

  test("un control dentro de una celda se queda con sus propias teclas", async () => {
    const u = userEvent.setup();
    montar({
      columnas: [
        ...COLUMNAS.slice(0, 3),
        { clave: "total", titulo: "Total", valor: (f) => f.total, render: () => <button type="button">Abrir</button> },
      ],
    });
    await u.click(celda("10,5"));
    const boton = screen.getAllByRole("button", { name: "Abrir" })[0]!;
    boton.focus();
    expect(fireEvent.keyDown(boton, { key: "ArrowLeft" })).toBe(true);
    expect(document.activeElement).toBe(boton);
  });

  test("al mover el foco se acerca la celda con block y inline nearest", async () => {
    const u = userEvent.setup();
    montar();
    await u.tab();
    await u.tab();
    acercar.mockClear();
    await u.keyboard("{ArrowDown}");
    expect(acercar).toHaveBeenCalledTimes(1);
    expect(acercar).toHaveBeenCalledWith({ block: "nearest", inline: "nearest" });
  });
});

describe("edición de celdas", () => {
  test("F2 abre el campo con el valor, solo en columnas editables", async () => {
    const u = userEvent.setup();
    const { alEditar } = montar();
    await u.click(celda("Excavación manual"));
    await u.keyboard("{F2}");
    expect(screen.queryByRole("textbox")).toBeNull();
    await u.click(celda("10,5"));
    await u.keyboard("{F2}");
    const campo = screen.getByRole("textbox", { name: "Cantidad, EXC-01" });
    expect((campo as HTMLInputElement).value).toBe("10,5");
    expect(document.activeElement).toBe(campo);
    expect(alEditar).not.toHaveBeenCalled();
  });

  test("Enter confirma con el valor nuevo, avisa una vez y baja a la fila siguiente", async () => {
    const u = userEvent.setup();
    const { alEditar } = montar();
    await u.click(celda("10,5"));
    await u.keyboard("{Enter}");
    const campo = screen.getByRole("textbox");
    await u.clear(campo);
    await u.type(campo, "12,5");
    await u.keyboard("{Enter}");
    expect(alEditar).toHaveBeenCalledTimes(1);
    expect(alEditar).toHaveBeenCalledWith("a", "cantidad", "12,5");
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(document.activeElement).toBe(celda("20"));
  });

  test("Esc restaura el original, no avisa y devuelve el foco a la celda", async () => {
    const u = userEvent.setup();
    const { alEditar } = montar();
    await u.click(celda("10,5"));
    await u.keyboard("{F2}");
    await u.keyboard("99");
    await u.keyboard("{Escape}");
    expect(alEditar).not.toHaveBeenCalled();
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(celda("10,5")).toBeTruthy();
    expect(document.activeElement).toBe(celda("10,5"));
  });

  test("confirmar sin cambiar el valor no avisa", async () => {
    const u = userEvent.setup();
    const { alEditar } = montar();
    await u.click(celda("10,5"));
    await u.keyboard("{F2}{Enter}");
    expect(alEditar).not.toHaveBeenCalled();
  });

  test("escribir un carácter en una celda editable empieza a editar con ese carácter, como Excel", async () => {
    const u = userEvent.setup();
    const { alEditar } = montar();
    await u.click(celda("10,5"));
    await u.keyboard("7");
    const campo = screen.getByRole("textbox") as HTMLInputElement;
    expect(campo.value).toBe("7");
    await u.keyboard("5{Enter}");
    expect(alEditar).toHaveBeenCalledWith("a", "cantidad", "75");
  });

  test("escribir en una celda que no se edita no hace nada", async () => {
    const u = userEvent.setup();
    montar();
    await u.click(celda("Excavación manual"));
    await u.keyboard("7");
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  test("en edición el campo se queda las flechas, Inicio y Fin", async () => {
    const u = userEvent.setup();
    montar();
    await u.click(celda("10,5"));
    await u.keyboard("{F2}");
    const campo = screen.getByRole("textbox");
    for (const key of ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"]) {
      expect(fireEvent.keyDown(campo, { key })).toBe(true);
    }
    expect(screen.getByRole("textbox")).toBe(campo);
    expect(document.activeElement).toBe(campo);
  });

  test("Tab en edición confirma y deja que el navegador siga su camino fuera de la grilla", async () => {
    const u = userEvent.setup();
    const { alEditar } = montar();
    await u.click(celda("10,5"));
    await u.keyboard("{F2}");
    await u.clear(screen.getByRole("textbox"));
    await u.keyboard("11");
    await u.tab();
    expect(alEditar).toHaveBeenCalledWith("a", "cantidad", "11");
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "despues" }));
  });

  test("hacer clic en otra celda mientras se edita confirma la edición", async () => {
    const u = userEvent.setup();
    const { alEditar } = montar();
    await u.click(celda("10,5"));
    await u.keyboard("{F2}");
    await u.clear(screen.getByRole("textbox"));
    await u.keyboard("8");
    await u.click(celda("Acarreo de material"));
    expect(alEditar).toHaveBeenCalledWith("a", "cantidad", "8");
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  test("sin alEditar las celdas no se editan (solo lectura)", async () => {
    const u = userEvent.setup();
    render(<Grilla<Fila> etiqueta="Partidas" columnas={COLUMNAS} filas={FILAS} idDeFila={(f) => f.id} />);
    await u.click(celda("10,5"));
    await u.keyboard("{F2}");
    expect(screen.queryByRole("textbox")).toBeNull();
  });
});

describe("avisos de la celda activa", () => {
  test("alActivar recibe el id de la fila y la clave de la columna al moverse, no al montar", async () => {
    const u = userEvent.setup();
    const alActivar = vi.fn();
    montar({ alActivar });
    expect(alActivar).not.toHaveBeenCalled();
    await u.click(celda("10,5"));
    expect(alActivar).toHaveBeenLastCalledWith("a", "cantidad");
    await u.keyboard("{ArrowDown}");
    expect(alActivar).toHaveBeenLastCalledWith("b", "cantidad");
  });
});

describe("estilos de la grilla (guías responsive-table y single-line-overflow, escala de z-index)", () => {
  interface Fs {
    readFileSync(ruta: string, codificacion: string): string;
  }
  const nodo = (
    globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }
  ).process;
  const fs = nodo.getBuiltinModule("node:fs");
  const scss = () => fs.readFileSync(`${nodo.cwd()}/src/comun/Grilla.scss`, "utf-8");
  const tokens = () => fs.readFileSync(`${nodo.cwd()}/src/estilos/tokens.scss`, "utf-8");

  test("las cabeceras de columna y de fila son sticky", () => {
    expect(scss()).toMatch(/thead\s+th[^{]*\{[^}]*position:\s*sticky/);
    expect(scss()).toMatch(/tbody\s+th[^{]*\{[^}]*position:\s*sticky/);
  });

  test("las celdas de una línea usan overflow: hidden con puntos suspensivos, nunca clip", () => {
    expect(scss()).toMatch(/overflow:\s*hidden/);
    expect(scss()).toMatch(/text-overflow:\s*ellipsis/);
    expect(scss()).toMatch(/white-space:\s*nowrap/);
    expect(scss()).not.toMatch(/overflow:\s*clip/);
    expect(scss()).toMatch(/table-layout:\s*fixed/);
  });

  test("se adapta con @container y no con @media de ancho", () => {
    expect(scss()).toMatch(/container-type:\s*inline-size/);
    expect(scss()).toMatch(/@container/);
    expect(scss()).not.toMatch(/@media\s*\(\s*(min|max)-width/);
  });

  test("la cara: filetes, cabecera, fila elegida con raya de 2 px y cifras tabulares, solo con tokens", () => {
    const s = scss();
    expect(s).toMatch(/var\(--silice-linea\)/);
    expect(s).toMatch(/var\(--silice-hoja\)/);
    expect(s).toMatch(/var\(--silice-resaltador\)/);
    expect(s).toMatch(/inset\s+2px\s+0\s+0\s+var\(--silice-resaltador-borde\)/);
    expect(s).toMatch(/__celda--numerica\s*\{[^}]*text-align:\s*right[^}]*font-variant-numeric:\s*tabular-nums/);
    expect(s).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(s).not.toMatch(/rgba?\(/);
  });

  test("el foco de la celda se ve y los z-index salen de la escala de tokens", () => {
    const s = scss();
    expect(s).toMatch(/:focus-visible/);
    expect(s).toMatch(/var\(--silice-z-celda-fija\)/);
    expect(s).toMatch(/var\(--silice-z-cabecera-grilla\)/);
    expect(s).not.toMatch(/z-index:\s*\d/);
  });

  test("tokens.scss define la escala: celda fija, cabecera de la grilla, cabecera de la obra y panel, en orden", () => {
    const t = tokens();
    const valor = (nombre: string) => Number(new RegExp(`--silice-z-${nombre}:\\s*(\\d+)`).exec(t)?.[1]);
    const escala = ["celda-fija", "cabecera-grilla", "cabecera-obra", "panel"].map(valor);
    expect(escala.every((n) => Number.isFinite(n))).toBe(true);
    expect([...escala].sort((a, b) => a - b)).toEqual(escala);
    expect(new Set(escala).size).toBe(4);
  });
});

describe("abrir la fila (alAbrir, B1-10)", () => {
  test("Enter sobre una celda que no se edita abre la fila con su id, la columna y la celda, y consume la tecla", async () => {
    const alAbrir = vi.fn();
    montar({ alAbrir });
    const u = userEvent.setup();
    const descripcion = celda("Excavación manual");
    descripcion.focus();
    await u.keyboard("{Enter}");
    expect(alAbrir).toHaveBeenCalledTimes(1);
    expect(alAbrir).toHaveBeenCalledWith("a", "descripcion", descripcion);
  });

  test("Enter sobre una celda editable edita en lugar de abrir", async () => {
    const alAbrir = vi.fn();
    montar({ alAbrir });
    const u = userEvent.setup();
    celda("10,5").focus();
    await u.keyboard("{Enter}");
    expect(alAbrir).not.toHaveBeenCalled();
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  test("con un modificador o con la tecla ya consumida no abre nada", async () => {
    const alAbrir = vi.fn();
    montar({ alAbrir });
    const u = userEvent.setup();
    celda("Excavación manual").focus();
    await u.keyboard("{Control>}{Enter}{/Control}");
    await u.keyboard("{Alt>}{Enter}{/Alt}");
    expect(alAbrir).not.toHaveBeenCalled();
  });

  test("el doble clic sobre una celda abre la fila, salvo que algo dentro ya lo atendiera", async () => {
    const alAbrir = vi.fn();
    const columnas: ColumnaDeGrilla<Fila>[] = [
      ...COLUMNAS.slice(0, 3),
      {
        clave: "total",
        titulo: "Total",
        valor: (f) => f.total,
        render: (f) => (
          <span
            onDoubleClick={(e) => {
              e.preventDefault();
            }}
          >
            {f.total}
          </span>
        ),
      },
    ];
    montar({ alAbrir, columnas });
    const u = userEvent.setup();
    await u.dblClick(celda("Relleno compactado"));
    expect(alAbrir).toHaveBeenCalledTimes(1);
    expect(alAbrir).toHaveBeenCalledWith("b", "descripcion", celda("Relleno compactado"));
    await u.dblClick(screen.getByText("3.000,00"));
    expect(alAbrir).toHaveBeenCalledTimes(1);
  });

  test("sin alAbrir, Enter sobre una celda que no se edita no hace nada", async () => {
    montar();
    const u = userEvent.setup();
    celda("Excavación manual").focus();
    await u.keyboard("{Enter}");
    expect(screen.queryByRole("textbox")).toBeNull();
  });
});
