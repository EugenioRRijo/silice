import { act, configure, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { MemoryRouter } from "react-router";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, test, vi } from "vitest";
import type { InformeAuditoriaRespuesta, SesionRespuesta } from "../../../api/tipos";
import { ProveedorDeAnuncios } from "../../../comun/Anunciador";
import { vaciarRecursosParaPruebas } from "../../../comun/recurso";
import { ContextoDeLaObra } from "../../../marco/obraAbierta";
import type { ObraAbierta } from "../../../marco/obraAbierta";
import { ContextoAplicacion } from "../../../shell/contexto";
import type { Aplicacion } from "../../../shell/contexto";
import { olvidarFormularios } from "../../../shell/sucio";
import { informeAuditoria, vistaApu, vistaPresupuesto } from "../datosDePrueba";
import type { BorradorAbierto, FilaPresupuesto, VistaPresupuesto } from "../logica";
import { SuperficiePresupuesto } from "./SuperficiePresupuesto";
import type { PropiedadesDeSuperficiePresupuesto } from "./SuperficiePresupuesto";

// Lote B1-4 (ficha-b1 §1.8, §1.10 pruebas 1, 2, 9 y 10): superficie de solo lectura del Presupuesto sin ruta.
configure({ asyncUtilTimeout: 5000 });

beforeAll(() => {
  const proto = HTMLElement.prototype as HTMLElement & { showPopover?: () => void; hidePopover?: () => void };
  proto.showPopover = function showPopover(this: HTMLElement) {
    this.style.display = "block";
  };
  proto.hidePopover = function hidePopover(this: HTMLElement) {
    this.style.display = "";
  };
});
afterAll(() => {
  const proto = HTMLElement.prototype as HTMLElement & { showPopover?: () => void; hidePopover?: () => void };
  Reflect.deleteProperty(proto, "showPopover");
  Reflect.deleteProperty(proto, "hidePopover");
});

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

const ID = "id-borrador-b1-4";

function crearBorrador(parcial: {
  rev?: number;
  version?: string | null;
  vigente?: string | null;
  cambios?: number;
  soloLectura?: boolean;
} = {}): BorradorAbierto {
  const version = parcial.version === undefined ? "001" : parcial.version;
  const vigente = parcial.vigente === undefined ? version : parcial.vigente;
  return {
    id: ID,
    base: {
      proyecto: "OF-001",
      version,
      vigente,
      lista: "Lista",
      espacio_de: version,
      solo_lectura: parcial.soloLectura ?? false,
      moneda: "USD",
    },
    resumen: {
      rev: parcial.rev ?? 2,
      moneda: "USD",
      total: { texto: "2703.86", exacto: "2703.8602323440440333" },
      cambios: parcial.cambios ?? 0,
      pendientes_catalogo: 1,
      hallazgos: [
        { severidad: "ERROR", total: 1 },
        { severidad: "ADVERTENCIA", total: 1 },
      ],
      hay_plan: true,
      version_mas_nueva: null,
      guardado_como: null,
      espacio_vacio: true,
    },
    instantanea: { creadas: 0, mensaje: null },
  };
}

const APROBACIONES = {
  rastro: { integro: true, mensaje: "Rastro de aprobaciones íntegro." },
  fases: "",
  versiones: {
    "001": { estado: "guardada", por: null, el: null, notas: "", armo: false },
  },
  eventos: [],
  ultima_aprobada: null,
};

const obraAbierta: ObraAbierta = {
  carpeta: null,
  obraId: 1,
  ficha: { estado: "cargando" },
  recargarFicha: vi.fn(),
};

const antes = (a: Element, b: Element) => Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);

describe("SuperficiePresupuesto (lote B1-4)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let responderVista: () => Response | Promise<Response>;
  let responderRevision: () => Response | Promise<Response>;
  let responderFrentes: () => Response | Promise<Response>;

  beforeEach(() => {
    vaciarRecursosParaPruebas();
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    responderVista = () => json(vistaPresupuesto());
    responderRevision = () => json(informeAuditoria());
    responderFrentes = () =>
      json({
        rev: 2,
        frentes: [
          { frente: "FRENTE A", renglones: 2, pendientes: 1, total: { texto: "2703.86", exacto: "2703.8602323440440333" } },
        ],
        total: { texto: "2703.86", exacto: "2703.8602323440440333" },
        con_frentes: true,
      });
    fetchFalso.mockImplementation(async (ruta) => {
      const url = String(ruta);
      const camino = new URL(url, "http://silice.local").pathname;
      if (camino === "/v1/aprobaciones") return json(APROBACIONES);
      if (camino === `/v1/hoja/borradores/${ID}/vistas/presupuesto`) return responderVista();
      if (camino === `/v1/hoja/borradores/${ID}/vistas/auditoria`) return responderRevision();
      if (camino === `/v1/hoja/borradores/${ID}/vistas/frentes`) return responderFrentes();
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
      props?: Partial<PropiedadesDeSuperficiePresupuesto>;
      conObra?: boolean;
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
    const props: PropiedadesDeSuperficiePresupuesto = {
      proyecto: "OF-001",
      borrador: crearBorrador(),
      puedeEditar: sesion.acciones.includes("editar_hoja"),
      alAusente: vi.fn(),
      alGuardar: vi.fn(),
      alDescartar: vi.fn(),
      alReabrir: vi.fn(),
      ...opciones.props,
    };

    const arbol = (
      <MemoryRouter>
        <ContextoAplicacion.Provider value={aplicacion}>
          <ProveedorDeAnuncios>
            {opciones.conObra ? (
              <ContextoDeLaObra.Provider value={obraAbierta}>
                <SuperficiePresupuesto {...props} />
              </ContextoDeLaObra.Provider>
            ) : (
              <SuperficiePresupuesto {...props} />
            )}
          </ProveedorDeAnuncios>
        </ContextoAplicacion.Provider>
      </MemoryRouter>
    );
    return { ...render(arbol), props, aplicacion };
  }

  test("prueba 10 de §1.10: mientras carga, el esqueleto tiene las cabeceras reales, «Calculando…», ninguna cifra y ninguna región viva con texto", () => {
    responderVista = () => new Promise<Response>(() => {});
    responderRevision = () => new Promise<Response>(() => {});
    const { container } = montar({ props: { borrador: null } });

    const esqueleto = container.querySelector("[aria-busy='true']");
    expect(esqueleto).not.toBeNull();
    const tabla = within(esqueleto as HTMLElement).getByRole("table");
    expect(within(tabla).getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      "Partida",
      "Descripción",
      "Unidad",
      "Cantidad",
      "Precio unitario",
      "Total",
      "Problemas",
    ]);
    expect(screen.getByRole("progressbar", { name: "Cargando el presupuesto" })).toBeInTheDocument();
    expect(screen.getAllByText("Calculando…").length).toBeGreaterThan(0);
    expect(esqueleto?.textContent).not.toMatch(/\d/);
    expect(container.textContent).not.toMatch(/\d/);

    const regionesVivas = container.querySelectorAll('[role="status"], [role="alert"], [aria-live="polite"], [aria-live="assertive"]');
    for (const region of regionesVivas) {
      expect(region.textContent?.trim()).toBe("");
    }
  });

  test("cuando la vista sigue cargando con el borrador abierto, el esqueleto conserva cabeceras sin cifras ni regiones vivas con texto", () => {
    responderVista = () => new Promise<Response>(() => {});
    const { container } = montar();

    const esqueleto = container.querySelector("[aria-busy='true']") as HTMLElement;
    expect(esqueleto).not.toBeNull();
    expect(within(esqueleto).getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      "Partida",
      "Descripción",
      "Unidad",
      "Cantidad",
      "Precio unitario",
      "Total",
      "Problemas",
    ]);
    expect(within(esqueleto).getByText("Calculando…")).toBeInTheDocument();
    expect(esqueleto.textContent).not.toMatch(/\d/);

    const regionesVivas = container.querySelectorAll('[role="status"], [role="alert"], [aria-live="polite"], [aria-live="assertive"]');
    for (const region of regionesVivas) {
      expect(region.textContent?.trim()).toBe("");
    }
  });

  test("prueba 2 de §1.10: la frase de respuesta precede a la grilla en el DOM y la cabecera tiene un solo botón principal", async () => {
    montar();
    const grilla = await screen.findByRole("grid", { name: "Presupuesto" });
    const frase = await screen.findByText(/El presupuesto suma .* sin IVA en 2 partidas\. 1 partida tiene problemas: 1 error y 1 advertencia\./);
    expect(antes(frase, grilla)).toBe(true);

    // Con un error abierto la franja no ofrece «Enviar a aprobación…» (pasoDelPresupuesto): lo que se exige es un solo
    // botón principal en la pantalla, sea cual sea el paso.
    await screen.findByRole("button", { name: /^Problemas \(/ });
    expect(document.querySelectorAll(".cds--btn--primary")).toHaveLength(1);
  });

  test("prueba 1 de §1.10: hay 8 controles de decisión a la vista por omisión o menos, con la fila de alta incluida (sin «Ver el valor exacto» ni lo plegado)", async () => {
    const { container } = montar();
    await screen.findByRole("grid", { name: "Presupuesto" });
    await screen.findByRole("button", { name: /^Problemas \(/ });

    const botones = screen
      .queryAllByRole("button")
      .filter((b) => !(b.getAttribute("aria-label") ?? b.textContent ?? "").startsWith("Ver el valor exacto"));
    const enlaces = screen.queryAllByRole("link");
    // Lo que está dentro de un pliegue cerrado («Cálculo y nota») no se ve ni se tabula: no cuenta como decisión a la vista.
    const camposTexto = screen.queryAllByRole("textbox").filter((c) => c.closest("details:not([open])") === null);
    const combos = screen.queryAllByRole("combobox");
    const grillas = screen.queryAllByRole("grid");
    const summaries = container.querySelectorAll("summary");

    const totalControles = botones.length + enlaces.length + camposTexto.length + combos.length + grillas.length + summaries.length;
    expect(totalControles).toBeLessThanOrEqual(8);
  });

  test("pide la vista y la revisión por su clave ruta@rev y vuelve a pedir cuando sube rev", async () => {
    const aplicacion: Aplicacion = {
      sesion: ARMA,
      proyecto: "OF-001",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    const baseProps: PropiedadesDeSuperficiePresupuesto = {
      proyecto: "OF-001",
      borrador: crearBorrador({ rev: 2 }),
      puedeEditar: true,
      alAusente: vi.fn(),
    };
    const { rerender } = render(
      <MemoryRouter>
        <ContextoAplicacion.Provider value={aplicacion}>
          <SuperficiePresupuesto {...baseProps} />
        </ContextoAplicacion.Provider>
      </MemoryRouter>,
    );

    await screen.findByRole("grid", { name: "Presupuesto" });
    await screen.findByText(/1 partida tiene problemas/);

    const llamadasVistaAntes = fetchFalso.mock.calls.filter(([r]) => String(r).endsWith("/vistas/presupuesto")).length;
    const llamadasRevAntes = fetchFalso.mock.calls.filter(([r]) => String(r).endsWith("/vistas/auditoria")).length;
    expect(llamadasVistaAntes).toBe(1);
    expect(llamadasRevAntes).toBe(1);

    // Con el mismo rev no vuelve a pedir (la caché de useRecurso por ruta@rev responde al instante).
    rerender(
      <MemoryRouter>
        <ContextoAplicacion.Provider value={aplicacion}>
          <SuperficiePresupuesto {...baseProps} borrador={crearBorrador({ rev: 2 })} />
        </ContextoAplicacion.Provider>
      </MemoryRouter>,
    );
    expect(fetchFalso.mock.calls.filter(([r]) => String(r).endsWith("/vistas/presupuesto")).length).toBe(1);
    expect(fetchFalso.mock.calls.filter(([r]) => String(r).endsWith("/vistas/auditoria")).length).toBe(1);

    // Al subir rev cambia la clave a ruta@3 y vuelve a pedir ambas.
    rerender(
      <MemoryRouter>
        <ContextoAplicacion.Provider value={aplicacion}>
          <SuperficiePresupuesto {...baseProps} borrador={crearBorrador({ rev: 3 })} />
        </ContextoAplicacion.Provider>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(fetchFalso.mock.calls.filter(([r]) => String(r).endsWith("/vistas/presupuesto")).length).toBe(2);
      expect(fetchFalso.mock.calls.filter(([r]) => String(r).endsWith("/vistas/auditoria")).length).toBe(2);
    });
  });

  test("tfoot muestra el total sin IVA con MontoExacto, el IVA y el total con IVA del servidor sin ningún title", async () => {
    const { container } = montar();
    const grilla = await screen.findByRole("grid", { name: "Presupuesto" });
    const pie = grilla.querySelector("tfoot");
    expect(pie).not.toBeNull();

    const filaSinIva = within(pie as HTMLElement).getByRole("row", { name: /Total sin IVA/ });
    expect(filaSinIva).toHaveTextContent("2.703,86 USD");
    const botonExacto = within(filaSinIva).getByRole("button", { name: "Ver el valor exacto del total sin IVA" });
    await userEvent.click(botonExacto);
    expect(filaSinIva).toHaveTextContent("Valor exacto: 2.703,8602323440440333 USD");

    expect(within(pie as HTMLElement).getByRole("row", { name: /^IVA \(16 %\)/ })).toHaveTextContent("432,62 USD");
    expect(within(pie as HTMLElement).getByRole("row", { name: /Total con IVA/ })).toHaveTextContent("3.136,48 USD");
    expect(container.querySelectorAll("[title]")).toHaveLength(0);
  });

  test("estado parcial (§1.8): las partidas sin precio dicen «Pendiente» en texto y un fallo de la revisión ofrece «Reintentar la revisión»", async () => {
    let intentoRevision = 0;
    responderRevision = () => {
      intentoRevision += 1;
      if (intentoRevision === 1) return json({ detalle: "Fallo temporal al revisar." }, 503);
      return json(informeAuditoria({ hallazgos: [], sin_hallazgos: "Sílice revisó 18 reglas y no halló problemas." }));
    };
    montar();

    const grilla = await screen.findByRole("grid", { name: "Presupuesto" });
    const filaSalida = within(grilla).getByRole("row", { name: /AF-SALIDA/ });
    expect(within(filaSalida).getAllByRole("gridcell", { name: "Pendiente" })).toHaveLength(2);
    expect(within(filaSalida).getByText("Error")).toBeInTheDocument();

    expect(await screen.findByText(/No se pudo revisar el presupuesto\./)).toBeInTheDocument();
    const reintentar = screen.getByRole("button", { name: "Reintentar la revisión" });
    await userEvent.click(reintentar);

    expect(await screen.findByText(/Sílice revisó 18 reglas y no halló problemas\./)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reintentar la revisión" })).toBeNull();
  });

  test("estado error al leer (§1.8): muestra AvisoError con el detalle del servidor y «Reintentar» vuelve a pedirlo", async () => {
    let intentos = 0;
    responderVista = () => {
      intentos += 1;
      if (intentos === 1) return json({ detalle: "No se pudo leer la carpeta de trabajo." }, 503);
      return json(vistaPresupuesto());
    };
    montar();

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("No se pudo leer la carpeta de trabajo.");
    const reintentar = screen.getByRole("button", { name: "Reintentar" });
    await userEvent.click(reintentar);

    expect(await screen.findByRole("grid", { name: "Presupuesto" })).toBeInTheDocument();
    expect(intentos).toBe(2);
  });

  test("borrador ausente 404 (§1.8): avisa a alAusente y muestra «El borrador ya no está» con «Abrir de nuevo»", async () => {
    responderVista = () => json({ detalle: "Ese borrador ya no está." }, 404);
    const { props } = montar();

    expect(await screen.findByRole("alert")).toHaveTextContent("Ese borrador ya no está.");
    expect(screen.getByText("El borrador ya no está")).toBeInTheDocument();
    await waitFor(() => expect(props.alAusente).toHaveBeenCalledTimes(1));

    await userEvent.click(screen.getByRole("button", { name: "Abrir de nuevo" }));
    expect(props.alReabrir).toHaveBeenCalledTimes(1);
  });

  test("estado vacío (§1.8): muestra «Esta obra aún no tiene partidas», «Agregar la primera partida» como principal y «Traer un cómputo (.csv)»", async () => {
    const vacia: VistaPresupuesto = vistaPresupuesto({ filas: [], vacio_mensaje: null });
    responderVista = () => json(vacia);
    const vacioSinHallazgos: InformeAuditoriaRespuesta = informeAuditoria({
      hallazgos: [],
      sin_hallazgos: "Sílice revisó 18 reglas y no halló problemas.",
    });
    responderRevision = () => json(vacioSinHallazgos);

    montar({
      conObra: true,
      props: {
        borrador: crearBorrador({ version: null, vigente: null, cambios: 0 }),
      },
    });

    expect(await screen.findByText("Esta obra aún no tiene partidas")).toBeInTheDocument();
    const agregarPrimera = screen.getByRole("button", { name: "Agregar la primera partida" });
    expect(agregarPrimera).toHaveClass("cds--btn--primary");
    const traerComputo = screen.getByRole("link", { name: "Traer un cómputo (.csv)" });
    expect(traerComputo).toHaveAttribute("href", "/obra/empresa/1/archivos");
    expect(screen.queryByRole("grid")).toBeNull();
  });

  test("prueba 9 de §1.10: sin permiso muestra la nota de solo lectura, sin fila de alta ni celdas editables", async () => {
    const u = userEvent.setup();
    montar({ sesion: REVISA });

    expect(await screen.findByRole("note")).toHaveTextContent("Está viendo este presupuesto en solo lectura.");
    const grilla = await screen.findByRole("grid", { name: "Presupuesto" });
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("combobox")).toBeNull();

    const celdaCantidad = within(grilla).getByRole("gridcell", { name: "3" });
    await u.click(celdaCantidad);
    await u.keyboard("{F2}{Enter}44");
    expect(screen.queryByRole("textbox")).toBeNull();

    expect(screen.queryByRole("button", { name: "Guardar versión…" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Enviar a aprobación…" })).toBeNull();
    expect(screen.getByRole("button", { name: "Problemas (2)" })).toBeInTheDocument();
  });

  test("con borrador solo_lectura tampoco permite editar aunque la sesión tenga editar_hoja", async () => {
    const u = userEvent.setup();
    montar({
      sesion: ARMA,
      props: {
        borrador: crearBorrador({ soloLectura: true }),
      },
    });

    const nota = await screen.findByRole("note");
    expect(nota).toHaveTextContent("Está viendo este presupuesto en solo lectura.");
    expect(nota).toHaveTextContent("Esta versión no se puede guardar");
    const grilla = await screen.findByRole("grid", { name: "Presupuesto" });
    await u.click(within(grilla).getByRole("gridcell", { name: "3" }));
    await u.keyboard("{F2}");
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  test("lote G3: la cabecera dice «Total sin IVA» con «Con IVA (16 %)» debajo cuando hay filas, sin <p> anidados", async () => {
    const { container } = montar();
    await screen.findByRole("grid", { name: "Presupuesto" });
    const estado = screen.getByRole("region", { name: "Estado del borrador" });
    expect(estado).toHaveTextContent("Total sin IVA 2.703,86 USD");
    expect(estado).toHaveTextContent("Con IVA (16 %) 3.136,48 USD");
    expect(container.querySelectorAll("p p")).toHaveLength(0);
  });

  test("lote G3: «Más acciones» ofrece «Subtotales por frente» en panel lateral y los enlaces a Archivos y a pestañas", async () => {
    const u = userEvent.setup();
    montar({ conObra: true });
    await screen.findByRole("grid", { name: "Presupuesto" });

    const botonMenu = screen.getByRole("button", { name: "Más acciones del presupuesto" });
    await u.click(botonMenu);

    expect(screen.getByRole("link", { name: "Traer un plano o cómputo" })).toHaveAttribute(
      "href",
      "/obra/empresa/1/archivos",
    );
    expect(screen.getByRole("link", { name: "Espacio, plan y ajustes" })).toHaveAttribute(
      "href",
      "/obra/empresa/1/presupuesto/pestanas",
    );

    const frentesBtn = screen.getByRole("button", { name: "Subtotales por frente" });
    await u.click(frentesBtn);

    const panel = await screen.findByRole("complementary", { name: "Subtotales por frente" });
    expect(await within(panel).findByText("FRENTE A")).toBeInTheDocument();
    expect(within(panel).getByText(/^Total general: /)).toBeInTheDocument();

    await u.click(within(panel).getByRole("button", { name: "Cerrar" }));
    expect(screen.queryByRole("complementary", { name: "Subtotales por frente" })).toBeNull();
    expect(botonMenu).toHaveFocus();
  });

  test("el medio céntimo del IVA (0,03 -> 0,01 -> 0,04) se muestra verbatim y quien revisa también ve el IVA", async () => {
    responderVista = () =>
      json(
        vistaPresupuesto({
          total: { texto: "0.03", exacto: "0.03" },
          impuestos: {
            subtotal: "0.03",
            iva: "0.01",
            total: "0.04",
            alicuota: "0.16",
            fuente_alicuota: "Ley del IVA",
          },
        }),
      );
    const { rerender, aplicacion, props } = montar();
    const grilla = await screen.findByRole("grid", { name: "Presupuesto" });
    const pie = grilla.querySelector("tfoot")!;
    expect(within(pie).getByRole("row", { name: /^IVA \(16 %\)/ })).toHaveTextContent("0,01 USD");
    const pieRevisa = screen.getByRole("grid", { name: "Presupuesto" }).querySelector("tfoot")!;
    expect(within(pieRevisa).getByRole("row", { name: /Total con IVA/ })).toHaveTextContent("0,04 USD");

    rerender(
      <MemoryRouter>
        <ContextoAplicacion.Provider value={{ ...aplicacion, sesion: REVISA }}>
          <ProveedorDeAnuncios>
            <SuperficiePresupuesto {...props} puedeEditar={false} />
          </ProveedorDeAnuncios>
        </ContextoAplicacion.Provider>
      </MemoryRouter>,
    );
    const pieRevisa = screen.getByRole("grid", { name: "Presupuesto" }).querySelector("tfoot")!;
    expect(within(pieRevisa).getByRole("row", { name: /Total con IVA/ })).toHaveTextContent("0,04 USD");
  });

  describe("portado de pruebas de edición, alta, Componer e inspector en superficie", () => {
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

    const PARED: FilaPresupuesto = {
      ...vistaPresupuesto().filas[0]!,
      clave: "OBRA-04|a-mano:1",
      partida: "OBRA-04",
      descripcion: "Pared de bloques de arcilla de 15 cm",
      unidad: "m2",
      cantidad: "12",
      cantidad_calculada: "12",
      escrita: false,
      quitable: true,
    };

    afterEach(() => {
      olvidarFormularios();
    });

    function diferida() {
      let soltar: (r: Response) => void = () => undefined;
      const promesa = new Promise<Response>((resolver) => {
        soltar = resolver;
      });
      return { promesa, soltar };
    }

    function prepararServidor(opciones: {
      alPonerCantidades?: (cuerpo: Record<string, unknown>) => Response | Promise<Response>;
      alAgregar?: (cuerpo: Record<string, unknown>) => Response | Promise<Response>;
      alPonerApu?: (cuerpo: Record<string, unknown>) => Response | Promise<Response>;
      vistaActual?: () => VistaPresupuesto;
    } = {}) {
      let vista = vistaPresupuesto();
      fetchFalso.mockImplementation(async (ruta, init) => {
        const url = String(ruta);
        const metodo = init?.method ?? "GET";
        const u = new URL(url, "http://silice.local");
        const camino = decodeURIComponent(u.pathname);
        if (camino === "/v1/aprobaciones") return json(APROBACIONES);
        if (camino === `/v1/hoja/borradores/${ID}/vistas/presupuesto`) return json(opciones.vistaActual ? opciones.vistaActual() : vista);
        if (camino === `/v1/hoja/borradores/${ID}/vistas/auditoria`) return json(informeAuditoria());
        if (camino === `/v1/hoja/borradores/${ID}/vistas/apu`) return json(vistaApu());
        if (camino === `/v1/hoja/borradores/${ID}/cantidades` && metodo === "PUT") {
          return opciones.alPonerCantidades
            ? opciones.alPonerCantidades(JSON.parse(String(init?.body)) as Record<string, unknown>)
            : json({ rev: 3, resumen: { ...crearBorrador().resumen, rev: 3, cambios: 1 } });
        }
        if (camino === `/v1/hoja/borradores/${ID}/partidas` && metodo === "POST") {
          const cuerpo = JSON.parse(String(init?.body)) as Record<string, unknown>;
          if (opciones.alAgregar) return opciones.alAgregar(cuerpo);
          vista = { ...vista, filas: [...vista.filas, PARED] };
          return json({
            rev: (cuerpo.rev as number) + 1,
            resumen: { ...crearBorrador().resumen, rev: (cuerpo.rev as number) + 1, cambios: 1 },
            clave: PARED.clave,
          });
        }
        if (camino.startsWith(`/v1/hoja/borradores/${ID}/apu/`) && metodo === "PUT") {
          return opciones.alPonerApu
            ? opciones.alPonerApu(JSON.parse(String(init?.body)) as Record<string, unknown>)
            : json({ rev: 3, resumen: { ...crearBorrador().resumen, rev: 3, cambios: 1 }, apu: vistaApu() });
        }
        if (camino === "/v1/buscar/partidas") {
          const q = u.searchParams.get("q") ?? "";
          return json(q.toLowerCase().includes("bloq") ? HALLADAS : { ...HALLADAS, resultados: [] });
        }
        if (camino === "/v1/composicion/opciones") return json({ dominios: ["civil"], modalidades: ["jornal"] });
        if (camino === "/v1/composicion/evaluar") {
          return json({ estado: "vacio", aviso: "Complete la partida.", desglose: null, advertencias: [], requiere_justificacion: false, contraste: null });
        }
        if (camino.startsWith("/v1/composicion/partidas/")) {
          return json({ existe: false, tablas: { materiales: [], equipos: [], mano_obra: [] }, rendimiento_propuesto: null, hay_historial: false });
        }
        if (camino === "/v1/composicion/prever") {
          return json({ lista: { nombre: "Lista", moneda: "USD", fecha: "2026-10-26" }, lista_nueva: false, variantes: [] });
        }
        if (camino === "/v1/composicion/guardar" && metodo === "POST") {
          return json({ precio_unitario: "120.00", mensaje: "Composición guardada para Z-99.", justificada: false, avisos: [] });
        }
        if (camino === "/v1/carpeta") {
          return json({ moneda: "USD", declarada: true, lista: { nombre: "Lista", moneda: "USD", fecha: "2026-10-25", origen: "prueba" }, aviso: null });
        }
        if (camino === "/v1/consulta/unidades") return json({ unidades: [] });
        if (camino.startsWith("/v1/composicion/referencia") || camino.startsWith("/v1/composicion/similares")) return json([]);
        return new Response(null, { status: 404 });
      });
    }

    test("al agregar con FilaDeAlta, POST /partidas espera el PUT de cantidades pendiente y lleva su rev", async () => {
      const put = diferida();
      prepararServidor({ alPonerCantidades: () => put.promesa });
      const u = userEvent.setup();
      montar();

      const grilla = await screen.findByRole("grid", { name: "Presupuesto" });
      const celda = within(grilla).getByRole("gridcell", { name: "3" });
      celda.focus();
      await u.keyboard("{F2}{Backspace}250");

      const partida = screen.getByRole("combobox", { name: "Partida" });
      await u.type(partida, "bloq");
      await u.click(await screen.findByRole("option", { name: /OBRA-04/ }));
      await u.type(screen.getByRole("textbox", { name: /^Cantidad/ }), "12");
      await u.click(screen.getByRole("button", { name: "Agregar al presupuesto" }));

      await waitFor(() =>
        expect(fetchFalso.mock.calls.filter(([r, i]) => String(r).endsWith("/cantidades") && i?.method === "PUT")).toHaveLength(1),
      );
      expect(fetchFalso.mock.calls.filter(([r, i]) => String(r).endsWith("/partidas") && i?.method === "POST")).toHaveLength(0);

      put.soltar(json({ rev: 5, resumen: { ...crearBorrador().resumen, rev: 5, cambios: 1 } }));
      await waitFor(() => {
        const posts = fetchFalso.mock.calls.filter(([r, i]) => String(r).endsWith("/partidas") && i?.method === "POST");
        expect(posts).toHaveLength(1);
        expect(JSON.parse(String(posts[0]![1]?.body))).toEqual({ rev: 5, codigo: "OBRA-04", cantidad: "12", calculo: "", nota: "" });
      });
    });

    test("al agregar, la cantidad rechazada con 422 en otra fila sigue escrita con su aviso", async () => {
      const DETALLE = "presupuesto, fila 1 (AF-LLAVE): Use la coma para los decimales.";
      prepararServidor({ alPonerCantidades: () => json({ detalle: DETALLE }, 422) });
      const u = userEvent.setup();
      montar();

      const grilla = await screen.findByRole("grid", { name: "Presupuesto" });
      within(grilla).getByRole("gridcell", { name: "3" }).focus();
      await u.keyboard("{F2}{Backspace}2.5");
      await u.type(screen.getByRole("combobox", { name: "Partida" }), "bloq");
      expect(await screen.findByRole("alert")).toHaveTextContent(DETALLE);

      await u.click(await screen.findByRole("option", { name: /OBRA-04/ }));
      await u.type(screen.getByRole("textbox", { name: /^Cantidad/ }), "12");
      await u.click(screen.getByRole("button", { name: "Agregar al presupuesto" }));

      await waitFor(() => expect(within(grilla).getByRole("rowheader", { name: "OBRA-04" })).toBeInTheDocument());
      expect(within(grilla).getByRole("textbox", { name: "Cantidad, AF-LLAVE" })).toHaveValue("2.5");
      expect(screen.getByRole("alert")).toHaveTextContent(DETALLE);
    });

    test("B1-9: ComponerEnPanel abre desde FilaDeAlta, Esc vuelve a «Partida» conservando Cantidad, y guardar selecciona la partida nueva", async () => {
      prepararServidor();
      const u = userEvent.setup();
      montar();
      await screen.findByRole("grid", { name: "Presupuesto" });

      await u.type(screen.getByRole("textbox", { name: /^Cantidad/ }), "12");
      const partida = screen.getByRole("combobox", { name: "Partida" });
      await u.type(partida, "Z-99");
      await u.click(await screen.findByRole("option", { name: "Crear la partida «Z-99»" }));

      const panel = await screen.findByRole("complementary", { name: "Componer una partida" });
      expect(within(panel).getByRole("note")).toHaveTextContent("Esto cambia el catálogo de la empresa");
      expect(within(panel).getByLabelText("Código")).toHaveValue("Z-99");

      // Esc cierra sin guardar y vuelve el foco a «Partida» conservando «12» en Cantidad.
      await u.keyboard("{Escape}");
      await waitFor(() => expect(screen.queryByRole("complementary", { name: "Componer una partida" })).toBeNull());
      expect(screen.getByRole("textbox", { name: /^Cantidad/ })).toHaveValue("12");
      await waitFor(() => expect(screen.getByRole("combobox", { name: "Partida" })).toHaveFocus());

      // Vuelve a abrir, guarda la composición y la partida queda elegida en FilaDeAlta con foco en Cantidad.
      const partidaReabierta = screen.getByRole("combobox", { name: "Partida" });
      await u.clear(partidaReabierta);
      await u.type(partidaReabierta, "Z-99");
      await u.click(await screen.findByRole("option", { name: "Crear la partida «Z-99»" }));
      const panel2 = await screen.findByRole("complementary", { name: "Componer una partida" });
      await u.type(within(panel2).getByLabelText("Descripción"), "Zanja ficticia");
      await u.type(within(panel2).getByLabelText("Unidad"), "m3");
      await u.type(within(panel2).getByLabelText("Condiciones del rendimiento"), "Condiciones ficticias");
      await u.click(within(panel2).getByRole("button", { name: "Guardar composición" }));

      await waitFor(() => expect(screen.queryByRole("complementary", { name: "Componer una partida" })).toBeNull());
      expect(screen.getByRole("combobox", { name: "Partida" })).toHaveValue("Z-99 · Zanja ficticia");
      await waitFor(() => expect(screen.getByRole("textbox", { name: "Cantidad (m³)" })).toHaveFocus());
    });

    test("editar una cantidad del APU en InspectorDePartida relee el presupuesto y actualiza el total", async () => {
      let borradorActual = crearBorrador({ rev: 2 });
      let vistaActual = vistaPresupuesto();
      prepararServidor({
        vistaActual: () => vistaActual,
        alPonerApu: (cuerpo) => {
          const nuevoResumen = {
            ...borradorActual.resumen,
            rev: (cuerpo.rev as number) + 1,
            cambios: 1,
            total: { texto: "2800.50", exacto: "2800.5" },
          };
          borradorActual = { ...borradorActual, resumen: nuevoResumen };
          vistaActual = vistaPresupuesto({ total: { texto: "2800.50", exacto: "2800.5" } });
          return json({ rev: nuevoResumen.rev, resumen: nuevoResumen, apu: vistaApu() });
        },
      });
      const u = userEvent.setup();
      function Envoltura() {
        const [actual, setActual] = useState(borradorActual);
        return (
          <MemoryRouter>
            <ContextoAplicacion.Provider
              value={{
                sesion: ARMA,
                proyecto: "OF-001",
                caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
                recargarProyectos: vi.fn(),
                alExpirar: vi.fn(),
              }}
            >
              <ProveedorDeAnuncios>
                <SuperficiePresupuesto
                  proyecto="OF-001"
                  borrador={actual}
                  puedeEditar
                  alAusente={vi.fn()}
                  alAceptar={(r) => setActual((b) => ({ ...b, resumen: r }))}
                />
              </ProveedorDeAnuncios>
            </ContextoAplicacion.Provider>
          </MemoryRouter>
        );
      }
      render(<Envoltura />);

      const grilla = await screen.findByRole("grid", { name: "Presupuesto" });
      await u.click(within(grilla).getByRole("rowheader", { name: "AF-LLAVE" }));
      const panel = await screen.findByRole("complementary", { name: "AF-LLAVE · Llave de paso · unidad" });
      const campoMaterial = await within(panel).findByRole("textbox", { name: "Cantidad, Materiales fila 1" });
      fireEvent.change(campoMaterial, { target: { value: "2,5" } });

      await waitFor(() =>
        expect(within(grilla.querySelector("tfoot")!).getByRole("row", { name: /Total sin IVA/ })).toHaveTextContent("2.800,50 USD"),
      );
      expect(screen.getByRole("region", { name: "Estado del borrador" })).toHaveTextContent("2.800,50 USD");
    });
  });
});
