import { act, configure, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { vistaEspacio, vistaParametros, vistaPlan, vistaPresupuesto } from "./datosDePrueba";
import PaginaHoja from "./index";
import type { BorradorAbierto, Resumen, VersionesRespuesta, VistaParametros, VistaPlan, VistaPresupuesto } from "./logica";

// Rebanada 3c-2: cantidades, parámetros y plan se editan. El servidor se simula con respuestas ficticias con la forma del
// contrato (docs/bitacora/2026-10-19-hoja-3c2-contrato-rutas.md, diseño §4.4): E2 `PUT …/cantidades`, E3 `PUT …/parametros`,
// E4 `PUT …/plan`, E5 `POST …/plan/secuencial`, todas con `{rev}` y respuesta `{rev, resumen, <vista>}`; 422 con el
// `detalle` de la clásica; 409 por `rev` viejo. Caso ficticio OF-001; los literales son de su memoria y del diseño.
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
const CASO_CAMBIO = "El caso cambió desde que abrió este borrador: ábralo de nuevo en el caso actual.";
const YA_GUARDADO = "Este borrador ya se guardó como la versión 002; abra esa versión para seguir.";
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

type Seccion = "cantidades" | "parametros" | "plan" | "secuencial";
type Cuerpo = Record<string, unknown> & { rev: number };

describe("Hoja del proyecto: cantidades, parámetros y plan editables (3c-2)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();
  let abierto: BorradorAbierto;
  let presupuesto: VistaPresupuesto;
  let parametros: VistaParametros;
  let plan: VistaPlan;
  // Lo que el servidor simulado contesta a cada escritura; cada prueba lo cambia.
  let alPoner: Record<Seccion, (cuerpo: Cuerpo) => Response | Promise<Response>>;

  const acepta = (cuerpo: Cuerpo, extra: Partial<Resumen> = {}) =>
    json({
      rev: cuerpo.rev + 1,
      resumen: resumen({ rev: cuerpo.rev + 1, cambios: 1, total: { texto: "2800.50", exacto: "2800.5" }, ...extra }),
      presupuesto,
      parametros,
      plan,
    });

  const URL_DE: Record<Seccion, string> = {
    cantidades: `/v1/hoja/borradores/${ID}/cantidades`,
    parametros: `/v1/hoja/borradores/${ID}/parametros`,
    plan: `/v1/hoja/borradores/${ID}/plan`,
    secuencial: `/v1/hoja/borradores/${ID}/plan/secuencial`,
  };

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    localStorage.clear();
    sessionStorage.clear();
    abierto = borrador();
    presupuesto = vistaPresupuesto();
    parametros = vistaParametros();
    plan = vistaPlan();
    alPoner = { cantidades: acepta, parametros: acepta, plan: acepta, secuencial: acepta };
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/hoja/versiones")) return json(VERSIONES);
      if (url === "/v1/hoja/borradores" && metodo === "POST") return json(abierto, 201);
      if (url === `/v1/hoja/borradores/${ID}` && metodo === "GET") {
        return json({ id: abierto.id, base: abierto.base, resumen: abierto.resumen });
      }
      for (const seccion of Object.keys(URL_DE) as Seccion[]) {
        if (url === URL_DE[seccion] && (metodo === "PUT" || metodo === "POST")) {
          return alPoner[seccion](JSON.parse(String(init?.body)) as Cuerpo);
        }
      }
      if (url.endsWith("/vistas/espacio")) return json(vistaEspacio());
      if (url.endsWith("/vistas/presupuesto")) return json(presupuesto);
      if (url.endsWith("/vistas/parametros")) return json(parametros);
      if (url.endsWith("/vistas/plan")) return json(plan);
      return new Response(null, { status: 204 });
    });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  const escrituras = (seccion: Seccion): Cuerpo[] =>
    fetchFalso.mock.calls
      .filter(([ruta, init]) => String(ruta) === URL_DE[seccion] && (init?.method === "PUT" || init?.method === "POST"))
      .map(([, init]) => JSON.parse(String(init?.body)) as Cuerpo);
  const lecturas = (vista: string) => fetchFalso.mock.calls.filter(([r]) => String(r).endsWith(`/vistas/${vista}`)).length;
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

  async function irA(pestana: string) {
    montar();
    await screen.findByRole("region", { name: "Estado del borrador" });
    await userEvent.click(screen.getByRole("tab", { name: pestana }));
  }

  // Carbon pone en cada campo de texto un `role="alert"` vacío (su contador); los avisos de verdad son los que traen texto.
  const avisos = () => screen.queryAllByRole("alert").filter((a) => (a.textContent ?? "") !== "");
  const aviso = () => {
    const todos = avisos();
    if (todos.length !== 1) throw new Error(`Se esperaba un aviso y hay ${todos.length}`);
    return todos[0]!;
  };
  const campo = (nombre: string | RegExp) => screen.getByRole("textbox", { name: nombre });
  const pausa = (ms: number) =>
    act(async () => {
      vi.advanceTimersByTime(ms);
    });
  const saleLaPagina = () => {
    const evento = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(evento);
    return evento.defaultPrevented;
  };
  const regionDeEstado = () => screen.getByRole("region", { name: "Estado del borrador" });

  // Con setTimeout simulado, `findBy*` y `waitFor` de Testing Library se cuelgan: se espera dando turnos a las promesas.
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
  const relojFalso = () => vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });

  // --- Lo común a las tres pestañas: pausa, una petición en vuelo, rev, 409, 401, 404, texto verbatim ---------------------

  interface Escenario {
    nombre: string;
    pestana: string;
    seccion: Seccion;
    // Lo que la clásica agrega tras el error de cada sección (diseño §4.4; ui/paginas/hoja.py:1674, 1773, 1827, 2053).
    frase: string;
    abrir: () => Promise<void>;
    // El campo que se edita y su valor sembrado.
    campo: () => HTMLElement;
    sembrado: string;
    // El valor de ese campo dentro del cuerpo que se mandó.
    enCuerpo: (cuerpo: Cuerpo) => string;
    // Deja en el servidor otro valor para ese campo (otra ventana lo cambió).
    otroValorEnElServidor: (valor: string) => void;
  }

  const ESCENARIOS: Escenario[] = [
    {
      nombre: "Parámetros",
      pestana: "Parámetros",
      seccion: "parametros",
      frase: "La hoja sigue con los últimos parámetros válidos.",
      abrir: async () => {
        await irA("Parámetros");
        await screen.findByRole("textbox", { name: /^Administración/ });
      },
      campo: () => campo(/^Administración/),
      sembrado: "0.15",
      enCuerpo: (c) => String(c.administracion),
      otroValorEnElServidor: (valor) => {
        parametros = vistaParametros({
          campos: parametros.campos.map((f) => (f.clave === "administracion" ? { ...f, valor } : f)),
        });
      },
    },
    {
      nombre: "Presupuesto (cantidades)",
      pestana: "Presupuesto",
      seccion: "cantidades",
      frase: "La hoja sigue con las últimas cantidades válidas.",
      abrir: async () => {
        await irA("Presupuesto");
        await screen.findByRole("textbox", { name: "Cantidad, Presupuesto fila 1" });
      },
      campo: () => campo("Cantidad, Presupuesto fila 1"),
      sembrado: "3",
      enCuerpo: (c) => (c.filas as Array<{ cantidad: string }>)[0]!.cantidad,
      otroValorEnElServidor: (valor) => {
        presupuesto = vistaPresupuesto({ filas: presupuesto.filas.map((f, i) => (i === 0 ? { ...f, cantidad: valor } : f)) });
      },
    },
    {
      nombre: "Plan y curva",
      pestana: "Plan y curva",
      seccion: "plan",
      frase: "La hoja sigue con el último plan válido.",
      abrir: async () => {
        await irA("Plan y curva");
        await screen.findByRole("textbox", { name: "Día 1, Plan de trabajo fila 1" });
      },
      campo: () => campo("Día 1, Plan de trabajo fila 1"),
      sembrado: "1",
      enCuerpo: (c) => (c.filas as Array<{ valores: Record<string, string> }>)[0]!.valores["Dia 1"]!,
      otroValorEnElServidor: (valor) => {
        plan = vistaPlan({ filas: plan.filas.map((f, i) => (i === 0 ? { ...f, valores: { ...f.valores, "Dia 1": valor } } : f)) });
      },
    },
  ];

  describe.each(ESCENARIOS)("comportamiento común: $nombre", (e) => {
    async function abrirConRelojFalso() {
      await e.abrir();
      relojFalso();
    }

    test("el campo sale sembrado con el texto del servidor y no hay petición hasta que la persona escribe", async () => {
      await e.abrir();
      expect(e.campo()).toHaveValue(e.sembrado);
      expect(escrituras(e.seccion)).toHaveLength(0);
    });

    test("3c-F2: nada sale antes de los 400 ms de pausa; a los 400 ms sale una sola petición con el rev y lo escrito", async () => {
      await abrirConRelojFalso();
      fireEvent.change(e.campo(), { target: { value: "9.5" } });
      await pausa(399);
      expect(escrituras(e.seccion)).toHaveLength(0);
      await pausa(1);
      expect(escrituras(e.seccion)).toHaveLength(1);
      expect(escrituras(e.seccion)[0]!.rev).toBe(0);
      expect(e.enCuerpo(escrituras(e.seccion)[0]!)).toBe("9.5");
      // Lo escrito se queda como lo escribió la persona; la respuesta no lo reemplaza.
      await esperar(() => within(regionDeEstado()).getByText(/· 1 cambio sin guardar/));
      expect(e.campo()).toHaveValue("9.5");
    });

    test("varias teclas dentro de la pausa son una sola petición con lo último, y la siguiente lleva el rev nuevo", async () => {
      await abrirConRelojFalso();
      fireEvent.change(e.campo(), { target: { value: "4" } });
      await pausa(300);
      fireEvent.change(e.campo(), { target: { value: "4." } });
      await pausa(300);
      fireEvent.change(e.campo(), { target: { value: "4.2" } });
      await pausa(400);
      expect(escrituras(e.seccion)).toHaveLength(1);
      expect(e.enCuerpo(escrituras(e.seccion)[0]!)).toBe("4.2");
      await esperar(() => within(regionDeEstado()).getByText(/· 1 cambio sin guardar/));
      fireEvent.change(e.campo(), { target: { value: "4.25" } });
      await pausa(400);
      expect(escrituras(e.seccion)).toHaveLength(2);
      expect(escrituras(e.seccion)[1]!.rev).toBe(1);
    });

    test("mientras se aplica un cambio se dice; solo hay una petición en vuelo y lo escrito entre tanto sale en una sola más", async () => {
      await abrirConRelojFalso();
      let terminar: (r: Response) => void = () => undefined;
      alPoner[e.seccion] = (cuerpo) =>
        escrituras(e.seccion).length === 1
          ? new Promise<Response>((resolver) => {
              terminar = resolver;
            })
          : acepta(cuerpo);
      fireEvent.change(e.campo(), { target: { value: "3.1" } });
      await pausa(400);
      expect(await esperar(() => screen.getByText("Aplicando los cambios al borrador…"))).toBeInTheDocument();
      fireEvent.change(e.campo(), { target: { value: "3.12" } });
      await pausa(400);
      fireEvent.change(e.campo(), { target: { value: "3.123" } });
      await pausa(400);
      expect(escrituras(e.seccion)).toHaveLength(1); // la primera sigue en vuelo
      await act(async () => terminar(acepta({ rev: 0 })));
      await esperar(() => expect(escrituras(e.seccion)).toHaveLength(2));
      expect(escrituras(e.seccion)[1]!.rev).toBe(1);
      expect(e.enCuerpo(escrituras(e.seccion)[1]!)).toBe("3.123");
      await esperar(() => expect(screen.queryByText("Aplicando los cambios al borrador…")).toBeNull());
    });

    test("al cambiar de pestaña con una edición en la pausa, se manda en seguida: no se pierde", async () => {
      await abrirConRelojFalso();
      fireEvent.change(e.campo(), { target: { value: "8" } });
      await act(async () => {
        fireEvent.click(screen.getByRole("tab", { name: "Auditoría" }));
      });
      expect(escrituras(e.seccion)).toHaveLength(1);
      expect(e.enCuerpo(escrituras(e.seccion)[0]!)).toBe("8");
    });

    test("3c-F13: lo escrito sale exactamente como se escribió (30 cifras, ceros a la izquierda, coma), sin convertirlo", async () => {
      await abrirConRelojFalso();
      const largo = "123456789012345678901234567890.1234567890123456789";
      fireEvent.change(e.campo(), { target: { value: largo } });
      await pausa(400);
      expect(e.enCuerpo(escrituras(e.seccion)[0]!)).toBe(largo);
      await esperar(() => within(regionDeEstado()).getByText(/· 1 cambio sin guardar/));
      fireEvent.change(e.campo(), { target: { value: "007,50" } });
      await pausa(400);
      await esperar(() => expect(escrituras(e.seccion)).toHaveLength(2));
      expect(e.enCuerpo(escrituras(e.seccion)[1]!)).toBe("007,50");
    });

    test("409 por rev viejo: avisa con el detalle, ofrece recargar y al recargar vuelve a sembrar lo del servidor", async () => {
      await abrirConRelojFalso();
      alPoner[e.seccion] = () => json({ detalle: REV_VIEJO }, 409);
      fireEvent.change(e.campo(), { target: { value: "7" } });
      await pausa(400);
      expect(await esperar(() => aviso())).toHaveTextContent(REV_VIEJO);
      expect(screen.queryByRole("button", { name: "Abrir de nuevo" })).toBeNull();
      // Otra ventana dejó el borrador en rev 5 con otro valor.
      abierto = borrador({ rev: 5, cambios: 3 });
      e.otroValorEnElServidor("9");
      fireEvent.click(screen.getByRole("button", { name: "Recargar el borrador" }));
      await esperar(() => expect(e.campo()).toHaveValue("9"));
      expect(llamadas("GET", `/v1/hoja/borradores/${ID}`)).toBe(1);
      expect(avisos()).toHaveLength(0);
      expect(within(regionDeEstado()).getByText(/· 3 cambios sin guardar/)).toBeInTheDocument();
      // La siguiente edición ya lleva el rev que el servidor tiene.
      alPoner[e.seccion] = acepta;
      fireEvent.change(e.campo(), { target: { value: "9.5" } });
      await pausa(400);
      await esperar(() => expect(escrituras(e.seccion)).toHaveLength(2));
      expect(escrituras(e.seccion)[1]!.rev).toBe(5);
    });

    test.each([
      ["el caso cambió", CASO_CAMBIO],
      ["ya se guardó", YA_GUARDADO],
    ])("409 porque %s: recargar no sirve, se ofrece abrir de nuevo", async (_nombre, detalle) => {
      await abrirConRelojFalso();
      alPoner[e.seccion] = () => json({ detalle }, 409);
      fireEvent.change(e.campo(), { target: { value: "7" } });
      await pausa(400);
      expect((await esperar(() => aviso())).textContent).toContain(detalle);
      expect(screen.queryByRole("button", { name: "Recargar el borrador" })).toBeNull();
      fireEvent.click(screen.getByRole("button", { name: "Abrir de nuevo" }));
      await esperar(() => expect(llamadas("POST", "/v1/hoja/borradores")).toBe(2));
    });

    test("tras un 409 no se manda más hasta recargar", async () => {
      await abrirConRelojFalso();
      alPoner[e.seccion] = () => json({ detalle: REV_VIEJO }, 409);
      fireEvent.change(e.campo(), { target: { value: "7" } });
      await pausa(400);
      await esperar(() => aviso());
      fireEvent.change(e.campo(), { target: { value: "77" } });
      await pausa(800);
      expect(escrituras(e.seccion)).toHaveLength(1);
    });

    test("un 401 al editar avisa al marco para que pida la sesión de nuevo", async () => {
      await abrirConRelojFalso();
      alPoner[e.seccion] = () => json({ detalle: "Inicie sesión." }, 401);
      fireEvent.change(e.campo(), { target: { value: "7" } });
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
        return new Response(null, { status: 204 });
      });
      fireEvent.change(e.campo(), { target: { value: "7" } });
      await pausa(400);
      expect(await esperar(() => screen.getByText("El borrador ya no está"))).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Abrir de nuevo" })).toBeInTheDocument();
    });

    test("3c-F10: beforeunload solo mientras hay cambios sin guardar", async () => {
      await abrirConRelojFalso();
      expect(saleLaPagina()).toBe(false);
      fireEvent.change(e.campo(), { target: { value: "3.5" } });
      await pausa(400);
      await esperar(() => within(regionDeEstado()).getByText(/· 1 cambio sin guardar/));
      expect(saleLaPagina()).toBe(true);
    });

    test("editar no deja nada en localStorage ni sessionStorage", async () => {
      await abrirConRelojFalso();
      fireEvent.change(e.campo(), { target: { value: "secreto-no-guardar" } });
      await pausa(400);
      expect(localStorage.length).toBe(0);
      expect(sessionStorage.length).toBe(0);
    });

    test("un 422 de dominio deja el valor escrito para corregirlo, con la frase de la clásica en un alert, y corregir limpia el aviso", async () => {
      await abrirConRelojFalso();
      alPoner[e.seccion] = () => json({ detalle: "El detalle de la clásica" }, 422);
      fireEvent.change(e.campo(), { target: { value: "x" } });
      await pausa(400);
      expect(await esperar(() => aviso())).toHaveTextContent(`El detalle de la clásica. ${e.frase}`);
      expect(e.campo()).toHaveValue("x");
      // El borrador no avanzó: el total y los cambios son los de antes.
      expect(within(regionDeEstado()).getByTitle("2703.860232344044033333333333")).toBeInTheDocument();
      expect(within(regionDeEstado()).getByText(/Sin cambios sin guardar/)).toBeInTheDocument();
      alPoner[e.seccion] = acepta;
      fireEvent.change(e.campo(), { target: { value: "2" } });
      await pausa(400);
      await esperar(() => expect(escrituras(e.seccion)).toHaveLength(2));
      expect(escrituras(e.seccion)[1]!.rev).toBe(0);
      await esperar(() => expect(avisos()).toHaveLength(0));
    });

    test("Esc devuelve el campo a lo último que aceptó el servidor", async () => {
      await e.abrir();
      const u = userEvent.setup({ delay: null });
      e.campo().focus();
      await u.type(e.campo(), "99");
      expect(e.campo()).toHaveValue(`${e.sembrado}99`);
      await u.keyboard("{Escape}");
      expect(e.campo()).toHaveValue(e.sembrado);
    });
  });

  // --- Parámetros (E3) -----------------------------------------------------------------------------------------------------

  describe("Parámetros (E3)", () => {
    test("cuatro campos con etiqueta visible y el valor como texto; ayuda de decimales; ya no dice que solo se leen", async () => {
      await irA("Parámetros");
      expect(await screen.findByRole("textbox", { name: /^FCAS/ })).toHaveValue("6.00");
      expect(campo(/^Bono de alimentación/)).toHaveValue("5.8100");
      expect(campo(/^Administración/)).toHaveValue("0.15");
      expect(campo(/^Utilidad/)).toHaveValue("0.10");
      expect(screen.getAllByRole("textbox")).toHaveLength(4);
      expect(screen.getByText(/Decimales con punto, por ejemplo 2\.5/)).toBeInTheDocument();
      expect(screen.getByText(/Cambiarlos recalcula/)).toBeInTheDocument();
      expect(screen.queryByText(/solo se leen/)).toBeNull();
      expect(screen.getByText("Moneda del proyecto: USD")).toBeInTheDocument();
      // La etiqueta se ve (no está oculta): es el rótulo de la clásica.
      expect(screen.getByText(/^Administración \(fracción del costo directo\)/)).toBeVisible();
    });

    test("3c-B1 (P13): administración 0.20 manda los cuatro textos y el total pasa a 2.821,42 en la pestaña y en el estado", async () => {
      await irA("Parámetros");
      await screen.findByRole("textbox", { name: /^Administración/ });
      relojFalso();
      const nuevo = { texto: "2821.42", exacto: "2821.4208" };
      parametros = vistaParametros({
        campos: parametros.campos.map((f) => (f.clave === "administracion" ? { ...f, valor: "0.20" } : f)),
        total: nuevo,
      });
      alPoner.parametros = (c) => acepta(c, { total: nuevo });
      fireEvent.change(campo(/^Administración/), { target: { value: "0.20" } });
      await pausa(400);
      expect(escrituras("parametros")).toEqual([
        { rev: 0, fcas: "6.00", bono_alimentacion: "5.8100", administracion: "0.20", utilidad: "0.10" },
      ]);
      const antes = lecturas("parametros");
      await esperar(() => expect(screen.getAllByTitle("2821.4208")).toHaveLength(2)); // el estado y el total de la pestaña
      expect(screen.getAllByTitle("2821.4208")[0]).toHaveTextContent("2.821,42 USD");
      expect(lecturas("parametros")).toBe(antes + 1);
      expect(within(regionDeEstado()).getByText(/· 1 cambio sin guardar/)).toBeInTheDocument();
      expect(campo(/^Administración/)).toHaveValue("0.20");
    });

    test("3c-B2 (P14): «mucho» en utilidad se rechaza con el mensaje de la clásica; solo ese campo queda inválido, con su texto", async () => {
      await irA("Parámetros");
      await screen.findByRole("textbox", { name: /^Utilidad/ });
      relojFalso();
      const DETALLE = "parametros: utilidad: 'mucho' no es un numero decimal valido";
      alPoner.parametros = () => json({ detalle: DETALLE }, 422);
      fireEvent.change(campo(/^Utilidad/), { target: { value: "mucho" } });
      await pausa(400);
      const alerta = await esperar(() => aviso());
      expect(alerta).toHaveTextContent(`${DETALLE}. La hoja sigue con los últimos parámetros válidos.`);
      await esperar(() => expect(campo(/^Utilidad/)).toHaveAttribute("aria-invalid", "true"));
      expect(campo(/^Administración/)).not.toHaveAttribute("aria-invalid", "true");
      expect(campo(/^FCAS/)).not.toHaveAttribute("aria-invalid", "true");
      // El texto propio del campo (el color nunca va solo) y la descripción accesible con el aviso completo.
      expect(screen.getByText("'mucho' no es un numero decimal valido")).toBeInTheDocument();
      expect(document.getElementById(campo(/^Utilidad/).getAttribute("aria-describedby")!)).toHaveTextContent(DETALLE);
      expect(campo(/^Utilidad/)).toHaveValue("mucho"); // se queda lo escrito para corregirlo
      expect(within(regionDeEstado()).getByTitle("2703.860232344044033333333333")).toBeInTheDocument();
    });

    test("D-8 (P17): la coma decimal se manda tal cual y se rechaza con el mensaje de la clásica, sin convertirla", async () => {
      await irA("Parámetros");
      await screen.findByRole("textbox", { name: /^Administración/ });
      relojFalso();
      alPoner.parametros = () =>
        json({ detalle: "parametros: administracion: '0,20' no es un numero decimal valido" }, 422);
      fireEvent.change(campo(/^Administración/), { target: { value: "0,20" } });
      await pausa(400);
      expect(escrituras("parametros")[0]!.administracion).toBe("0,20");
      expect(await esperar(() => aviso())).toHaveTextContent("'0,20' no es un numero decimal valido");
      expect(campo(/^Administración/)).toHaveAttribute("aria-invalid", "true");
    });

    test("un 422 de forma (sin campo) se muestra sin dejar ningún campo inválido", async () => {
      await irA("Parámetros");
      await screen.findByRole("textbox", { name: /^FCAS/ });
      relojFalso();
      alPoner.parametros = () =>
        json({ detalle: "Los parámetros no tienen la forma esperada: envíe fcas, bono_alimentacion, administracion y utilidad, cada uno como texto de hasta 500 caracteres." }, 422);
      fireEvent.change(campo(/^FCAS/), { target: { value: "7" } });
      await pausa(400);
      expect(await esperar(() => aviso())).toHaveTextContent("Los parámetros no tienen la forma esperada");
      expect(document.querySelector("[aria-invalid='true']")).toBeNull();
    });
  });

  // --- Cantidades (E2) ------------------------------------------------------------------------------------------------------

  describe("Presupuesto: cantidades (E2)", () => {
    test("3c-F8: solo la columna Cantidad es editable; la escrita a mano dice cuál era la calculada y ofrece volver a ella", async () => {
      await irA("Presupuesto");
      const tabla = await screen.findByRole("table", { name: "Presupuesto" });
      expect(within(tabla).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([
        "Partida",
        "Descripción",
        "Unidad",
        "Cantidad",
        "Precio unitario",
        "Total",
        "Estado",
      ]);
      // Dos renglones, dos campos: la cantidad. Lo demás es texto.
      expect(within(tabla).getAllByRole("textbox")).toHaveLength(2);
      expect(campo("Cantidad, Presupuesto fila 1")).toHaveValue("3");
      expect(campo("Cantidad, Presupuesto fila 2")).toHaveValue("5");
      const filas = within(tabla).getAllByRole("row");
      expect(within(filas[1]!).queryByText(/calculada/)).toBeNull();
      expect(within(filas[1]!).queryByRole("button", { name: /Volver a la calculada/ })).toBeNull();
      expect(within(filas[2]!).getByText("(calculada: 3)")).toBeInTheDocument();
      expect(within(filas[2]!).getByRole("button", { name: /^Volver a la calculada/ })).toBeInTheDocument();
      // Lo de la lectura sigue: precio unitario, total y Estado.
      expect(within(filas[1]!).getByText("13,20")).toBeInTheDocument();
      expect(within(filas[2]!).getAllByText("Pendiente")).toHaveLength(2);
      expect(within(filas[2]!).getByText("Error")).toBeInTheDocument();
      expect(screen.getByText(/Decimales con punto, por ejemplo 2\.5/)).toBeInTheDocument();
    });

    test("3c-B3 (P15): escribir 5 en AF-LLAVE manda solo esa fila; la vista nueva la marca como escrita y sube el total", async () => {
      await irA("Presupuesto");
      await screen.findByRole("textbox", { name: "Cantidad, Presupuesto fila 1" });
      relojFalso();
      // Cuando el servidor acepte, la vista trae la fila escrita y el total nuevo (oráculo de mano: 2.703,86 + 26,40 = 2.730,26).
      presupuesto = vistaPresupuesto({
        filas: vistaPresupuesto().filas.map((f, i) => (i === 0 ? { ...f, cantidad: "5", cantidad_calculada: "3", escrita: true } : f)),
        total: { texto: "2730.26", exacto: "2730.2577124" },
      });
      alPoner.cantidades = (c) => acepta(c, { total: { texto: "2730.26", exacto: "2730.2577124" } });
      fireEvent.change(campo("Cantidad, Presupuesto fila 1"), { target: { value: "5" } });
      await pausa(400);
      expect(escrituras("cantidades")).toEqual([{ rev: 0, filas: [{ clave: "AF-LLAVE|esp_puntos:P1", cantidad: "5" }] }]);
      const fila1 = async () => within(await screen.findByRole("table", { name: "Presupuesto" })).getAllByRole("row")[1]!;
      expect(await esperar(async () => within(await fila1()).getByText("(calculada: 3)"))).toBeInTheDocument();
      expect(screen.getByTitle("2730.2577124")).toHaveTextContent("2.730,26 USD");
      expect(campo("Cantidad, Presupuesto fila 1")).toHaveValue("5");
    });

    test("las filas tocadas se acumulan, en el orden de la tabla, y las que no se tocaron no viajan", async () => {
      await irA("Presupuesto");
      await screen.findByRole("textbox", { name: "Cantidad, Presupuesto fila 1" });
      relojFalso();
      fireEvent.change(campo("Cantidad, Presupuesto fila 2"), { target: { value: "6" } });
      await pausa(400);
      await esperar(() => expect(escrituras("cantidades")).toHaveLength(1));
      expect(escrituras("cantidades")[0]!.filas).toEqual([{ clave: "AF-SALIDA|esp_puntos:P2", cantidad: "6" }]);
      await esperar(() => within(regionDeEstado()).getByText(/· 1 cambio sin guardar/));
      fireEvent.change(campo("Cantidad, Presupuesto fila 1"), { target: { value: "4" } });
      await pausa(400);
      await esperar(() => expect(escrituras("cantidades")).toHaveLength(2));
      expect(escrituras("cantidades")[1]).toEqual({
        rev: 1,
        filas: [
          { clave: "AF-LLAVE|esp_puntos:P1", cantidad: "4" },
          { clave: "AF-SALIDA|esp_puntos:P2", cantidad: "6" },
        ],
      });
    });

    test("3c-B4: «Volver a la calculada» pone la cantidad calculada en el campo y la manda (el servidor deja de verla como escrita)", async () => {
      await irA("Presupuesto");
      await screen.findByRole("textbox", { name: "Cantidad, Presupuesto fila 2" });
      relojFalso();
      fireEvent.click(screen.getByRole("button", { name: /^Volver a la calculada/ }));
      expect(campo("Cantidad, Presupuesto fila 2")).toHaveValue("3");
      await pausa(400);
      expect(escrituras("cantidades")).toEqual([{ rev: 0, filas: [{ clave: "AF-SALIDA|esp_puntos:P2", cantidad: "3" }] }]);
    });

    test("3c-B5 (P16): una cantidad negativa se rechaza con el mensaje de la clásica; solo esa fila queda inválida", async () => {
      await irA("Presupuesto");
      await screen.findByRole("textbox", { name: "Cantidad, Presupuesto fila 1" });
      relojFalso();
      const DETALLE =
        "presupuesto, fila 1 (AF-LLAVE): la cantidad no puede ser negativa; escriba cero o una cantidad positiva";
      alPoner.cantidades = () => json({ detalle: DETALLE }, 422);
      fireEvent.change(campo("Cantidad, Presupuesto fila 1"), { target: { value: "-1" } });
      await pausa(400);
      expect(await esperar(() => aviso())).toHaveTextContent(`${DETALLE}. La hoja sigue con las últimas cantidades válidas.`);
      await esperar(() => expect(campo("Cantidad, Presupuesto fila 1")).toHaveAttribute("aria-invalid", "true"));
      expect(campo("Cantidad, Presupuesto fila 2")).not.toHaveAttribute("aria-invalid", "true");
      expect(screen.getByText("Valor no válido")).toBeInTheDocument();
      expect(document.getElementById(campo("Cantidad, Presupuesto fila 1").getAttribute("aria-describedby")!)).toHaveTextContent(DETALLE);
      expect(campo("Cantidad, Presupuesto fila 1")).toHaveValue("-1");
    });

    test("la coma decimal se manda tal cual y la rechaza el servidor con el mensaje de la clásica", async () => {
      await irA("Presupuesto");
      await screen.findByRole("textbox", { name: "Cantidad, Presupuesto fila 2" });
      relojFalso();
      alPoner.cantidades = () =>
        json({ detalle: "presupuesto, fila 2 (AF-SALIDA): cantidad: '2,5' no es un numero decimal valido" }, 422);
      fireEvent.change(campo("Cantidad, Presupuesto fila 2"), { target: { value: "2,5" } });
      await pausa(400);
      expect(escrituras("cantidades")[0]!.filas).toEqual([{ clave: "AF-SALIDA|esp_puntos:P2", cantidad: "2,5" }]);
      expect(await esperar(() => aviso())).toHaveTextContent("'2,5' no es un numero decimal valido");
      expect(campo("Cantidad, Presupuesto fila 2")).toHaveAttribute("aria-invalid", "true");
    });

    test("el Estado de cada renglón sigue con «Ver en Auditoría» al lado del campo (3b-F6b)", async () => {
      await irA("Presupuesto");
      const tabla = await screen.findByRole("table", { name: "Presupuesto" });
      expect(within(tabla).getByRole("button", { name: "Ver en Auditoría: AF-SALIDA, Punto P2" })).toBeInTheDocument();
    });

    test("flechas arriba y abajo y Enter mueven entre renglones de la columna Cantidad", async () => {
      await irA("Presupuesto");
      await screen.findByRole("textbox", { name: "Cantidad, Presupuesto fila 1" });
      const u = userEvent.setup({ delay: null });
      campo("Cantidad, Presupuesto fila 1").focus();
      await u.keyboard("{ArrowDown}");
      expect(campo("Cantidad, Presupuesto fila 2")).toHaveFocus();
      await u.keyboard("{ArrowUp}");
      expect(campo("Cantidad, Presupuesto fila 1")).toHaveFocus();
      await u.keyboard("{Enter}");
      expect(campo("Cantidad, Presupuesto fila 2")).toHaveFocus();
    });

    test("sin renglones sigue el mensaje del servidor y no hay campos", async () => {
      const mensaje = "El presupuesto no tiene renglones todavía.";
      presupuesto = vistaPresupuesto({ filas: [], vacio_mensaje: mensaje });
      await irA("Presupuesto");
      expect(await screen.findByText(mensaje)).toBeInTheDocument();
      expect(screen.queryAllByRole("textbox")).toEqual([]);
    });
  });

  // --- Plan y curva (E4, E5) ----------------------------------------------------------------------------------------------

  describe("Plan y curva (E4 y E5)", () => {
    const SIN_PLAN = "Esta versión no tiene plan de trabajo, así que no hay curva de inversión.";
    const sinPlan = () => vistaPlan({ hay_plan: false, etiquetas: [], filas: [], curva: [], mensaje: SIN_PLAN });

    test("3b-F8 con edición: la matriz tiene un campo por partida y período con nombre accesible, y la curva sigue debajo", async () => {
      await irA("Plan y curva");
      const matriz = await screen.findByRole("table", { name: "Plan de trabajo" });
      expect(within(matriz).getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Partida", "Día 1", "Día 2"]);
      expect(within(matriz).getAllByRole("textbox")).toHaveLength(4);
      expect(campo("Día 1, Plan de trabajo fila 1")).toHaveValue("1");
      expect(campo("Día 2, Plan de trabajo fila 1")).toHaveValue("0");
      expect(campo("Día 1, Plan de trabajo fila 2")).toHaveValue("0");
      expect(campo("Día 2, Plan de trabajo fila 2")).toHaveValue("1");
      expect(within(within(matriz).getAllByRole("row")[1]!).getAllByRole("cell")[0]).toHaveTextContent("AF-CODO-1/2");
      expect(screen.getByText(/Decimales con punto, por ejemplo 2\.5/)).toBeInTheDocument();
      expect(screen.getByRole("heading", { level: 2, name: "Curva de inversión" })).toBeInTheDocument();
      expect(screen.getByRole("table", { name: "Curva de inversión: montos" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /Crear plan secuencial/ })).toBeNull();
    });

    test("3c-F12: la matriz completa viaja como texto y la curva se vuelve a leer y se muestra recalculada", async () => {
      await irA("Plan y curva");
      await screen.findByRole("textbox", { name: "Día 1, Plan de trabajo fila 1" });
      relojFalso();
      // Cuando el servidor acepte, la curva trae los montos nuevos (cifras de mano para esta prueba).
      plan = vistaPlan({
        filas: [
          { partida: "AF-CODO-1/2", valores: { "Dia 1": "0.5", "Dia 2": "0.5" } },
          { partida: "AF-LLAVE", valores: { "Dia 1": "0", "Dia 2": "1" } },
        ],
        curva: [
          { periodo: "Dia 1", monto: { texto: "5.59", exacto: "5.59" }, acumulado: { texto: "5.59", exacto: "5.59" }, porcentaje: { texto: "0.21", exacto: "0.2067" } },
          { periodo: "Dia 2", monto: { texto: "15.46", exacto: "15.46" }, acumulado: { texto: "21.05", exacto: "21.05" }, porcentaje: { texto: "0.78", exacto: "0.7785" } },
        ],
      });
      fireEvent.change(campo("Día 1, Plan de trabajo fila 1"), { target: { value: "0.5" } });
      fireEvent.change(campo("Día 2, Plan de trabajo fila 1"), { target: { value: "0.5" } });
      await pausa(400);
      expect(escrituras("plan")).toEqual([
        {
          rev: 0,
          etiquetas: ["Dia 1", "Dia 2"],
          filas: [
            { partida: "AF-CODO-1/2", valores: { "Dia 1": "0.5", "Dia 2": "0.5" } },
            { partida: "AF-LLAVE", valores: { "Dia 1": "0", "Dia 2": "1" } },
          ],
        },
      ]);
      const curva = () => screen.getByRole("table", { name: "Curva de inversión: montos" });
      expect(await esperar(() => within(within(curva()).getAllByRole("row")[1]!).getAllByText("5,59"))).toHaveLength(2);
      expect(within(within(curva()).getAllByRole("row")[2]!).getByText("15,46")).toBeInTheDocument();
      expect(campo("Día 1, Plan de trabajo fila 1")).toHaveValue("0.5");
      expect(within(regionDeEstado()).getByText(/· 1 cambio sin guardar/)).toBeInTheDocument();
    });

    test("3c-B12 (P19): fracciones que no suman 1 se rechazan con el mensaje de la clásica; la fila queda inválida y se ofrece ir a ella", async () => {
      await irA("Plan y curva");
      await screen.findByRole("textbox", { name: "Día 1, Plan de trabajo fila 2" });
      relojFalso();
      const DETALLE =
        "plan, partida AF-LLAVE: las fracciones suman 1.5 y deben sumar exactamente 1; repartala entre los periodos hasta completar 1";
      alPoner.plan = () => json({ detalle: DETALLE }, 422);
      campo("Día 2, Plan de trabajo fila 1").focus();
      fireEvent.change(campo("Día 1, Plan de trabajo fila 2"), { target: { value: "0.5" } });
      await pausa(400);
      expect(await esperar(() => aviso())).toHaveTextContent(`${DETALLE}. La hoja sigue con el último plan válido.`);
      // Todas las celdas de la partida señalada, y solo ellas.
      await esperar(() => expect(campo("Día 1, Plan de trabajo fila 2")).toHaveAttribute("aria-invalid", "true"));
      expect(campo("Día 2, Plan de trabajo fila 2")).toHaveAttribute("aria-invalid", "true");
      expect(campo("Día 1, Plan de trabajo fila 1")).not.toHaveAttribute("aria-invalid", "true");
      expect(campo("Día 2, Plan de trabajo fila 1")).not.toHaveAttribute("aria-invalid", "true");
      expect(screen.getByText("Revise esta partida")).toBeInTheDocument();
      // El foco no se mueve solo; el botón lo lleva a la primera celda de la partida.
      expect(campo("Día 2, Plan de trabajo fila 1")).toHaveFocus();
      fireEvent.click(screen.getByRole("button", { name: "Ir a la partida AF-LLAVE" }));
      expect(campo("Día 1, Plan de trabajo fila 2")).toHaveFocus();
      // La curva es la anterior.
      expect(within(screen.getByRole("table", { name: "Curva de inversión: montos" })).getAllByText("11,18")).toHaveLength(2);
    });

    test("una fracción negativa o con coma se manda tal cual; el servidor decide", async () => {
      await irA("Plan y curva");
      await screen.findByRole("textbox", { name: "Día 1, Plan de trabajo fila 1" });
      relojFalso();
      alPoner.plan = () => json({ detalle: "plan, partida AF-CODO-1/2: Dia 1: '0,5' no es un numero decimal valido" }, 422);
      fireEvent.change(campo("Día 1, Plan de trabajo fila 1"), { target: { value: "0,5" } });
      await pausa(400);
      const cuerpo = escrituras("plan")[0] as unknown as { filas: Array<{ valores: Record<string, string> }> };
      expect(cuerpo.filas[0]!.valores["Dia 1"]).toBe("0,5");
      expect(await esperar(() => aviso())).toHaveTextContent("'0,5' no es un numero decimal valido");
      expect(campo("Día 1, Plan de trabajo fila 1")).toHaveAttribute("aria-invalid", "true");
      expect(campo("Día 1, Plan de trabajo fila 2")).not.toHaveAttribute("aria-invalid", "true");
    });

    test("3c-F12 (P20): sin plan se ofrece «Crear plan secuencial»; al crearlo aparece la matriz y el botón desaparece", async () => {
      plan = sinPlan();
      await irA("Plan y curva");
      expect(await screen.findByText(SIN_PLAN)).toBeInTheDocument();
      expect(screen.queryByRole("table", { name: "Plan de trabajo" })).toBeNull();
      const boton = screen.getByRole("button", { name: "Crear plan secuencial (una partida por periodo)" });
      alPoner.secuencial = (c) => {
        plan = vistaPlan();
        return acepta(c, { hay_plan: true });
      };
      fireEvent.click(boton);
      expect(await screen.findByRole("table", { name: "Plan de trabajo" })).toBeInTheDocument();
      expect(escrituras("secuencial")).toEqual([{ rev: 0 }]);
      expect(screen.queryByRole("button", { name: /Crear plan secuencial/ })).toBeNull();
      expect(campo("Día 1, Plan de trabajo fila 1")).toHaveValue("1");
      expect(await screen.findByTestId("grafico")).toHaveAttribute("data-filas", "2");
      expect(within(regionDeEstado()).getByText(/· 1 cambio sin guardar/)).toBeInTheDocument();
      // Ya con matriz, la siguiente edición lleva el rev que contestó el servidor.
      relojFalso();
      fireEvent.change(campo("Día 1, Plan de trabajo fila 1"), { target: { value: "0.5" } });
      await pausa(400);
      expect(escrituras("plan")[0]!.rev).toBe(1);
    });

    test("crear el plan con el rev viejo (409): avisa y ofrece recargar; recargar trae el plan que ya existe", async () => {
      plan = sinPlan();
      await irA("Plan y curva");
      await screen.findByRole("button", { name: /Crear plan secuencial/ });
      alPoner.secuencial = () => json({ detalle: REV_VIEJO }, 409);
      fireEvent.click(screen.getByRole("button", { name: /Crear plan secuencial/ }));
      expect(await screen.findByText(REV_VIEJO)).toBeInTheDocument();
      abierto = borrador({ rev: 3, cambios: 1 });
      plan = vistaPlan();
      fireEvent.click(screen.getByRole("button", { name: "Recargar el borrador" }));
      expect(await screen.findByRole("table", { name: "Plan de trabajo" })).toBeInTheDocument();
      expect(avisos()).toHaveLength(0);
    });

    test("«ya tiene plan» (409 de E5) se muestra con su detalle, sin pedir recargar ni abrir de nuevo, y se vuelve a leer el plan", async () => {
      plan = sinPlan();
      await irA("Plan y curva");
      await screen.findByRole("button", { name: /Crear plan secuencial/ });
      const YA_TIENE = "Esta versión ya tiene plan de trabajo: edítelo en la matriz del plan.";
      alPoner.secuencial = () => json({ detalle: YA_TIENE }, 409);
      plan = vistaPlan(); // otra ventana lo creó
      fireEvent.click(screen.getByRole("button", { name: /Crear plan secuencial/ }));
      expect(await screen.findByRole("table", { name: "Plan de trabajo" })).toBeInTheDocument();
      expect(aviso()).toHaveTextContent(YA_TIENE);
      expect(screen.queryByRole("button", { name: "Recargar el borrador" })).toBeNull();
      expect(screen.queryByRole("button", { name: "Abrir de nuevo" })).toBeNull();
    });

    test("mientras se crea el plan el botón no se puede pulsar otra vez: una sola petición", async () => {
      plan = sinPlan();
      await irA("Plan y curva");
      const boton = await screen.findByRole("button", { name: /Crear plan secuencial/ });
      let terminar: (r: Response) => void = () => undefined;
      alPoner.secuencial = () =>
        new Promise<Response>((resolver) => {
          terminar = resolver;
        });
      fireEvent.click(boton);
      await esperar(() => expect(screen.getByRole("button", { name: /Crear plan secuencial/ })).toBeDisabled());
      fireEvent.click(screen.getByRole("button", { name: /Crear plan secuencial/ }));
      expect(escrituras("secuencial")).toHaveLength(1);
      plan = vistaPlan();
      await act(async () => terminar(acepta({ rev: 0 }, { hay_plan: true })));
      expect(await screen.findByRole("table", { name: "Plan de trabajo" })).toBeInTheDocument();
    });
  });

  // --- Estática -------------------------------------------------------------------------------------------------------------

  test("3c-F13: los archivos nuevos de la carpeta están bajo la prueba estática (sin Number, parseFloat, toFixed ni + unario)", () => {
    const fuentes = import.meta.glob("./*.{ts,tsx}", { query: "?raw", import: "default", eager: true }) as Record<string, string>;
    for (const ruta of [
      "./logicaSecciones.ts",
      "./useEdicionDeSeccion.ts",
      "./AvisoDeEdicion.tsx",
      "./CampoDeCelda.tsx",
      "./PestanaParametros.tsx",
      "./PestanaPresupuesto.tsx",
      "./PestanaPlan.tsx",
    ]) {
      expect(Object.keys(fuentes), ruta).toContain(ruta);
      expect(fuentes[ruta], ruta).not.toMatch(
        /\bNumber\s*\(|\bparseFloat\s*\(|\bparseInt\s*\(|\.toFixed\s*\(|(?:[=(,:?]|\breturn)\s*\+\s*[A-Za-z_$(]/,
      );
    }
  });
});
