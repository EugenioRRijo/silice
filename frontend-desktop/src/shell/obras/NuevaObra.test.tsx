import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import { ContextoAplicacion } from "../contexto";
import type { Aplicacion } from "../contexto";
import PaginaHoja from "../../paginas/hoja/index";
import { DialogoNuevaObra } from "./DialogoNuevaObra";
import { TORRE_B, botonDeObra, estadoInicial, json, montarShell, servidorFalso, sesionDe } from "./datosDePrueba";

// Plan de modulos, MOD-3b (absorbe T7 del plan de montar): «Nueva obra» (diseno de la bienvenida, BCP-6 §5.2, F10 y F11,
// con la ficha de la obra de MOD-3a y la moneda de la carpeta de T2). Oraculos escritos a mano.

const CONVERSION = "Esta obra se valorará convirtiendo los precios de la carpeta con la tasa del BCV del día.";
const VACIO_DE_LA_API = "Escriba un nombre para la obra: no puede quedar vacío.";

let servidor: ReturnType<typeof servidorFalso>;

// La carpeta empieza solo con «Torre B»: «Casa Demo» es la obra que se crea.
function conTorreB(moneda: string | null = "Bs") {
  const estado = estadoInicial();
  estado.proyectos = [TORRE_B];
  estado.moneda = moneda;
  return estado;
}

function instalar(moneda: string | null = "Bs") {
  servidor = servidorFalso(conTorreB(moneda), (metodo, ruta, cuerpo) => {
    // El 422 de la API por un nombre vacío, con su texto real (`aplicacion/proyectos.py`).
    if (metodo === "POST" && ruta === "/v1/proyectos" && !String((cuerpo as { nombre?: string }).nombre ?? "").trim()) {
      return json({ detalle: VACIO_DE_LA_API }, 422);
    }
    return undefined;
  });
  vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
}

beforeEach(() => {
  instalar();
  fijarCsrf("tok");
});
afterEach(() => {
  vi.unstubAllGlobals();
  fijarCsrf(null);
});

const dialogo = () => screen.getByRole("dialog", { name: "Nueva obra" });

async function abrirNuevaObra(u: ReturnType<typeof userEvent.setup>) {
  montarShell(sesionDe("ana"), "/hoja");
  await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
  await u.click(await botonDeObra());
  await u.click(await screen.findByRole("button", { name: "Nueva obra" }));
  return screen.findByRole("dialog", { name: "Nueva obra" });
}

describe("«Nueva obra» (F10 adaptado)", () => {
  test("trae Nombre, Cliente, Ubicación, Tipo de obra y Moneda; la moneda viene en la de la carpeta (Bs)", async () => {
    const u = userEvent.setup();
    const caja = await abrirNuevaObra(u);
    expect(caja).toHaveAttribute("aria-modal", "true");
    expect(within(caja).getByRole("textbox", { name: /^Nombre/ })).toHaveFocus();
    expect(within(caja).getByRole("textbox", { name: /^Cliente/ })).toBeInTheDocument();
    expect(within(caja).getByRole("textbox", { name: /^Ubicación/ })).toBeInTheDocument();
    expect(
      within(within(caja).getByRole("combobox", { name: "Tipo de obra" }))
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["Sin especificar", "Obra civil", "Telecomunicaciones", "Industrial", "Sistemas"]);
    await waitFor(() => expect(within(caja).getByRole("combobox", { name: "Moneda" })).toHaveValue("Bs"));
    expect(within(caja).queryByText(CONVERSION)).toBeNull();
  });

  test("elegir la otra moneda (USD) muestra la conversión con la tasa del BCV; volver a Bs la quita", async () => {
    const u = userEvent.setup();
    const caja = await abrirNuevaObra(u);
    const moneda = within(caja).getByRole("combobox", { name: "Moneda" });
    await waitFor(() => expect(moneda).toHaveValue("Bs"));
    await u.selectOptions(moneda, "USD");
    expect(within(caja).getByText(CONVERSION)).toBeInTheDocument();
    await u.selectOptions(moneda, "Bs");
    expect(within(caja).queryByText(CONVERSION)).toBeNull();
  });

  test("sin moneda de la carpeta la moneda no viene elegida y es obligatoria (no llama a la API)", async () => {
    const u = userEvent.setup();
    instalar(null);
    const caja = await abrirNuevaObra(u);
    await waitFor(() => expect(servidor.de("GET", "/v1/carpeta").length).toBeGreaterThan(0));
    expect(within(caja).getByRole("combobox", { name: "Moneda" })).toHaveValue("");
    await u.type(within(caja).getByRole("textbox", { name: /^Nombre/ }), "Casa Demo");
    await u.click(within(caja).getByRole("button", { name: "Crear obra" }));
    expect(await within(caja).findByText("Elija la moneda de la obra.")).toBeInTheDocument();
    expect(servidor.de("POST", "/v1/proyectos")).toEqual([]);
  });

  test("con el nombre vacío muestra en línea el mensaje de la API", async () => {
    const u = userEvent.setup();
    const caja = await abrirNuevaObra(u);
    await waitFor(() => expect(within(caja).getByRole("combobox", { name: "Moneda" })).toHaveValue("Bs"));
    await u.click(within(caja).getByRole("button", { name: "Crear obra" }));
    expect(await within(caja).findByText(VACIO_DE_LA_API)).toBeInTheDocument();
    expect(dialogo()).toBeInTheDocument();
  });

  test("crear manda la ficha completa, recarga las obras y la barra dice «Obra: Casa Demo»", async () => {
    const u = userEvent.setup();
    const caja = await abrirNuevaObra(u);
    await waitFor(() => expect(within(caja).getByRole("combobox", { name: "Moneda" })).toHaveValue("Bs"));
    const listasAntes = servidor.de("GET", "/v1/proyectos").length;
    await u.type(within(caja).getByRole("textbox", { name: /^Nombre/ }), "Casa Demo");
    await u.type(within(caja).getByRole("textbox", { name: /^Cliente/ }), "Contratista Demo, C.A.");
    await u.type(within(caja).getByRole("textbox", { name: /^Ubicación/ }), "Maracay");
    await u.selectOptions(within(caja).getByRole("combobox", { name: "Tipo de obra" }), "civil");
    await u.click(within(caja).getByRole("button", { name: "Crear obra" }));
    await waitFor(() =>
      expect(servidor.de("POST", "/v1/proyectos").map((l) => l.cuerpo)).toEqual([
        {
          nombre: "Casa Demo",
          moneda: "Bs",
          dominio: "civil",
          descripcion: "",
          cliente: "Contratista Demo, C.A.",
          ubicacion: "Maracay",
        },
      ]),
    );
    await waitFor(async () => expect(await botonDeObra()).toHaveAccessibleName("Obra: Casa Demo. Cambiar obra"));
    expect(screen.queryByRole("dialog", { name: "Nueva obra" })).not.toBeInTheDocument();
    await waitFor(() => expect(servidor.de("GET", "/v1/proyectos").length).toBeGreaterThan(listasAntes));
    await waitFor(() =>
      expect(servidor.de("PUT", "/v1/sesion/proyecto").map((l) => l.cuerpo)).toEqual([{ proyecto: "10" }]),
    );
    expect(await botonDeObra()).toHaveFocus();
  });

  test("Esc cierra sin crear y devuelve el foco al botón de la barra", async () => {
    const u = userEvent.setup();
    await abrirNuevaObra(u);
    await u.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Nueva obra" })).not.toBeInTheDocument();
    expect(servidor.de("POST", "/v1/proyectos")).toEqual([]);
    expect(await botonDeObra()).toHaveFocus();
  });

  test("ninguna cadena visible del diálogo dice «caso» ni «proyecto»", async () => {
    const u = userEvent.setup();
    const caja = await abrirNuevaObra(u);
    await u.selectOptions(within(caja).getByRole("combobox", { name: "Moneda" }), "USD");
    for (const patron of [/\bcaso\b/i, /\bproyecto\b/i]) {
      expect(within(caja).queryByText(patron)).toBeNull();
      expect(within(caja).queryByLabelText(patron)).toBeNull();
    }
  });

  test("cerrado no pinta nada", () => {
    const { container } = render(<DialogoNuevaObra abierto={false} alCerrar={vi.fn()} alCrear={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("F11: obra sin versión guardada", () => {
  test("la Hoja de una obra sin versiones enseña a describir el espacio y a guardar la primera versión", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (entrada: RequestInfo | URL) => {
        const ruta = String(entrada);
        if (ruta.startsWith("/v1/hoja/versiones")) return json({ proyecto: "8", moneda: "Bs", por_omision: null, versiones: [] });
        return json({ detalle: "No disponible en esta prueba." }, 503);
      }),
    );
    const valor: Aplicacion = {
      sesion: sesionDe("ana"),
      proyecto: "8",
      nombreProyecto: "Torre B",
      caso: { nombre: "silice.db", ruta_relativa: "casos/silice.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    render(
      <ContextoAplicacion.Provider value={valor}>
        <PaginaHoja />
      </ContextoAplicacion.Provider>,
    );
    expect(
      await screen.findByText(
        "Describa el espacio (ambientes y puntos) o importe un plano, y guarde la primera versión con «Guardar primera versión…».",
      ),
    ).toBeInTheDocument();
  });
});
