import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RielLateral } from "./RielLateral";
import type { CifrasDeRiel, OpcionDeRiel } from "./RielLateral";
import { iconoDeOpcion } from "./riel";

// Con `css: false` el `?raw` de un .scss llega vacío: se lee con el módulo de Node (como BarraLateral.test.tsx).
interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (
  globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }
).process;
const leer = (ruta: string) => nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/${ruta}`, "utf-8");

const OPCIONES: OpcionDeRiel[] = [
  { id: "vista-general", texto: "Inicio", icono: iconoDeOpcion("vista-general"), ruta: "/inicio/general", actual: true, cuenta: 4, detalle: "4 por hacer" },
  { id: "precios", texto: "Precios y catálogo", icono: iconoDeOpcion("precios"), ruta: "/precios/listas" },
];

const CIFRAS: CifrasDeRiel = {
  titulo: "La obra en cifras",
  filas: [
    { id: "bloquean", texto: "2 bloquean", valor: 2, gravedad: "error", ruta: "/inicio/pendientes" },
    { id: "avisos", texto: "1 aviso", valor: 1, gravedad: "advertencia", ruta: "/inicio/pendientes" },
  ],
};

interface Opciones {
  reducida?: boolean;
  alAlternar?: () => void;
  cifras?: CifrasDeRiel;
  carpeta?: { nombre: string; rutaDeCambio?: string };
  opciones?: OpcionDeRiel[];
}

function pintar({ reducida = false, alAlternar = vi.fn(), cifras, carpeta, opciones = OPCIONES }: Opciones = {}) {
  return render(
    <MemoryRouter>
      <RielLateral lugar="Obras y espacios" reducida={reducida} alAlternar={alAlternar} opciones={opciones} cifras={cifras} carpeta={carpeta}>
        <a href="/obra/uno">Una obra</a>
      </RielLateral>
    </MemoryRouter>,
  );
}

afterEach(() => window.localStorage.clear());

describe("RielLateral: la barra ampliada", () => {
  it("es el complementario «Barra lateral», con su nav y las opciones como enlaces con icono y texto", () => {
    pintar();
    const barra = screen.getByRole("complementary", { name: "Barra lateral" });
    expect(barra).toHaveAttribute("data-collapsed", "false");
    const nav = within(barra).getByRole("navigation", { name: "Obras y espacios" });
    const enlaces = within(nav).getAllByRole("link");
    expect(enlaces.map((e) => e.getAttribute("href"))).toEqual(["/inicio/general", "/precios/listas", "/obra/uno"]);
    expect(within(nav).getByText("Precios y catálogo")).toBeVisible();
    expect(enlaces[1]!.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });

  it("la opción actual lleva aria-current=page y las demás no", () => {
    pintar();
    expect(screen.getByRole("link", { name: "Inicio, 4 por hacer" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Precios y catálogo" })).not.toHaveAttribute("aria-current");
  });

  it("el nombre del lugar está en la cabecera y el botón dice que reduce a iconos", () => {
    pintar();
    const barra = screen.getByRole("complementary", { name: "Barra lateral" });
    expect(within(barra).getByText("Obras y espacios", { selector: "span" })).toBeVisible();
    const boton = within(barra).getByRole("button", { name: "Reducir a iconos" });
    expect(boton).toHaveAttribute("aria-expanded", "true");
    expect(boton).toHaveAttribute("title", "Reducir a iconos (Ctrl+B)");
  });

  it("pulsar el botón avisa para reducir", async () => {
    const alAlternar = vi.fn();
    pintar({ alAlternar });
    await userEvent.setup().click(screen.getByRole("button", { name: "Reducir a iconos" }));
    expect(alAlternar).toHaveBeenCalledTimes(1);
  });
});

describe("RielLateral: la barra reducida a iconos", () => {
  it("el botón dice «Mostrar» y «Ampliar la barra», y aria-expanded es falso", () => {
    pintar({ reducida: true });
    const barra = screen.getByRole("complementary", { name: "Barra lateral" });
    expect(barra).toHaveAttribute("data-collapsed", "true");
    const boton = within(barra).getByRole("button", { name: "Ampliar la barra" });
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(boton).toHaveAttribute("title", "Ampliar la barra (Ctrl+B)");
  });

  it("cada opción conserva su nombre accesible y su title, aunque no se vea el texto; el contenido propio no se pinta", () => {
    pintar({ reducida: true });
    const vista = screen.getByRole("link", { name: "Inicio, 4 por hacer" });
    expect(vista).toHaveAttribute("aria-current", "page");
    expect(vista).toHaveAttribute("title", "Inicio (4 por hacer)");
    expect(within(vista).queryByText("Inicio")).toBeNull();
    const precios = screen.getByRole("link", { name: "Precios y catálogo" });
    expect(precios).toHaveAttribute("title", "Precios y catálogo");
    expect(precios.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    expect(screen.queryByRole("link", { name: "Una obra" })).toBeNull();
  });

  it("el contador pasa a un número sobre el icono, sin repetirlo a los lectores de pantalla", () => {
    pintar({ reducida: true });
    const vista = screen.getByRole("link", { name: "Inicio, 4 por hacer" });
    const insignia = vista.querySelector(".silice-marco-lateral__insignia");
    expect(insignia).toHaveTextContent("4");
    expect(insignia).toHaveAttribute("aria-hidden", "true");
  });

  it("el botón conserva el foco al reducir y al ampliar (es el mismo elemento)", async () => {
    function Con() {
      const [reducida, setReducida] = useState(false);
      return (
        <MemoryRouter>
          <RielLateral lugar="Obras" reducida={reducida} alAlternar={() => setReducida((r) => !r)} opciones={OPCIONES} />
        </MemoryRouter>
      );
    }
    const u = userEvent.setup();
    render(<Con />);
    screen.getByRole("button", { name: "Reducir a iconos" }).focus();
    await u.keyboard("{Enter}");
    expect(screen.getByRole("button", { name: "Ampliar la barra" })).toHaveFocus();
    await u.keyboard("{Enter}");
    expect(screen.getByRole("button", { name: "Reducir a iconos" })).toHaveFocus();
  });

  it("si el foco estaba en lo que desaparece, pasa al botón y no al cuerpo del documento", () => {
    const alternar = vi.fn();
    const { rerender } = render(
      <MemoryRouter>
        <RielLateral lugar="Obras" reducida={false} alAlternar={alternar} opciones={OPCIONES}>
          <a href="/obra/uno">Una obra</a>
        </RielLateral>
      </MemoryRouter>,
    );
    screen.getByRole("link", { name: "Una obra" }).focus();
    rerender(
      <MemoryRouter>
        <RielLateral lugar="Obras" reducida alAlternar={alternar} opciones={OPCIONES}>
          <a href="/obra/uno">Una obra</a>
        </RielLateral>
      </MemoryRouter>,
    );
    expect(screen.getByRole("button", { name: "Ampliar la barra" })).toHaveFocus();
  });
});

// El estado reducido lo gobierna quien monta la barra (el marco, con su clave `silice_sidebar_collapsed`): el riel no guarda nada propio.
describe("RielLateral: no guarda nada en el navegador", () => {
  it("al reducir y ampliar solo avisa; no escribe ninguna clave", async () => {
    const alAlternar = vi.fn();
    pintar({ alAlternar });
    await userEvent.setup().click(screen.getByRole("button", { name: "Reducir a iconos" }));
    expect(alAlternar).toHaveBeenCalledTimes(1);
    expect(window.localStorage.length).toBe(0);
  });
});

describe("RielLateral: «La obra en cifras»", () => {
  it("sin cifras no hay tarjeta", () => {
    pintar();
    expect(screen.queryByRole("heading", { name: "La obra en cifras" })).toBeNull();
  });

  it("ampliada, cada cifra dice su gravedad con palabra y enlaza a su pantalla", () => {
    pintar({ cifras: CIFRAS });
    const tarjeta = screen.getByRole("region", { name: "La obra en cifras" });
    const filas = within(tarjeta).getAllByRole("link");
    expect(filas.map((f) => f.textContent)).toEqual(["2 bloquean", "1 aviso"]);
    expect(filas.map((f) => f.getAttribute("href"))).toEqual(["/inicio/pendientes", "/inicio/pendientes"]);
    expect(filas.map((f) => f.getAttribute("data-gravedad"))).toEqual(["error", "advertencia"]);
    for (const fila of filas) expect(fila.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });

  it("puede traer su propio renglón de avance debajo de las cifras", () => {
    render(
      <MemoryRouter>
        <RielLateral lugar="Obras" reducida={false} alAlternar={vi.fn()} opciones={OPCIONES} cifras={{ ...CIFRAS, extra: <p>Avance 62,5 %</p> }} />
      </MemoryRouter>,
    );
    expect(within(screen.getByRole("region", { name: "La obra en cifras" })).getByText("Avance 62,5 %")).toBeVisible();
  });

  it("reducida, las cifras pasan a un número sobre el icono y su nombre accesible conserva la palabra", () => {
    pintar({ reducida: true, cifras: CIFRAS });
    const lista = screen.getByRole("list", { name: "La obra en cifras" });
    const filas = within(lista).getAllByRole("link");
    expect(filas.map((f) => f.getAttribute("aria-label"))).toEqual(["2 bloquean", "1 aviso"]);
    expect(filas.map((f) => f.querySelector(".silice-marco-lateral__insignia")?.textContent)).toEqual(["2", "1"]);
    expect(filas.map((f) => f.getAttribute("data-gravedad"))).toEqual(["error", "advertencia"]);
    expect(screen.queryByRole("heading", { name: "La obra en cifras" })).toBeNull();
  });
});

describe("RielLateral: la carpeta abierta al pie", () => {
  it("ampliada dice su nombre y ofrece Cambiar", () => {
    pintar({ carpeta: { nombre: "Obras 2026", rutaDeCambio: "/cuenta/carpetas" } });
    const pie = screen.getByRole("group", { name: "Carpeta abierta" });
    expect(within(pie).getByText("Obras 2026")).toBeVisible();
    expect(within(pie).getByRole("link", { name: "Cambiar" })).toHaveAttribute("href", "/cuenta/carpetas");
  });

  it("sin permiso para cambiar de carpeta no hay Cambiar", () => {
    pintar({ carpeta: { nombre: "Obras 2026" } });
    expect(screen.getByText("Obras 2026")).toBeVisible();
    expect(screen.queryByRole("link", { name: "Cambiar" })).toBeNull();
  });

  it("reducida es un icono con su nombre accesible, que lleva a cambiarla si se puede", () => {
    pintar({ reducida: true, carpeta: { nombre: "Obras 2026", rutaDeCambio: "/cuenta/carpetas" } });
    const enlace = screen.getByRole("link", { name: "Carpeta abierta: Obras 2026. Cambiar" });
    expect(enlace).toHaveAttribute("href", "/cuenta/carpetas");
    expect(enlace).toHaveAttribute("title", "Obras 2026");
  });
});

describe("RielLateral: la hoja de estilos", () => {
  const hoja = () => leer("marco/BarraLateral.scss");

  it("mide 14,75 rem abierta y 3,5 rem reducida, con el fondo y el filete del tema", () => {
    const fuente = hoja();
    const base = /\.silice-marco-lateral\s*\{([^}]*)\}/.exec(fuente)?.[1] ?? "";
    expect(base).toMatch(/inline-size:\s*14\.75rem/);
    expect(base).toMatch(/background-color:\s*var\(--silice-lateral\)/);
    expect(fuente).toMatch(/\.silice-marco-lateral--colapsada\s*\{[^}]*inline-size:\s*3\.5rem/);
    expect(fuente).toMatch(/border-inline-end(-color)?:[^;]*var\(--silice-linea\)/);
  });

  it("la opción actual va en el resaltador y en peso 500, no solo en color", () => {
    const fuente = hoja();
    const actual = /\.silice-marco-lateral--riel \.silice-marco-lateral__fila\s*\{[\s\S]*?&\[aria-current="page"\]\s*\{([^}]*)\}/.exec(fuente)?.[1] ?? "";
    expect(actual).toMatch(/background-color:\s*var\(--silice-resaltador\)/);
    expect(actual).toMatch(/font-weight:\s*500/);
  });

  it("las filas miden 2,25 rem con radio de 6 px y la tarjeta usa la hoja y el filete", () => {
    const fuente = hoja();
    expect(fuente).toMatch(/\.silice-marco-lateral--riel \.silice-marco-lateral__fila\s*\{[^}]*min-block-size:\s*2\.25rem/);
    expect(fuente).toMatch(/\.silice-marco-lateral--riel \.silice-marco-lateral__fila\s*\{[^}]*border-radius:\s*0\.375rem/);
    expect(fuente).toMatch(/\.silice-marco-lateral__cifras\s*\{[^}]*background-color:\s*var\(--silice-hoja\)/);
    expect(fuente).toMatch(/\.silice-marco-lateral__cifras\s*\{[^}]*var\(--silice-linea\)/);
  });

  it("la gravedad se pinta con los tokens de error y de advertencia", () => {
    const fuente = hoja();
    expect(fuente).toMatch(/data-gravedad="error"[\s\S]*?var\(--silice-gravedad-error\)/);
    expect(fuente).toMatch(/data-gravedad="advertencia"[\s\S]*?var\(--silice-gravedad-advertencia\)/);
  });

  it("no hay tamaños de letra en px ni colores sueltos", () => {
    const fuente = hoja();
    expect(fuente).not.toMatch(/font-size:\s*[\d.]+px/);
    expect(fuente).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });
});
