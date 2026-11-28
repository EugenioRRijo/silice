import { act, configure, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useCallback, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../../api/tipos";
import { ProveedorDeAnuncios } from "../../../comun/Anunciador";
import { vaciarRecursosParaPruebas } from "../../../comun/recurso";
import { ContextoAplicacion } from "../../../shell/contexto";
import type { Aplicacion } from "../../../shell/contexto";
import { informeAuditoria, vistaApu, vistaPresupuesto } from "../datosDePrueba";
import { ContextoDeDialogos } from "../ContextoDeDialogos";
import type { BorradorAbierto, FilaPresupuesto, Resumen } from "../logica";
import type { PartidaCompuesta } from "../../componer/ComponerPartida";
import { SuperficiePresupuesto } from "./SuperficiePresupuesto";
import type { PropiedadesDeSuperficiePresupuesto } from "./SuperficiePresupuesto";

// Lote B1-10 (ficha-b1 §1.10, pruebas 4 a 8 sobre la superficie conectada) y B1-9 con el plan B de R1: la grilla con sus
// celdas de cantidad, el inspector de la partida, el de problemas y la fila de alta, todo junto, con un servidor simulado.
// «Componer» se sustituye por un doble que solo guarda: su propio comportamiento lo prueban `ComponerEnPanel.test.tsx` y
// `componer/`. Datos ficticios.
configure({ asyncUtilTimeout: 5000 });

vi.mock("../../componer/ComponerPartida", () => ({
  ComponerPartida: ({
    codigoInicial,
    descripcionInicial,
    alGuardar,
  }: {
    codigoInicial: string;
    descripcionInicial: string;
    alGuardar: (p: PartidaCompuesta) => void;
  }) => (
    <div>
      <p>{`Se compone con el código «${codigoInicial}» y la descripción «${descripcionInicial}»`}</p>
      <button type="button" onClick={() => alGuardar({ codigo: "FRI-01", descripcion: "Friso de pared", unidad: "m2" })}>
        Guardar la partida en el catálogo
      </button>
    </div>
  ),
}));

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

const ID = "id-borrador-b1-10";
const RUTA = `/v1/hoja/borradores/${ID}`;
const CLAVE_LLAVE = "AF-LLAVE|esp_puntos:P1";

const APROBACIONES = {
  rastro: { integro: true, mensaje: "Rastro de aprobaciones íntegro." },
  fases: "",
  versiones: { "001": { estado: "guardada", por: null, el: null, notas: "", armo: false } },
  eventos: [],
  ultima_aprobada: null,
};

function resumen(rev: number, extra: Partial<Resumen> = {}): Resumen {
  return {
    rev,
    moneda: "USD",
    total: { texto: "2703.86", exacto: "2703.8602323440440333" },
    cambios: 1,
    pendientes_catalogo: 1,
    hallazgos: [
      { severidad: "ERROR", total: 1 },
      { severidad: "ADVERTENCIA", total: 1 },
    ],
    hay_plan: true,
    version_mas_nueva: null,
    guardado_como: null,
    espacio_vacio: true,
    ...extra,
  };
}

function crearBorrador(rev = 2, version: string | null = "001"): BorradorAbierto {
  return {
    id: ID,
    base: { proyecto: "OF-001", version, vigente: version, lista: "Lista", espacio_de: "001", solo_lectura: false, moneda: "USD" },
    resumen: resumen(rev, { cambios: 0 }),
    instantanea: { creadas: 0, mensaje: null },
  };
}

const HALLADAS = {
  rotulo: "Partidas del catálogo",
  resultados: [
    { clave: "partida:OBRA-04", codigo: "OBRA-04", descripcion: "Pared de bloques de arcilla de 15 cm", unidad: "m2", dominio: "civil", tiene_composicion: true },
  ],
  hay_mas: false,
};

function nuevaFila(codigo: string, cantidad: string): FilaPresupuesto {
  return {
    clave: `${codigo}|a-mano:1`,
    partida: codigo,
    descripcion: "Pared de bloques de arcilla de 15 cm",
    unidad: "m2",
    cantidad,
    cantidad_calculada: cantidad,
    escrita: true,
    pu: { texto: "85.30", exacto: "85.3" },
    total: { texto: "17913.00", exacto: "17913" },
    estado: { severidad: null, texto: "OK" },
    quitable: true,
    nota: null,
    calculo: null,
  };
}

describe("SuperficiePresupuesto conectada (B1-9 y B1-10)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let filasDelServidor: FilaPresupuesto[];
  let revDelServidor: number;
  let alPoner: (cuerpo: { rev: number; filas: { clave: string; cantidad: string }[] }) => Response;
  let alAgregar: (cuerpo: { rev: number; codigo: string; cantidad: string }) => Response;
  let alQuitar: (cuerpo: { rev: number; clave: string }) => Response | Promise<Response>;
  const alAceptar = vi.fn<(r: Resumen) => void>();

  beforeEach(() => {
    vaciarRecursosParaPruebas();
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alAceptar.mockReset();
    filasDelServidor = vistaPresupuesto().filas;
    revDelServidor = 2;
    alPoner = (cuerpo) => {
      revDelServidor = cuerpo.rev + 1;
      return json({ rev: revDelServidor, resumen: resumen(revDelServidor) });
    };
    alAgregar = (cuerpo) => {
      filasDelServidor = [...filasDelServidor, nuevaFila(cuerpo.codigo, cuerpo.cantidad)];
      revDelServidor = cuerpo.rev + 1;
      return json({ rev: revDelServidor, resumen: resumen(revDelServidor), clave: `${cuerpo.codigo}|a-mano:1` });
    };
    alQuitar = (cuerpo) => {
      filasDelServidor = filasDelServidor.filter((f) => f.clave !== cuerpo.clave);
      revDelServidor = cuerpo.rev + 1;
      return json({ rev: revDelServidor, resumen: resumen(revDelServidor) });
    };
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = new URL(String(ruta), "http://silice.local");
      const metodo = init?.method ?? "GET";
      const cuerpo = (init?.body === undefined ? {} : JSON.parse(String(init.body))) as never;
      if (url.pathname === "/v1/aprobaciones") return json(APROBACIONES);
      if (url.pathname === `${RUTA}/vistas/presupuesto`) return json(vistaPresupuesto({ filas: filasDelServidor }));
      if (url.pathname === `${RUTA}/vistas/auditoria`) return json(informeAuditoria());
      if (url.pathname === `${RUTA}/vistas/apu`) return json(vistaApu());
      if (url.pathname === "/v1/mercado/objetivos") return json({ objetivos: [] });
      if (url.pathname === RUTA && metodo === "GET") return json({ ...crearBorrador(revDelServidor), resumen: resumen(revDelServidor) });
      if (url.pathname === `${RUTA}/cantidades` && metodo === "PUT") return alPoner(cuerpo);
      if (url.pathname === `${RUTA}/partidas` && metodo === "POST") return alAgregar(cuerpo);
      if (url.pathname === `${RUTA}/partidas/quitar` && metodo === "POST") return alQuitar(cuerpo);
      if (url.pathname === "/v1/buscar/partidas") {
        const q = url.searchParams.get("q") ?? "";
        return json(q.toLowerCase().includes("bloq") ? HALLADAS : { ...HALLADAS, resultados: [] });
      }
      if (url.pathname === "/v1/similares") return json({ propuestas: [], falla: null, mensaje: null });
      return json({ detalle: `ruta inesperada ${metodo} ${url.pathname}` }, 500);
    });
  });

  afterEach(() => {
    vaciarRecursosParaPruebas();
    vi.unstubAllGlobals();
  });

  function Arnes({ children }: { children: (anfitrion: HTMLElement | null) => ReactNode }) {
    const [anfitrion, setAnfitrion] = useState<HTMLElement | null>(null);
    const [abiertos, setAbiertos] = useState(0);
    const registrar = useCallback((delta: number) => setAbiertos((n) => n + delta), []);
    const dialogos = useMemo(() => ({ anfitrion, abiertos, registrar }), [anfitrion, abiertos, registrar]);
    return (
      <ContextoDeDialogos.Provider value={dialogos}>
        <div inert={abiertos > 0}>{children(anfitrion)}</div>
        <div ref={setAnfitrion} />
      </ContextoDeDialogos.Provider>
    );
  }

  function Pagina({ sinVersion, ...extra }: Partial<PropiedadesDeSuperficiePresupuesto> & { sinVersion?: boolean }) {
    const [borrador, setBorrador] = useState<BorradorAbierto>(crearBorrador(2, sinVersion === true ? null : "001"));
    return (
      <SuperficiePresupuesto
        proyecto="OF-001"
        borrador={borrador}
        puedeEditar
        alAusente={vi.fn()}
        alGuardar={vi.fn()}
        alReabrir={vi.fn()}
        alRecargarBorrador={async () => setBorrador((b) => ({ ...b, resumen: resumen(revDelServidor) }))}
        alAceptar={(r) => {
          alAceptar(r);
          setBorrador((b) => ({ ...b, resumen: r }));
        }}
        {...extra}
      />
    );
  }

  function montar(extra: Partial<PropiedadesDeSuperficiePresupuesto> & { sinVersion?: boolean } = {}) {
    const aplicacion: Aplicacion = {
      sesion: ARMA,
      proyecto: "OF-001",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    return render(
      <MemoryRouter>
        <ContextoAplicacion.Provider value={aplicacion}>
          <ProveedorDeAnuncios>
            <Arnes>{() => <Pagina {...extra} />}</Arnes>
          </ProveedorDeAnuncios>
        </ContextoAplicacion.Provider>
      </MemoryRouter>,
    );
  }

  const escrituras = (metodo: "PUT" | "POST", sufijo: string) =>
    fetchFalso.mock.calls
      .filter(([r, init]) => String(r) === `${RUTA}${sufijo}` && init?.method === metodo)
      .map(([, init]) => JSON.parse(String(init?.body)) as Record<string, unknown>);
  const lecturas = (sufijo: string) => fetchFalso.mock.calls.filter(([r]) => String(r) === `${RUTA}${sufijo}`).length;

  async function grilla() {
    return screen.findByRole("grid", { name: "Presupuesto" });
  }

  test("pruebas 2 y 3 de §1.10 con todo conectado: un solo botón principal, la frase antes de la grilla y ningún atributo title", async () => {
    const { container } = montar();
    const g = await grilla();
    const frase = await screen.findByText(/El presupuesto suma .* sin IVA en 2 partidas\./);
    expect(Boolean(frase.compareDocumentPosition(g) & Node.DOCUMENT_POSITION_FOLLOWING)).toBe(true);
    expect(container.querySelectorAll(".cds--btn--primary")).toHaveLength(1);
    expect(container.querySelectorAll("[title]")).toHaveLength(0);
    // La fila de alta va debajo de la grilla, con su botón terciario.
    const agregar = screen.getByRole("button", { name: "Agregar al presupuesto" });
    expect(agregar).toHaveClass("cds--btn--tertiary");
    expect(Boolean(g.compareDocumentPosition(agregar) & Node.DOCUMENT_POSITION_FOLLOWING)).toBe(true);
  });

  test("prueba 6 de §1.10: F2 en la cantidad, escribir con coma y Enter manda el PUT con su rev; el total y la lectura se renuevan", async () => {
    const u = userEvent.setup();
    montar();
    const g = await grilla();
    const celda = within(within(g).getByRole("row", { name: /AF-LLAVE/ })).getByRole("gridcell", { name: "3" });
    celda.focus();
    await u.keyboard("{F2}");
    const campo = await screen.findByRole("textbox", { name: "Cantidad, AF-LLAVE" });
    await u.clear(campo);
    await u.type(campo, "12,5{Enter}");

    await waitFor(() => expect(escrituras("PUT", "/cantidades")).toEqual([{ rev: 2, filas: [{ clave: CLAVE_LLAVE, cantidad: "12,5" }] }]));
    await waitFor(() => expect(alAceptar).toHaveBeenCalledTimes(1));
    expect(alAceptar.mock.calls[0]![0].rev).toBe(3);
    // La cabecera sube de versión del servidor: la vista y la revisión se leen otra vez, y la grilla no se vacía entre tanto.
    await waitFor(() => expect(lecturas("/vistas/presupuesto")).toBe(2));
    await waitFor(() => expect(lecturas("/vistas/auditoria")).toBe(2));
    expect(screen.getByRole("grid", { name: "Presupuesto" })).toBeInTheDocument();
  });

  test("prueba 5 de §1.10: un 422 en la celda deja lo escrito, la marca con texto y el aviso dice el detalle del servidor", async () => {
    const u = userEvent.setup();
    alPoner = () => json({ detalle: "presupuesto, fila 1 (AF-LLAVE): cantidad: no puede ser negativa." }, 422);
    montar();
    const g = await grilla();
    const celda = within(within(g).getByRole("row", { name: /AF-LLAVE/ })).getByRole("gridcell", { name: "3" });
    celda.focus();
    await u.keyboard("{F2}");
    const campo = await screen.findByRole("textbox", { name: "Cantidad, AF-LLAVE" });
    await u.clear(campo);
    await u.type(campo, "-4{Enter}");

    const aviso = await screen.findByText(/no puede ser negativa/, { selector: ".cds--inline-notification__subtitle" });
    expect(aviso).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Cantidad, AF-LLAVE" })).toHaveValue("-4");
  });

  test("prueba 4 de §1.10: agregar una partida deja la fila nueva en la grilla con el foco en su Cantidad y un solo anuncio", async () => {
    const u = userEvent.setup();
    montar();
    await grilla();
    await u.type(screen.getByRole("combobox", { name: "Partida" }), "bloq");
    await u.click(await screen.findByRole("option", { name: /OBRA-04/ }));
    await u.type(screen.getByRole("textbox", { name: /^Cantidad/ }), "210");
    await u.click(screen.getByRole("button", { name: "Agregar al presupuesto" }));

    await waitFor(() => expect(escrituras("POST", "/partidas")).toHaveLength(1));
    expect(escrituras("POST", "/partidas")[0]).toMatchObject({ codigo: "OBRA-04", cantidad: "210" });
    const filaNueva = await within(await grilla()).findByRole("row", { name: /OBRA-04/ });
    const celdaCantidad = within(filaNueva).getByRole("gridcell", { name: "210" });
    await waitFor(() => expect(celdaCantidad).toHaveFocus());
    expect(alAceptar).toHaveBeenCalled();

    const conTexto = screen.getAllByRole("status").filter((n) => (n.textContent ?? "").trim() !== "");
    expect(conTexto).toHaveLength(1);
    expect(conTexto[0]).toHaveTextContent("Se agregó OBRA-04 al presupuesto.");
  });

  test("prueba 7 de §1.10: Enter en una celda abre el inspector de la partida con el foco en su h2, y Esc lo cierra devolviendo el foco a esa celda", async () => {
    const u = userEvent.setup();
    montar();
    const g = await grilla();
    const celda = within(within(g).getByRole("row", { name: /AF-LLAVE/ })).getByRole("gridcell", { name: "Llave de paso" });
    celda.focus();
    await u.keyboard("{Enter}");

    const panel = await screen.findByRole("complementary", { name: /AF-LLAVE · Llave de paso/ });
    expect(within(panel).getByRole("heading", { level: 2 })).toHaveFocus();
    expect(within(panel).getByRole("button", { name: "Cerrar" })).toBeVisible();

    await u.keyboard("{Escape}");
    expect(screen.queryByRole("complementary")).toBeNull();
    expect(celda).toHaveFocus();
  });

  test("el inspector de la partida abierto con doble clic; «Volver a la calculada» escribe el cálculo en la celda y lo manda con su rev", async () => {
    const u = userEvent.setup();
    montar();
    const g = await grilla();
    // AF-SALIDA tiene la cantidad escrita a mano (5) y la calculada es 3.
    const fila = within(g).getByRole("row", { name: /AF-SALIDA/ });
    await u.dblClick(within(fila).getByRole("gridcell", { name: "Salida de agua" }));
    const panel = await screen.findByRole("complementary", { name: /AF-SALIDA/ });
    await u.click(within(panel).getByRole("button", { name: "Volver a la calculada" }));

    await waitFor(() => expect(escrituras("PUT", "/cantidades")).toEqual([{ rev: 2, filas: [{ clave: "AF-SALIDA|esp_puntos:P2", cantidad: "3" }] }]));
  });

  test("Enter en la celda de cantidad abre su campo y no el inspector de la partida", async () => {
    const u = userEvent.setup();
    montar();
    const g = await grilla();
    const celda = within(within(g).getByRole("row", { name: /AF-LLAVE/ })).getByRole("gridcell", { name: "3" });
    celda.focus();
    await u.keyboard("{Enter}");
    expect(await screen.findByRole("textbox", { name: "Cantidad, AF-LLAVE" })).toHaveFocus();
    expect(screen.queryByRole("complementary")).toBeNull();
  });

  // --- B1-6: «Quitar» del inspector entra en la misma cola que las cantidades ---

  // Con las dos filas quitables, abre el inspector de AF-SALIDA (la cantidad escrita a mano, con «Volver a la calculada»).
  async function abrirElInspectorDeSalida() {
    filasDelServidor = filasDelServidor.map((f) => ({ ...f, quitable: true }));
    const u = userEvent.setup();
    montar();
    const g = await grilla();
    await u.dblClick(within(within(g).getByRole("row", { name: /AF-SALIDA/ })).getByRole("gridcell", { name: "Salida de agua" }));
    return { u, panel: await screen.findByRole("complementary", { name: /AF-SALIDA/ }) };
  }

  test("B1-6 (3): quitar sin cambios pendientes manda el POST con el rev vigente, no escribe cantidades y cierra el inspector", async () => {
    const { u, panel } = await abrirElInspectorDeSalida();
    await u.click(within(panel).getByRole("button", { name: "Quitar del presupuesto" }));
    await u.click(within(await screen.findByRole("dialog", { name: "Quitar partida" })).getByRole("button", { name: "Quitar" }));

    await waitFor(() => expect(escrituras("POST", "/partidas/quitar")).toEqual([{ rev: 2, clave: "AF-SALIDA|esp_puntos:P2" }]));
    await waitFor(() => expect(screen.queryByRole("complementary")).toBeNull());
    expect(escrituras("PUT", "/cantidades")).toEqual([]);
    await waitFor(() => expect(within(screen.getByRole("grid", { name: "Presupuesto" })).queryByRole("row", { name: /AF-SALIDA/ })).toBeNull());
    expect(screen.queryByRole("alert")).toBeNull();
  });

  test("B1-6 (1): «Quitar» con lo escrito dentro de la pausa; si el servidor lo rechaza (422) no manda el POST y deja ver el aviso", async () => {
    alPoner = () => json({ detalle: "presupuesto, fila 2 (AF-SALIDA): cantidad: no puede ser negativa." }, 422);
    const { panel } = await abrirElInspectorDeSalida();
    // Con el reloj de la pausa detenido, lo escrito sale porque «Quitar» lo saca, no porque pasen 400 ms.
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    try {
      fireEvent.click(within(panel).getByRole("button", { name: "Volver a la calculada" }));
      fireEvent.click(within(panel).getByRole("button", { name: "Quitar del presupuesto" }));
      let confirmacion: HTMLElement | null = null;
      for (let i = 0; i < 300 && confirmacion === null; i++) {
        await act(async () => {
          await new Promise<void>((resolver) => setImmediate(resolver));
        });
        confirmacion = screen.queryByRole("dialog", { name: "Quitar partida" });
      }
      fireEvent.click(within(confirmacion!).getByRole("button", { name: "Quitar" }));
    } finally {
      vi.useRealTimers();
    }
    await waitFor(() => expect(escrituras("PUT", "/cantidades")).toEqual([{ rev: 2, filas: [{ clave: "AF-SALIDA|esp_puntos:P2", cantidad: "3" }] }]));
    await new Promise((r) => setTimeout(r, 300)); // tiempo de sobra para que saliera el quitar, si saliera
    expect(escrituras("POST", "/partidas/quitar")).toEqual([]);
    expect(await screen.findByText(/no puede ser negativa/, { selector: ".cds--inline-notification__subtitle" })).toBeInTheDocument();
    // La partida sigue en la grilla y el inspector sigue abierto, sin el diálogo de confirmación.
    expect(within(screen.getByRole("grid", { name: "Presupuesto" })).getByRole("row", { name: /AF-SALIDA/ })).toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: "Quitar partida" })).toBeNull();
    expect(screen.getByRole("complementary", { name: /AF-SALIDA/ })).toBeInTheDocument();
  });

  test("B1-6 (2): mientras «Quitar» va en vuelo, una cantidad nueva espera y sale después con el rev que dejó el quitar, sin 409", async () => {
    let soltar: (r: Response) => void = () => {};
    const quitada = new Promise<Response>((resolver) => (soltar = resolver));
    alQuitar = () => quitada;
    // El servidor es estricto: una escritura con un rev que no es el suyo es un 409.
    alPoner = (cuerpo) => {
      if (cuerpo.rev !== revDelServidor) return json({ detalle: "El borrador cambió en otra ventana: vuelva a cargarlo." }, 409);
      revDelServidor = cuerpo.rev + 1;
      return json({ rev: revDelServidor, resumen: resumen(revDelServidor) });
    };
    const { u, panel } = await abrirElInspectorDeSalida();
    await u.click(within(panel).getByRole("button", { name: "Quitar del presupuesto" }));
    await u.click(within(await screen.findByRole("dialog", { name: "Quitar partida" })).getByRole("button", { name: "Quitar" }));
    await waitFor(() => expect(escrituras("POST", "/partidas/quitar")).toHaveLength(1));

    // Lo escrito entre tanto (aquí, «Volver a la calculada» del propio inspector) no sale con el rev viejo.
    fireEvent.click(within(panel).getByRole("button", { name: "Volver a la calculada" }));
    await new Promise((r) => setTimeout(r, 700)); // pasa la pausa de 400 ms con el quitar en vuelo
    expect(escrituras("PUT", "/cantidades")).toEqual([]);

    revDelServidor = 3;
    soltar(json({ rev: 3, resumen: resumen(3) }));
    await waitFor(() => expect(escrituras("PUT", "/cantidades")).toEqual([{ rev: 3, filas: [{ clave: "AF-SALIDA|esp_puntos:P2", cantidad: "3" }] }]));
    expect(escrituras("POST", "/partidas/quitar")).toHaveLength(1);
    expect(screen.queryByText(/El borrador cambió/)).toBeNull();
  });

  test("prueba 8 de §1.10: «Problemas (2)» abre la lista y «Ir a la partida» activa la fila y lleva el foco a ella", async () => {
    const u = userEvent.setup();
    montar();
    const g = await grilla();
    await u.click(await screen.findByRole("button", { name: "Problemas (2)" }));

    const panel = await screen.findByRole("complementary", { name: "Problemas" });
    expect(within(panel).getByRole("heading", { level: 2, name: "Problemas" })).toHaveFocus();
    const ir = within(panel).getByRole("button", { name: /^Ir a la partida AF-LLAVE/ });
    await u.click(ir);

    const fila = within(g).getByRole("row", { name: /AF-LLAVE/ });
    expect(fila).toHaveAttribute("aria-selected", "true");
    await waitFor(() => expect(within(fila).getByRole("rowheader", { name: "AF-LLAVE" })).toHaveFocus());
    // La palabra de la severidad se dice, no solo el color.
    expect(within(panel).getAllByText(/^(Error|Advertencia)$/).length).toBeGreaterThan(0);
  });

  test("con la obra vacía, «Agregar la primera partida» lleva el foco a «Partida» y la fila de alta ya está a la vista", async () => {
    const u = userEvent.setup();
    filasDelServidor = [];
    montar({ sinVersion: true });
    await screen.findByText("Esta obra aún no tiene partidas");
    const partida = screen.getByRole("combobox", { name: "Partida" });
    expect(screen.queryByRole("grid")).toBeNull();
    await u.click(screen.getByRole("button", { name: "Agregar la primera partida" }));
    await waitFor(() => expect(partida).toHaveFocus());
  });

  test("B1-9 plan B: «Crear la partida «friso de pared»» abre Componer con la descripción escrita; al guardar, la partida queda elegida en la fila de alta y el foco en Cantidad", async () => {
    const u = userEvent.setup();
    montar();
    await grilla();
    await u.type(screen.getByRole("combobox", { name: "Partida" }), "friso de pared");
    await u.click(await screen.findByRole("option", { name: /Crear la partida «friso de pared»/ }));

    const panel = await screen.findByRole("complementary", { name: "Componer una partida" });
    expect(within(panel).getByText("Se compone con el código «» y la descripción «friso de pared»")).toBeInTheDocument();
    await u.click(within(panel).getByRole("button", { name: "Guardar la partida en el catálogo" }));

    await waitFor(() => expect(screen.queryByRole("complementary", { name: "Componer una partida" })).toBeNull());
    const partida = screen.getByRole("combobox", { name: "Partida" });
    expect(partida).toHaveValue("FRI-01 · Friso de pared");
    await waitFor(() => expect(screen.getByRole("textbox", { name: /^Cantidad/ })).toHaveFocus());
    // Lo que se guardó no se agregó solo al presupuesto: falta la cantidad.
    expect(escrituras("POST", "/partidas")).toHaveLength(0);
  });

  test("B1-9: cancelar Componer devuelve el foco a «Partida» sin cambiar lo escrito", async () => {
    const u = userEvent.setup();
    montar();
    await grilla();
    await u.type(screen.getByRole("combobox", { name: "Partida" }), "friso de pared");
    await u.click(await screen.findByRole("option", { name: /Crear la partida «friso de pared»/ }));
    const panel = await screen.findByRole("complementary", { name: "Componer una partida" });
    await u.click(within(panel).getByRole("button", { name: "Cerrar" }));

    await waitFor(() => expect(screen.queryByRole("complementary", { name: "Componer una partida" })).toBeNull());
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Partida" })).toHaveFocus());
    expect(screen.getByRole("combobox", { name: "Partida" })).toHaveValue("friso de pared");
  });

  test("B1-9: llegar desde la subvista Componer deja la partida elegida y el foco en Cantidad, y se consume una sola vez", async () => {
    const consumir = vi.fn();
    montar({ partidaInicial: { codigo: "FRI-01", descripcion: "Friso de pared", unidad: "m2" }, alConsumirPartidaInicial: consumir });
    await grilla();
    expect(screen.getByRole("combobox", { name: "Partida" })).toHaveValue("FRI-01 · Friso de pared");
    await waitFor(() => expect(screen.getByRole("textbox", { name: /^Cantidad/ })).toHaveFocus());
    expect(consumir).toHaveBeenCalledTimes(1);
  });
});
