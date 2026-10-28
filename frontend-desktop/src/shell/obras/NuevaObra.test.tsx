import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import { ContextoAplicacion } from "../contexto";
import { DialogoSalida } from "../DialogoSalida";
import type { Aplicacion } from "../contexto";
import PaginaHoja from "../../paginas/hoja/index";
import { DialogoNuevaObra, type DestinoDeNuevaObra } from "./DialogoNuevaObra";
import { TORRE_B, estadoInicial, json, montarMarco, servidorFalso, sesionDe } from "./datosDePrueba";

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

// «Nueva obra» es el botón principal de la barra lateral del marco (Tarea 6 del plan del marco).
const botonNuevaObra = () => within(screen.getByRole("complementary", { name: "Barra lateral" })).getByRole("button", { name: "Nueva obra" });

async function abrirNuevaObra(u: ReturnType<typeof userEvent.setup>) {
  montarMarco(sesionDe("ana"), "/pendientes");
  await screen.findByRole("heading", { level: 1, name: "Pendientes" });
  await u.click(botonNuevaObra());
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

  test("crear manda la ficha completa, recarga las obras y abre la obra nueva", async () => {
    const u = userEvent.setup();
    const caja = await abrirNuevaObra(u);
    await waitFor(() => expect(within(caja).getByRole("combobox", { name: "Moneda" })).toHaveValue("Bs"));
    const listasAntes = servidor.de("GET", "/v1/obras/todas").length;
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
          // «Nueva obra» siempre dice dónde se crea: sin obra abierta, en la carpeta de la sesión (la de la empresa).
          carpeta: "empresa",
        },
      ]),
    );
    const cabecera = await screen.findByRole("region", { name: "Obra abierta" });
    expect(await within(cabecera).findByText("Casa Demo")).toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: "Nueva obra" })).not.toBeInTheDocument();
    await waitFor(() => expect(servidor.de("GET", "/v1/obras/todas").length).toBeGreaterThan(listasAntes));
    await waitFor(() =>
      expect(servidor.de("PUT", "/v1/sesion/proyecto").map((l) => l.cuerpo)).toEqual([{ proyecto: "10" }]),
    );
    expect(botonNuevaObra()).toHaveFocus();
  });

  test("Esc cierra sin crear y devuelve el foco a «Nueva obra»", async () => {
    const u = userEvent.setup();
    await abrirNuevaObra(u);
    await u.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Nueva obra" })).not.toBeInTheDocument();
    expect(servidor.de("POST", "/v1/proyectos")).toEqual([]);
    expect(botonNuevaObra()).toHaveFocus();
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
    const { container } = render(
      <DialogoNuevaObra abierto={false} alCerrar={vi.fn()} alCrear={vi.fn()} destino={{ carpeta: null, titulo: "Carpeta de la empresa" }} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});

describe("F11: obra sin versión guardada", () => {
  test("la Hoja de una obra sin versiones enseña a agregar las partidas y a guardar la primera versión", async () => {
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
        // Tarea 11: una obra civil empieza por «Presupuesto»; el espacio queda para las de instalaciones.
        "Agregue las partidas en «Presupuesto» (o, en una obra de instalaciones, describa el espacio o importe un plano) y guarde la primera versión con «Guardar primera versión…».",
      ),
    ).toBeInTheDocument();
  });
});

// Rediseño del marco, Tarea 6b: «Nueva obra» crea donde está la persona. El diálogo nombra la carpeta y la manda; no
// pregunta, no pide confirmar la salida y no abre ni cierra carpetas (eso lo hace el servidor sin mover la sesión).
describe("«Nueva obra» dice dónde se creará", () => {
  const DESTINO: DestinoDeNuevaObra = { carpeta: "s1.db", titulo: "S1" };

  async function llenarYCrear(u: ReturnType<typeof userEvent.setup>) {
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Moneda" })).toHaveValue("Bs"));
    await u.type(screen.getByRole("textbox", { name: /^Nombre/ }), "Casa Demo");
    await u.click(screen.getByRole("button", { name: "Crear obra" }));
  }

  test("nombra la carpeta, sin selector, y manda esa carpeta sin cambiar la de la sesión", async () => {
    const u = userEvent.setup();
    const alCrear = vi.fn();
    render(<DialogoNuevaObra abierto alCerrar={vi.fn()} alCrear={alCrear} destino={DESTINO} />);
    expect(await screen.findByText("Se creará en S1")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Carpeta" })).toBeNull();
    await llenarYCrear(u);
    await waitFor(() => expect(alCrear).toHaveBeenCalledTimes(1));
    expect(servidor.de("POST", "/v1/proyectos").map((l) => l.cuerpo)).toEqual([
      { nombre: "Casa Demo", moneda: "Bs", dominio: "", descripcion: "", cliente: "", ubicacion: "", carpeta: "s1.db" },
    ]);
    expect(servidor.llamadas.filter((l) => l.metodo !== "GET").map((l) => `${l.metodo} ${l.ruta}`)).toEqual([
      "POST /v1/proyectos",
    ]);
  });

  test("en otra carpeta que la abierta no propone la moneda de la sesión y la exige", async () => {
    const u = userEvent.setup();
    render(
      <DialogoNuevaObra abierto alCerrar={vi.fn()} alCrear={vi.fn()} destino={{ carpeta: "s2.db", titulo: "S2", enOtraCarpeta: true }} />,
    );
    expect(await screen.findByText("Se creará en S2")).toBeInTheDocument();
    await waitFor(() => expect(servidor.de("GET", "/v1/carpeta").length).toBeGreaterThan(0)); // la sesión dice Bs
    expect(screen.getByRole("combobox", { name: "Moneda" })).toHaveValue("");
    expect(screen.queryByText("Es la moneda de esta carpeta (Bs).")).toBeNull();
    await u.type(screen.getByRole("textbox", { name: /^Nombre/ }), "Casa Demo");
    await u.click(screen.getByRole("button", { name: "Crear obra" }));
    expect(await screen.findByText("Elija la moneda de la obra.")).toBeInTheDocument();
    expect(servidor.de("POST", "/v1/proyectos")).toEqual([]);
  });

  test("la carpeta de la empresa se manda como «empresa»", async () => {
    const u = userEvent.setup();
    const alCrear = vi.fn();
    render(
      <DialogoNuevaObra abierto alCerrar={vi.fn()} alCrear={alCrear} destino={{ carpeta: null, titulo: "Carpeta de la empresa" }} />,
    );
    expect(await screen.findByText("Se creará en Carpeta de la empresa")).toBeInTheDocument();
    await llenarYCrear(u);
    await waitFor(() => expect(alCrear).toHaveBeenCalledTimes(1));
    expect(servidor.de("POST", "/v1/proyectos")[0]!.cuerpo).toMatchObject({ carpeta: "empresa" });
  });

  test("no pregunta por borradores aunque los haya: crear no descarta nada", async () => {
    const u = userEvent.setup();
    servidor.estado.borradores = [{ id: "b1", proyecto: "7", version: null, cambios: 3, rev: 1, tocado: "2026-10-27" }];
    const alCrear = vi.fn();
    render(
      <>
        <DialogoNuevaObra abierto alCerrar={vi.fn()} alCrear={alCrear} destino={DESTINO} />
        <DialogoSalida />
      </>,
    );
    await llenarYCrear(u);
    await waitFor(() => expect(alCrear).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("button", { name: "Quedarme" })).toBeNull();
    expect(servidor.de("GET", "/v1/hoja/borradores")).toEqual([]);
  });

  test("si crear falla muestra el error y no llama a alCrear ni toca la sesión", async () => {
    const u = userEvent.setup();
    const alCrear = vi.fn();
    render(<DialogoNuevaObra abierto alCerrar={vi.fn()} alCrear={alCrear} destino={DESTINO} />);
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Moneda" })).toHaveValue("Bs"));
    await u.click(screen.getByRole("button", { name: "Crear obra" })); // nombre vacío: 422
    expect(await screen.findByText(VACIO_DE_LA_API)).toBeInTheDocument();
    expect(alCrear).not.toHaveBeenCalled();
    expect(servidor.llamadas.filter((l) => l.metodo !== "GET" && l.ruta !== "/v1/proyectos")).toEqual([]);
  });

  test("el texto de la moneda no dice «carpeta de trabajo»", async () => {
    render(<DialogoNuevaObra abierto alCerrar={vi.fn()} alCrear={vi.fn()} destino={DESTINO} />);
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Moneda" })).toHaveValue("Bs"));
    expect(screen.getByText("Es la moneda de esta carpeta (Bs).")).toBeInTheDocument();
    expect(screen.queryByText(/carpeta de trabajo/i)).toBeNull();
  });
});
