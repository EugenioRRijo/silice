import { configure, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaHoja from "./index";
import type { BorradorAbierto, FilaPresupuesto, Resumen, VersionesRespuesta, VistaPresupuesto } from "./logica";

// Tarea 11 del plan de montar un presupuesto: la Hoja agrega y quita partidas (rutas de la Tarea 9) y una obra sin
// espacio abre en «Presupuesto». El servidor se simula con la forma del contrato (`api/rutas/hoja.py`, `docs/api.json`):
// `POST …/partidas` `{rev, codigo, cantidad, calculo, nota}` → `{rev, resumen, clave}`; `POST …/partidas/quitar`
// `{rev, clave}` → `{rev, resumen}`; las filas traen `quitable`, `nota` y `calculo`; el resumen, `espacio_vacio`. Los
// textos de los errores son los de `aplicacion/hoja_partidas.py` y `aplicacion/hoja_edicion.py`. Obra y partidas
// ficticias (la vivienda de 80 m²).
configure({ asyncUtilTimeout: 5000 });

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja"],
  modo_entrega: false,
};

const ID = "id-borrador-vivienda-aaaa";
const RUTA_AGREGAR = `/v1/hoja/borradores/${ID}/partidas`;
const RUTA_QUITAR = `/v1/hoja/borradores/${ID}/partidas/quitar`;
const SIN_RENGLONES = "El presupuesto no tiene renglones todavía.";
const CALCULO_NO_CUADRA = "El cálculo da 16 y la cantidad es 15: corrija uno de los dos.";
const FUERA_DEL_CATALOGO = "La partida «OBRA-04» no está en el catálogo: compóngala primero en Componer.";
const SIN_TASA = "No hay tasa del BCV de los últimos 7 días: cárguela en Índices y vuelva a intentar.";
const CONFIRMAR_QUITAR = "¿Quitar OBRA-04 del presupuesto? Lo puede descartar antes de guardar.";

const SIN_VERSIONES_DE_LA_OBRA: VersionesRespuesta = { proyecto: "VIV-80", moneda: "Bs", por_omision: null, versiones: [] };

function resumen(extra: Partial<Resumen> = {}): Resumen {
  return {
    rev: 0,
    moneda: "Bs",
    total: { texto: "0.00", exacto: "0" },
    cambios: 0,
    pendientes_catalogo: 0,
    hallazgos: [],
    hay_plan: false,
    version_mas_nueva: null,
    guardado_como: null,
    espacio_vacio: true,
    ...extra,
  };
}

function borradorEnBlanco(extra: Partial<Resumen> = {}): BorradorAbierto {
  return {
    id: ID,
    base: { proyecto: "VIV-80", version: null, vigente: null, lista: null, espacio_de: null, solo_lectura: false, moneda: "Bs" },
    resumen: resumen(extra),
    instantanea: { creadas: 0, mensaje: null },
  };
}

const PARED: FilaPresupuesto = {
  clave: "OBRA-04|a-mano:1",
  partida: "OBRA-04",
  descripcion: "Pared de bloques de arcilla de 15 cm",
  unidad: "m2",
  cantidad: "210",
  cantidad_calculada: "210",
  escrita: false,
  pu: { texto: "85.30", exacto: "85.3" },
  total: { texto: "17913.00", exacto: "17913" },
  estado: { severidad: "ADVERTENCIA", texto: "Advertencia" },
  quitable: true,
  nota: null,
  calculo: null,
};

const LLAVE_DEL_ESPACIO: FilaPresupuesto = {
  clave: "AF-LLAVE|esp_puntos:P1",
  partida: "AF-LLAVE",
  descripcion: "Llave de paso",
  unidad: "unidad",
  cantidad: "3",
  cantidad_calculada: "3",
  escrita: false,
  pu: { texto: "13.20", exacto: "13.198738025" },
  total: { texto: "39.60", exacto: "39.596214075" },
  estado: { severidad: null, texto: "OK" },
  quitable: false,
  nota: null,
  calculo: null,
};

function vista(filas: FilaPresupuesto[], total = { texto: "17913.00", exacto: "17913" }): VistaPresupuesto {
  return { filas, total, moneda: "Bs", vacio_mensaje: filas.length === 0 ? SIN_RENGLONES : null };
}

const HALLADAS = {
  rotulo: "Partidas del catálogo",
  resultados: [
    {
      clave: "partida:OBRA-04",
      codigo: "OBRA-04",
      descripcion: "Pared de bloques de arcilla de 15 cm",
      unidad: "m2",
      dominio: "civil",
      tiene_composicion: true,
    },
  ],
  hay_mas: false,
};

type Cuerpo = Record<string, unknown> & { rev: number };

function Ubicacion() {
  const { pathname, search } = useLocation();
  return <p data-testid="ubicacion">{`${pathname}${search}`}</p>;
}

describe("Hoja: agregar y quitar partidas (Tarea 11)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();
  let versiones: VersionesRespuesta;
  let abierto: BorradorAbierto;
  let filas: FilaPresupuesto[];
  let alAgregar: (cuerpo: Cuerpo) => Response;
  let alQuitar: (cuerpo: Cuerpo) => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    versiones = SIN_VERSIONES_DE_LA_OBRA;
    abierto = borradorEnBlanco();
    filas = [];
    alAgregar = (cuerpo) => {
      filas = [...filas, PARED];
      return json({ rev: cuerpo.rev + 1, resumen: resumen({ rev: cuerpo.rev + 1, cambios: 1, total: PARED.total! }), clave: PARED.clave });
    };
    alQuitar = (cuerpo) => {
      filas = filas.filter((f) => f.clave !== cuerpo.clave);
      return json({ rev: cuerpo.rev + 1, resumen: resumen({ rev: cuerpo.rev + 1, cambios: 0 }) });
    };
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/hoja/versiones")) return json(versiones);
      if (url.startsWith("/v1/hoja/borradores") && !url.includes(ID) && metodo === "GET") return json({ borradores: [] });
      if (url === "/v1/hoja/borradores" && metodo === "POST") return json(abierto, 201);
      if (url === `/v1/hoja/borradores/${ID}` && metodo === "GET") return json({ id: ID, base: abierto.base, resumen: abierto.resumen });
      if (url === RUTA_AGREGAR && metodo === "POST") return alAgregar(JSON.parse(String(init?.body)) as Cuerpo);
      if (url === RUTA_QUITAR && metodo === "POST") return alQuitar(JSON.parse(String(init?.body)) as Cuerpo);
      if (url.endsWith("/vistas/presupuesto")) return json(vista(filas));
      if (url.startsWith("/v1/buscar/partidas")) {
        const q = new URL(url, "http://local").searchParams.get("q") ?? "";
        return json(q.toLowerCase().includes("bloq") ? HALLADAS : { ...HALLADAS, resultados: [] });
      }
      return json({ detalle: `ruta inesperada ${metodo} ${url}` }, 500);
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  const escrituras = (ruta: string): Cuerpo[] =>
    fetchFalso.mock.calls
      .filter(([r, init]) => String(r) === ruta && init?.method === "POST")
      .map(([, init]) => JSON.parse(String(init?.body)) as Cuerpo);
  const vistasPedidas = () => fetchFalso.mock.calls.map(([r]) => String(r)).filter((r) => r.includes("/vistas/"));

  function montar() {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: "VIV-80",
      nombreProyecto: "Vivienda de 80 m²",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter initialEntries={["/hoja"]}>
          <Routes>
            <Route path="/hoja" element={<PaginaHoja />} />
            <Route path="/componer" element={<Ubicacion />} />
          </Routes>
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  async function abrirDialogo() {
    const boton = await screen.findByRole("button", { name: "Agregar partida" });
    await userEvent.click(boton);
    return screen.findByRole("dialog", { name: "Agregar partida" });
  }

  async function elegirPared(dialogo: HTMLElement) {
    await userEvent.type(within(dialogo).getByRole("combobox", { name: "Partida" }), "bloq");
    await userEvent.click(await screen.findByRole("option", { name: /OBRA-04/ }));
  }

  test("una obra sin espacio abre en «Presupuesto» y solo pide esa vista", async () => {
    montar();
    const pestana = await screen.findByRole("tab", { name: "Presupuesto" });
    await waitFor(() => expect(pestana).toHaveAttribute("aria-selected", "true"));
    expect(screen.getByRole("tab", { name: "Espacio y metrajes" })).toHaveAttribute("aria-selected", "false");
    await screen.findByText(SIN_RENGLONES);
    expect(vistasPedidas()).toEqual([`/v1/hoja/borradores/${ID}/vistas/presupuesto`]);
  });

  test("una obra con espacio sigue abriendo en «Espacio y metrajes»", async () => {
    abierto = borradorEnBlanco({ espacio_vacio: false });
    montar();
    await screen.findByRole("region", { name: "Estado del borrador" });
    expect(screen.getByRole("tab", { name: "Espacio y metrajes" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Presupuesto" })).toHaveAttribute("aria-selected", "false");
  });

  test("la obra sin versiones lo dice con «obra» y explica cómo empezar por Presupuesto", async () => {
    montar();
    expect(await screen.findByText("Esta obra aún no tiene versiones")).toBeInTheDocument();
    expect(screen.getByText(/Agregue las partidas en «Presupuesto»/)).toBeInTheDocument();
  });

  test("buscar «bloq», elegir OBRA-04 y escribir 210 manda la partida tal cual y la fila aparece", async () => {
    montar();
    const dialogo = await abrirDialogo();
    await elegirPared(dialogo);
    await userEvent.type(within(dialogo).getByRole("textbox", { name: /^Cantidad/ }), "210");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));

    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Agregar partida" })).toBeNull());
    expect(escrituras(RUTA_AGREGAR)).toEqual([{ rev: 0, codigo: "OBRA-04", cantidad: "210", calculo: "", nota: "" }]);
    const tabla = await screen.findByRole("table", { name: "Presupuesto" });
    const fila = within(tabla).getAllByRole("row")[1]!;
    expect(within(fila).getByText("OBRA-04")).toBeInTheDocument();
    expect(within(fila).getByRole("textbox", { name: "Cantidad, Presupuesto fila 1" })).toHaveValue("210");
    // El estado del borrador recibe el resumen nuevo: un cambio sin guardar.
    expect(within(screen.getByRole("region", { name: "Estado del borrador" })).getByText(/1 cambio sin guardar/)).toBeInTheDocument();
    expect(screen.getByText("Se agregó OBRA-04 al presupuesto.")).toBeInTheDocument();
    // El foco vuelve al botón que abrió el diálogo.
    await waitFor(() => expect(screen.getByRole("button", { name: "Agregar partida" })).toHaveFocus());
  });

  test("el cálculo y la nota viajan como se escribieron, con coma decimal", async () => {
    montar();
    const dialogo = await abrirDialogo();
    await elegirPared(dialogo);
    await userEvent.type(within(dialogo).getByRole("textbox", { name: "Cálculo (opcional)" }), "2,5*84");
    await userEvent.type(within(dialogo).getByRole("textbox", { name: "Nota de medición (opcional)" }), "6 m × 35 m de muro");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));
    await waitFor(() =>
      expect(escrituras(RUTA_AGREGAR)).toEqual([
        { rev: 0, codigo: "OBRA-04", cantidad: "", calculo: "2,5*84", nota: "6 m × 35 m de muro" },
      ]),
    );
  });

  test("el campo «Cálculo» tiene su ayuda y, escrito sin cantidad, dice que la cantidad sale del cálculo", async () => {
    montar();
    const dialogo = await abrirDialogo();
    const calculo = within(dialogo).getByRole("textbox", { name: "Cálculo (opcional)" });
    expect(calculo).toHaveAccessibleDescription(expect.stringContaining("Por ejemplo 6*3-2 o 2,5*4"));
    await userEvent.type(calculo, "6*35");
    await userEvent.tab();
    expect(within(dialogo).getByRole("textbox", { name: /^Cantidad/ })).toHaveAccessibleDescription(
      expect.stringContaining("Si la deja vacía, Sílice la toma del resultado del cálculo al agregar."),
    );
  });

  test("el 422 del cálculo se muestra junto al campo «Cálculo» y el diálogo sigue abierto", async () => {
    alAgregar = () => json({ detalle: CALCULO_NO_CUADRA }, 422);
    montar();
    const dialogo = await abrirDialogo();
    await elegirPared(dialogo);
    await userEvent.type(within(dialogo).getByRole("textbox", { name: /^Cantidad/ }), "15");
    await userEvent.type(within(dialogo).getByRole("textbox", { name: "Cálculo (opcional)" }), "6*3-2");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));

    const calculo = within(dialogo).getByRole("textbox", { name: "Cálculo (opcional)" });
    await waitFor(() => expect(calculo).toHaveAttribute("aria-invalid", "true"));
    expect(calculo).toHaveAccessibleDescription(expect.stringContaining(CALCULO_NO_CUADRA));
    expect(within(dialogo).getByRole("textbox", { name: /^Cantidad/ })).not.toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("dialog", { name: "Agregar partida" })).toBeInTheDocument();
    expect(screen.queryByRole("table", { name: "Presupuesto" })).toBeNull();
  });

  test("una cantidad mal escrita sin cálculo se marca en «Cantidad»", async () => {
    alAgregar = () =>
      json({ detalle: "Use la coma para los decimales: por ejemplo 2,5. El punto separa los miles: 1.234,56." }, 422);
    montar();
    const dialogo = await abrirDialogo();
    await elegirPared(dialogo);
    await userEvent.type(within(dialogo).getByRole("textbox", { name: /^Cantidad/ }), "2.5");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));
    const cantidad = within(dialogo).getByRole("textbox", { name: /^Cantidad/ });
    await waitFor(() => expect(cantidad).toHaveAttribute("aria-invalid", "true"));
    expect(within(dialogo).getByRole("textbox", { name: "Cálculo (opcional)" })).not.toHaveAttribute("aria-invalid", "true");
  });

  test("sin elegir una partida de la lista no se manda nada y lo dice en el campo", async () => {
    montar();
    const dialogo = await abrirDialogo();
    await userEvent.type(within(dialogo).getByRole("textbox", { name: /^Cantidad/ }), "210");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));
    const partida = within(dialogo).getByRole("combobox", { name: "Partida" });
    expect(partida).toHaveAttribute("aria-invalid", "true");
    expect(partida).toHaveAccessibleDescription(expect.stringContaining("Elija la partida de la lista de sugerencias."));
    expect(escrituras(RUTA_AGREGAR)).toEqual([]);
  });

  test("la partida fuera del catálogo (404) se dice en el campo «Partida», tal cual", async () => {
    alAgregar = () => json({ detalle: FUERA_DEL_CATALOGO }, 404);
    montar();
    const dialogo = await abrirDialogo();
    await elegirPared(dialogo);
    await userEvent.type(within(dialogo).getByRole("textbox", { name: /^Cantidad/ }), "210");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));
    const partida = within(dialogo).getByRole("combobox", { name: "Partida" });
    await waitFor(() => expect(partida).toHaveAttribute("aria-invalid", "true"));
    expect(partida).toHaveAccessibleDescription(expect.stringContaining(FUERA_DEL_CATALOGO));
  });

  test("sin tasa del BCV (409) el diálogo lo dice tal cual y no agrega nada", async () => {
    alAgregar = () => json({ detalle: SIN_TASA }, 409);
    montar();
    const dialogo = await abrirDialogo();
    await elegirPared(dialogo);
    await userEvent.type(within(dialogo).getByRole("textbox", { name: /^Cantidad/ }), "210");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Agregar al presupuesto" }));
    expect(await within(dialogo).findByText(SIN_TASA)).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Agregar partida" })).toBeInTheDocument();
  });

  test("«Componer una partida nueva» lleva a Componer con el código y la vuelta a la Hoja", async () => {
    montar();
    const dialogo = await abrirDialogo();
    await userEvent.type(within(dialogo).getByRole("combobox", { name: "Partida" }), "OBRA-99");
    await userEvent.click(await screen.findByRole("option", { name: "Componer una partida nueva con el código «OBRA-99»" }));
    expect(await screen.findByTestId("ubicacion")).toHaveTextContent("/componer?codigo=OBRA-99&volver=hoja");
  });

  test("Esc cierra el diálogo sin mandar nada y el foco vuelve a «Agregar partida»", async () => {
    montar();
    await abrirDialogo();
    expect(screen.getByRole("combobox", { name: "Partida" })).toHaveFocus();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Agregar partida" })).toBeNull());
    await waitFor(() => expect(screen.getByRole("button", { name: "Agregar partida" })).toHaveFocus());
    expect(escrituras(RUTA_AGREGAR)).toEqual([]);
  });

  test("«Quitar» pide confirmación y solo entonces quita; la fila del espacio no tiene «Quitar»", async () => {
    versiones = { ...SIN_VERSIONES_DE_LA_OBRA, por_omision: "VIV-001", versiones: [{ codigo: "VIV-001", fecha: "2026-10-25", motivo: "", origen: "", vigente: true, descartada: false, cambios: 0 }] };
    abierto = {
      ...borradorEnBlanco(),
      base: { proyecto: "VIV-80", version: "VIV-001", vigente: "VIV-001", lista: "Lista de la carpeta", espacio_de: "VIV-001", solo_lectura: false, moneda: "Bs" },
    };
    filas = [LLAVE_DEL_ESPACIO, { ...PARED, calculo: "6*35", nota: "6 m × 35 m de muro" }];
    montar();
    const tabla = await screen.findByRole("table", { name: "Presupuesto" });
    const [, delEspacio, aMano] = within(tabla).getAllByRole("row");
    expect(within(delEspacio!).queryByRole("button", { name: /^Quitar/ })).toBeNull();
    expect(within(delEspacio!).getByText("Sale del espacio")).toBeInTheDocument();
    expect(within(aMano!).getByText("6*35")).toBeInTheDocument();
    expect(within(aMano!).getByText("6 m × 35 m de muro")).toBeInTheDocument();

    const quitar = within(aMano!).getByRole("button", { name: "Quitar OBRA-04, Presupuesto fila 2" });
    await userEvent.click(quitar);
    const confirmacion = await screen.findByRole("alertdialog", { name: "Quitar partida" });
    expect(confirmacion).toHaveAccessibleDescription(CONFIRMAR_QUITAR);
    // Cancelar no quita nada y devuelve el foco al botón de la fila.
    await userEvent.click(within(confirmacion).getByRole("button", { name: "Cancelar" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    await waitFor(() => expect(quitar).toHaveFocus());
    expect(escrituras(RUTA_QUITAR)).toEqual([]);

    await userEvent.click(quitar);
    const otra = await screen.findByRole("alertdialog", { name: "Quitar partida" });
    await userEvent.click(within(otra).getByRole("button", { name: "Quitar" }));
    await waitFor(() => expect(escrituras(RUTA_QUITAR)).toEqual([{ rev: 0, clave: "OBRA-04|a-mano:1" }]));
    await waitFor(() => expect(screen.queryByText("Pared de bloques de arcilla de 15 cm")).toBeNull());
    expect(screen.getByText("Se quitó OBRA-04 del presupuesto.")).toBeInTheDocument();
  });

  test("la columna «Cómo se midió» va tras la cantidad y la de «Quitar» al final", async () => {
    filas = [LLAVE_DEL_ESPACIO, PARED];
    abierto = borradorEnBlanco({ espacio_vacio: true });
    montar();
    const tabla = await screen.findByRole("table", { name: "Presupuesto" });
    expect(within(tabla).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([
      "Partida",
      "Descripción",
      "Unidad",
      "Cantidad",
      "Cómo se midió",
      "Precio unitario",
      "Total",
      "Estado",
      "Quitar",
    ]);
    const aMano = within(tabla).getAllByRole("row")[2]!;
    expect(within(aMano).getByText("Sin cálculo")).toBeInTheDocument();
  });

  test("el total de una obra en bolívares dice «Bs» en el estado y en el presupuesto", async () => {
    filas = [PARED];
    abierto = borradorEnBlanco({ total: { texto: "17913.00", exacto: "17913" } });
    montar();
    await screen.findByRole("table", { name: "Presupuesto" });
    expect(within(screen.getByRole("region", { name: "Estado del borrador" })).getByText(/Total 17\.913,00 Bs/)).toBeInTheDocument();
    expect(screen.getByText("Total del presupuesto").closest("p")).toHaveTextContent("Total del presupuesto 17.913,00 Bs");
  });

  test("un presupuesto vacío dice el mensaje del servidor y ofrece «Agregar partida»", async () => {
    montar();
    expect(await screen.findByText(SIN_RENGLONES)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Agregar partida" })).toBeInTheDocument();
  });
});
