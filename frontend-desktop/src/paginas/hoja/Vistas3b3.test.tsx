import { configure, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import {
  atipicosRespuesta,
  cuerpoDeVista,
  informeAuditoria,
  preciosRespuesta,
  trazabilidadRespuesta,
  vistaEquilibrio,
  vistaParametros,
} from "./datosDePrueba";
import PaginaHoja from "./index";
import { PESTANAS } from "./logica";
import type { BorradorAbierto, VersionesRespuesta } from "./logica";

// La primera vista tarda en una máquina cargada (importa Carbon y la tabla): se espera más que el 1 s por omisión.
configure({ asyncUtilTimeout: 5000 });

// El gráfico de Carbon no se dibuja en jsdom: se deja una marca con las filas que recibiría.
vi.mock("../../comun/GraficoCarbon", () => ({
  default: ({ datos }: { datos: unknown[] }) => <div data-testid="grafico" data-filas={datos.length} />,
}));

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

const ID = "id-borrador-aaaaaaaaaaaa";
const VERSIONES: VersionesRespuesta = {
  proyecto: "OF-001",
  moneda: "USD",
  por_omision: "002",
  versiones: [
    { codigo: "001", fecha: "2026-10-05", motivo: "", origen: "", vigente: false, descartada: false, cambios: 0 },
    { codigo: "002", fecha: "2026-10-06", motivo: "edicion", origen: "001", vigente: true, descartada: false, cambios: 1 },
  ],
};

function borrador(version: string | null = "002"): BorradorAbierto {
  return {
    id: ID,
    base: { proyecto: "OF-001", version, vigente: "002", lista: "Lista MaPreX", espacio_de: version, solo_lectura: false, moneda: "USD" },
    resumen: {
      rev: 0,
      moneda: "USD",
      total: { texto: "2703.86", exacto: "2703.860232344044033333333333" },
      cambios: 0,
      pendientes_catalogo: 0,
      hallazgos: [],
      hay_plan: true,
      version_mas_nueva: null,
      guardado_como: null,
    },
    instantanea: { creadas: 0, mensaje: null },
  };
}

type Respuesta = (url: string) => Response | Promise<Response>;
interface Propias {
  vistas?: Partial<Record<"espacio" | "presupuesto" | "equilibrio" | "parametros" | "auditoria", Respuesta>>;
  precios?: Respuesta;
  atipicos?: Respuesta;
  trazabilidad?: Respuesta;
  version?: string | null;
}

describe("Hoja del proyecto: Equilibrio, Parámetros, Auditoría, Precios y Trazabilidad (3b-3)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    localStorage.clear();
    sessionStorage.clear();
  });
  afterEach(() => vi.unstubAllGlobals());

  function servidor(propias: Propias = {}) {
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/hoja/versiones")) return json(VERSIONES);
      if (url === "/v1/hoja/borradores" && metodo === "POST") return json(borrador(propias.version), 201);
      if (url.includes("/vistas/")) {
        const nombre = /\/vistas\/([a-z]+)/.exec(url)![1] as keyof NonNullable<Propias["vistas"]>;
        const propia = propias.vistas?.[nombre];
        return propia ? propia(url) : json(cuerpoDeVista(url));
      }
      if (url.startsWith("/v1/hoja/precios/atipicos")) return (propias.atipicos ?? (() => json(atipicosRespuesta())))(url);
      if (url.startsWith("/v1/hoja/precios")) return (propias.precios ?? (() => json(preciosRespuesta())))(url);
      if (url.startsWith("/v1/hoja/trazabilidad")) return (propias.trazabilidad ?? (() => json(trazabilidadRespuesta())))(url);
      return new Response(null, { status: 204 });
    });
  }

  function pedidas(trozo: string): string[] {
    return fetchFalso.mock.calls.map(([r]) => String(r)).filter((r) => r.includes(trozo));
  }

  function montar() {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: "OF-001",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <PaginaHoja />
      </ContextoAplicacion.Provider>,
    );
  }

  async function irA(pestana: string) {
    await screen.findByRole("region", { name: "Estado del borrador" });
    await userEvent.click(screen.getByRole("tab", { name: pestana }));
  }

  // --- Punto de equilibrio ------------------------------------------------------------------------

  test("3b-F9: las cuatro métricas, el punto, su porcentaje y la frase del caso (cifras de OF-001)", async () => {
    servidor();
    montar();
    await irA("Punto de equilibrio");
    const rotulo = await screen.findByText("Ventas (contrato)");
    const dl = rotulo.closest("dl")!;
    expect(within(dl).getByText("Ventas (contrato)").nextElementSibling).toHaveTextContent("2.703,86 USD");
    expect(within(dl).getByText("Costo variable").nextElementSibling).toHaveTextContent("2.137,44 USD");
    expect(within(dl).getByText("Costo fijo").nextElementSibling).toHaveTextContent("320,62 USD");
    expect(within(dl).getByText("Utilidad").nextElementSibling).toHaveTextContent("245,81 USD");
    expect(within(dl).getByText("Punto de equilibrio").nextElementSibling).toHaveTextContent("1.530,49 USD");
    expect(within(dl).getByText("Como % de las ventas").nextElementSibling).toHaveTextContent("56,60 %");
    expect(within(dl).getByText("Se alcanza en").nextElementSibling).toHaveTextContent("Día 23");
    // El exacto va en el title y en un texto accesible; nada se redondea en la interfaz.
    expect(within(dl).getByTitle("1530.4912345")).toBeInTheDocument();
    expect(within(dl).getByText(/Valor exacto 1530.4912345/)).toBeInTheDocument();
    expect(screen.getByText("Se alcanza en Dia 23, al 50 % de ese periodo.")).toBeInTheDocument();
  });

  test("3b-F9: sin punto de equilibrio no se muestra «Punto de equilibrio» y sí la frase que lo explica", async () => {
    const mensaje = "El presupuesto no tiene ventas: el punto de equilibrio no aplica.";
    servidor({
      vistas: {
        equilibrio: () =>
          json(vistaEquilibrio({ estado: "sin_ventas", punto: null, porcentaje: null, periodo: null, fraccion_periodo: null, mensaje })),
      },
    });
    montar();
    await irA("Punto de equilibrio");
    expect(await screen.findByText(mensaje)).toBeInTheDocument();
    expect(screen.getByText("Ventas (contrato)")).toBeInTheDocument();
    expect(screen.queryByText("Punto de equilibrio", { selector: "dt" })).toBeNull();
    expect(screen.queryByText("Como % de las ventas")).toBeNull();
    expect(screen.queryByText("Se alcanza en")).toBeNull();
  });

  test("3b-F9: el punto sin período (sin curva) muestra el punto y la frase, sin «Se alcanza en»", async () => {
    const mensaje = "Sin curva de inversión: el punto de equilibrio no se ubica en el plan.";
    servidor({ vistas: { equilibrio: () => json(vistaEquilibrio({ periodo: null, fraccion_periodo: null, mensaje })) } });
    montar();
    await irA("Punto de equilibrio");
    expect(await screen.findByText(mensaje)).toBeInTheDocument();
    expect(screen.getByText("Punto de equilibrio", { selector: "dt" })).toBeInTheDocument();
    expect(screen.queryByText("Se alcanza en")).toBeNull();
  });

  test("3b-F9: un monto de treinta cifras no pierde ninguna", async () => {
    const largo = "1234567890123456789012345.123456789012";
    servidor({ vistas: { equilibrio: () => json(vistaEquilibrio({ venta: { texto: largo, exacto: largo } })) } });
    montar();
    await irA("Punto de equilibrio");
    expect(await screen.findByText(/1\.234\.567\.890\.123\.456\.789\.012\.345,123456789012 USD/)).toBeInTheDocument();
  });

  test("3b-F9: la moneda que manda la vista es la de las cifras", async () => {
    servidor({ vistas: { equilibrio: () => json(vistaEquilibrio({ moneda: "Bs" })) } });
    montar();
    await irA("Punto de equilibrio");
    expect(await screen.findByText("Ventas (contrato)")).toBeInTheDocument();
    expect(screen.getByTitle("1530.4912345")).toHaveTextContent("1.530,49 Bs");
  });

  test("3b-F9: el período se lee sin los códigos entre corchetes que le pone el servidor", async () => {
    servidor({ vistas: { equilibrio: () => json(vistaEquilibrio({ periodo: "Dia 6 [TI-PTO, TI-UTP, TI-LAP]" })) } });
    montar();
    await irA("Punto de equilibrio");
    const dd = (await screen.findByText("Se alcanza en")).nextElementSibling!;
    expect(dd).toHaveTextContent("Día 6");
    expect(dd).not.toHaveTextContent(/TI-PTO|\[/);
  });

  test("Parámetros: el texto de ayuda habla de lectura, no de edición", async () => {
    servidor();
    montar();
    await irA("Parámetros");
    expect(await screen.findByText(/solo se leen/)).toBeInTheDocument();
    expect(screen.queryByText(/Cambiarlos recalcula/)).toBeNull();
  });

  // --- Parámetros ---------------------------------------------------------------------------------

  test("Parámetros: los cuatro parámetros de costo en lectura, con es-VE y su valor escrito en el title", async () => {
    servidor();
    montar();
    await irA("Parámetros");
    const lista = (await screen.findByText(/^FCAS/)).closest("dl")!;
    const fila = (rotulo: RegExp) => within(lista).getByText(rotulo).nextElementSibling!;
    expect(fila(/^FCAS/)).toHaveTextContent("6,00");
    expect(fila(/^FCAS/).querySelector('[title="6.00"]')).not.toBeNull();
    expect(fila(/^Bono de alimentación/)).toHaveTextContent("5,8100");
    expect(fila(/^Administración/)).toHaveTextContent("0,15");
    expect(fila(/^Utilidad/)).toHaveTextContent("0,10");
    // En esta entrega solo se leen: editarlos es de la rebanada 3c.
    expect(screen.queryAllByRole("textbox")).toEqual([]);
  });

  test("Parámetros: la moneda del proyecto y el total del presupuesto", async () => {
    servidor();
    montar();
    await irA("Parámetros");
    expect(await screen.findByText("Moneda del proyecto: USD")).toBeInTheDocument();
    expect(screen.getByTitle("2703.860232344044")).toHaveTextContent("2.703,86 USD");
  });

  test("Parámetros: sin moneda del proyecto no se inventa una", async () => {
    servidor({ vistas: { parametros: () => json(vistaParametros({ moneda_proyecto: null })) } });
    montar();
    await irA("Parámetros");
    await screen.findByText(/^FCAS/);
    expect(screen.queryByText(/Moneda del proyecto/)).toBeNull();
  });

  // --- Auditoría ----------------------------------------------------------------------------------

  test("Auditoría: el veredicto, la tabla de hallazgos con R17 nombrando el punto y las reglas evaluadas", async () => {
    servidor();
    montar();
    await irA("Auditoría");
    const informe = await screen.findByRole("region", { name: "Informe de auditoría" });
    expect(within(informe).getByText(/Presupuesto OF-001-001/)).toBeInTheDocument();
    expect(within(informe).getByText(/Resultado: NO CUMPLE/)).toBeInTheDocument();
    const tabla = within(informe).getByRole("table", { name: "Hallazgos" });
    expect(within(tabla).getAllByRole("row")).toHaveLength(3);
    expect(within(tabla).getByText("R17")).toBeInTheDocument();
    expect(within(tabla).getByText("El punto P1 no tiene fuente que lo alimente")).toBeInTheDocument();
    expect(screen.getByText("El informe se genera siempre, con todas las reglas, sobre el borrador vigente.")).toBeInTheDocument();
  });

  test("3b-F12: la descripción de un hallazgo es texto plano: un Markdown de imagen no crea una imagen", async () => {
    servidor();
    montar();
    await irA("Auditoría");
    const informe = await screen.findByRole("region", { name: "Informe de auditoría" });
    expect(within(informe).getByText(/!\[x\]\(http:\/\/ejemplo\.invalid\/a\.png\)/)).toBeInTheDocument();
    expect(informe.querySelector("img")).toBeNull();
    expect(informe.querySelector("a")).toBeNull();
  });

  test("Auditoría: sin hallazgos se muestra el informe con su declaración, no un vacío", async () => {
    const limpio = informeAuditoria({
      cumple: true,
      veredicto: "CUMPLE",
      total_hallazgos: 0,
      hallazgos: [],
      por_severidad: [],
      sin_hallazgos: "Se verificaron 17 reglas y no hubo hallazgos.",
    });
    servidor({ vistas: { auditoria: () => json(limpio) } });
    montar();
    await irA("Auditoría");
    expect(await screen.findByText("Se verificaron 17 reglas y no hubo hallazgos.")).toBeInTheDocument();
    expect(screen.getByText(/Resultado: CUMPLE/)).toBeInTheDocument();
  });

  test("3b-F6b: «Ver en Auditoría» lleva a la pestaña con solo los hallazgos de esa fila", async () => {
    servidor();
    montar();
    const tabla = await screen.findByRole("table", { name: "Fuentes" });
    await userEvent.click(within(tabla).getByRole("button", { name: "Ver en Auditoría: Fuente F1" }));
    expect(await screen.findByRole("tab", { name: "Auditoría", selected: true })).toBeInTheDocument();
    const informe = await screen.findByRole("region", { name: "Informe de auditoría" });
    expect(screen.getByText("Hallazgos de Fuente F1").parentElement).toHaveFocus();
    const hallazgos = within(informe).getByRole("table", { name: "Hallazgos" });
    expect(within(hallazgos).getAllByRole("row")).toHaveLength(2);
    expect(within(hallazgos).getByText(/Fuente F1: falta el origen/)).toBeInTheDocument();
    expect(within(hallazgos).queryByText("R17")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Quitar filtro" }));
    expect(within(await screen.findByRole("table", { name: "Hallazgos" })).getAllByRole("row")).toHaveLength(3);
    expect(screen.queryByText("Hallazgos de Fuente F1")).toBeNull();
  });

  test("3b-F6b: las filas sin hallazgos (Estado OK) no ofrecen el enlace", async () => {
    servidor();
    montar();
    const tabla = await screen.findByRole("table", { name: "Ambientes" });
    expect(within(tabla).getByRole("button", { name: "Ver en Auditoría: Ambiente BAN-01" })).toBeInTheDocument();
    expect(within(tabla).getAllByRole("button")).toHaveLength(1); // COC-01 está OK
  });

  test("3b-F6b: una fila cuyos hallazgos no están en el informe lo dice, sin tabla vacía", async () => {
    servidor();
    montar();
    const tabla = await screen.findByRole("table", { name: "Ambientes" });
    await userEvent.click(within(tabla).getByRole("button", { name: "Ver en Auditoría: Ambiente BAN-01" }));
    expect(await screen.findByText("Ningún hallazgo del informe nombra a Ambiente BAN-01.")).toBeInTheDocument();
    expect(screen.queryByRole("table", { name: "Hallazgos" })).toBeNull();
  });

  test("3b-F6b: ir a la pestaña Auditoría a mano muestra el informe entero, sin el filtro de antes", async () => {
    servidor();
    montar();
    const tabla = await screen.findByRole("table", { name: "Fuentes" });
    await userEvent.click(within(tabla).getByRole("button", { name: "Ver en Auditoría: Fuente F1" }));
    await screen.findByText("Hallazgos de Fuente F1");
    await userEvent.click(screen.getByRole("tab", { name: "APU" }));
    await userEvent.click(screen.getByRole("tab", { name: "Auditoría" }));
    const hallazgos = await screen.findByRole("table", { name: "Hallazgos" });
    expect(within(hallazgos).getAllByRole("row")).toHaveLength(3);
    expect(screen.queryByText("Hallazgos de Fuente F1")).toBeNull();
  });

  test("3b-F6b: en el Presupuesto, el Estado de un renglón también lleva a sus hallazgos", async () => {
    const informe = informeAuditoria();
    const propio = { ...informe.hallazgos[1]!, numero: 7, origen: ["esp_puntos:P2"], descripcion: "El punto P2 sin APU" };
    servidor({ vistas: { auditoria: () => json({ ...informe, hallazgos: [informe.hallazgos[0]!, propio] }) } });
    montar();
    await irA("Presupuesto");
    const tabla = await screen.findByRole("table", { name: "Presupuesto" });
    await userEvent.click(within(tabla).getByRole("button", { name: "Ver en Auditoría: AF-SALIDA, Punto P2" }));
    const hallazgos = await screen.findByRole("table", { name: "Hallazgos" });
    expect(within(hallazgos).getAllByRole("row")).toHaveLength(2);
    expect(within(hallazgos).getByText("El punto P2 sin APU")).toBeInTheDocument();
  });

  // --- Precios ------------------------------------------------------------------------------------

  test("Precios: sin versión abierta lo dice y no pide nada", async () => {
    servidor({ version: null });
    montar();
    await irA("Precios");
    expect(await screen.findByText("Abra una versión guardada para ver el origen de sus precios.")).toBeInTheDocument();
    expect(pedidas("/v1/hoja/precios")).toEqual([]);
  });

  test("3b-F10: la tabla muestra las columnas principales y el detalle de cada insumo lleva el resto", async () => {
    servidor();
    montar();
    await irA("Precios");
    const tabla = await screen.findByRole("table", { name: "Precios" });
    expect(within(tabla).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([
      "Insumo",
      "Código",
      "Precio",
      "Lista",
      "Moneda",
      "Fecha del precio",
      "Referencia",
      "Cotización",
      "Estado",
      "Detalle",
    ]);
    const fila = within(tabla).getAllByRole("row")[1]!;
    expect(within(fila).getByText("Tubo PVC 1/2")).toBeInTheDocument();
    expect(within(fila).getByTitle("3.1034")).toHaveTextContent("3,10");
    expect(within(fila).getByText("01/07/2026")).toBeInTheDocument();
    expect(within(fila).getByText("OK")).toBeInTheDocument();
    // Lo que no es principal no está en la tabla.
    expect(within(tabla).queryByText("Tasa")).toBeNull();
    await userEvent.click(within(fila).getByRole("button", { name: "Detalle de MAT-001" }));
    const detalle = await screen.findByRole("region", { name: "Detalle de MAT-001" });
    const campo = (rotulo: string) => within(detalle).getByText(rotulo, { selector: "dt" }).nextElementSibling!;
    expect(campo("Tipo")).toHaveTextContent("material");
    expect(campo("Tasa")).toHaveTextContent("633,3644");
    expect(campo("Fecha de la tasa")).toHaveTextContent("01/07/2026");
    expect(campo("Moneda original")).toHaveTextContent("Bs");
    expect(campo("Precio original")).toHaveTextContent("1.963,43");
    expect(campo("Fuente de la tasa")).toHaveTextContent("BCV");
    expect(campo("Fuente")).toHaveTextContent("MaPreX");
    expect(campo("Propio/heredado")).toHaveTextContent("heredado");
    expect(campo("Erosión USD")).toHaveTextContent("0,12");
    expect(campo("Erosión Bs")).toHaveTextContent("78,15");
    expect(campo("Erosión %")).toHaveTextContent("3,98 %");
    expect(within(detalle).getByTitle("78.1500")).toBeInTheDocument();
    expect(within(detalle).queryByText("Erosión por índice")).toBeNull();
  });

  test("3b-F10: el detalle se abre y se cierra con su botón, que dice si está abierto", async () => {
    servidor();
    montar();
    await irA("Precios");
    const boton = await screen.findByRole("button", { name: "Detalle de MAT-001" });
    expect(boton).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(boton);
    expect(boton).toHaveAttribute("aria-expanded", "true");
    await userEvent.click(boton);
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("region", { name: "Detalle de MAT-001" })).toBeNull();
  });

  test("3b-F10: lo que no tiene dato se lee «Sin dato» en el detalle y el Estado sin fuente lleva ícono", async () => {
    servidor();
    montar();
    await irA("Precios");
    const tabla = await screen.findByRole("table", { name: "Precios" });
    const fila = within(tabla).getAllByRole("row")[2]!;
    expect(within(fila).getByText("Sin referencia ni cotización: el precio no tiene fuente")).toBeInTheDocument();
    expect(within(fila).getByText("Advertencia")).toBeInTheDocument();
    await userEvent.click(within(fila).getByRole("button", { name: "Detalle de MAT-002" }));
    const detalle = await screen.findByRole("region", { name: "Detalle de MAT-002" });
    expect(within(detalle).getByText("Tasa", { selector: "dt" }).nextElementSibling).toHaveTextContent("Sin dato");
    expect(within(detalle).getByText("Erosión USD", { selector: "dt" }).nextElementSibling).toHaveTextContent("Sin dato");
  });

  test("3b-F10: «Erosión por índice» aparece en el detalle solo si algún valor viene", async () => {
    const base = preciosRespuesta();
    const filas = base.filas.map((f, i) => (i === 0 ? { ...f, erosion_indice: { texto: "1.25", exacto: "1.2512" } } : f));
    servidor({ precios: () => json({ ...base, filas }) });
    montar();
    await irA("Precios");
    await userEvent.click(await screen.findByRole("button", { name: "Detalle de MAT-001" }));
    const detalle = await screen.findByRole("region", { name: "Detalle de MAT-001" });
    expect(within(detalle).getByText("Erosión por índice", { selector: "dt" }).nextElementSibling).toHaveTextContent("1,25");
  });

  test("Precios: un error de la vista se muestra tal cual", async () => {
    servidor({ precios: () => json({ detalle: "El proyecto «OF-001» no tiene una version «002»: elija una de la lista." }, 404) });
    montar();
    await irA("Precios");
    expect(await screen.findByText(/no tiene una version «002»/)).toBeInTheDocument();
  });

  test("Precios: la ayuda dice que la tabla es la versión guardada, evaluada a la fecha del servidor", async () => {
    servidor();
    montar();
    await irA("Precios");
    expect(await screen.findByText(/versión guardada, no los cambios sin guardar/)).toBeInTheDocument();
    expect(screen.getByText(/Evaluada al 20\/10\/2026/)).toBeInTheDocument();
  });

  test("3b-F10: «Buscar variaciones atípicas de precio» solo pide al pulsarlo y muestra avisos y la tabla en morado", async () => {
    servidor();
    montar();
    await irA("Precios");
    const boton = await screen.findByRole("button", { name: "Buscar variaciones atípicas de precio" });
    expect(pedidas("/precios/atipicos")).toEqual([]);
    await userEvent.click(boton);
    expect(await screen.findByText("Se revisaron 2 insumos con serie de precios.")).toBeInTheDocument();
    expect(pedidas("/precios/atipicos")).toEqual(["/v1/hoja/precios/atipicos?proyecto=OF-001&version=002"]);
    const tabla = await screen.findByRole("table", { name: "Variaciones atípicas de precio" });
    const fila = within(tabla).getAllByRole("row")[1]!;
    expect(within(fila).getByText("MAT-001")).toBeInTheDocument();
    expect(within(fila).getByTitle("38.4000123")).toHaveTextContent("38,40 %");
    expect(within(fila).getByText("01/01/2026")).toBeInTheDocument();
    expect(within(fila).getByText("01/07/2026")).toBeInTheDocument();
    // La severidad dice «Advertencia» con su ícono; solo su color es el de los atípicos (DESIGN.md).
    expect(within(fila).getByText("Advertencia")).toBeInTheDocument();
    expect(tabla.closest<HTMLElement>(".silice-hoja__atipicos")!.style.getPropertyValue("--silice-sev-advertencia")).toBe(
      "var(--silice-atipico)",
    );
  });

  test("3b-F10: sin el extra de aprendizaje automático solo hay el aviso, sin tabla", async () => {
    const aviso = "La búsqueda de variaciones atípicas necesita el extra ml.";
    servidor({ atipicos: () => json(atipicosRespuesta({ disponible: false, avisos: [{ nivel: "info", texto: aviso }], variaciones: [] })) });
    montar();
    await irA("Precios");
    await userEvent.click(await screen.findByRole("button", { name: "Buscar variaciones atípicas de precio" }));
    expect(await screen.findByText(aviso)).toBeInTheDocument();
    expect(screen.queryByRole("table", { name: "Variaciones atípicas de precio" })).toBeNull();
  });

  test("3b-F10: un error de la búsqueda se muestra tal cual y la tabla de precios sigue a la vista", async () => {
    servidor({ atipicos: () => json({ detalle: "No se pudo leer el caso." }, 503) });
    montar();
    await irA("Precios");
    await userEvent.click(await screen.findByRole("button", { name: "Buscar variaciones atípicas de precio" }));
    expect(await screen.findByText("No se pudo leer el caso.")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Precios" })).toBeInTheDocument();
  });

  // --- Trazabilidad -------------------------------------------------------------------------------

  test("Trazabilidad: sin versión abierta lo dice y no pide nada", async () => {
    servidor({ version: null });
    montar();
    await irA("Trazabilidad");
    expect(
      await screen.findByText("Abra una versión guardada para ver su historial y sus registros de cambio."),
    ).toBeInTheDocument();
    expect(pedidas("/v1/hoja/trazabilidad")).toEqual([]);
  });

  test("3b-F11: las versiones del proyecto, con «elaborada» donde no hay motivo y la vigente dicha en texto", async () => {
    servidor();
    montar();
    await irA("Trazabilidad");
    const tabla = await screen.findByRole("table", { name: "Versiones del proyecto" });
    expect(within(tabla).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([
      "Versión",
      "Fecha",
      "Motivo",
      "Sale de",
      "Cambios",
      "Vigente",
    ]);
    const filas = within(tabla).getAllByRole("row");
    expect(filas).toHaveLength(3);
    expect(within(filas[1]!).getByText("001")).toBeInTheDocument();
    expect(within(filas[1]!).getByText("05/10/2026")).toBeInTheDocument();
    expect(within(filas[1]!).getByText("elaborada")).toBeInTheDocument();
    expect(within(filas[2]!).getByText("edicion")).toBeInTheDocument();
    expect(within(filas[2]!).getByText("Sí")).toBeInTheDocument();
    expect(within(filas[1]!).queryByText("Sí")).toBeNull();
    expect(screen.getByRole("heading", { level: 2, name: "Versiones del proyecto" })).toHaveClass(
      "cds--type-heading-compact-02",
    );
  });

  test("3b-F11: el registro de cambios de la versión abierta, con la clave en palabras y la hora legible", async () => {
    servidor();
    montar();
    await irA("Trazabilidad");
    expect(await screen.findByRole("heading", { level: 2, name: "Registro de cambios de la versión 002" })).toBeInTheDocument();
    const tabla = screen.getByRole("table", { name: "Registro de cambios de la versión 002" });
    expect(within(tabla).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([
      "Objeto",
      "Clave",
      "Campo",
      "Antes",
      "Después",
      "Fuente",
      "Responsable",
      "Fecha y hora",
    ]);
    const fila = within(tabla).getAllByRole("row")[1]!;
    expect(within(fila).getByText("AF-LLAVE, Fuente F1, Fuente FC1, Punto P1, Punto P2, Punto PC1")).toHaveAttribute(
      "title",
      "AF-LLAVE|esp_fuentes:F1;esp_fuentes:FC1;esp_puntos:P1;esp_puntos:P2;esp_puntos:PC1",
    );
    expect(within(fila).queryByText(/esp_/)).toBeNull();
    expect(within(fila).getByText("3")).toBeInTheDocument();
    expect(within(fila).getByText("5")).toBeInTheDocument();
    expect(within(fila).getByText("Plano revisado en obra")).toBeInTheDocument();
    expect(within(fila).getByText("Ana Pérez <ana>")).toBeInTheDocument();
    expect(within(fila).getByText("06/10/2026 09:30:00")).toBeInTheDocument();
  });

  test("3b-F11: una versión que no nació de una edición dice por qué no hay registros, sin tabla vacía", async () => {
    const mensaje = "Esta versión no nació de una edición: no tiene registros de cambio.";
    servidor({ trazabilidad: () => json(trazabilidadRespuesta({ registros: [], vacio_mensaje: mensaje })) });
    montar();
    await irA("Trazabilidad");
    expect(await screen.findByText(mensaje)).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Versiones del proyecto" })).toBeInTheDocument();
    expect(screen.queryByRole("table", { name: /Registro de cambios/ })).toBeNull();
  });

  test("Trazabilidad: un error de la vista se muestra tal cual", async () => {
    servidor({ trazabilidad: () => json({ detalle: "El proyecto «OF-001» no existe en este caso." }, 404) });
    montar();
    await irA("Trazabilidad");
    expect(await screen.findByText("El proyecto «OF-001» no existe en este caso.")).toBeInTheDocument();
  });

  test("Trazabilidad: un 401 llama a alExpirar", async () => {
    servidor({ trazabilidad: () => json({ detalle: "Inicie sesión." }, 401) });
    montar();
    await irA("Trazabilidad");
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("Trazabilidad: lo escrito va como texto plano, no como Markdown", async () => {
    const registro = { ...trazabilidadRespuesta().registros[0]!, despues: "![x](http://ejemplo.invalid/b.png)" };
    servidor({ trazabilidad: () => json(trazabilidadRespuesta({ registros: [registro] })) });
    montar();
    await irA("Trazabilidad");
    const tabla = await screen.findByRole("table", { name: "Registro de cambios de la versión 002" });
    expect(within(tabla).getByText("![x](http://ejemplo.invalid/b.png)")).toBeInTheDocument();
    expect(tabla.querySelector("img")).toBeNull();
  });

  // --- navegación de las nueve pestañas -----------------------------------------------------------

  test("3b-F3: las nueve pestañas son alcanzables con el teclado y ninguna es un marcador de lugar", async () => {
    servidor();
    montar();
    await screen.findByRole("region", { name: "Estado del borrador" });
    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual([...PESTANAS]);
    screen.getByRole("tab", { name: PESTANAS[0] }).focus();
    for (let i = 1; i < PESTANAS.length; i++) {
      await userEvent.keyboard("{ArrowRight}");
      expect(screen.getByRole("tab", { name: PESTANAS[i] })).toHaveFocus();
    }
    await userEvent.keyboard("{Enter}");
    expect(screen.getByRole("tab", { name: "Trazabilidad", selected: true })).toBeInTheDocument();
    expect(screen.queryByText(/llega en la siguiente entrega/)).toBeNull();
  });

  test("3b-F3: cada pestaña pide solo su vista, con la ruta de su contrato", async () => {
    servidor();
    montar();
    await screen.findByRole("heading", { level: 3, name: "Ambientes" });
    await userEvent.click(screen.getByRole("tab", { name: "Punto de equilibrio" }));
    await screen.findByText("Ventas (contrato)");
    await userEvent.click(screen.getByRole("tab", { name: "Parámetros" }));
    await screen.findByText(/^FCAS/);
    await userEvent.click(screen.getByRole("tab", { name: "Auditoría" }));
    await screen.findByRole("region", { name: "Informe de auditoría" });
    await userEvent.click(screen.getByRole("tab", { name: "Precios" }));
    await screen.findByRole("table", { name: "Precios" });
    await userEvent.click(screen.getByRole("tab", { name: "Trazabilidad" }));
    await screen.findByRole("table", { name: "Versiones del proyecto" });
    expect(pedidas("/vistas/")).toEqual([
      `/v1/hoja/borradores/${ID}/vistas/espacio`,
      `/v1/hoja/borradores/${ID}/vistas/equilibrio`,
      `/v1/hoja/borradores/${ID}/vistas/parametros`,
      `/v1/hoja/borradores/${ID}/vistas/auditoria`,
    ]);
    expect(pedidas("/v1/hoja/precios")).toEqual(["/v1/hoja/precios?proyecto=OF-001&version=002"]);
    expect(pedidas("/v1/hoja/trazabilidad")).toEqual(["/v1/hoja/trazabilidad?proyecto=OF-001&version=002"]);
  });
});
