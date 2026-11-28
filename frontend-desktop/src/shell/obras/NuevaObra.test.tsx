import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import PaginaHoja from "../../paginas/hoja/pestanas";
import { ContextoAplicacion } from "../contexto";
import type { Aplicacion } from "../contexto";
import { DialogoSalida } from "../DialogoSalida";
import { DialogoNuevaObra, type DestinoDeNuevaObra } from "./DialogoNuevaObra";
import { TORRE_B, estadoInicial, json, montarMarco, servidorFalso, sesionDe } from "./datosDePrueba";

// «Nueva obra › Componer la obra» (especificación 01b-nueva-obra.html sobre MOD-3b / F10 / F11): conserva foco, Esc,
// validaciones, creación y apertura en el Resumen cuando empieza en blanco, y prueba las tres secciones, las ayudas, la
// nota de conversión BCV y el arranque «Desde un cómputo en Excel» hacia Presupuestar › Plano o cómputo.

const CONVERSION = "Esta obra se valorará convirtiendo los precios de la carpeta con la tasa del BCV del día.";
const NOTA_TASA_BCV = "La tasa usada queda anotada en cada versión.";

let servidor: ReturnType<typeof servidorFalso>;

function conTorreB(moneda: string | null = "Bs") {
  const estado = estadoInicial();
  estado.proyectos = [TORRE_B];
  estado.moneda = moneda;
  return estado;
}

function instalar(moneda: string | null = "Bs") {
  servidor = servidorFalso(conTorreB(moneda));
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
const botonNuevaObra = () =>
  within(screen.getByRole("complementary", { name: "Barra lateral" })).getByRole("button", { name: "Nueva obra" });

async function abrirNuevaObra(u: ReturnType<typeof userEvent.setup>) {
  montarMarco(sesionDe("ana"), "/inicio/pendientes");
  await screen.findByRole("heading", { level: 1, name: "Pendientes" });
  await u.click(botonNuevaObra());
  return screen.findByRole("dialog", { name: "Nueva obra" });
}

describe("«Nueva obra › Componer la obra» (secciones, controles y validaciones)", () => {
  test("presenta las tres secciones («Datos de la obra», «Cómo empezar» y «Dónde se guarda»), enfoca Nombre y propone la moneda de la carpeta", async () => {
    const u = userEvent.setup();
    const caja = await abrirNuevaObra(u);
    expect(caja).toHaveAttribute("aria-modal", "true");

    // Secciones por rol y nombre.
    expect(within(caja).getByRole("heading", { name: "Datos de la obra" })).toBeInTheDocument();
    expect(within(caja).getByRole("heading", { name: "Cómo empezar" })).toBeInTheDocument();
    expect(within(caja).getByRole("heading", { name: "Dónde se guarda" })).toBeInTheDocument();

    expect(within(caja).getByRole("textbox", { name: /^Nombre/ })).toHaveFocus();
    expect(within(caja).getByText("Así se verá en la lista de obras y en el presupuesto que se entrega")).toBeInTheDocument();
    expect(within(caja).getByRole("textbox", { name: /^Cliente/ })).toBeInTheDocument();
    expect(within(caja).getByRole("textbox", { name: /^Ubicación/ })).toBeInTheDocument();
    expect(within(caja).getByRole("textbox", { name: "Fecha de entrega al cliente" })).toBeInTheDocument();
    expect(within(caja).getByText("Decide qué catálogo y qué reglas de auditoría se usan")).toBeInTheDocument();
    expect(
      within(within(caja).getByRole("combobox", { name: "Tipo de obra" }))
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["Sin especificar", "Obra civil", "Telecomunicaciones", "Industrial", "Sistemas"]);

    await waitFor(() => expect(within(caja).getByRole("combobox", { name: "Moneda" })).toHaveValue("Bs"));
    expect(within(caja).queryByText(CONVERSION)).toBeNull();
    expect(within(caja).queryByText(NOTA_TASA_BCV)).toBeNull();

    // «Dónde se guarda»: carpeta, primera versión y persona que la crea.
    expect(within(caja).getByText("Se creará en Carpeta de la empresa")).toBeInTheDocument();
    expect(within(caja).getByText("V1 · en elaboración")).toBeInTheDocument();
    expect(within(caja).getByText("Ana Pérez")).toBeInTheDocument();
  });

  test("«Cómo empezar» ofrece como grupo de radios solo «En blanco» y «Desde un cómputo en Excel» (sin «Copiar de otra obra»)", async () => {
    const u = userEvent.setup();
    const caja = await abrirNuevaObra(u);
    const grupo = within(caja).getByRole("radiogroup", { name: "Cómo empezar" });
    const radios = within(grupo).getAllByRole("radio");
    expect(radios).toHaveLength(2);

    const enBlanco = within(grupo).getByRole("radio", { name: "En blanco" });
    const desdeComputo = within(grupo).getByRole("radio", { name: "Desde un cómputo en Excel" });
    expect(enBlanco).toBeChecked();
    expect(enBlanco).toHaveAccessibleDescription("Agregue las partidas una a una desde el catálogo");
    expect(desdeComputo).not.toBeChecked();
    expect(desdeComputo).toHaveAccessibleDescription("Traiga las partidas y cantidades de un cómputo métrico");

    expect(within(caja).queryByRole("radio", { name: /Copiar de otra obra/i })).toBeNull();
    expect(within(caja).queryByText(/Copiar de otra obra/i)).toBeNull();

    expect(within(caja).getByText("Después de crearla se abre la portada de la obra")).toBeInTheDocument();
    await u.click(desdeComputo);
    expect(desdeComputo).toBeChecked();
    expect(within(caja).getByText("Después de crearla se abre Presupuestar › Plano o cómputo")).toBeInTheDocument();
  });

  test("elegir la otra moneda (USD) muestra la conversión con la tasa del BCV y la nota de versión; volver a Bs las quita", async () => {
    const u = userEvent.setup();
    const caja = await abrirNuevaObra(u);
    const moneda = within(caja).getByRole("combobox", { name: "Moneda" });
    await waitFor(() => expect(moneda).toHaveValue("Bs"));
    await u.selectOptions(moneda, "USD");
    expect(within(caja).getByText(CONVERSION)).toBeInTheDocument();
    expect(within(caja).getByRole("note")).toHaveTextContent(NOTA_TASA_BCV);
    await u.selectOptions(moneda, "Bs");
    expect(within(caja).queryByText(CONVERSION)).toBeNull();
    expect(within(caja).queryByRole("note")).toBeNull();
  });

  test("sin moneda de la carpeta la moneda no viene elegida y es obligatoria (no llama a la API)", async () => {
    const u = userEvent.setup();
    instalar(null);
    const caja = await abrirNuevaObra(u);
    await waitFor(() => expect(servidor.de("GET", "/v1/carpeta").length).toBeGreaterThan(0));
    expect(within(caja).getByRole("combobox", { name: "Moneda" })).toHaveValue("");
    await u.type(within(caja).getByRole("textbox", { name: /^Nombre/ }), "Casa Demo");
    await u.click(within(caja).getByRole("button", { name: "Crear la obra" }));
    expect(await within(caja).findByText("Elija la moneda de la obra.")).toBeInTheDocument();
    expect(servidor.de("POST", "/v1/proyectos")).toEqual([]);
  });

  test("con el nombre vacío avisa antes de enviar, lleva el foco al campo y no llama a la API", async () => {
    const u = userEvent.setup();
    const caja = await abrirNuevaObra(u);
    await waitFor(() => expect(within(caja).getByRole("combobox", { name: "Moneda" })).toHaveValue("Bs"));
    const botonCrear = within(caja).getByRole("button", { name: "Crear la obra" });
    await u.click(botonCrear);
    expect(await within(caja).findByText("Escriba el nombre de la obra")).toBeInTheDocument();
    expect(within(caja).getByRole("textbox", { name: /^Nombre/ })).toHaveFocus();
    expect(servidor.de("POST", "/v1/proyectos")).toEqual([]);
    expect(dialogo()).toBeInTheDocument();
  });

  test("mientras crea la obra el botón dice «Creando la obra…» y queda deshabilitado", async () => {
    const u = userEvent.setup();
    let resolver: (r: Response) => void = () => {};
    servidor = servidorFalso(conTorreB("Bs"), (metodo, ruta) => {
      if (metodo === "POST" && ruta === "/v1/proyectos") {
        return new Promise<Response>((r) => {
          resolver = r;
        });
      }
      return undefined;
    });
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    const caja = await abrirNuevaObra(u);
    await waitFor(() => expect(within(caja).getByRole("combobox", { name: "Moneda" })).toHaveValue("Bs"));
    await u.type(within(caja).getByRole("textbox", { name: /^Nombre/ }), "Casa Demo");
    await u.click(within(caja).getByRole("button", { name: "Crear la obra" }));
    const botonOcupado = await within(caja).findByRole("button", { name: "Creando la obra…" });
    expect(botonOcupado).toBeDisabled();
    resolver(json({ codigo: "10", nombre: "Casa Demo", version_vigente: null, actualizado: null, cliente: "", ubicacion: "" }, 201));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Nueva obra" })).not.toBeInTheDocument());
  });

  test("crear «En blanco» manda la ficha completa, recarga las obras y abre la portada de la obra nueva", async () => {
    const u = userEvent.setup();
    const caja = await abrirNuevaObra(u);
    await waitFor(() => expect(within(caja).getByRole("combobox", { name: "Moneda" })).toHaveValue("Bs"));
    const listasAntes = servidor.de("GET", "/v1/obras/todas").length;
    await u.type(within(caja).getByRole("textbox", { name: /^Nombre/ }), "Casa Demo");
    await u.type(within(caja).getByRole("textbox", { name: /^Cliente/ }), "Contratista Demo, C.A.");
    await u.type(within(caja).getByRole("textbox", { name: /^Ubicación/ }), "Maracay");
    await u.selectOptions(within(caja).getByRole("combobox", { name: "Tipo de obra" }), "civil");
    await u.click(within(caja).getByRole("button", { name: "Crear la obra" }));
    await waitFor(() =>
      expect(servidor.de("POST", "/v1/proyectos").map((l) => l.cuerpo)).toEqual([
        {
          nombre: "Casa Demo",
          moneda: "Bs",
          dominio: "civil",
          descripcion: "",
          cliente: "Contratista Demo, C.A.",
          ubicacion: "Maracay",
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
    const resumen = await screen.findByRole("heading", { level: 1, name: "Resumen de la obra" });
    await waitFor(() => expect(resumen).toHaveFocus());
    expect(botonNuevaObra()).not.toHaveFocus();
    const resumenDeLaBarra = within(screen.getByRole("region", { name: "Obra abierta" })).getByRole("link", {
      name: /Portada de la obra/,
    });
    expect(resumenDeLaBarra).toHaveAttribute("href", "/obra/empresa/10/resumen");
    expect(resumenDeLaBarra).toHaveAttribute("aria-current", "page");
  });

  test("crear «Desde un cómputo en Excel» manda el mismo POST y lleva a Presupuestar › Plano o cómputo de la obra nueva", async () => {
    const u = userEvent.setup();
    const caja = await abrirNuevaObra(u);
    await waitFor(() => expect(within(caja).getByRole("combobox", { name: "Moneda" })).toHaveValue("Bs"));
    await u.type(within(caja).getByRole("textbox", { name: /^Nombre/ }), "Vialidad Norte");
    await u.click(within(caja).getByRole("radio", { name: "Desde un cómputo en Excel" }));
    await u.click(within(caja).getByRole("button", { name: "Crear la obra" }));

    await waitFor(() => expect(servidor.de("POST", "/v1/proyectos")).toHaveLength(1));
    expect(servidor.de("POST", "/v1/proyectos")[0]!.cuerpo).toMatchObject({
      nombre: "Vialidad Norte",
      moneda: "Bs",
      carpeta: "empresa",
    });

    const archivos = await screen.findByRole("heading", { level: 1, name: "Archivos y planos" });
    await waitFor(() => expect(archivos).toHaveFocus());
    const cabecera = screen.getByRole("region", { name: "Obra abierta" });
    expect(within(within(cabecera).getByRole("navigation", { name: "Herramientas de la obra" })).getByRole("link", { name: "Presupuestar" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    const opcionComputo = within(within(cabecera).getByRole("navigation", { name: "Opciones de Presupuestar" })).getByRole("link", {
      name: "Plano o cómputo",
    });
    expect(opcionComputo).toHaveAttribute("href", "/obra/empresa/10/archivos");
    expect(opcionComputo).toHaveAttribute("aria-current", "page");
  });

  test("Esc y Cancelar cierran sin crear y devuelven el foco a «Nueva obra»", async () => {
    const u = userEvent.setup();
    await abrirNuevaObra(u);
    await u.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Nueva obra" })).not.toBeInTheDocument();
    expect(servidor.de("POST", "/v1/proyectos")).toEqual([]);
    expect(botonNuevaObra()).toHaveFocus();

    await u.click(botonNuevaObra());
    const caja = await screen.findByRole("dialog", { name: "Nueva obra" });
    await u.click(within(caja).getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("dialog", { name: "Nueva obra" })).not.toBeInTheDocument();
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

  test("con «Fecha de entrega al cliente» escrita como dd/mm/aaaa la fija después de crear la obra; mal escrita avisa sin crear", async () => {
    const u = userEvent.setup();
    const caja = await abrirNuevaObra(u);
    await waitFor(() => expect(within(caja).getByRole("combobox", { name: "Moneda" })).toHaveValue("Bs"));
    await u.type(within(caja).getByRole("textbox", { name: /^Nombre/ }), "Puente Este");
    const campoFecha = within(caja).getByRole("textbox", { name: "Fecha de entrega al cliente" });
    await u.type(campoFecha, "31/02/2026");
    await u.click(within(caja).getByRole("button", { name: "Crear la obra" }));
    expect(await within(caja).findByText("La fecha escrita no existe en el calendario.")).toBeInTheDocument();
    expect(servidor.de("POST", "/v1/proyectos")).toEqual([]);

    await u.clear(campoFecha);
    await u.type(campoFecha, "15/12/2026");
    await u.click(within(caja).getByRole("button", { name: "Crear la obra" }));
    await waitFor(() => expect(servidor.de("POST", "/v1/proyectos")).toHaveLength(1));
    await waitFor(() =>
      expect(servidor.de("PUT", "/v1/obras/10/entrega").map((l) => l.cuerpo)).toEqual([
        { fecha_entrega: "2026-12-15" },
      ]),
    );
  });

  test("una «Fecha de entrega al cliente» ya pasada avisa antes de crear: no queda una obra creada sin su fecha", async () => {
    const u = userEvent.setup();
    const caja = await abrirNuevaObra(u);
    await waitFor(() => expect(within(caja).getByRole("combobox", { name: "Moneda" })).toHaveValue("Bs"));
    await u.type(within(caja).getByRole("textbox", { name: /^Nombre/ }), "Puente Este");
    await u.type(within(caja).getByRole("textbox", { name: "Fecha de entrega al cliente" }), "01/01/2020");
    await u.click(within(caja).getByRole("button", { name: "Crear la obra" }));
    expect(await within(caja).findByText("La fecha de entrega al cliente no puede estar en el pasado.")).toBeInTheDocument();
    expect(servidor.de("POST", "/v1/proyectos")).toEqual([]);
    expect(servidor.llamadas.filter((l) => l.metodo === "PUT" && l.ruta.endsWith("/entrega"))).toEqual([]);
  });

  // T4 (mutante DN2): si la carpeta de destino cambia a otra después de escribir una fecha, esa fecha ya no se ve ni se aplica:
  // no debe frenar la creación con un aviso de un campo que ya no está.
  test("una fecha pasada escrita antes de cambiar a otra carpeta no frena la creación", async () => {
    const u = userEvent.setup();
    const propias = { abierto: true, alCerrar: vi.fn(), alCrear: vi.fn() };
    const { rerender } = render(<DialogoNuevaObra {...propias} destino={{ carpeta: null, titulo: "La empresa" }} />);
    await u.type(await screen.findByRole("textbox", { name: /^Nombre/ }), "Puente Este");
    await u.type(screen.getByRole("textbox", { name: "Fecha de entrega al cliente" }), "01/01/2020");
    rerender(<DialogoNuevaObra {...propias} destino={{ carpeta: "s2.db", titulo: "S2", enOtraCarpeta: true }} />);
    expect(await screen.findByText("Se creará en S2")).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Fecha de entrega al cliente" })).toBeNull();
    await u.selectOptions(screen.getByRole("combobox", { name: "Moneda" }), "Bs");
    await u.click(screen.getByRole("button", { name: "Crear la obra" }));
    await waitFor(() => expect(servidor.de("POST", "/v1/proyectos")).toHaveLength(1));
    expect(screen.queryByText("La fecha de entrega al cliente no puede estar en el pasado.")).toBeNull();
  });

  test("en otra carpeta que la abierta no pide la fecha de entrega (se fija en el Resumen de la obra)", async () => {
    render(<DialogoNuevaObra abierto alCerrar={vi.fn()} alCrear={vi.fn()} destino={{ carpeta: "s2.db", titulo: "S2", enOtraCarpeta: true }} />);
    expect(await screen.findByText("Se creará en S2")).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Fecha de entrega al cliente" })).toBeNull();
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
        "Agregue las partidas en la pestaña «Partidas» (o, en una obra de instalaciones, describa el espacio o importe un plano en «Archivos y planos») y guarde la primera versión con «Guardar primera versión…».",
      ),
    ).toBeInTheDocument();
  });
});

describe("«Nueva obra» dice dónde se creará", () => {
  const DESTINO: DestinoDeNuevaObra = { carpeta: "s1.db", titulo: "S1" };

  async function llenarYCrear(u: ReturnType<typeof userEvent.setup>) {
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Moneda" })).toHaveValue("Bs"));
    await u.type(screen.getByRole("textbox", { name: /^Nombre/ }), "Casa Demo");
    await u.click(screen.getByRole("button", { name: "Crear la obra" }));
  }

  test("nombra la carpeta, sin selector, y manda esa carpeta sin cambiar la de la sesión", async () => {
    const u = userEvent.setup();
    const alCrear = vi.fn();
    render(<DialogoNuevaObra abierto alCerrar={vi.fn()} alCrear={alCrear} destino={DESTINO} />);
    expect(await screen.findByText("Se creará en S1")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Carpeta" })).toBeNull();
    await llenarYCrear(u);
    await waitFor(() => expect(alCrear).toHaveBeenCalledTimes(1));
    expect(alCrear).toHaveBeenCalledWith(expect.objectContaining({ nombre: "Casa Demo" }), "en_blanco");
    expect(servidor.de("POST", "/v1/proyectos").map((l) => l.cuerpo)).toEqual([
      { nombre: "Casa Demo", moneda: "Bs", dominio: "", descripcion: "", cliente: "", ubicacion: "", carpeta: "s1.db" },
    ]);
    expect(servidor.llamadas.filter((l) => l.metodo !== "GET").map((l) => `${l.metodo} ${l.ruta}`)).toEqual(["POST /v1/proyectos"]);
  });

  test("en otra carpeta que la abierta no propone la moneda de la sesión y la exige", async () => {
    const u = userEvent.setup();
    render(<DialogoNuevaObra abierto alCerrar={vi.fn()} alCrear={vi.fn()} destino={{ carpeta: "s2.db", titulo: "S2", enOtraCarpeta: true }} />);
    expect(await screen.findByText("Se creará en S2")).toBeInTheDocument();
    await waitFor(() => expect(servidor.de("GET", "/v1/carpeta").length).toBeGreaterThan(0));
    expect(screen.getByRole("combobox", { name: "Moneda" })).toHaveValue("");
    expect(screen.queryByText("Es la moneda de esta carpeta (Bs).")).toBeNull();
    await u.type(screen.getByRole("textbox", { name: /^Nombre/ }), "Casa Demo");
    await u.click(screen.getByRole("button", { name: "Crear la obra" }));
    expect(await screen.findByText("Elija la moneda de la obra.")).toBeInTheDocument();
    expect(servidor.de("POST", "/v1/proyectos")).toEqual([]);
  });

  test("la carpeta de la empresa se manda como «empresa»", async () => {
    const u = userEvent.setup();
    const alCrear = vi.fn();
    render(<DialogoNuevaObra abierto alCerrar={vi.fn()} alCrear={alCrear} destino={{ carpeta: null, titulo: "Carpeta de la empresa" }} />);
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
    const errorApi = "Ya existe una obra con ese nombre.";
    servidor = servidorFalso(conTorreB("Bs"), (metodo, ruta) =>
      metodo === "POST" && ruta === "/v1/proyectos" ? json({ detalle: errorApi }, 422) : undefined,
    );
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    render(<DialogoNuevaObra abierto alCerrar={vi.fn()} alCrear={alCrear} destino={DESTINO} />);
    await llenarYCrear(u);
    expect(await screen.findByText(errorApi)).toBeInTheDocument();
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
