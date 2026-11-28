import { fileURLToPath } from "node:url";
import { configure, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRef, useState } from "react";
import { MemoryRouter } from "react-router";
import * as sass from "sass";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../../api/tipos";
import { ProveedorDeAnuncios } from "../../../comun/Anunciador";
import { vaciarRecursosParaPruebas } from "../../../comun/recurso";
import { ContextoAplicacion } from "../../../shell/contexto";
import type { Aplicacion } from "../../../shell/contexto";
import { vistaApu, vistaPresupuesto } from "../datosDePrueba";
import type { BorradorAbierto, FilaPresupuesto, Resumen } from "../logica";
import { AYUDA_OBJETIVO } from "../ObjetivoDeMercado";
import { InspectorDePartida, resumenDeMedicion } from "./InspectorDePartida";
import type { PropiedadesDeInspectorDePartida } from "./InspectorDePartida";

// Lote B1-6 (ficha-b1 §1.6, §1.10 prueba 7 y §4): inspector lateral acoplado de la partida.
configure({ asyncUtilTimeout: 5000 });

const json = (cuerpo: unknown, estado = 200) =>
  new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });

const ARMA: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "leer_proyecto"],
  modo_entrega: false,
};

const REVISA: SesionRespuesta = {
  ...ARMA,
  login: "rita",
  nombre: "Rita Gómez",
  roles: ["revisa"],
  acciones: ["leer_proyecto"],
};

const ID = "id-borrador-b1-6";

function crearResumen(parcial: Partial<Resumen> = {}): Resumen {
  return {
    rev: 2,
    moneda: "USD",
    total: { texto: "2703.86", exacto: "2703.8602323440440333" },
    cambios: 0,
    pendientes_catalogo: 1,
    hallazgos: [
      { severidad: "ERROR", total: 1 },
      { severidad: "ADVERTENCIA", total: 1 },
    ],
    hay_plan: true,
    version_mas_nueva: null,
    guardado_como: null,
    espacio_vacio: true,
    ...parcial,
  };
}

function crearBorrador(parcial: { rev?: number; soloLectura?: boolean } = {}): BorradorAbierto {
  return {
    id: ID,
    base: {
      proyecto: "OF-001",
      version: "001",
      vigente: "001",
      lista: "Lista",
      espacio_de: "001",
      solo_lectura: parcial.soloLectura ?? false,
      moneda: "USD",
    },
    resumen: crearResumen({ rev: parcial.rev ?? 2 }),
    instantanea: { creadas: 0, mensaje: null },
  };
}

function filaEditable(extra: Partial<FilaPresupuesto> = {}): FilaPresupuesto {
  const base = vistaPresupuesto().filas[0]!;
  return {
    ...base,
    clave: "AF-LLAVE|a-mano:1",
    quitable: true,
    ...extra,
  };
}

describe("InspectorDePartida (lote B1-6)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let responderApu: (url: URL) => Response | Promise<Response>;
  let responderObjetivos: (url: URL) => Response | Promise<Response>;
  let responderQuitar: (cuerpo: { rev: number; clave: string }) => Response | Promise<Response>;
  let responderCantidades: (cuerpo: { rev: number; filas: Array<{ clave: string; cantidad: string }> }) => Response | Promise<Response>;

  beforeEach(() => {
    vaciarRecursosParaPruebas();
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    responderApu = () => json(vistaApu());
    responderObjetivos = () =>
      json({
        objetivos: [{ codigo: "AF-LLAVE", precio: "15.00", moneda: "USD", margen: "13.6" }],
      });
    responderQuitar = (cuerpo) =>
      json({
        rev: cuerpo.rev + 1,
        resumen: crearResumen({ rev: cuerpo.rev + 1, cambios: 1 }),
      });
    responderCantidades = (cuerpo) =>
      json({
        rev: cuerpo.rev + 1,
        resumen: crearResumen({ rev: cuerpo.rev + 1, cambios: 1 }),
      });

    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = new URL(String(ruta), "http://silice.local");
      const metodo = init?.method ?? "GET";
      if (url.pathname === `/v1/hoja/borradores/${ID}/vistas/apu` && metodo === "GET") {
        return responderApu(url);
      }
      if (url.pathname === "/v1/mercado/objetivos" && metodo === "GET") {
        return responderObjetivos(url);
      }
      if (url.pathname === `/v1/hoja/borradores/${ID}/partidas/quitar` && metodo === "POST") {
        return responderQuitar(JSON.parse(String(init?.body)) as { rev: number; clave: string });
      }
      if (url.pathname === `/v1/hoja/borradores/${ID}/cantidades` && metodo === "PUT") {
        return responderCantidades(
          JSON.parse(String(init?.body)) as { rev: number; filas: Array<{ clave: string; cantidad: string }> },
        );
      }
      return new Response(null, { status: 404 });
    });
  });

  afterEach(() => {
    vaciarRecursosParaPruebas();
    vi.unstubAllGlobals();
  });

  function montar(
    opciones: {
      sesion?: SesionRespuesta;
      props?: Partial<PropiedadesDeInspectorDePartida>;
    } = {},
  ) {
    const sesion = opciones.sesion ?? ARMA;
    const aplicacion: Aplicacion = {
      sesion,
      proyecto: "OF-001",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    const props: PropiedadesDeInspectorDePartida = {
      borrador: crearBorrador(),
      fila: filaEditable(),
      puedeEditar: sesion.acciones.includes("editar_hoja"),
      alCerrar: vi.fn(),
      alAceptar: vi.fn(),
      alQuitar: vi.fn(),
      alAusente: vi.fn(),
      ...opciones.props,
    };

    const vista = render(
      <MemoryRouter>
        <ContextoAplicacion.Provider value={aplicacion}>
          <ProveedorDeAnuncios>
            <InspectorDePartida {...props} />
          </ProveedorDeAnuncios>
        </ContextoAplicacion.Provider>
      </MemoryRouter>,
    );
    return { ...vista, props, aplicacion };
  }

  test("cerrado (sin fila) no pinta ninguna región complementaria", () => {
    montar({ props: { fila: null } });
    expect(screen.queryByRole("complementary")).toBeNull();
  });

  test("prueba 7 de §1.10: el foco entra al h2, Tab puede salir (no atrapa el foco), «Cerrar» está a la vista y Esc devuelve el foco a la celda que lo abrió", async () => {
    const u = userEvent.setup();
    const fila = filaEditable();

    function BancoConCelda() {
      const [abierta, setAbierta] = useState<FilaPresupuesto | null>(null);
      const refCelda = useRef<HTMLTableCellElement>(null);
      const [celda, setCelda] = useState<HTMLElement | null>(null);
      return (
        <div>
          <table role="grid" aria-label="Presupuesto">
            <tbody>
              <tr>
                <td
                  ref={refCelda}
                  role="gridcell"
                  tabIndex={0}
                  onClick={() => {
                    setCelda(refCelda.current);
                    setAbierta(fila);
                  }}
                >
                  AF-LLAVE
                </td>
              </tr>
            </tbody>
          </table>
          <InspectorDePartida
            borrador={crearBorrador()}
            fila={abierta}
            celdaOrigen={celda}
            alCerrar={() => setAbierta(null)}
          />
          <button type="button">Control después del inspector</button>
        </div>
      );
    }

    const aplicacion: Aplicacion = {
      sesion: ARMA,
      proyecto: "OF-001",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };

    render(
      <MemoryRouter>
        <ContextoAplicacion.Provider value={aplicacion}>
          <ProveedorDeAnuncios>
            <BancoConCelda />
          </ProveedorDeAnuncios>
        </ContextoAplicacion.Provider>
      </MemoryRouter>,
    );

    const celda = screen.getByRole("gridcell", { name: "AF-LLAVE" });
    await u.click(celda);

    const panel = screen.getByRole("complementary", { name: "AF-LLAVE · Llave de paso · unidad" });
    const titulo = within(panel).getByRole("heading", { level: 2, name: "AF-LLAVE · Llave de paso · unidad" });
    expect(titulo).toHaveFocus();

    const botonCerrar = within(panel).getByRole("button", { name: "Cerrar" });
    expect(botonCerrar).toBeVisible();

    // No atrapa el foco cuando va acoplado: Shift+Tab desde el h2 sale a la celda anterior en el DOM.
    await u.tab({ shift: true });
    expect(celda).toHaveFocus();

    // De vuelta dentro del panel, Esc lo cierra y devuelve el foco a la celda que lo abrió.
    botonCerrar.focus();
    expect(botonCerrar).toHaveFocus();
    await u.keyboard("{Escape}");

    expect(screen.queryByRole("complementary")).toBeNull();
    expect(celda).toHaveFocus();
  });

  test("pulsar «Cerrar» también cierra el inspector y devuelve el foco a la celda recibida por props", async () => {
    const u = userEvent.setup();
    const celdaExterna = document.createElement("button");
    celdaExterna.textContent = "Celda AF-LLAVE";
    document.body.appendChild(celdaExterna);

    try {
      const { props } = montar({ props: { celdaOrigen: celdaExterna } });
      const panel = screen.getByRole("complementary", { name: "AF-LLAVE · Llave de paso · unidad" });
      await u.click(within(panel).getByRole("button", { name: "Cerrar" }));
      expect(props.alCerrar).toHaveBeenCalledTimes(1);
      expect(celdaExterna).toHaveFocus();
    } finally {
      celdaExterna.remove();
    }
  });

  test("muestra cómo se midió (cálculo, nota u origen), la cantidad calculada y «Volver a la calculada»", async () => {
    const u = userEvent.setup();
    const alVolverALaCalculada = vi.fn();
    const fila = filaEditable({
      cantidad: "5",
      cantidad_calculada: "3",
      escrita: true,
      calculo: "6*0,5",
      nota: "Tramo norte de la planta baja",
    });

    montar({
      props: {
        fila,
        alVolverALaCalculada,
      },
    });

    const panel = screen.getByRole("complementary", { name: "AF-LLAVE · Llave de paso · unidad" });
    expect(within(panel).getByText("6*0,5")).toBeInTheDocument();
    expect(within(panel).getByText("Tramo norte de la planta baja")).toBeInTheDocument();
    expect(within(panel).getByText(/3 unidad/)).toBeInTheDocument();

    const botonVolver = within(panel).getByRole("button", { name: "Volver a la calculada" });
    await u.click(botonVolver);
    expect(alVolverALaCalculada).toHaveBeenCalledWith("AF-LLAVE|a-mano:1", "3");
  });

  test("si no se pasa alVolverALaCalculada, «Volver a la calculada» manda PUT a /cantidades con la cantidad calculada", async () => {
    const u = userEvent.setup();
    const fila = filaEditable({
      cantidad: "5",
      cantidad_calculada: "3",
      escrita: true,
      calculo: null,
      nota: null,
    });

    const { props } = montar({ props: { fila } });
    const panel = screen.getByRole("complementary", { name: "AF-LLAVE · Llave de paso · unidad" });
    expect(within(panel).getByText("Medida sin cálculo; cantidad escrita a mano")).toBeInTheDocument();

    await u.click(within(panel).getByRole("button", { name: "Volver a la calculada" }));

    await waitFor(() => {
      const llamadasPut = fetchFalso.mock.calls.filter(
        ([r, init]) => String(r).endsWith(`/v1/hoja/borradores/${ID}/cantidades`) && init?.method === "PUT",
      );
      expect(llamadasPut).toHaveLength(1);
      expect(JSON.parse(String(llamadasPut[0]?.[1]?.body))).toEqual({
        rev: 2,
        filas: [{ clave: "AF-LLAVE|a-mano:1", cantidad: "3" }],
      });
    });
    expect(props.alAceptar).toHaveBeenCalledTimes(1);
  });

  test("muestra el precio unitario y el total exactos con MontoExacto en línea y «Pendiente» cuando faltan", () => {
    const { rerender, aplicacion, props } = montar();
    const panel = screen.getByRole("complementary", { name: "AF-LLAVE · Llave de paso · unidad" });
    expect(within(panel).getByText("13,20 USD (exacto: 13,198738025 USD)")).toBeInTheDocument();
    expect(within(panel).getByText("39,60 USD (exacto: 39,596214075 USD)")).toBeInTheDocument();

    const filaSinPrecio = vistaPresupuesto().filas[1]!;
    rerender(
      <MemoryRouter>
        <ContextoAplicacion.Provider value={aplicacion}>
          <ProveedorDeAnuncios>
            <InspectorDePartida {...props} fila={filaSinPrecio} />
          </ProveedorDeAnuncios>
        </ContextoAplicacion.Provider>
      </MemoryRouter>,
    );

    const panelSalida = screen.getByRole("complementary", { name: "AF-SALIDA · Salida de agua · unidad" });
    expect(within(panelSalida).getAllByText("Pendiente")).toHaveLength(2);
  });

  test("muestra el objetivo de mercado formateado en es-VE con su margen y el EditorDeApu de la partida", async () => {
    montar();
    const panel = screen.getByRole("complementary", { name: "AF-LLAVE · Llave de paso · unidad" });

    expect(await within(panel).findByText("15,00 · margen +13,6 %")).toBeInTheDocument();
    expect(await within(panel).findByText("Llave de bola PVC 1/2")).toBeInTheDocument();
    expect(within(panel).getByRole("heading", { name: "Cierre de partida" })).toBeInTheDocument();
  });

  test("al pulsar «Quitar del presupuesto» abre el Dialogo destructivo con foco inicial en «Cancelar», y al confirmar manda POST a /partidas/quitar", async () => {
    const u = userEvent.setup();
    const { props } = montar();
    const panel = screen.getByRole("complementary", { name: "AF-LLAVE · Llave de paso · unidad" });

    const botonQuitar = within(panel).getByRole("button", { name: "Quitar del presupuesto" });
    await u.click(botonQuitar);

    const dialogo = screen.getByRole("dialog", { name: "Quitar partida" });
    expect(dialogo).toHaveTextContent("¿Quitar AF-LLAVE del presupuesto? Lo puede descartar antes de guardar.");

    const botonCancelar = within(dialogo).getByRole("button", { name: "Cancelar" });
    expect(botonCancelar).toHaveFocus();

    // Cancelar cierra el diálogo sin enviar POST y devuelve el foco al botón de quitar del inspector.
    await u.click(botonCancelar);
    expect(screen.queryByRole("dialog", { name: "Quitar partida" })).toBeNull();
    expect(botonQuitar).toHaveFocus();
    expect(
      fetchFalso.mock.calls.filter(([r, init]) => String(r).endsWith("/partidas/quitar") && init?.method === "POST"),
    ).toHaveLength(0);

    // Confirmar envía el POST a /partidas/quitar con rev y clave.
    await u.click(botonQuitar);
    const dialogoConfirmar = screen.getByRole("dialog", { name: "Quitar partida" });
    await u.click(within(dialogoConfirmar).getByRole("button", { name: "Quitar" }));

    await waitFor(() => {
      const llamadasPost = fetchFalso.mock.calls.filter(
        ([r, init]) => String(r).endsWith(`/v1/hoja/borradores/${ID}/partidas/quitar`) && init?.method === "POST",
      );
      expect(llamadasPost).toHaveLength(1);
      expect(JSON.parse(String(llamadasPost[0]?.[1]?.body))).toEqual({
        rev: 2,
        clave: "AF-LLAVE|a-mano:1",
      });
    });

    expect(props.alAceptar).toHaveBeenCalledTimes(1);
    expect(props.alQuitar).toHaveBeenCalledWith("AF-LLAVE", expect.objectContaining({ rev: 3 }), "AF-LLAVE|a-mano:1");
    expect(props.alCerrar).toHaveBeenCalledTimes(1);
  });

  test("si POST /partidas/quitar responde 422, muestra la alerta con el detalle del servidor y mantiene abierto el inspector", async () => {
    const u = userEvent.setup();
    responderQuitar = () => json({ detalle: "Esa fila ya no está en el presupuesto." }, 422);
    const { props } = montar();
    const panel = screen.getByRole("complementary", { name: "AF-LLAVE · Llave de paso · unidad" });

    await u.click(within(panel).getByRole("button", { name: "Quitar del presupuesto" }));
    const dialogo = screen.getByRole("dialog", { name: "Quitar partida" });
    await u.click(within(dialogo).getByRole("button", { name: "Quitar" }));

    const alerta = await within(panel).findByRole("alert");
    expect(alerta).toHaveTextContent("Esa fila ya no está en el presupuesto.");
    expect(props.alCerrar).not.toHaveBeenCalled();
  });

  test("en solo lectura o para una fila del espacio (quitable: false) no ofrece «Volver a la calculada» ni «Quitar del presupuesto»", () => {
    const filaDelEspacio = vistaPresupuesto().filas[1]!; // escrita: true, quitable: false
    const { rerender, aplicacion, props } = montar({
      props: { fila: filaDelEspacio },
    });

    const panel = screen.getByRole("complementary", { name: "AF-SALIDA · Salida de agua · unidad" });
    expect(within(panel).getByRole("button", { name: "Volver a la calculada" })).toBeInTheDocument();
    expect(within(panel).queryByRole("button", { name: "Quitar del presupuesto" })).toBeNull();

    rerender(
      <MemoryRouter>
        <ContextoAplicacion.Provider value={{ ...aplicacion, sesion: REVISA }}>
          <ProveedorDeAnuncios>
            <InspectorDePartida {...props} fila={filaEditable({ escrita: true })} puedeEditar={false} />
          </ProveedorDeAnuncios>
        </ContextoAplicacion.Provider>
      </MemoryRouter>,
    );

    const panelLectura = screen.getByRole("complementary", { name: "AF-LLAVE · Llave de paso · unidad" });
    expect(within(panelLectura).queryByRole("button", { name: "Volver a la calculada" })).toBeNull();
    expect(within(panelLectura).queryByRole("button", { name: "Quitar del presupuesto" })).toBeNull();
  });

  test("resumenDeMedicion distingue cálculo, tramos, espacio y cantidad escrita a mano", () => {
    expect(resumenDeMedicion({ quitable: true, calculo: null, nota: null, escrita: true })).toBe(
      "Medida sin cálculo; cantidad escrita a mano",
    );
    expect(resumenDeMedicion({ quitable: true, calculo: "6*3", nota: null, escrita: false })).toBe(
      "Con cálculo: 6*3",
    );
    expect(resumenDeMedicion({ quitable: false, calculo: null, nota: null, de_tramo: true, escrita: false })).toBe(
      "Sale de los tramos",
    );
    expect(resumenDeMedicion({ quitable: false, calculo: null, nota: null, escrita: false })).toBe(
      "Sale del espacio",
    );
  });

  test("estilos de inspector.scss: compila con Sass, usa solo tokens --silice-*, sin font-size en px y con minmax(0, 1fr)", () => {
    // En una variable: con el texto literal, Vite reescribe new URL(...) como un recurso y deja de ser file:.
    const relativa = "./inspector.scss";
    const css = sass.compile(fileURLToPath(new URL(relativa, import.meta.url))).css;
    expect(css).toMatch(/\.silice-inspector\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)/);
    expect(css).not.toMatch(/font-size:\s*\d+px/);
    expect(css).not.toMatch(/#[0-9a-fA-F]{3,8}/);
  });

  test("objetivo de mercado: margen negativo con U+2212, otra moneda (equivalencia y sin tasa), sin precio unitario, error 503 y cuenta que revisa", async () => {
    responderObjetivos = () =>
      json({
        objetivos: [
          {
            codigo: "AF-LLAVE",
            precio: "1980.00",
            moneda: "USD",
            margen: "-4.6",
            equivalencia: null,
            sin_tasa: null,
          },
        ],
      });
    const { rerender, aplicacion, props } = montar({ sesion: REVISA });
    const panel = screen.getByRole("complementary", { name: "AF-LLAVE · Llave de paso · unidad" });
    expect(await within(panel).findByText("1.980,00 · margen −4,6 %")).toBeInTheDocument();
    expect(within(panel).getByText(AYUDA_OBJETIVO)).toBeInTheDocument();

    // Equivalencia en otra moneda y sin precio unitario.
    vaciarRecursosParaPruebas();
    responderObjetivos = () =>
      json({
        objetivos: [
          {
            codigo: "AF-SALIDA",
            precio: "31.50",
            moneda: "USD",
            margen: null,
            equivalencia: {
              precio_original: "31.50",
              moneda_original: "USD",
              tasa: "36.50",
              fecha_tasa: "2026-10-20",
              fuente_tasa: "importacion:bcv-venta",
              fuente_legible: "BCV, publicación del 20/10/2026",
              convertido: "1149.75",
              moneda: "Bs",
              operacion: "×",
            },
            sin_tasa: null,
          },
        ],
      });
    const filaSalida = { ...vistaPresupuesto().filas[1]!, pu: null };
    rerender(
      <MemoryRouter>
        <ContextoAplicacion.Provider value={aplicacion}>
          <ProveedorDeAnuncios>
            <InspectorDePartida {...props} borrador={{ ...crearBorrador(), resumen: crearResumen({ moneda: "Bs" }) }} fila={filaSalida} />
          </ProveedorDeAnuncios>
        </ContextoAplicacion.Provider>
      </MemoryRouter>,
    );
    const panelSalida = screen.getByRole("complementary", { name: "AF-SALIDA · Salida de agua · unidad" });
    expect(
      await within(panelSalida).findByText(
        "31,50 USD × 36,50 Bs/USD (BCV, publicación del 20/10/2026) = 1.149,75 Bs · sin precio unitario, sin margen",
      ),
    ).toBeInTheDocument();

    // Sin tasa del BCV ni error 503 rompen el inspector.
    responderObjetivos = () => json({ detalle: "No se pudo leer el estudio." }, 503);
    const otra = filaEditable({ clave: "ERR|1", partida: "ERR", descripcion: "Partida sin objetivo" });
    rerender(
      <MemoryRouter>
        <ContextoAplicacion.Provider value={aplicacion}>
          <ProveedorDeAnuncios>
            <InspectorDePartida {...props} fila={otra} />
          </ProveedorDeAnuncios>
        </ContextoAplicacion.Provider>
      </MemoryRouter>,
    );
    expect(await within(screen.getByRole("complementary")).findByText("Sin objetivo de mercado")).toBeInTheDocument();
  });

  test("en solo lectura (quien revisa o borrador solo_lectura) el APU dentro del inspector no muestra controles que escriban", async () => {
    const { rerender, aplicacion, props } = montar({ sesion: REVISA, props: { puedeEditar: false } });
    const panel = screen.getByRole("complementary", { name: "AF-LLAVE · Llave de paso · unidad" });
    expect(await within(panel).findByText("Cierre de partida")).toBeInTheDocument();
    expect(within(panel).queryAllByRole("textbox")).toEqual([]);
    expect(within(panel).queryByRole("button", { name: "Agregar línea" })).toBeNull();
    expect(within(panel).queryByRole("button", { name: /^Quitar/ })).toBeNull();
    expect(within(panel).queryByRole("button", { name: /^Cambiar el insumo/ })).toBeNull();

    rerender(
      <MemoryRouter>
        <ContextoAplicacion.Provider value={aplicacion}>
          <ProveedorDeAnuncios>
            <InspectorDePartida {...props} borrador={crearBorrador({ soloLectura: true })} puedeEditar={false} />
          </ProveedorDeAnuncios>
        </ContextoAplicacion.Provider>
      </MemoryRouter>,
    );
    expect(await within(panel).findByText("Cierre de partida")).toBeInTheDocument();
    expect(within(panel).queryAllByRole("textbox")).toEqual([]);
  });

  test("si el servidor devuelve el APU de otra partida, el inspector avisa sin abrir la otra", async () => {
    responderApu = () => json({ ...vistaApu(), seleccionada: "E-02", detalle: { ...vistaApu().detalle!, codigo: "E-02", descripcion: "Relleno" } });
    montar();
    const panel = screen.getByRole("complementary", { name: "AF-LLAVE · Llave de paso · unidad" });
    expect(await within(panel).findByText("AF-LLAVE no tiene análisis de precio en este presupuesto.")).toBeInTheDocument();
    expect(within(panel).queryAllByRole("textbox")).toEqual([]);
    expect(within(panel).queryByText("Relleno")).toBeNull();
  });

  test("cambiar el insumo de una línea del APU dentro del inspector manda POST .../insumo y avisa", async () => {
    const u = userEvent.setup();
    const previa = fetchFalso.getMockImplementation()!;
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = new URL(String(ruta), "http://silice.local");
      if (url.pathname === `/v1/hoja/borradores/${ID}/insumos`) {
        return json({ insumos: [{ codigo: "MAT-010", descripcion: "Llave de bola PVC 3/4", unidad: "pieza", precio: { texto: "8.10", exacto: "8.10" } }], hay_mas: false });
      }
      if (url.pathname === `/v1/hoja/borradores/${ID}/apu/AF-LLAVE/insumo` && init?.method === "POST") {
        const c = JSON.parse(String(init.body)) as { rev: number };
        return json({ rev: c.rev + 1, resumen: crearResumen({ rev: c.rev + 1, cambios: 1 }), apu: vistaApu() });
      }
      return previa(ruta, init);
    });
    const { props } = montar();
    const panel = screen.getByRole("complementary", { name: "AF-LLAVE · Llave de paso · unidad" });
    const botonCambiar = await within(panel).findByRole("button", { name: "Cambiar el insumo de Llave de bola PVC 1/2, Materiales fila 1" });
    await u.click(botonCambiar);

    const dialogo = screen.getByRole("dialog", { name: "Cambiar el insumo de Llave de bola PVC 1/2" });
    await u.type(within(dialogo).getByRole("combobox", { name: "Insumo" }), "llave");
    await u.click(await screen.findByRole("option", { name: /Llave de bola PVC 3\/4/ }));
    await u.click(within(dialogo).getByRole("button", { name: "Usar este insumo" }));

    expect(await within(panel).findByText("Insumo de la línea 1 cambiado: Llave de bola PVC 3/4.")).toBeInTheDocument();
    expect(props.alAceptar).toHaveBeenCalledTimes(1);
  });
});
