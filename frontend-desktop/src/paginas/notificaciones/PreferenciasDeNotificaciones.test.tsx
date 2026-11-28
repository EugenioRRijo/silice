import { fileURLToPath } from "node:url";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import * as sass from "sass";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ErrorDeApi, pedir } from "../../api/cliente";
import PreferenciasDeNotificaciones, { RUTA_DE_PREFERENCIAS } from "./PreferenciasDeNotificaciones";

vi.mock("../../api/cliente", async (importarOriginal) => ({
  ...(await importarOriginal<typeof import("../../api/cliente")>()),
  pedir: vi.fn(),
}));
const pedirFalso = vi.mocked(pedir);

interface Categoria {
  categoria: string;
  titulo: string;
  descripcion: string;
  activa: boolean;
  aplica: boolean;
  obligatoria: boolean;
}

// Las cuatro categorías del servidor (C11b). Cada prueba parte de una copia para poder cambiarla.
const BASE: Categoria[] = [
  {
    categoria: "por_dictaminar",
    titulo: "Versiones por dictaminar",
    descripcion: "Una versión espera su dictamen, con un recordatorio a los 2 días hábiles.",
    activa: true,
    aplica: true,
    obligatoria: false,
  },
  {
    categoria: "dictamen",
    titulo: "Dictamen de sus versiones",
    descripcion: "Una versión que usted envió fue aprobada o devuelta.",
    activa: true,
    aplica: true,
    obligatoria: false,
  },
  {
    categoria: "compras",
    titulo: "Compras por pedir",
    descripcion: "Falta poco para pedir un material de sus obras.",
    activa: true,
    aplica: true,
    obligatoria: false,
  },
  {
    categoria: "listas_de_precios",
    titulo: "Listas de precios nuevas",
    descripcion: "Se cargó una lista o referencia de precios nueva.",
    activa: false,
    aplica: false,
    obligatoria: false,
  },
];

let categorias: Categoria[];
const copia = () => ({ categorias: categorias.map((c) => ({ ...c })) });

function servidorNormal() {
  pedirFalso.mockImplementation(async (ruta: string, opciones?: { metodo?: string; cuerpo?: unknown }) => {
    if (ruta !== "/v1/notificaciones/preferencias") throw new Error(`petición inesperada: ${ruta}`);
    if (opciones?.metodo === "PUT") {
      const { categorias: cambios } = opciones.cuerpo as { categorias: { categoria: string; activa: boolean }[] };
      for (const cambio of cambios) {
        const c = categorias.find((x) => x.categoria === cambio.categoria);
        if (c) c.activa = cambio.activa;
      }
    }
    return copia();
  });
}

beforeEach(() => {
  categorias = BASE.map((c) => ({ ...c }));
  pedirFalso.mockReset();
  servidorNormal();
});

describe("Notificaciones › qué recibir", () => {
  it("dice qué es la pantalla y lista solo las categorías que le aplican, cada una con su interruptor y su frase", async () => {
    render(<PreferenciasDeNotificaciones />);

    const interruptores = await screen.findAllByRole("switch");
    expect(interruptores).toHaveLength(3);
    expect(screen.getByRole("heading", { level: 1, name: "Notificaciones" })).toBeInTheDocument();
    expect(screen.getByText(/Elija qué avisos quiere recibir/)).toBeInTheDocument();
    for (const titulo of ["Versiones por dictaminar", "Dictamen de sus versiones", "Compras por pedir"]) {
      expect(screen.getByRole("switch", { name: titulo })).toBeChecked();
    }
    expect(screen.queryByRole("switch", { name: "Listas de precios nuevas" })).toBeNull();
    expect(screen.queryByText("Se cargó una lista o referencia de precios nueva.")).toBeNull();
    expect(screen.getByText("Falta poco para pedir un material de sus obras.")).toBeInTheDocument();
  });

  it("una categoría apagada se ve apagada", async () => {
    categorias[2]!.activa = false;
    render(<PreferenciasDeNotificaciones />);
    expect(await screen.findByRole("switch", { name: "Compras por pedir" })).not.toBeChecked();
    expect(screen.getByRole("switch", { name: "Dictamen de sus versiones" })).toBeChecked();
  });

  it("la obligatoria se ve encendida y deshabilitada, con su razón en texto", async () => {
    categorias[0]!.obligatoria = true;
    render(<PreferenciasDeNotificaciones />);

    const interruptor = await screen.findByRole("switch", { name: "Versiones por dictaminar" });
    expect(interruptor).toBeChecked();
    expect(interruptor).toBeDisabled();
    expect(screen.getByText("Quien revisa recibe siempre las versiones que esperan su dictamen.")).toBeInTheDocument();
    expect(screen.getByRole("switch", { name: "Compras por pedir" })).toBeEnabled();
  });

  it("apagar una categoría la guarda al momento con el cuerpo exacto y muestra «Guardando…» mientras tanto", async () => {
    let soltar: () => void = () => undefined;
    const base = pedirFalso.getMockImplementation()!;
    pedirFalso.mockImplementation(async (ruta, opciones) => {
      if (opciones?.metodo === "PUT") await new Promise<void>((resolver) => (soltar = resolver));
      return base(ruta, opciones);
    });
    const usuario = userEvent.setup();
    render(<PreferenciasDeNotificaciones />);

    await usuario.click(await screen.findByRole("switch", { name: "Compras por pedir" }));

    expect(pedirFalso).toHaveBeenCalledWith("/v1/notificaciones/preferencias", {
      metodo: "PUT",
      cuerpo: { categorias: [{ categoria: "compras", activa: false }] },
    });
    expect(screen.getByRole("switch", { name: "Compras por pedir" })).not.toBeChecked();
    expect(screen.getByRole("status")).toHaveTextContent("Guardando…");

    soltar();
    await waitFor(() => expect(screen.queryByText("Guardando…")).toBeNull());
    expect(screen.getByRole("switch", { name: "Compras por pedir" })).not.toBeChecked();
    expect(categorias[2]!.activa).toBe(false);
    // Solo se pidió esa categoría: las otras quedan como estaban.
    expect(screen.getByRole("switch", { name: "Dictamen de sus versiones" })).toBeChecked();
  });

  it("encender una apagada manda activa: true", async () => {
    categorias[1]!.activa = false;
    const usuario = userEvent.setup();
    render(<PreferenciasDeNotificaciones />);

    await usuario.click(await screen.findByRole("switch", { name: "Dictamen de sus versiones" }));

    await waitFor(() => expect(categorias[1]!.activa).toBe(true));
    expect(pedirFalso).toHaveBeenCalledWith("/v1/notificaciones/preferencias", {
      metodo: "PUT",
      cuerpo: { categorias: [{ categoria: "dictamen", activa: true }] },
    });
  });

  it("si el servidor rechaza el cambio, el interruptor vuelve atrás y se muestra su detalle", async () => {
    const base = pedirFalso.getMockImplementation()!;
    pedirFalso.mockImplementation(async (ruta, opciones) => {
      if (opciones?.metodo === "PUT") {
        throw new ErrorDeApi(422, "La categoría «por_dictaminar» no se puede apagar para quien revisa.");
      }
      return base(ruta, opciones);
    });
    const usuario = userEvent.setup();
    render(<PreferenciasDeNotificaciones />);

    await usuario.click(await screen.findByRole("switch", { name: "Compras por pedir" }));

    const aviso = await screen.findByRole("alert");
    expect(aviso).toHaveTextContent("La categoría «por_dictaminar» no se puede apagar para quien revisa.");
    expect(screen.getByRole("switch", { name: "Compras por pedir" })).toBeChecked();
    expect(screen.queryByText("Guardando…")).toBeNull();
  });

  it("mientras carga muestra el título con un esqueleto y ninguna categoría", async () => {
    pedirFalso.mockImplementation(() => new Promise(() => undefined));
    render(<PreferenciasDeNotificaciones />);

    expect(screen.getByRole("heading", { level: 1, name: "Notificaciones" })).toBeInTheDocument();
    expect(screen.getByRole("status", { name: "Cargando sus notificaciones" })).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByRole("switch")).toBeNull();
  });

  it("si no carga, dice el detalle del servidor y «Reintentar» vuelve a pedir", async () => {
    let falla = true;
    const base = pedirFalso.getMockImplementation()!;
    pedirFalso.mockImplementation(async (ruta, opciones) => {
      if (falla) throw new ErrorDeApi(500, "El servidor no pudo leer sus preferencias.");
      return base(ruta, opciones);
    });
    const usuario = userEvent.setup();
    render(<PreferenciasDeNotificaciones />);

    expect(await screen.findByRole("alert")).toHaveTextContent("El servidor no pudo leer sus preferencias.");
    expect(screen.queryByRole("switch")).toBeNull();

    falla = false;
    await usuario.click(screen.getByRole("button", { name: "Reintentar" }));

    expect(await screen.findByRole("switch", { name: "Compras por pedir" })).toBeChecked();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("si ninguna categoría le aplica, lo dice y explica cuándo aparecerán", async () => {
    categorias = categorias.map((c) => ({ ...c, aplica: false }));
    render(<PreferenciasDeNotificaciones />);

    const vacio = await screen.findByText("Por ahora no hay avisos que elegir.");
    expect(vacio).toBeInTheDocument();
    expect(screen.getByText(/según los permisos de su cuenta/)).toBeInTheDocument();
    expect(within(vacio.parentElement!).queryByRole("switch")).toBeNull();
  });

  it("la ruta de la pantalla es /cuenta/notificaciones", () => {
    expect(RUTA_DE_PREFERENCIAS).toBe("/cuenta/notificaciones");
  });

  it("el SCSS usa solo tokens --silice-* y ningún font-size en px", () => {
    // En una variable: con el texto literal, Vite reescribe new URL(...) como un recurso y deja de ser file:.
    const relativa = "./PreferenciasDeNotificaciones.scss";
    const ruta = fileURLToPath(new URL(relativa, import.meta.url));
    const css = sass.compile(ruta).css;
    expect(css).toMatch(/silice-pref-notificaciones/);
    expect(css).not.toMatch(/font-size:\s*[\d.]+(px|pt)/);
    expect(css).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(css).not.toMatch(/\brgba?\(/);
  });
});
