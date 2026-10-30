import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import CostosDelPeriodo from "./CostosDelPeriodo";

// Datos ficticios. La API manda los montos como texto con punto; la pantalla los muestra con coma.
const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["operar_arenera", "registrar_costos_produccion"],
  modo_entrega: false,
};
const SIN_LA_ACCION: SesionRespuesta = { ...SESION, acciones: ["operar_arenera"] };

interface Fila {
  id: number;
  periodo: string;
  centro: string;
  concepto: string;
  monto: string;
  moneda: string;
  fecha: string;
  fuente: string;
  nota: string;
  usuario: string;
  registrado: string;
  anulado: boolean;
  anula_id: number | null;
  motivo: string;
}

function fila(id: number, parcial: Partial<Fila> = {}): Fila {
  return {
    id,
    periodo: "2026-11",
    centro: "cantera",
    concepto: "gasoil",
    monto: "1250.50",
    moneda: "USD",
    fecha: "2026-11-03",
    fuente: `factura ${id}`,
    nota: "",
    usuario: "ana",
    registrado: "2026-11-04T09:00:00",
    anulado: false,
    anula_id: null,
    motivo: "",
    ...parcial,
  };
}

const COSTOS = [
  fila(1),
  fila(2, { concepto: "equipo", monto: "300.00" }),
  fila(3, { centro: "planta", concepto: "nomina", monto: "800", moneda: "Bs" }),
];

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

type Usuario = ReturnType<typeof userEvent.setup>;

describe("Costos del período", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let lista: (consulta: URLSearchParams) => Response;
  let totales: (consulta: URLSearchParams) => Response;
  let alta: () => Response;
  let anulacion: () => Response;
  let usuario: Usuario;
  const alExpirar = vi.fn();

  function montar(sesion: SesionRespuesta = SESION) {
    render(
      <ContextoAplicacion.Provider value={{ sesion, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar }}>
        <MemoryRouter>
          <CostosDelPeriodo />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  const peticiones = (metodo: string) =>
    fetchFalso.mock.calls
      .filter((c) => (c[1]?.method ?? "GET") === metodo)
      .map((c) => ({ ruta: String(c[0]), cuerpo: c[1]?.body ? JSON.parse(String(c[1].body)) : null }));

  const listas = () => peticiones("GET").filter((p) => !p.ruta.includes("/totales"));

  async function abrirRegistro() {
    await usuario.click(screen.getByRole("button", { name: "Registrar un costo" }));
    return screen.getByRole("dialog", { name: "Registrar un costo" });
  }

  // La moneda no tiene valor por defecto: se elige siempre.
  async function elegirMoneda(dialogo: HTMLElement, moneda = "USD") {
    await usuario.selectOptions(within(dialogo).getByLabelText("Moneda"), moneda);
  }
  // El centro tampoco tiene valor por defecto: de él depende a qué producto se reparte el costo.
  async function elegirCentro(dialogo: HTMLElement, centro = "cantera") {
    await usuario.selectOptions(within(dialogo).getByLabelText("Centro"), centro);
  }
  async function elegirCentroYMoneda(dialogo: HTMLElement) {
    await elegirCentro(dialogo);
    await elegirMoneda(dialogo);
  }

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 10, 15, 10, 0, 0));
    usuario = userEvent.setup();
    fijarCsrf("tok");
    alExpirar.mockReset();
    fetchFalso.mockReset();
    vi.stubGlobal("fetch", fetchFalso);
    lista = () => json(COSTOS);
    // Los totales los calcula el servidor (la interfaz no suma montos).
    totales = () =>
      json([
        { centro: "cantera", moneda: "USD", total: "1550.50" },
        { centro: "planta", moneda: "Bs", total: "800" },
      ]);
    alta = () => json({ id: 9 }, 201);
    anulacion = () => json({ id: 10 }, 201);
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://prueba");
      const metodo = init?.method ?? "GET";
      if (url.pathname === "/v1/produccion/costos/totales" && metodo === "GET") return totales(url.searchParams);
      if (url.pathname === "/v1/produccion/costos" && metodo === "GET") return lista(url.searchParams);
      if (url.pathname === "/v1/produccion/costos" && metodo === "POST") return alta();
      if (/\/costos\/\d+\/anular$/.test(url.pathname) && metodo === "POST") return anulacion();
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    fijarCsrf(null);
  });

  test("muestra los costos del período con total por centro y moneda", async () => {
    montar();
    expect(screen.getByRole("heading", { level: 1, name: "Costos del período" })).toBeInTheDocument();
    const totales = await screen.findByRole("list", { name: "Total por centro y moneda" });
    expect(within(totales).getByText("Cantera: 1.550,50 USD")).toBeInTheDocument();
    expect(within(totales).getByText("Planta: 800,00 Bs")).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Gasoil/ })).toHaveTextContent("1.250,50");
    expect(listas()[0].ruta).toBe("/v1/produccion/costos?periodo=2026-11");
    expect(peticiones("GET").map((p) => p.ruta)).toContain("/v1/produccion/costos/totales?periodo=2026-11");
  });

  test("los totales son los del servidor: la pantalla solo les da formato", async () => {
    totales = () => json([{ centro: "cantera", moneda: "USD", total: "99999.99" }]);
    montar();
    expect(await screen.findByText("Cantera: 99.999,99 USD")).toBeInTheDocument();
  });

  test("cambiar el mes pide ese mes", async () => {
    montar();
    await screen.findByText("Cantera: 1.550,50 USD");
    fireEvent.change(screen.getByLabelText("Mes"), { target: { value: "2026-10" } });
    await waitFor(() => expect(peticiones("GET").map((p) => p.ruta)).toEqual(
        expect.arrayContaining(["/v1/produccion/costos?periodo=2026-10", "/v1/produccion/costos/totales?periodo=2026-10"]),
      ));
  });

  test("escribe el monto con coma y lo envía con punto", async () => {
    montar();
    await screen.findByText("Cantera: 1.550,50 USD");
    const dialogo = await abrirRegistro();
    await usuario.type(within(dialogo).getByLabelText("Monto"), "1.250,50");
    await elegirCentroYMoneda(dialogo);
    await usuario.type(within(dialogo).getByLabelText("Fuente (factura o recibo)"), "factura 77");
    await usuario.click(within(dialogo).getByRole("button", { name: "Registrar costo" }));
    await waitFor(() => expect(peticiones("POST")).toHaveLength(1));
    expect(peticiones("POST")[0].cuerpo).toEqual({
      periodo: "2026-11",
      centro: "cantera",
      concepto: "gasoil",
      monto: "1250.50",
      moneda: "USD",
      fecha: "2026-11-15",
      fuente: "factura 77",
      nota: "",
    });
    expect(peticiones("POST")[0].cuerpo).not.toHaveProperty("ahora");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(listas()).toHaveLength(2); // recargó la lista
    expect(peticiones("GET")).toHaveLength(4); // y los totales
  });

  test.each(["diez", "1,2,3", "1.2", ""])("el monto «%s» no se envía y dice por qué", async (monto) => {
    montar();
    await screen.findByText("Cantera: 1.550,50 USD");
    const dialogo = await abrirRegistro();
    if (monto) await usuario.type(within(dialogo).getByLabelText("Monto"), monto);
    await elegirCentroYMoneda(dialogo);
    await usuario.type(within(dialogo).getByLabelText("Fuente (factura o recibo)"), "factura 77");
    await usuario.click(within(dialogo).getByRole("button", { name: "Registrar costo" }));
    expect(
      await within(dialogo).findByText(/^(Escriba el monto|El monto está mal escrito)/, { selector: ".cds--form-requirement" }),
    ).toBeInTheDocument();
    expect(peticiones("POST")).toHaveLength(0);
  });

  test("sin elegir el centro no se envía", async () => {
    montar();
    await screen.findByText("Cantera: 1.550,50 USD");
    const dialogo = await abrirRegistro();
    await usuario.type(within(dialogo).getByLabelText("Monto"), "10");
    await elegirMoneda(dialogo);
    await usuario.type(within(dialogo).getByLabelText("Fuente (factura o recibo)"), "factura 77");
    await usuario.click(within(dialogo).getByRole("button", { name: "Registrar costo" }));
    expect(await within(dialogo).findByText("Elija el centro del costo.")).toBeInTheDocument();
    expect(peticiones("POST")).toHaveLength(0);
  });

  test("sin elegir la moneda no se envía", async () => {
    montar();
    await screen.findByText("Cantera: 1.550,50 USD");
    const dialogo = await abrirRegistro();
    await elegirCentro(dialogo);
    await usuario.type(within(dialogo).getByLabelText("Monto"), "10");
    await usuario.type(within(dialogo).getByLabelText("Fuente (factura o recibo)"), "factura 77");
    await usuario.click(within(dialogo).getByRole("button", { name: "Registrar costo" }));
    expect(await within(dialogo).findByText("Elija la moneda del monto.")).toBeInTheDocument();
    expect(peticiones("POST")).toHaveLength(0);
  });

  test("una fecha fuera del mes o sin fuente no se envía", async () => {
    montar();
    await screen.findByText("Cantera: 1.550,50 USD");
    const dialogo = await abrirRegistro();
    await usuario.type(within(dialogo).getByLabelText("Monto"), "10");
    await elegirCentroYMoneda(dialogo);
    fireEvent.change(within(dialogo).getByLabelText("Fecha"), { target: { value: "2026-12-01" } });
    await usuario.click(within(dialogo).getByRole("button", { name: "Registrar costo" }));
    expect(await within(dialogo).findByText("La fecha debe caer en noviembre de 2026.")).toBeInTheDocument();
    expect(within(dialogo).getByText("Escriba la fuente: la factura, el recibo o la nómina de donde sale el monto.")).toBeInTheDocument();
    expect(peticiones("POST")).toHaveLength(0);
  });

  test("Esc cierra el diálogo de registro y devuelve el foco al botón", async () => {
    montar();
    await screen.findByText("Cantera: 1.550,50 USD");
    await abrirRegistro();
    await usuario.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Registrar un costo" })).toHaveFocus();
  });

  test.each([
    [403, { detalle: "Forbidden" }, "Su cuenta no tiene permiso para registrar costos."],
    [409, { detalle: "Ese costo ya fue anulado." }, "Ese costo ya fue anulado."],
    [422, { detail: [{ loc: ["body", "monto"], msg: "bad", type: "x" }] }, "Revise los datos: alguno no es válido."],
    [422, { detalle: "La fecha (fecha) cae fuera del periodo." }, "La fecha (fecha) cae fuera del periodo."],
  ])("un %s del servidor al registrar se muestra en español", async (estado, cuerpo, texto) => {
    alta = () => json(cuerpo, estado);
    montar();
    await screen.findByText("Cantera: 1.550,50 USD");
    const dialogo = await abrirRegistro();
    await usuario.type(within(dialogo).getByLabelText("Monto"), "10");
    await elegirCentroYMoneda(dialogo);
    await usuario.type(within(dialogo).getByLabelText("Fuente (factura o recibo)"), "factura 1");
    await usuario.click(within(dialogo).getByRole("button", { name: "Registrar costo" }));
    expect(await within(dialogo).findByText(texto)).toBeInTheDocument();
    expect(dialogo).toHaveTextContent(/No se pudo registrar/);
    expect(dialogo.textContent).not.toMatch(/Forbidden|estado \d{3}|\bbody\b/);
  });

  test("anular pide el motivo y no borra la fila hasta recargar", async () => {
    montar();
    await screen.findByText("Cantera: 1.550,50 USD");
    await usuario.click(within(screen.getByRole("row", { name: /Equipo/ })).getByRole("button", { name: /^Anular / }));
    const dialogo = screen.getByRole("dialog", { name: "Anular un costo" });
    // sin motivo no se envía
    await usuario.click(within(dialogo).getByRole("button", { name: "Anular costo" }));
    expect(await within(dialogo).findByText("Escriba el motivo de la anulación.")).toBeInTheDocument();
    expect(peticiones("POST")).toHaveLength(0);

    let soltar: (r: Response) => void = () => undefined;
    const pendiente = new Promise<Response>((res) => (soltar = res));
    lista = () => json(COSTOS.filter((c) => c.id !== 2));
    totales = () =>
      json([
        { centro: "cantera", moneda: "USD", total: "1250.50" },
        { centro: "planta", moneda: "Bs", total: "800" },
      ]);
    fetchFalso.mockImplementationOnce(async () => pendiente); // la anulación queda en vuelo
    await usuario.type(within(dialogo).getByLabelText("Motivo de la anulación"), "se cargó dos veces");
    await usuario.click(within(dialogo).getByRole("button", { name: "Anular costo" }));
    await waitFor(() => expect(fetchFalso).toHaveBeenCalledTimes(3)); // lista, totales y la anulación
    expect(screen.getByRole("row", { name: /Equipo/ })).toBeInTheDocument(); // sigue ahí mientras tanto
    soltar(json({ id: 10 }, 201));
    await waitFor(() => expect(screen.queryByRole("row", { name: /Equipo/ })).not.toBeInTheDocument());
    expect(screen.getByText("Cantera: 1.250,50 USD")).toBeInTheDocument();
    const aviso = await screen.findByRole("status");
    expect(aviso).toHaveTextContent("Costo anulado.");
    // El botón que tenía el foco desapareció con su fila: el foco pasa al aviso, no a BODY.
    await waitFor(() => expect(aviso.closest("[tabindex='-1']")).toHaveFocus());
    expect(peticiones("POST")[0]).toEqual({ ruta: "/v1/produccion/costos/2/anular", cuerpo: { motivo: "se cargó dos veces" } });
  });

  test("cada botón de fila lleva su propio nombre, que empieza por lo que se ve", async () => {
    montar();
    await screen.findByText("Cantera: 1.550,50 USD");
    expect(screen.getByRole("button", { name: "Anular Equipo de cantera del 03/11/2026 por 300,00 USD" })).toHaveTextContent("Anular");
    expect(screen.getByRole("button", { name: "Anular Nómina de planta del 03/11/2026 por 800,00 Bs" })).toBeInTheDocument();
  });

  test("si la anulación falla, la fila queda y se dice por qué", async () => {
    anulacion = () => json({ detalle: "Ese costo ya fue anulado." }, 409);
    montar();
    await screen.findByText("Cantera: 1.550,50 USD");
    await usuario.click(within(screen.getByRole("row", { name: /Equipo/ })).getByRole("button", { name: /^Anular / }));
    const dialogo = screen.getByRole("dialog", { name: "Anular un costo" });
    await usuario.type(within(dialogo).getByLabelText("Motivo de la anulación"), "duplicado");
    await usuario.click(within(dialogo).getByRole("button", { name: "Anular costo" }));
    expect(await within(dialogo).findByText("Ese costo ya fue anulado.")).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Equipo/ })).toBeInTheDocument();
  });

  test("con «Mostrar anulados» se ve la fila anulada con su motivo y no suma", async () => {
    lista = (consulta) =>
      json(
        consulta.get("incluir_anulados") === "true"
          ? [
              fila(1),
              fila(2, { concepto: "equipo", monto: "300.00", anulado: true }),
              fila(4, { concepto: "equipo", monto: "300.00", anulado: true, anula_id: 2, motivo: "se cargó dos veces" }),
            ]
          : [fila(1)],
      );
    totales = () => json([{ centro: "cantera", moneda: "USD", total: "1250.50" }]);
    montar();
    await screen.findByText("Cantera: 1.250,50 USD");
    expect(screen.queryByText("se cargó dos veces")).not.toBeInTheDocument();
    await usuario.click(screen.getByRole("checkbox", { name: "Mostrar anulados" }));
    expect(await screen.findByText("se cargó dos veces")).toBeInTheDocument();
    expect(listas().at(-1)?.ruta).toBe("/v1/produccion/costos?periodo=2026-11&incluir_anulados=true");
    expect(screen.getAllByText("Anulado").length).toBeGreaterThan(0);
    expect(screen.getByText("Anulación")).toBeInTheDocument();
    expect(screen.getByText("Cantera: 1.250,50 USD")).toBeInTheDocument(); // los anulados no suman
    expect(screen.getAllByRole("button", { name: /^Anular / })).toHaveLength(1); // solo el vigente
  });

  test("sin la acción no aparece Registrar y no se pide nada", () => {
    montar(SIN_LA_ACCION);
    expect(screen.queryByRole("button", { name: "Registrar un costo" })).not.toBeInTheDocument();
    expect(screen.getByText(/no registra costos/)).toBeInTheDocument();
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("sin costos en el mes enseña qué hacer", async () => {
    lista = () => json([]);
    montar();
    expect(await screen.findByText("Todavía no hay costos en este mes")).toBeInTheDocument();
  });

  test("un 403 al leer dice que falta el permiso, sin tecnicismos", async () => {
    lista = () => json({ detalle: "Forbidden" }, 403);
    montar();
    expect(await screen.findByText("Su cuenta no tiene permiso para registrar costos.")).toBeInTheDocument();
  });
});
