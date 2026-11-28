import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { act, configure, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect, useRef, useState } from "react";
import * as sass from "sass";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../../api/tipos";
import { ProveedorDeAnuncios } from "../../../comun/Anunciador";
import { Grilla } from "../../../comun/Grilla";
import type { ColumnaDeGrilla } from "../../../comun/Grilla";
import { MENSAJE_CIFRA, MENSAJE_CIFRA_VACIA } from "../../../indicadores/cifraEscrita";
import { ContextoAplicacion } from "../../../shell/contexto";
import type { Aplicacion } from "../../../shell/contexto";
import { vistaPresupuesto } from "../datosDePrueba";
import type { FilaPresupuesto, Resumen } from "../logica";
import { FilaDeAlta } from "./FilaDeAlta";
import type { PropiedadesDeFilaDeAlta } from "./FilaDeAlta";
import type { ResultadoDePartidaAgregada } from "./altaDePartida";

// Lote B1-8 (ficha-b1 §1.6, §1.7, §1.8 y §1.10 pruebas 4 y 5): fila de alta aislada con casos ficticios.
configure({ asyncUtilTimeout: 5000 });

const ID = "id-borrador-b1-8";
const RUTA_AGREGAR = `/v1/hoja/borradores/${ID}/partidas`;
const CALCULO_NO_CUADRA = "El cálculo da 16 y la cantidad es 15: corrija uno de los dos.";
const FUERA_DEL_CATALOGO = "La partida «OBRA-04» no está en el catálogo: compóngala primero en Componer.";
const SIN_TASA = "No hay tasa del BCV de los últimos 7 días: cárguela en Índices y vuelva a intentar.";
const REV_VIEJO = "El borrador cambió en otra ventana: vuelva a cargarlo.";
const RECARGADO = "Ya se volvió a leer el borrador: puede agregarla otra vez.";
const FALTA =
  "Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). Lo que no guardó se perdió: abra la versión otra vez.";

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "leer_proyecto"],
  modo_entrega: false,
};

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

function resumen(extra: Partial<Resumen> = {}): Resumen {
  const base = vistaPresupuesto();
  return {
    rev: 1,
    moneda: base.moneda,
    total: base.total,
    cambios: 1,
    pendientes_catalogo: 0,
    hallazgos: [],
    hay_plan: false,
    version_mas_nueva: null,
    guardado_como: null,
    espacio_vacio: true,
    ...extra,
  };
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

const EXCAVACION = {
  codigo: "FIC-01",
  descripcion: "Excavación de zanja ficticia a mano",
  puntaje: "0.9137",
  puntaje_corto: "0.91",
  aviso: null,
  composicion: { unidad: "m3", rendimiento: "8.00", materiales: [], equipos: [], mano_obra: [] },
};

function diferida() {
  let soltar: (r: Response) => void = () => undefined;
  const promesa = new Promise<Response>((resolver) => {
    soltar = resolver;
  });
  return { promesa, soltar };
}

type Cuerpo = Record<string, unknown> & { rev: number };

describe("FilaDeAlta (lote B1-8)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();
  let alAgregar: (cuerpo: Cuerpo) => Response | Promise<Response>;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    alAgregar = (cuerpo) =>
      json({
        rev: cuerpo.rev + 1,
        resumen: resumen({ rev: cuerpo.rev + 1, cambios: 1 }),
        clave: `${String(cuerpo.codigo)}|a-mano:1`,
      });
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      const metodo = init?.method ?? "GET";
      if (url === RUTA_AGREGAR && metodo === "POST") {
        return alAgregar(JSON.parse(String(init?.body)) as Cuerpo);
      }
      if (url.startsWith("/v1/buscar/partidas")) {
        const q = new URL(url, "http://local").searchParams.get("q") ?? "";
        return json(q.toLowerCase().includes("bloq") ? HALLADAS : { ...HALLADAS, resultados: [] });
      }
      if (url === "/v1/similares" && metodo === "POST") {
        return json({ propuestas: [EXCAVACION], falla: null, mensaje: null });
      }
      return json({ detalle: `ruta inesperada ${metodo} ${url}` }, 500);
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function montar(extra: Partial<PropiedadesDeFilaDeAlta> = {}) {
    const alAgregada = vi.fn<(r: ResultadoDePartidaAgregada) => void>();
    const alAusente = vi.fn();
    const alReleer = vi.fn(async () => undefined);
    const alCrearPartida = vi.fn();
    const props: PropiedadesDeFilaDeAlta = {
      borradorId: ID,
      revActual: async () => 0,
      alAgregada,
      alAusente,
      alReleer,
      alCrearPartida,
      ...extra,
    };
    const aplicacion: Aplicacion = {
      sesion: SESION,
      proyecto: "OF-001",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    const resultado = render(
      <ContextoAplicacion.Provider value={aplicacion}>
        <ProveedorDeAnuncios>
          <FilaDeAlta {...props} />
        </ProveedorDeAnuncios>
      </ContextoAplicacion.Provider>,
    );
    return { ...resultado, alAgregada, alAusente, alReleer, alCrearPartida, props };
  }

  const escrituras = (ruta = RUTA_AGREGAR): Cuerpo[] =>
    fetchFalso.mock.calls
      .filter(([r, init]) => String(r) === ruta && init?.method === "POST")
      .map(([, init]) => JSON.parse(String(init?.body)) as Cuerpo);

  const pedidosDeParecidas = () =>
    fetchFalso.mock.calls
      .filter(([r, init]) => String(r) === "/v1/similares" && init?.method === "POST")
      .map(([, init]) => JSON.parse(String(init?.body)) as unknown);

  async function elegirPared(u: ReturnType<typeof userEvent.setup>) {
    await u.type(screen.getByRole("combobox", { name: "Partida" }), "bloq");
    await u.click(await screen.findByRole("option", { name: /OBRA-04/ }));
  }

  test("por omisión expone 4 controles en orden visual y tabulación, botón terciario y pliegue cerrado", () => {
    const { container } = montar();

    const partida = screen.getByRole("combobox", { name: "Partida" });
    const cantidad = screen.getByRole("textbox", { name: "Cantidad" });
    const boton = screen.getByRole("button", { name: "Agregar al presupuesto" });
    const pliegue = container.querySelector("details");
    const resumenPliegue = container.querySelector("summary");

    expect(partida).toHaveAccessibleDescription(expect.stringContaining("por ejemplo, bloque"));
    expect(cantidad).toHaveAttribute("inputmode", "decimal");
    expect(cantidad).toHaveAccessibleDescription("Con coma decimal: 50 o 12,5");
    expect(boton).toHaveClass("cds--btn--tertiary");
    expect(boton).not.toHaveClass("cds--btn--primary");
    expect(boton).not.toBeDisabled();
    expect(pliegue).not.toHaveAttribute("open");
    expect(resumenPliegue).toHaveTextContent("Cálculo y nota (opcional): Sin cálculo ni nota. Cambiar");

    // 4 controles propios de decisión (combinados con los 4 de cabecera y grilla dan el tope de 8 de §1.10).
    // Los campos de dentro del pliegue cerrado no están a la vista (el navegador no los pinta ni los tabula) y la
    // ficha los reparte en «Más opciones» (§1.6): jsdom no aplica ese estilo por omisión, así que se descartan aquí.
    const aLaVista = (el: Element) => el.closest("details:not([open])") === null || el.tagName === "SUMMARY";
    const controles = [
      ...screen.queryAllByRole("button"),
      ...screen.queryAllByRole("link"),
      ...screen.queryAllByRole("textbox"),
      ...screen.queryAllByRole("combobox"),
      ...container.querySelectorAll("summary"),
    ].filter(aLaVista);
    expect(controles).toHaveLength(4);
    expect(screen.queryByRole("button", { name: "Buscar parecidas" })).toBeNull();

    // Ninguna región viva con texto ni alertas vacías en reposo.
    const regiones = container.querySelectorAll('[role="status"], [role="alert"], [aria-live]');
    for (const region of regiones) {
      expect(region.textContent?.trim()).toBe("");
    }
    expect(container.querySelectorAll('[role="alert"]')).toHaveLength(0);
  });

  test("prueba 4 de §1.10: al agregar, avisa la partida nueva, la grilla enfoca su Cantidad y hay un anuncio en es-VE", async () => {
    const u = userEvent.setup();
    const columnas: ColumnaDeGrilla<FilaPresupuesto>[] = [
      { clave: "partida", titulo: "Partida", valor: (f) => f.partida },
      { clave: "descripcion", titulo: "Descripción", valor: (f) => f.descripcion },
      { clave: "unidad", titulo: "Unidad", valor: (f) => f.unidad },
      { clave: "cantidad", titulo: "Cantidad", numerica: true, editable: true, valor: (f) => f.cantidad },
    ];

    function ArnesConGrilla() {
      const [filas, setFilas] = useState<FilaPresupuesto[]>(vistaPresupuesto().filas);
      const [focoEnClave, setFocoEnClave] = useState<string | null>(null);
      const contenedor = useRef<HTMLDivElement>(null);

      useEffect(() => {
        if (focoEnClave === null) return;
        const indice = filas.findIndex((f) => f.clave === focoEnClave);
        if (indice < 0) return;
        const celdaCantidad = contenedor.current?.querySelector<HTMLElement>(
          `[data-celda][data-fila="${indice}"][data-columna="3"]`,
        );
        celdaCantidad?.focus();
      }, [filas, focoEnClave]);

      return (
        <div ref={contenedor}>
          <Grilla<FilaPresupuesto>
            etiqueta="Presupuesto"
            columnas={columnas}
            filas={filas}
            idDeFila={(f) => f.clave}
          />
          <FilaDeAlta
            borradorId={ID}
            revActual={async () => 0}
            alAgregada={(resultado) => {
              const nueva: FilaPresupuesto = {
                clave: resultado.clave,
                partida: resultado.codigo,
                descripcion: "Pared de bloques de arcilla de 15 cm",
                unidad: "m2",
                cantidad: "210",
                cantidad_calculada: "210",
                escrita: false,
                pu: { texto: "85.30", exacto: "85.3" },
                total: { texto: "17913.00", exacto: "17913" },
                estado: { severidad: null, texto: "OK" },
                quitable: true,
                nota: null,
                calculo: null,
              };
              setFilas((previas) => [...previas, nueva]);
              setFocoEnClave(resultado.clave);
            }}
            alAusente={vi.fn()}
            alReleer={vi.fn(async () => undefined)}
            alCrearPartida={vi.fn()}
          />
        </div>
      );
    }

    const aplicacion: Aplicacion = {
      sesion: SESION,
      proyecto: "OF-001",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    render(
      <ContextoAplicacion.Provider value={aplicacion}>
        <ProveedorDeAnuncios>
          <ArnesConGrilla />
        </ProveedorDeAnuncios>
      </ContextoAplicacion.Provider>,
    );

    await elegirPared(u);
    await u.type(screen.getByRole("textbox", { name: /^Cantidad/ }), "210");
    await u.click(screen.getByRole("button", { name: "Agregar al presupuesto" }));

    expect(escrituras()).toEqual([{ rev: 0, codigo: "OBRA-04", cantidad: "210", calculo: "", nota: "" }]);
    const grilla = screen.getByRole("grid", { name: "Presupuesto" });
    const filaNueva = await within(grilla).findByRole("row", { name: /OBRA-04/ });
    const celdaCantidad = within(filaNueva).getByRole("gridcell", { name: "210" });
    await waitFor(() => expect(celdaCantidad).toHaveFocus());

    // Anuncio único en la región cortés de Anunciador con el total del servidor formateado en es-VE.
    const anuncios = screen.getAllByRole("status");
    const conTexto = anuncios.filter((n) => (n.textContent ?? "").trim() !== "");
    expect(conTexto).toHaveLength(1);
    expect(conTexto[0]).toHaveTextContent("Se agregó OBRA-04 al presupuesto. Total: 2.703,86 USD.");

    // La fila de alta queda limpia para volver a agregar otra partida.
    expect(screen.getByRole("combobox", { name: "Partida" })).toHaveValue("");
    expect(screen.getByRole("textbox", { name: "Cantidad" })).toHaveValue("");
  });

  test("una partida sin precio incluye el aviso del servidor en el callback y en el anuncio", async () => {
    const u = userEvent.setup();
    const aviso = "La partida «OBRA-04» queda pendiente en el Presupuesto, sin precio.";
    alAgregar = (cuerpo) =>
      json({ rev: cuerpo.rev + 1, resumen: resumen({ rev: cuerpo.rev + 1 }), clave: "OBRA-04|a-mano:1", aviso });

    const { alAgregada } = montar();
    await elegirPared(u);
    await u.type(screen.getByRole("textbox", { name: /^Cantidad/ }), "210");
    await u.click(screen.getByRole("button", { name: "Agregar al presupuesto" }));

    await waitFor(() => expect(alAgregada).toHaveBeenCalledTimes(1));
    expect(alAgregada.mock.calls[0]![0]).toMatchObject({
      codigo: "OBRA-04",
      clave: "OBRA-04|a-mano:1",
      aviso,
    });
    expect(screen.getByRole("status")).toHaveTextContent(
      `Se agregó OBRA-04 al presupuesto. Total: 2.703,86 USD. ${aviso}`,
    );
  });

  test("el pliegue «Cálculo y nota» envía cálculo y nota tal cual y actualiza la ayuda de Cantidad", async () => {
    const u = userEvent.setup();
    const { container, alAgregada } = montar();
    await elegirPared(u);

    await u.click(container.querySelector("summary")!);
    expect(container.querySelector("details")).toHaveAttribute("open");

    const calculo = screen.getByRole("textbox", { name: "Cálculo (opcional)" });
    expect(calculo).toHaveAccessibleDescription(expect.stringContaining("6*3-2"));
    await u.type(calculo, "2,5*84");
    await u.tab();
    expect(screen.getByRole("textbox", { name: /^Cantidad/ })).toHaveAccessibleDescription(
      expect.stringContaining("Si la deja vacía, Sílice la toma del resultado del cálculo al agregar."),
    );

    await u.type(screen.getByRole("textbox", { name: "Nota de medición (opcional)" }), "6 m × 35 m de muro");
    await u.click(screen.getByRole("button", { name: "Agregar al presupuesto" }));

    await waitFor(() => expect(alAgregada).toHaveBeenCalledTimes(1));
    expect(escrituras()).toEqual([
      { rev: 0, codigo: "OBRA-04", cantidad: "", calculo: "2,5*84", nota: "6 m × 35 m de muro" },
    ]);
  });

  test("sin partida elegida muestra error en «Partida», enfoca «Partida» y no manda POST", async () => {
    const u = userEvent.setup();
    montar();

    const cantidad = screen.getByRole("textbox", { name: /^Cantidad/ });
    await u.type(cantidad, "210");
    await u.click(screen.getByRole("button", { name: "Agregar al presupuesto" }));

    const partida = screen.getByRole("combobox", { name: "Partida" });
    expect(partida).toHaveAttribute("aria-invalid", "true");
    expect(partida).toHaveAccessibleDescription(expect.stringContaining("Elija la partida de la lista de sugerencias."));
    await waitFor(() => expect(partida).toHaveFocus());
    expect(cantidad).toHaveValue("210");
    expect(escrituras()).toEqual([]);
  });

  test("con partida elegida y sin cantidad ni cálculo marca «Cantidad», la enfoca y no manda POST", async () => {
    const u = userEvent.setup();
    montar();
    await elegirPared(u);

    await u.click(screen.getByRole("button", { name: "Agregar al presupuesto" }));

    const cantidad = screen.getByRole("textbox", { name: /^Cantidad/ });
    await waitFor(() => expect(cantidad).toHaveAttribute("aria-invalid", "true"));
    expect(cantidad).toHaveAccessibleDescription(expect.stringContaining(MENSAJE_CIFRA_VACIA));
    await waitFor(() => expect(cantidad).toHaveFocus());
    expect(escrituras()).toEqual([]);
  });

  test("validate-input-after-interaction: escribir «50.5» en Cantidad muestra el error solo al salir", async () => {
    const u = userEvent.setup();
    montar();
    await elegirPared(u);

    const cantidad = screen.getByRole("textbox", { name: /^Cantidad/ });
    await u.type(cantidad, "50.5");
    expect(cantidad).toHaveAttribute("aria-invalid", "false");
    expect(screen.queryByText(MENSAJE_CIFRA)).toBeNull();

    await u.tab();
    expect(cantidad).toHaveAttribute("aria-invalid", "true");
    expect(cantidad).toHaveValue("50.5");
    expect(cantidad).toHaveAccessibleDescription(expect.stringContaining(MENSAJE_CIFRA));
  });

  test("prueba 5 de §1.10 (422 en Cantidad): conserva lo escrito, marca con texto y enfoca Cantidad", async () => {
    const u = userEvent.setup();
    alAgregar = () => json({ detalle: "La cantidad no puede ser negativa." }, 422);
    montar();
    await elegirPared(u);

    const cantidad = screen.getByRole("textbox", { name: /^Cantidad/ });
    await u.type(cantidad, "-1");
    await u.click(screen.getByRole("button", { name: "Agregar al presupuesto" }));

    await waitFor(() => expect(cantidad).toHaveAttribute("aria-invalid", "true"));
    expect(cantidad).toHaveValue("-1");
    expect(cantidad).toHaveAccessibleDescription(expect.stringContaining("La cantidad no puede ser negativa."));
    await waitFor(() => expect(cantidad).toHaveFocus());
  });

  test("prueba 5 de §1.10 (422 en Cálculo): abre el pliegue si estaba cerrado, conserva todo y enfoca Cálculo", async () => {
    const u = userEvent.setup();
    alAgregar = () => json({ detalle: CALCULO_NO_CUADRA }, 422);
    const { container } = montar();
    await elegirPared(u);

    const cantidad = screen.getByRole("textbox", { name: /^Cantidad/ });
    await u.type(cantidad, "15");
    await u.click(container.querySelector("summary")!);
    const calculo = screen.getByRole("textbox", { name: "Cálculo (opcional)" });
    await u.type(calculo, "6*3-2");
    await u.click(container.querySelector("summary")!);
    expect(container.querySelector("details")).not.toHaveAttribute("open");

    await u.click(screen.getByRole("button", { name: "Agregar al presupuesto" }));

    await waitFor(() => expect(container.querySelector("details")).toHaveAttribute("open"));
    expect(calculo).toHaveAttribute("aria-invalid", "true");
    expect(calculo).toHaveAccessibleDescription(expect.stringContaining(CALCULO_NO_CUADRA));
    expect(calculo).toHaveValue("6*3-2");
    expect(cantidad).toHaveValue("15");
    expect(cantidad).toHaveAttribute("aria-invalid", "false");
    await waitFor(() => expect(calculo).toHaveFocus());
  });

  test("un segundo clic mientras se envía no manda dos POST", async () => {
    const u = userEvent.setup();
    const enVuelo = diferida();
    alAgregar = () => enVuelo.promesa;
    const { alAgregada } = montar();
    await elegirPared(u);
    await u.type(screen.getByRole("textbox", { name: /^Cantidad/ }), "50");

    const boton = screen.getByRole("button", { name: "Agregar al presupuesto" });
    fireEvent.click(boton);
    fireEvent.click(boton);

    await waitFor(() => expect(escrituras()).toHaveLength(1));
    expect(boton).toBeDisabled();
    fireEvent.click(boton);
    expect(escrituras()).toHaveLength(1);

    await act(async () => {
      enVuelo.soltar(
        json({
          rev: 1,
          resumen: resumen({ rev: 1 }),
          clave: "OBRA-04|a-mano:1",
        }),
      );
    });

    await waitFor(() => expect(alAgregada).toHaveBeenCalledTimes(1));
    expect(escrituras()).toHaveLength(1);
  });

  test("404 fuera del catálogo marca Partida tal cual y 409 sin tasa avisa con palabra de gravedad", async () => {
    const u = userEvent.setup();
    alAgregar = () => json({ detalle: FUERA_DEL_CATALOGO }, 404);
    montar();
    await elegirPared(u);
    await u.type(screen.getByRole("textbox", { name: /^Cantidad/ }), "210");
    await u.click(screen.getByRole("button", { name: "Agregar al presupuesto" }));

    const partida = screen.getByRole("combobox", { name: "Partida" });
    await waitFor(() => expect(partida).toHaveAttribute("aria-invalid", "true"));
    expect(partida).toHaveAccessibleDescription(expect.stringContaining(FUERA_DEL_CATALOGO));
    await waitFor(() => expect(partida).toHaveFocus());

    alAgregar = () => json({ detalle: SIN_TASA }, 409);
    await u.click(screen.getByRole("button", { name: "Agregar al presupuesto" }));

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(/Error/);
    expect(alerta).toHaveTextContent(SIN_TASA);
    await waitFor(() => expect(alerta.closest("[tabindex='-1']")).toHaveFocus());
  });

  test("409 por rev viejo llama a alReleer, conserva lo escrito y el segundo intento manda el rev actualizado", async () => {
    const u = userEvent.setup();
    let revActual = 0;
    let primera = true;
    alAgregar = (cuerpo) => {
      if (!primera) {
        return json({ rev: cuerpo.rev + 1, resumen: resumen({ rev: cuerpo.rev + 1 }), clave: "OBRA-04|a-mano:1" });
      }
      primera = false;
      revActual = 7;
      return json({ detalle: REV_VIEJO }, 409);
    };
    const { container, alReleer, alAgregada } = montar({
      revActual: async () => revActual,
    });
    await elegirPared(u);
    await u.type(screen.getByRole("textbox", { name: /^Cantidad/ }), "210");
    await u.click(container.querySelector("summary")!);
    await u.type(screen.getByRole("textbox", { name: "Cálculo (opcional)" }), "6*35");
    await u.type(screen.getByRole("textbox", { name: "Nota de medición (opcional)" }), "muro norte");

    await u.click(screen.getByRole("button", { name: "Agregar al presupuesto" }));

    expect(await screen.findByText(`${REV_VIEJO} ${RECARGADO}`)).toBeInTheDocument();
    await waitFor(() => expect(alReleer).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("combobox", { name: "Partida" })).toHaveValue("OBRA-04 · Pared de bloques de arcilla de 15 cm");
    expect(screen.getByRole("textbox", { name: /^Cantidad/ })).toHaveValue("210");
    expect(screen.getByRole("textbox", { name: "Cálculo (opcional)" })).toHaveValue("6*35");
    expect(screen.getByRole("textbox", { name: "Nota de medición (opcional)" })).toHaveValue("muro norte");

    await u.click(screen.getByRole("button", { name: "Agregar al presupuesto" }));
    await waitFor(() => expect(alAgregada).toHaveBeenCalledTimes(1));
    expect(escrituras().map((c) => c.rev)).toEqual([0, 7]);
  });

  test("401 avisa a alExpirar y 404 de borrador ausente avisa a alAusente", async () => {
    const u = userEvent.setup();
    alAgregar = () => json({ detalle: "La sesión venció." }, 401);
    const { alAusente } = montar();
    await elegirPared(u);
    await u.type(screen.getByRole("textbox", { name: /^Cantidad/ }), "10");
    await u.click(screen.getByRole("button", { name: "Agregar al presupuesto" }));
    await waitFor(() => expect(alExpirar).toHaveBeenCalledTimes(1));

    alAgregar = () => json({ detalle: FALTA }, 404);
    await u.click(screen.getByRole("button", { name: "Agregar al presupuesto" }));
    await waitFor(() => expect(alAusente).toHaveBeenCalledTimes(1));
  });

  test("«Buscar parecidas» lista propuestas, usa solo la descripción y «Usar esta partida» enfoca Cantidad", async () => {
    const u = userEvent.setup();
    montar();
    await u.type(screen.getByRole("combobox", { name: "Partida" }), "excavación de zanja");
    await u.click(screen.getByRole("button", { name: "Buscar parecidas" }));

    const usar = await screen.findByRole("button", { name: "Usar esta partida: FIC-01" });
    expect(pedidosDeParecidas()).toEqual([{ descripcion: "excavación de zanja" }]);

    await u.click(usar);
    expect(screen.getByRole("combobox", { name: "Partida" })).toHaveValue("FIC-01 · Excavación de zanja ficticia a mano");
    const cantidad = screen.getByRole("textbox", { name: "Cantidad (m³)" });
    await waitFor(() => expect(cantidad).toHaveFocus());

    await u.click(screen.getByRole("button", { name: "Buscar parecidas" }));
    await waitFor(() =>
      expect(pedidosDeParecidas()).toEqual([
        { descripcion: "excavación de zanja" },
        { descripcion: "Excavación de zanja ficticia a mano" },
      ]),
    );
  });

  test("«Crear la partida «friso de pared»» avisa con la descripción (D4) y código Z-99 avisa con el código", async () => {
    const u = userEvent.setup();
    const { alCrearPartida } = montar();

    const partida = screen.getByRole("combobox", { name: "Partida" });
    await u.type(partida, "friso de pared");
    const opcionDesc = await screen.findByRole("option", { name: "Crear la partida «friso de pared»" });
    await u.click(opcionDesc);
    expect(alCrearPartida).toHaveBeenLastCalledWith({ codigo: "", descripcion: "friso de pared" });

    await u.clear(partida);
    await u.type(partida, "Z-99");
    const opcionCodigo = await screen.findByRole("option", { name: "Crear la partida «Z-99»" });
    await u.click(opcionCodigo);
    expect(alCrearPartida).toHaveBeenLastCalledWith({ codigo: "Z-99", descripcion: "" });
  });

  test("con partidaInicial y solicitudDeFocoEnPartida dirige el foco al campo correspondiente", async () => {
    const alConsumirPartidaInicial = vi.fn();
    const { rerender, props } = montar({
      partidaInicial: { codigo: "FRI-01", descripcion: "Friso de pared", unidad: "m2" },
      alConsumirPartidaInicial,
    });

    expect(screen.getByRole("combobox", { name: "Partida" })).toHaveValue("FRI-01 · Friso de pared");
    const cantidad = screen.getByRole("textbox", { name: "Cantidad (m²)" });
    await waitFor(() => expect(cantidad).toHaveFocus());
    expect(alConsumirPartidaInicial).toHaveBeenCalledTimes(1);

    const aplicacion: Aplicacion = {
      sesion: SESION,
      proyecto: "OF-001",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    rerender(
      <ContextoAplicacion.Provider value={aplicacion}>
        <ProveedorDeAnuncios>
          <FilaDeAlta {...props} partidaInicial={null} solicitudDeFocoEnPartida={1} />
        </ProveedorDeAnuncios>
      </ContextoAplicacion.Provider>,
    );
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Partida" })).toHaveFocus());

    // Al recibir una partida creada desde el inspector (B1-9) tras estar montada, la elige y enfoca Cantidad.
    rerender(
      <ContextoAplicacion.Provider value={aplicacion}>
        <ProveedorDeAnuncios>
          <FilaDeAlta
            {...props}
            partidaInicial={{ codigo: "Z-99", descripcion: "Zanja ficticia", unidad: "m3" }}
            alConsumirPartidaInicial={alConsumirPartidaInicial}
          />
        </ProveedorDeAnuncios>
      </ContextoAplicacion.Provider>,
    );
    expect(screen.getByRole("combobox", { name: "Partida" })).toHaveValue("Z-99 · Zanja ficticia");
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Cantidad (m³)" })).toHaveFocus());
    expect(alConsumirPartidaInicial).toHaveBeenCalledTimes(2);
  });

  test("la hoja de estilos compila sin font-size en px ni colores literales", () => {
    // En una variable: con el texto literal, Vite reescribe new URL(...) como un recurso y deja de ser file:.
    const relativa = "./filaDeAlta.scss";
    const ruta = fileURLToPath(new URL(relativa, import.meta.url));
    const fuente = readFileSync(ruta, "utf8");
    const compilado = sass.compile(ruta).css;

    expect(compilado).toContain(".silice-fila-alta");
    expect(fuente).not.toMatch(/font-size:\s*[\d.]+(px|pt)/);
    expect(fuente).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(fuente).not.toContain("IBM Plex");
  });
});
