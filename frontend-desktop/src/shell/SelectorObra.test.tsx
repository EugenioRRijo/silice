import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../api/cliente";
import type { ProyectoRespuesta } from "../api/tipos";
import { CASA_DEMO, TORRE_B, botonDeObra, estadoInicial, montarShell, servidorFalso, sesionDe } from "./obras/datosDePrueba";
import { SelectorObra } from "./SelectorObra";

// Plan de modulos, MOD-3b: «Obra» en vez de «Carpeta y proyecto» en la barra de Presupuestos y obras (diseno de modulos
// §7 y §12.2). Oraculos escritos a mano: los nombres, clientes y ubicaciones ficticios de `obras/datosDePrueba.tsx`.

const GALPON: ProyectoRespuesta = {
  codigo: "9",
  nombre: "Galpón Norte",
  version_vigente: 2,
  actualizado: null,
  cliente: "Contratista Demo, C.A.",
  ubicacion: "Ciudad Bolívar",
};

type Props = Parameters<typeof SelectorObra>[0];

function pintar(extra: Partial<Props> = {}) {
  const props: Props = {
    obras: [CASA_DEMO, TORRE_B, GALPON],
    elegida: "7",
    enInicio: false,
    carpeta: "silice",
    puedeCambiarCarpeta: true,
    puedeCrearObra: true,
    alElegir: vi.fn(),
    alNuevaObra: vi.fn(),
    alCambiarCarpeta: vi.fn(),
    ...extra,
  };
  render(<SelectorObra {...props} />);
  return props;
}

// Lo que se ve de cada obra de la lista: su nombre (la primera linea del boton).
function nombresDeLaLista(): string[] {
  return within(screen.getByRole("list", { name: "Obras de la carpeta de trabajo" }))
    .getAllByRole("button")
    .map((b) => b.querySelector(".silice-obra__nombre")?.textContent ?? "");
}

describe("SelectorObra", () => {
  test("con «Casa Demo» elegida el botón dice «Obra: Casa Demo» y su nombre accesible pide cambiarla", () => {
    pintar();
    const boton = screen.getByRole("button", { name: "Obra: Casa Demo. Cambiar obra" });
    expect(boton).toHaveTextContent("Obra: Casa Demo");
    expect(boton).toHaveAttribute("aria-expanded", "false");
  });

  test("en el inicio del módulo dice «Todas las obras»", () => {
    pintar({ enInicio: true });
    expect(screen.getByRole("button", { name: /^Todas las obras/ })).toHaveTextContent("Todas las obras");
  });

  test("sin obra elegida dice «Obra: sin elegir»", () => {
    pintar({ elegida: null });
    expect(screen.getByRole("button", { name: /^Obra: sin elegir/ })).toHaveTextContent("Obra: sin elegir");
  });

  test("un nombre de 80 caracteres se recorta por la clase del texto; el nombre accesible y el título lo traen completo", () => {
    const largo = `Obra ${"x".repeat(75)}`;
    expect(largo).toHaveLength(80);
    pintar({ obras: [{ ...CASA_DEMO, nombre: largo }] });
    const boton = screen.getByRole("button", { name: `Obra: ${largo}. Cambiar obra` });
    const texto = boton.querySelector(".silice-obra__texto");
    expect(texto).not.toBeNull();
    expect(texto).toHaveTextContent(`Obra: ${largo}`);
    expect(boton).toHaveAttribute("title", largo);
  });

  test("el panel lista las obras con «cliente · ubicación» debajo y la elegida marcada", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(screen.getByRole("button", { name: /^Obra: / }));
    expect(nombresDeLaLista()).toEqual(["Casa Demo", "Torre B (sin versión guardada)", "Galpón Norte"]);
    const casa = screen.getByRole("button", { name: /^Casa Demo/ });
    expect(casa).toHaveAttribute("aria-current", "true");
    expect(casa).toHaveTextContent("Contratista Demo, C.A. · Maracay");
    expect(screen.getByRole("button", { name: /^Torre B/ })).not.toHaveAttribute("aria-current");
  });

  test("«Buscar obra» filtra por nombre, cliente y ubicación sin distinguir tildes ni mayúsculas", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(screen.getByRole("button", { name: /^Obra: / }));
    const buscar = screen.getByRole("searchbox", { name: "Buscar obra" });
    await u.type(buscar, "maracay");
    expect(nombresDeLaLista()).toEqual(["Casa Demo"]);
    await u.clear(buscar);
    await u.type(buscar, "TORRE");
    expect(nombresDeLaLista()).toEqual(["Torre B (sin versión guardada)"]);
    await u.clear(buscar);
    await u.type(buscar, "galpon");
    expect(nombresDeLaLista()).toEqual(["Galpón Norte"]);
    await u.clear(buscar);
    await u.type(buscar, "bolivar");
    expect(nombresDeLaLista()).toEqual(["Galpón Norte"]);
    await u.clear(buscar);
    await u.type(buscar, "contratista demo");
    expect(nombresDeLaLista()).toEqual(["Casa Demo", "Galpón Norte"]);
    await u.clear(buscar);
    await u.type(buscar, "zzz");
    expect(screen.getByText("Ninguna obra coincide con «zzz».")).toBeInTheDocument();
  });

  test("elegir una obra avisa con su código y cierra el panel con el foco en el botón", async () => {
    const u = userEvent.setup();
    const props = pintar();
    const boton = screen.getByRole("button", { name: /^Obra: / });
    await u.click(boton);
    await u.click(screen.getByRole("button", { name: /^Torre B/ }));
    expect(props.alElegir).toHaveBeenCalledWith("8");
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(boton).toHaveFocus();
  });

  test("Esc cierra el panel y devuelve el foco al botón", async () => {
    const u = userEvent.setup();
    pintar();
    const boton = screen.getByRole("button", { name: /^Obra: / });
    await u.click(boton);
    await u.keyboard("{Escape}");
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("searchbox", { name: "Buscar obra" })).not.toBeInTheDocument();
    expect(boton).toHaveFocus();
  });

  test("al pie: «Carpeta: silice · Cambiar carpeta…», «Nueva obra» y el hueco para lo que venga", async () => {
    const u = userEvent.setup();
    const props = pintar({ pie: <p>Hueco del pie</p> });
    await u.click(screen.getByRole("button", { name: /^Obra: / }));
    const panel = screen.getByRole("region", { name: "Obra" });
    expect(within(panel).getByText("Carpeta: silice")).toBeInTheDocument();
    expect(within(panel).getByText("Hueco del pie")).toBeInTheDocument();
    await u.click(within(panel).getByRole("button", { name: "Nueva obra" }));
    expect(props.alNuevaObra).toHaveBeenCalled();
    await u.click(screen.getByRole("button", { name: /^Obra: / }));
    await u.click(screen.getByRole("button", { name: "Cambiar carpeta…" }));
    expect(props.alCambiarCarpeta).toHaveBeenCalled();
  });

  test("una carpeta sin obras lo dice y enseña a crear la primera", async () => {
    const u = userEvent.setup();
    pintar({ obras: [], elegida: null });
    await u.click(screen.getByRole("button", { name: /^Obra: / }));
    expect(screen.getByText("Esta carpeta de trabajo aún no tiene obras. Cree la primera con «Nueva obra».")).toBeInTheDocument();
  });

  test("rita (revisa): lista y búsqueda, sin «Nueva obra» ni «Cambiar carpeta…»", async () => {
    const u = userEvent.setup();
    pintar({ puedeCambiarCarpeta: false, puedeCrearObra: false });
    await u.click(screen.getByRole("button", { name: /^Obra: / }));
    expect(screen.getByRole("searchbox", { name: "Buscar obra" })).toBeInTheDocument();
    expect(nombresDeLaLista()).toHaveLength(3);
    expect(screen.queryByRole("button", { name: "Nueva obra" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cambiar carpeta…" })).not.toBeInTheDocument();
    expect(screen.getByText("Carpeta: silice")).toBeInTheDocument();
  });

  test("admin (sin leer obras, con cambiar de carpeta): «Carpeta: silice» y el panel solo trae el pie", async () => {
    const u = userEvent.setup();
    const props = pintar({ obras: null, elegida: null, puedeCrearObra: false });
    const boton = screen.getByRole("button", { name: /^Carpeta: silice/ });
    expect(boton).toHaveTextContent("Carpeta: silice");
    await u.click(boton);
    expect(screen.queryByRole("searchbox", { name: "Buscar obra" })).not.toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Obras de la carpeta de trabajo" })).not.toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: "Cambiar carpeta…" }));
    expect(props.alCambiarCarpeta).toHaveBeenCalled();
  });

  test("sin leer obras ni cambiar de carpeta no se pinta nada", () => {
    const { container } = render(
      <SelectorObra
        obras={null}
        elegida={null}
        enInicio={false}
        carpeta="silice"
        puedeCambiarCarpeta={false}
        puedeCrearObra={false}
        alElegir={vi.fn()}
        alNuevaObra={vi.fn()}
        alCambiarCarpeta={vi.fn()}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  test("ninguna cadena visible del selector dice «caso» ni «proyecto»", async () => {
    const u = userEvent.setup();
    pintar({ pie: undefined });
    await u.click(screen.getByRole("button", { name: /^Obra: / }));
    for (const patron of [/\bcaso\b/i, /\bproyecto\b/i]) {
      expect(screen.queryByText(patron)).toBeNull();
      expect(screen.queryByLabelText(patron)).toBeNull();
      expect(screen.queryByRole("button", { name: patron })).toBeNull();
    }
  });
});

describe("SelectorObra en el armazón", () => {
  let servidor: ReturnType<typeof servidorFalso>;

  beforeEach(() => {
    servidor = servidorFalso();
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    fijarCsrf("tok");
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    fijarCsrf(null);
  });

  test("elegir «Torre B» llama PUT /v1/sesion/proyecto {\"proyecto\":\"8\"} y la barra la muestra", async () => {
    const u = userEvent.setup();
    montarShell(sesionDe("ana"), "/hoja");
    await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
    await u.click(await botonDeObra());
    await u.click(await screen.findByRole("button", { name: /^Torre B/ }));
    await waitFor(() => expect(servidor.de("PUT", "/v1/sesion/proyecto").map((l) => l.cuerpo)).toEqual([{ proyecto: "8" }]));
    expect(await botonDeObra()).toHaveAccessibleName("Obra: Torre B. Cambiar obra");
  });

  test("restaura la obra que la cuenta recuerda: en /hoja dice «Obra: Casa Demo» sin elegir nada", async () => {
    const estado = estadoInicial();
    estado.actual = estado.casos[1]!; // s1.db, la que restauró GET /v1/sesion
    servidor = servidorFalso(estado);
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    montarShell(sesionDe("ana", { eleccion: { caso: "s1.db", proyecto: "7", aviso: null } }), "/hoja");
    await waitFor(async () => expect(await botonDeObra()).toHaveAccessibleName("Obra: Casa Demo. Cambiar obra"));
    expect(servidor.de("PUT", "/v1/sesion/proyecto")).toEqual([]);
  });

  test("el aviso de lo recordado se ve una vez y no vuelve al navegar", async () => {
    const u = userEvent.setup();
    const aviso = "La carpeta de trabajo «vieja» ya no existe; se abrió la de siempre.";
    montarShell(sesionDe("ana", { eleccion: { caso: null, proyecto: null, aviso } }), "/hoja");
    expect(await screen.findByText(aviso)).toBeInTheDocument();
    await u.click(within(screen.getByRole("navigation", { name: "Menú principal" })).getByRole("link", { name: "Inicio" }));
    await screen.findByRole("heading", { level: 1, name: "Inicio de presupuestos y obras" });
    expect(screen.queryByText(aviso)).not.toBeInTheDocument();
    await u.click(await botonDeObra());
    await u.click(await screen.findByRole("button", { name: /^Casa Demo/ }));
    expect(screen.queryByText(aviso)).not.toBeInTheDocument();
  });

  test("en /obras dice «Todas las obras»", async () => {
    montarShell(sesionDe("ana"), "/obras");
    await screen.findByRole("heading", { level: 1, name: "Inicio de presupuestos y obras" });
    expect(await botonDeObra()).toHaveTextContent("Todas las obras");
  });

  test.each([
    ["/libros", "Auditar un presupuesto"],
    ["/existencias", "Existencias de la arenera"],
  ])("en %s (Auditoría y Producción) no hay selector de obra ni de carpeta", async (ruta) => {
    montarShell(sesionDe("ana"), ruta);
    await screen.findByRole("heading", { level: 1 });
    await waitFor(() => expect(servidor.de("GET", "/v1/casos").length).toBeGreaterThan(0));
    const banner = screen.getByRole("banner");
    expect(within(banner).queryByRole("button", { name: /^(Obra: |Todas las obras|Carpeta: |Carpeta de trabajo: )/ })).toBeNull();
  });

  test("admin en Precios de la empresa: «Carpeta: silice» sin pedir la lista de obras", async () => {
    montarShell(sesionDe("admin"), "/precios_empresa");
    await screen.findByRole("heading", { level: 1 });
    expect(await botonDeObra()).toHaveTextContent("Carpeta: silice");
    expect(servidor.de("GET", "/v1/proyectos")).toEqual([]);
  });

  test("rita en el Tablero ve sus obras, sin «Nueva obra» ni «Cambiar carpeta…»", async () => {
    const u = userEvent.setup();
    montarShell(sesionDe("rita"), "/tablero");
    await screen.findByRole("heading", { level: 1 });
    await u.click(await botonDeObra());
    expect(await screen.findByRole("button", { name: /^Casa Demo/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Nueva obra" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cambiar carpeta…" })).not.toBeInTheDocument();
  });
});
