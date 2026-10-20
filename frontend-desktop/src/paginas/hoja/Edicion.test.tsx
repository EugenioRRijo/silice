import { act, configure, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { vistaEspacio, vistaPresupuesto } from "./datosDePrueba";
import PaginaHoja from "./index";
import type { BorradorAbierto, Resumen, VersionesRespuesta, VistaEspacio } from "./logica";

// Rebanada 3c-1: las cinco tablas del espacio se editan. El servidor se simula con respuestas ficticias con la forma del
// contrato E1 (diseño §4.4: `PUT /v1/hoja/borradores/{id}/espacio` con `{rev, tablas}` y respuesta `{rev, resumen}`;
// 422 con el `detalle` de la clásica; 409 por `rev` viejo). Caso ficticio OF-001.
configure({ asyncUtilTimeout: 5000 });

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
const FALTA =
  "Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). Lo que no guardó se perdió: abra la versión otra vez.";
const REV_VIEJO = "El borrador cambió en otra ventana: vuelva a cargarlo.";
const VERSIONES: VersionesRespuesta = {
  proyecto: "OF-001",
  moneda: "USD",
  por_omision: "001",
  versiones: [{ codigo: "001", fecha: "2026-10-05", motivo: "", origen: "", vigente: true, descartada: false, cambios: 0 }],
};

function resumen(extra: Partial<Resumen> = {}): Resumen {
  return {
    rev: 0,
    moneda: "USD",
    total: { texto: "2703.86", exacto: "2703.860232344044033333333333" },
    cambios: 0,
    pendientes_catalogo: 0,
    hallazgos: [],
    hay_plan: true,
    version_mas_nueva: null,
    guardado_como: null,
    ...extra,
  };
}

function borrador(extra: Partial<Resumen> = {}): BorradorAbierto {
  return {
    id: ID,
    base: { proyecto: "OF-001", version: "001", vigente: "001", lista: "Lista", espacio_de: "001", solo_lectura: false, moneda: "USD" },
    resumen: resumen(extra),
    instantanea: { creadas: 0, mensaje: null },
  };
}

interface Cuerpo {
  rev: number;
  tablas: Record<string, Array<Record<string, string>>>;
}

describe("Hoja del proyecto: tablas editables del espacio (3c-1)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();
  // Lo que el servidor simulado contesta; cada prueba lo cambia.
  let vista: VistaEspacio;
  let abierto: BorradorAbierto;
  let alPonerse: (cuerpo: Cuerpo) => Response | Promise<Response>;

  const ACEPTA = (cuerpo: Cuerpo) =>
    json({
      rev: cuerpo.rev + 1,
      resumen: resumen({ rev: cuerpo.rev + 1, cambios: 1, total: { texto: "2800.50", exacto: "2800.5" } }),
    });

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    localStorage.clear();
    sessionStorage.clear();
    vista = vistaEspacio();
    abierto = borrador();
    alPonerse = ACEPTA;
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/hoja/versiones")) return json(VERSIONES);
      if (url === "/v1/hoja/borradores" && metodo === "POST") return json(abierto, 201);
      if (url === `/v1/hoja/borradores/${ID}` && metodo === "GET") {
        return json({ id: abierto.id, base: abierto.base, resumen: abierto.resumen });
      }
      if (url === `/v1/hoja/borradores/${ID}/espacio` && metodo === "PUT") {
        return alPonerse(JSON.parse(String(init?.body)) as Cuerpo);
      }
      if (url.endsWith("/vistas/espacio")) return json(vista);
      if (url.endsWith("/vistas/presupuesto")) return json(vistaPresupuesto());
      return new Response(null, { status: 204 });
    });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  const puestas = (): Array<{ url: string; cuerpo: Cuerpo }> =>
    fetchFalso.mock.calls
      .filter(([, init]) => init?.method === "PUT")
      .map(([ruta, init]) => ({ url: String(ruta), cuerpo: JSON.parse(String(init?.body)) as Cuerpo }));
  const lecturasDelEspacio = () => fetchFalso.mock.calls.filter(([r]) => String(r).endsWith("/vistas/espacio")).length;
  const llamadas = (metodo: string, url: string) =>
    fetchFalso.mock.calls.filter(([r, init]) => String(r) === url && (init?.method ?? "GET") === metodo).length;

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

  async function abrir() {
    const r = montar();
    await screen.findByRole("textbox", { name: "Largo (m), Ambientes fila 1" });
    return r;
  }

  // Carbon pone en cada campo de texto un `role="alert"` vacío (su contador); los avisos de verdad son los que traen texto.
  const avisos = () => screen.queryAllByRole("alert").filter((a) => (a.textContent ?? "") !== "");
  const aviso = () => {
    const todos = avisos();
    if (todos.length !== 1) throw new Error(`Se esperaba un aviso y hay ${todos.length}`);
    return todos[0]!;
  };
  const celda = (nombre: string) => screen.getByRole("textbox", { name: nombre });
  const pausa = (ms: number) =>
    act(async () => {
      vi.advanceTimersByTime(ms);
    });
  const saleLaPagina = () => {
    const evento = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(evento);
    return evento.defaultPrevented;
  };

  // Con setTimeout simulado, `findBy*` y `waitFor` de Testing Library se cuelgan (su espera final usa setTimeout): se espera
  // dando turnos a las promesas con setImmediate, que no se simula.
  async function esperar<T>(comprobar: () => T): Promise<T> {
    let ultimo: unknown;
    for (let i = 0; i < 300; i++) {
      try {
        return comprobar();
      } catch (e) {
        ultimo = e;
      }
      await act(async () => {
        await new Promise<void>((resolver) => setImmediate(resolver));
      });
    }
    throw ultimo;
  }

  // Solo se simulan los temporizadores de la pausa; las promesas y el sondeo de Testing Library siguen reales.
  async function abrirConRelojFalso() {
    await abrir();
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  }

  // --- 3c-F1 ----------------------------------------------------------------------------------

  test("3c-F1: cada celda es un campo con el nombre «{columna}, {tabla} fila {n}»; las listas cerradas son select", async () => {
    await abrir();
    expect(celda("Código, Ambientes fila 1")).toHaveValue("BAN-01");
    expect(celda("Nombre, Ambientes fila 2")).toHaveValue("Cocineta");
    expect(celda("Largo (m), Ambientes fila 2")).toHaveValue("2");
    expect(celda("Referencia, Orígenes de medida fila 1")).toHaveValue("motivo=ejemplo");
    const superficie = screen.getByRole("combobox", { name: "Superficie, Puntos fila 1" });
    expect(superficie).toHaveValue("pared"); // el valor interno
    expect(within(superficie).getByRole("option", { name: "Pared" })).toHaveValue("pared"); // el rótulo a la vista
    expect(within(superficie).getAllByRole("option").map((o) => o.textContent)).toEqual(["Pared", "Techo"]);
    expect(screen.getByRole("combobox", { name: "Tipo de origen, Orígenes de medida fila 1" })).toHaveValue("supuesto");
  });

  test("3c-F1: cada celda admite hasta 500 caracteres; los títulos, contadores y encabezados siguen", async () => {
    await abrir();
    expect(celda("Largo (m), Ambientes fila 1")).toHaveAttribute("maxlength", "500");
    const titulo = screen.getByRole("heading", { level: 3, name: "Ambientes" });
    expect(titulo.parentElement).toHaveTextContent("2 filas");
    const tabla = screen.getByRole("table", { name: "Ambientes" });
    expect(within(tabla).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([
      "Código",
      "Nombre",
      "Largo (m)",
      "Estado",
      "Acciones",
    ]);
    expect(screen.getByText(/Decimales con punto, por ejemplo 2\.5/)).toBeInTheDocument();
  });

  test("el Estado de la fila sigue visible con ícono y texto, y una fila nueva dice que aún no se evalúa", async () => {
    await abrir();
    const tabla = screen.getByRole("table", { name: "Ambientes" });
    const filas = within(tabla).getAllByRole("row");
    expect(within(filas[1]!).getByText("Advertencia")).toBeInTheDocument();
    expect(filas[1]!.querySelector("svg")).not.toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Agregar fila a Ambientes" }));
    const nueva = within(screen.getByRole("table", { name: "Ambientes" })).getAllByRole("row")[3]!;
    expect(within(nueva).getByText("Sin evaluar")).toBeInTheDocument();
  });

  // --- 3c-F2 ----------------------------------------------------------------------------------

  test("3c-F2: tras la pausa de 400 ms se manda una sola petición con la tabla completa y se actualizan total, estado y derivadas", async () => {
    await abrirConRelojFalso();
    const antes = lecturasDelEspacio();
    fireEvent.change(celda("Largo (m), Ambientes fila 1"), { target: { value: "2.5" } });
    await pausa(399);
    expect(puestas()).toHaveLength(0);
    // Cuando el servidor acepte, la vista trae el estado y las cantidades nuevas.
    vista = vistaEspacio({
      derivadas: [
        { partida: "AF-LLAVE", descripcion: "Llave de paso", unidad: "unidad", cantidad: { texto: "4.00", exacto: "4" }, origen: "esp_puntos:P1" },
      ],
      estado: { ...vista.estado, "esp_ambientes:BAN-01": { severidad: null, texto: "OK" } },
      total: { texto: "2800.50", exacto: "2800.5" },
    });
    await pausa(1);
    expect(puestas()).toHaveLength(1);
    expect(puestas()[0]!.url).toBe(`/v1/hoja/borradores/${ID}/espacio`);
    expect(puestas()[0]!.cuerpo).toEqual({
      rev: 0,
      tablas: {
        origenes: [{ id: "O1", tipo: "supuesto", referencia: "motivo=ejemplo" }],
        ambientes: [
          { id: "BAN-01", nombre: "Baño", largo: "2.5" },
          { id: "COC-01", nombre: "Cocineta", largo: "2" },
        ],
        fuentes: [{ id: "F1", especialidad: "agua" }],
        puntos: [{ id: "P1", superficie: "pared" }],
        tramos: [],
      },
    });
    const estado = await esperar(() => screen.getByRole("region", { name: "Estado del borrador" }));
    expect(await esperar(() => within(estado).getByTitle("2800.5"))).toHaveTextContent("2.800,50 USD");
    expect(within(estado).getByText(/· 1 cambio sin guardar/)).toBeInTheDocument();
    expect(within(estado).getByTitle("2800.5")).toHaveAttribute("aria-live", "polite");
    expect(lecturasDelEspacio()).toBe(antes + 1);
    const derivadas = await esperar(() => screen.getByRole("table", { name: "Cantidades derivadas" }));
    expect(await esperar(() => within(derivadas).getByText("4,00"))).toBeInTheDocument();
    const filas = within(screen.getByRole("table", { name: "Ambientes" })).getAllByRole("row");
    expect(await esperar(() => within(filas[1]!).getByText("OK"))).toBeInTheDocument();
    // Lo escrito se queda como lo escribió la persona; la respuesta no lo reemplaza.
    expect(celda("Largo (m), Ambientes fila 1")).toHaveValue("2.5");
  });

  test("3c-F2: varias teclas seguidas dentro de la pausa son una sola petición con lo último escrito, y la siguiente lleva el rev nuevo", async () => {
    await abrirConRelojFalso();
    fireEvent.change(celda("Largo (m), Ambientes fila 1"), { target: { value: "3" } });
    await pausa(300);
    fireEvent.change(celda("Largo (m), Ambientes fila 1"), { target: { value: "3." } });
    await pausa(300);
    fireEvent.change(celda("Largo (m), Ambientes fila 1"), { target: { value: "3.2" } });
    await pausa(400);
    expect(puestas()).toHaveLength(1);
    expect(puestas()[0]!.cuerpo.tablas.ambientes![0]!.largo).toBe("3.2");
    await esperar(() => screen.getByText(/· 1 cambio sin guardar/));
    fireEvent.change(celda("Nombre, Ambientes fila 1"), { target: { value: "Baño principal" } });
    await pausa(400);
    expect(puestas()).toHaveLength(2);
    expect(puestas()[1]!.cuerpo.rev).toBe(1);
  });

  test("3c-F2: mientras se aplica un cambio se dice; solo hay una petición en vuelo y lo escrito entre tanto sale en una sola más", async () => {
    await abrirConRelojFalso();
    let terminar: (r: Response) => void = () => undefined;
    alPonerse = (cuerpo) =>
      puestas().length === 1
        ? new Promise<Response>((resolver) => {
            terminar = resolver;
          })
        : ACEPTA(cuerpo);
    fireEvent.change(celda("Largo (m), Ambientes fila 1"), { target: { value: "3" } });
    await pausa(400);
    expect(await esperar(() => screen.getByText("Aplicando los cambios al borrador…"))).toBeInTheDocument();
    fireEvent.change(celda("Largo (m), Ambientes fila 1"), { target: { value: "31" } });
    await pausa(400);
    fireEvent.change(celda("Largo (m), Ambientes fila 1"), { target: { value: "312" } });
    await pausa(400);
    expect(puestas()).toHaveLength(1); // la primera sigue en vuelo
    await act(async () => terminar(ACEPTA({ rev: 0, tablas: {} })));
    await esperar(() => expect(puestas()).toHaveLength(2));
    expect(puestas()[1]!.cuerpo.rev).toBe(1);
    expect(puestas()[1]!.cuerpo.tablas.ambientes![0]!.largo).toBe("312");
    await esperar(() => expect(screen.queryByText("Aplicando los cambios al borrador…")).toBeNull());
  });

  test("al cambiar de pestaña con una edición en la pausa, se manda en seguida: no se pierde", async () => {
    await abrirConRelojFalso();
    fireEvent.change(celda("Nombre, Ambientes fila 2"), { target: { value: "Cocina" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("tab", { name: "Presupuesto" }));
    });
    expect(puestas()).toHaveLength(1);
    expect(puestas()[0]!.cuerpo.tablas.ambientes![1]!.nombre).toBe("Cocina");
  });

  // --- 3c-F3, F4 ------------------------------------------------------------------------------

  test("3c-F3: una edición inválida muestra el detalle del servidor y la frase de la clásica en un alert; la celda queda inválida; nada cambia", async () => {
    await abrirConRelojFalso();
    const DETALLE = "ambientes, fila 1: largo: '2,5' no es un numero decimal valido";
    alPonerse = () => json({ detalle: DETALLE }, 422);
    fireEvent.change(celda("Largo (m), Ambientes fila 1"), { target: { value: "2,5" } });
    await pausa(400);
    const alerta = await esperar(() => aviso());
    expect(alerta).toHaveTextContent(`${DETALLE}. La hoja sigue con el último borrador válido.`);
    const invalida = celda("Largo (m), Ambientes fila 1");
    await esperar(() => expect(invalida).toHaveAttribute("aria-invalid", "true"));
    expect(invalida).toHaveValue("2,5"); // se queda lo escrito para corregirlo
    // Carbon señala su «Valor no válido» con aria-errormessage; la descripción accesible es el aviso completo.
    expect(document.getElementById(invalida.getAttribute("aria-describedby")!)).toHaveTextContent(DETALLE);
    expect(celda("Largo (m), Ambientes fila 2")).not.toHaveAttribute("aria-invalid", "true");
    // El texto de la celda inválida dice que no es válida (el color no va solo).
    expect(screen.getByText("Valor no válido")).toBeInTheDocument();
    // El total mostrado es el anterior y el borrador no avanzó.
    const estado = screen.getByRole("region", { name: "Estado del borrador" });
    expect(within(estado).getByTitle("2703.860232344044033333333333")).toBeInTheDocument();
    expect(within(estado).getByText(/Sin cambios sin guardar/)).toBeInTheDocument();
    // Corregir y volver a mandar: sigue con el rev que el servidor no avanzó y el alert desaparece.
    alPonerse = ACEPTA;
    fireEvent.change(invalida, { target: { value: "2.5" } });
    await pausa(400);
    await esperar(() => expect(puestas()).toHaveLength(2));
    expect(puestas()[1]!.cuerpo.rev).toBe(0);
    await esperar(() => expect(avisos()).toHaveLength(0));
    expect(celda("Largo (m), Ambientes fila 1")).not.toHaveAttribute("aria-invalid", "true");
  });

  test("3c-F3: la coma decimal se rechaza con el mensaje de la clásica, sin convertirla en el navegador", async () => {
    await abrirConRelojFalso();
    alPonerse = () => json({ detalle: "ambientes, fila 2: largo: '2,5' no es un numero decimal valido" }, 422);
    fireEvent.change(celda("Largo (m), Ambientes fila 2"), { target: { value: "2,5" } });
    await pausa(400);
    expect(puestas()[0]!.cuerpo.tablas.ambientes![1]!.largo).toBe("2,5"); // se manda tal cual: decide el servidor (D-8)
    expect(await esperar(() => aviso())).toHaveTextContent("'2,5' no es un numero decimal valido");
  });

  test("3c-F4: si el mensaje nombra tabla y fila se ofrece ir a esa fila, sin robar el foco mientras se escribe", async () => {
    await abrirConRelojFalso();
    alPonerse = () => json({ detalle: "ambientes, fila 2: nombre: 'x' no es un valor valido (a, b)" }, 422);
    celda("Largo (m), Ambientes fila 1").focus();
    fireEvent.change(celda("Largo (m), Ambientes fila 1"), { target: { value: "5" } });
    await pausa(400);
    const ir = await esperar(() => screen.getByRole("button", { name: "Ir a la fila 2 de Ambientes" }));
    expect(celda("Largo (m), Ambientes fila 1")).toHaveFocus(); // el foco sigue donde escribe la persona
    expect(celda("Nombre, Ambientes fila 2")).toHaveAttribute("aria-invalid", "true");
    fireEvent.click(ir);
    expect(celda("Nombre, Ambientes fila 2")).toHaveFocus();
  });

  test("3c-F4: un mensaje que no nombra fila (un id repetido) se muestra sin botón ni celda inválida", async () => {
    await abrirConRelojFalso();
    alPonerse = () => json({ detalle: "El id 'BAN-01' esta repetido en ambientes" }, 422);
    fireEvent.change(celda("Código, Ambientes fila 2"), { target: { value: "BAN-01" } });
    await pausa(400);
    expect(await esperar(() => aviso())).toHaveTextContent("El id 'BAN-01' esta repetido en ambientes. La hoja sigue");
    expect(screen.queryByRole("button", { name: /Ir a la fila/ })).toBeNull();
    expect(document.querySelector("[aria-invalid='true']")).toBeNull();
  });

  // --- rev, 409 -------------------------------------------------------------------------------

  test("409 por rev viejo: avisa con el detalle, ofrece recargar y al recargar vuelve a sembrar las celdas del servidor", async () => {
    await abrirConRelojFalso();
    alPonerse = () => json({ detalle: REV_VIEJO }, 409);
    fireEvent.change(celda("Largo (m), Ambientes fila 1"), { target: { value: "7" } });
    await pausa(400);
    const elAviso = await esperar(() => aviso());
    expect(elAviso).toHaveTextContent(REV_VIEJO);
    // Otra ventana dejó el borrador en rev 5 con otro largo.
    abierto = borrador({ rev: 5, cambios: 3 });
    vista = vistaEspacio({
      filas: {
        ...vista.filas,
        ambientes: [
          { id: "BAN-01", nombre: "Baño", largo: "9" },
          { id: "COC-01", nombre: "Cocineta", largo: "2" },
        ],
      },
    });
    const antes = lecturasDelEspacio();
    fireEvent.click(screen.getByRole("button", { name: "Recargar el borrador" }));
    await esperar(() => expect(celda("Largo (m), Ambientes fila 1")).toHaveValue("9"));
    expect(llamadas("GET", `/v1/hoja/borradores/${ID}`)).toBe(1);
    expect(lecturasDelEspacio()).toBeGreaterThan(antes);
    expect(avisos()).toHaveLength(0);
    expect(within(screen.getByRole("region", { name: "Estado del borrador" })).getByText(/· 3 cambios sin guardar/)).toBeInTheDocument();
    // La siguiente edición ya lleva el rev que el servidor tiene.
    alPonerse = ACEPTA;
    fireEvent.change(celda("Largo (m), Ambientes fila 1"), { target: { value: "9.5" } });
    await pausa(400);
    await esperar(() => expect(puestas()).toHaveLength(2));
    expect(puestas()[1]!.cuerpo.rev).toBe(5);
  });

  test("tras un 409 no se manda más hasta recargar", async () => {
    await abrirConRelojFalso();
    alPonerse = () => json({ detalle: REV_VIEJO }, 409);
    fireEvent.change(celda("Largo (m), Ambientes fila 1"), { target: { value: "7" } });
    await pausa(400);
    await esperar(() => aviso());
    fireEvent.change(celda("Largo (m), Ambientes fila 1"), { target: { value: "77" } });
    await pausa(800);
    expect(puestas()).toHaveLength(1);
  });

  test("un 401 al editar avisa al marco para que pida la sesión de nuevo", async () => {
    await abrirConRelojFalso();
    alPonerse = () => json({ detalle: "Inicie sesión." }, 401);
    fireEvent.change(celda("Largo (m), Ambientes fila 1"), { target: { value: "7" } });
    await pausa(400);
    await esperar(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("si el servidor ya no tiene el borrador, la página lo dice y ofrece abrirlo de nuevo", async () => {
    await abrirConRelojFalso();
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      if (url.startsWith("/v1/hoja/versiones")) return json(VERSIONES);
      if (init?.method === "PUT") return json({ detalle: FALTA }, 404);
      if (url === `/v1/hoja/borradores/${ID}`) return json({ detalle: FALTA }, 404);
      if (url.endsWith("/vistas/espacio")) return json(vista);
      return new Response(null, { status: 204 });
    });
    fireEvent.change(celda("Largo (m), Ambientes fila 1"), { target: { value: "7" } });
    await pausa(400);
    expect(await esperar(() => screen.getByText("El borrador ya no está"))).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Abrir de nuevo" })).toBeInTheDocument();
  });

  // --- 3c-F6 teclado --------------------------------------------------------------------------

  test("3c-F6: flechas arriba y abajo y Enter mueven entre filas de la misma columna; Esc devuelve la celda a lo aceptado", async () => {
    await abrir();
    const u = userEvent.setup({ delay: null });
    celda("Largo (m), Ambientes fila 1").focus();
    await u.keyboard("{ArrowDown}");
    expect(celda("Largo (m), Ambientes fila 2")).toHaveFocus();
    await u.keyboard("{ArrowUp}");
    expect(celda("Largo (m), Ambientes fila 1")).toHaveFocus();
    await u.keyboard("{Enter}");
    expect(celda("Largo (m), Ambientes fila 2")).toHaveFocus();
    await u.keyboard("{Enter}"); // en la última fila se queda
    expect(celda("Largo (m), Ambientes fila 2")).toHaveFocus();
    // Esc: lo escrito vuelve a lo último aceptado por el servidor.
    await u.type(celda("Largo (m), Ambientes fila 2"), "99");
    expect(celda("Largo (m), Ambientes fila 2")).toHaveValue("299");
    await u.keyboard("{Escape}");
    expect(celda("Largo (m), Ambientes fila 2")).toHaveValue("2");
  });

  test("3c-F6: Tab recorre las celdas en orden y en un select las flechas no se interceptan", async () => {
    await abrir();
    const u = userEvent.setup({ delay: null });
    celda("Código, Ambientes fila 1").focus();
    await u.tab();
    expect(celda("Nombre, Ambientes fila 1")).toHaveFocus();
    await u.tab();
    expect(celda("Largo (m), Ambientes fila 1")).toHaveFocus();
    const select = screen.getByRole("combobox", { name: "Superficie, Puntos fila 1" });
    select.focus();
    expect(fireEvent.keyDown(select, { key: "ArrowDown" })).toBe(true); // true = nadie canceló el evento
    expect(fireEvent.keyDown(select, { key: "ArrowUp" })).toBe(true);
    expect(select).toHaveFocus();
  });

  // --- 3c-F7 agregar y quitar -----------------------------------------------------------------

  test("3c-F7: «Agregar fila» pone el foco en la primera celda de la fila nueva y la fila en blanco se manda sin error", async () => {
    await abrirConRelojFalso();
    fireEvent.click(screen.getByRole("button", { name: "Agregar fila a Ambientes" }));
    expect(celda("Código, Ambientes fila 3")).toHaveFocus();
    expect(celda("Código, Ambientes fila 3")).toHaveValue("");
    expect(screen.getByRole("heading", { level: 3, name: "Ambientes" }).parentElement).toHaveTextContent("3 filas");
    await pausa(400);
    expect(puestas()[0]!.cuerpo.tablas.ambientes![2]).toEqual({ id: "", nombre: "", largo: "" });
  });

  test("3c-F7: «Quitar fila» deja el foco en la fila vecina; sin filas, en «Agregar fila»", async () => {
    await abrir();
    await userEvent.click(screen.getByRole("button", { name: "Quitar fila 1 de Ambientes" }));
    expect(screen.queryByRole("textbox", { name: "Código, Ambientes fila 2" })).toBeNull();
    expect(celda("Código, Ambientes fila 1")).toHaveValue("COC-01");
    expect(celda("Código, Ambientes fila 1")).toHaveFocus();
    await userEvent.click(screen.getByRole("button", { name: "Quitar fila 1 de Ambientes" }));
    expect(screen.getByRole("button", { name: "Agregar fila a Ambientes" })).toHaveFocus();
    expect(screen.getByRole("heading", { level: 3, name: "Ambientes" }).parentElement).toHaveTextContent("0 filas");
    // Quitar la última de una tabla con varias deja el foco en la anterior.
    await userEvent.click(screen.getByRole("button", { name: "Agregar fila a Fuentes" }));
    await userEvent.click(screen.getByRole("button", { name: "Quitar fila 2 de Fuentes" }));
    expect(celda("Código, Fuentes fila 1")).toHaveFocus();
  });

  test("quitar una fila manda la tabla sin ella", async () => {
    await abrirConRelojFalso();
    fireEvent.click(screen.getByRole("button", { name: "Quitar fila 1 de Ambientes" }));
    await pausa(400);
    expect(puestas()[0]!.cuerpo.tablas.ambientes).toEqual([{ id: "COC-01", nombre: "Cocineta", largo: "2" }]);
  });

  test("topes: «Agregar fila» se cierra en el tope de la tabla y las tablas largas se pagan de 50 en 50", async () => {
    vista = vistaEspacio();
    vista.filas.ambientes = Array.from({ length: 1000 }, (_, i) => ({ id: `A${i + 1}`, nombre: `Ambiente ${i + 1}`, largo: "2" }));
    await abrir();
    expect(screen.getByRole("button", { name: "Agregar fila a Ambientes" })).toBeDisabled();
    expect(screen.getByText("Ambientes llegó a su tope de 1000 filas.")).toBeInTheDocument();
    const tabla = screen.getByRole("table", { name: "Ambientes" });
    expect(within(tabla).getAllByRole("row")).toHaveLength(51); // encabezado y 50 filas
    expect(celda("Código, Ambientes fila 50")).toHaveValue("A50");
    fireEvent.click(screen.getAllByRole("button", { name: "Página siguiente" })[0]!);
    expect(await screen.findByRole("textbox", { name: "Código, Ambientes fila 51" })).toHaveValue("A51");
    expect(screen.queryByRole("textbox", { name: "Código, Ambientes fila 50" })).toBeNull();
  });

  // --- 3c-F10 ---------------------------------------------------------------------------------

  test("3c-F10: beforeunload solo mientras hay cambios sin guardar", async () => {
    await abrirConRelojFalso();
    expect(saleLaPagina()).toBe(false);
    fireEvent.change(celda("Largo (m), Ambientes fila 1"), { target: { value: "3" } });
    await pausa(400);
    await esperar(() => screen.getByText(/· 1 cambio sin guardar/));
    expect(saleLaPagina()).toBe(true);
  });

  test("3c-F10: al abrir un borrador que ya tiene cambios, beforeunload ya avisa; y al desmontar deja de avisar", async () => {
    abierto = borrador({ cambios: 2 });
    const { unmount } = montar();
    await screen.findByText(/· 2 cambios sin guardar/);
    expect(saleLaPagina()).toBe(true);
    unmount();
    expect(saleLaPagina()).toBe(false);
  });

  // --- Descartar cambios ----------------------------------------------------------------------

  test("con cambios hay «Descartar cambios»: pide confirmar, descarta el borrador y lo abre de nuevo desde la versión", async () => {
    abierto = borrador({ cambios: 2 });
    await abrir();
    expect(screen.queryByRole("button", { name: "Seguir editando" })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Descartar cambios" }));
    expect(screen.getByText("¿Descartar los 2 cambios sin guardar? No se pueden recuperar.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Seguir editando" }));
    expect(llamadas("DELETE", `/v1/hoja/borradores/${ID}`)).toBe(0);
    await userEvent.click(screen.getByRole("button", { name: "Descartar cambios" }));
    abierto = borrador();
    await userEvent.click(screen.getByRole("button", { name: "Descartar y abrir de nuevo" }));
    await waitFor(() => expect(llamadas("DELETE", `/v1/hoja/borradores/${ID}`)).toBe(1));
    await waitFor(() => expect(llamadas("POST", "/v1/hoja/borradores")).toBe(2));
    expect(await screen.findByText(/Sin cambios sin guardar/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Descartar cambios" })).toBeNull();
  });

  test("sin cambios no hay «Descartar cambios»", async () => {
    await abrir();
    expect(screen.queryByRole("button", { name: "Descartar cambios" })).toBeNull();
  });

  // --- 3c-F13 y secretos ----------------------------------------------------------------------

  test("3c-F13: lo escrito sale exactamente como se escribió (30 cifras, notación científica, ceros a la izquierda)", async () => {
    await abrirConRelojFalso();
    const largo = "123456789012345678901234567890.1234567890123456789";
    fireEvent.change(celda("Largo (m), Ambientes fila 1"), { target: { value: largo } });
    fireEvent.change(celda("Largo (m), Ambientes fila 2"), { target: { value: "007e3" } });
    await pausa(400);
    expect(puestas()[0]!.cuerpo.tablas.ambientes!.map((f) => f.largo)).toEqual([largo, "007e3"]);
  });

  test("3c-F13: los archivos nuevos de la carpeta están bajo la prueba estática de 3b-F5 (sin Number, parseFloat, toFixed ni + unario)", () => {
    const fuentes = import.meta.glob("./*.{ts,tsx}", { query: "?raw", import: "default", eager: true }) as Record<string, string>;
    for (const ruta of ["./TablaEditable.tsx", "./PestanaEspacio.tsx", "./useBorrador.ts", "./logica.ts"]) {
      expect(Object.keys(fuentes), ruta).toContain(ruta);
      expect(fuentes[ruta], ruta).not.toMatch(
        /\bNumber\s*\(|\bparseFloat\s*\(|\bparseInt\s*\(|\.toFixed\s*\(|(?:[=(,:?]|\breturn)\s*\+\s*[A-Za-z_$(]/,
      );
    }
  });

  test("editar no deja nada en localStorage ni sessionStorage", async () => {
    await abrirConRelojFalso();
    fireEvent.change(celda("Nombre, Ambientes fila 1"), { target: { value: "secreto-no-guardar" } });
    await pausa(400);
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });
});
