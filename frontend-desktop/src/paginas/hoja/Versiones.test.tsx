import { act, configure, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { atipicosRespuesta, cuerpoDeVista, preciosRespuesta, vistaParametros } from "./datosDePrueba";
import PaginaHoja from "./index";
import type { BorradorAbierto, PreciosRespuesta, Resumen, VersionesRespuesta } from "./logica";

// Rebanada 3d-2 (front): cotizar (S3), retirar (S4) y convertir (S5), contrato
// `2026-10-20-hoja-3d2-contrato-rutas.md`. El servidor se simula con respuestas ficticias con la forma del contrato. Caso ficticio
// OF-001; los literales de los mensajes están escritos a mano desde el contrato y la clásica (ui/paginas/hoja.py:1946-2213).
// Restaurar (S2) y la cadena de sellos (S6) se mudaron a la sección Versiones con la baja 24 (Tarea 6 del plan F4): sus
// pruebas están en `paginas/versiones/Versiones.test.tsx`.
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
  acciones: ["editar_hoja", "convertir_y_reajustar"],
  modo_entrega: false,
};

const ID = "id-borrador-aaaaaaaaaaaa";
const m = (texto: string, exacto = texto) => ({ texto, exacto });
const fila = (codigo: string, vigente: boolean, origen = "") => ({
  codigo,
  fecha: "2026-10-06",
  motivo: "",
  origen,
  vigente,
  descartada: false,
  cambios: 0,
});
const VERSIONES: VersionesRespuesta = {
  proyecto: "OF-001",
  moneda: "USD",
  por_omision: "002",
  versiones: [fila("002", true, "001"), fila("001", false)],
};
const VERSIONES_CON_003: VersionesRespuesta = {
  ...VERSIONES,
  por_omision: "003",
  versiones: [fila("003", true, "002"), ...VERSIONES.versiones.map((v) => ({ ...v, vigente: false }))],
};

function resumen(extra: Partial<Resumen> = {}): Resumen {
  return {
    rev: 3,
    moneda: "USD",
    total: m("2703.86", "2703.860232344044033333333333"),
    cambios: 0,
    pendientes_catalogo: 0,
    hallazgos: [],
    hay_plan: true,
    version_mas_nueva: null,
    guardado_como: null,
    ...extra,
  };
}

function borrador(version: string | null, extra: Partial<Resumen> = {}): BorradorAbierto {
  return {
    id: ID,
    base: { proyecto: "OF-001", version, vigente: version, lista: "Lista", espacio_de: version, solo_lectura: false, moneda: "USD" },
    resumen: resumen(extra),
    instantanea: { creadas: 0, mensaje: null },
  };
}

// MAT-002 ya tiene una cotización propia (la que se puede retirar); MAT-001 no.
function preciosConCotizacion(): PreciosRespuesta {
  const base = preciosRespuesta();
  return {
    ...base,
    filas: base.filas.map((f) => (f["codigo"] === "MAT-002" ? { ...f, cotizacion: "COT-17 · Ferretería Demo" } : f)),
  };
}

describe("Hoja de la obra: cotizar, retirar y convertir (3d-2)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();
  let versiones: VersionesRespuesta;
  let cambiosSinGuardar: number;
  let soloLectura: boolean;
  let precios: PreciosRespuesta;
  let parametros: ReturnType<typeof vistaParametros>;
  let alOperacion: (ruta: string, cuerpo: Record<string, unknown>) => Response | Promise<Response>;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    versiones = VERSIONES;
    cambiosSinGuardar = 0;
    soloLectura = false;
    precios = preciosConCotizacion();
    parametros = vistaParametros();
    alOperacion = () => json({ codigo: "003", proyecto: "OF-001", mensaje: "Se guardó la versión 003 sin la cotización." });
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = new URL(String(ruta), "http://silice.local");
      const metodo = init?.method ?? "GET";
      const camino = url.pathname;
      if (camino === "/v1/hoja/versiones" && metodo === "GET") return json(versiones);
      if (camino.startsWith("/v1/hoja/versiones/") && metodo === "POST") {
        return alOperacion(camino, JSON.parse(String(init?.body)) as Record<string, unknown>);
      }
      if (camino === "/v1/hoja/borradores" && metodo === "GET") return json({ borradores: [] });
      if (camino === "/v1/hoja/borradores" && metodo === "POST") {
        const c = JSON.parse(String(init?.body)) as { version: string | null };
        const b = borrador(c.version, c.version === "002" ? { cambios: cambiosSinGuardar } : { cambios: 0, rev: 0 });
        b.base.solo_lectura = soloLectura;
        return json(b, 201);
      }
      if (camino === "/v1/hoja/precios") return json(precios);
      if (camino === "/v1/hoja/precios/atipicos") return json(atipicosRespuesta());
      if (camino.endsWith("/vistas/parametros")) return json(parametros);
      if (camino.includes("/vistas/")) return json(cuerpoDeVista(camino));
      const propio = /^\/v1\/hoja\/borradores\/([^/]+)$/.exec(camino);
      if (propio && metodo === "GET") {
        const b = borrador("002", { cambios: cambiosSinGuardar });
        return json({ id: ID, base: b.base, resumen: b.resumen });
      }
      if (propio && metodo === "DELETE") return new Response(null, { status: 204 });
      return new Response(null, { status: 204 });
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const llamadas = (metodo: string, termina: string) =>
    fetchFalso.mock.calls.filter(([r, init]) => new URL(String(r), "http://silice.local").pathname.endsWith(termina) && (init?.method ?? "GET") === metodo);
  const enviados = (termina: string) => llamadas("POST", termina).map(([, i]) => JSON.parse(String(i?.body)) as Record<string, unknown>);
  const aperturas = () => llamadas("POST", "/v1/hoja/borradores").map(([, i]) => JSON.parse(String(i?.body)) as { version: string | null });

  function valor(): Aplicacion {
    return {
      sesion: SESION,
      proyecto: "OF-001",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
  }
  function montar() {
    return render(
      <ContextoAplicacion.Provider value={valor()}>
        <PaginaHoja />
      </ContextoAplicacion.Provider>,
    );
  }
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
  const irA = async (pestana: string) => {
    await userEvent.click(await screen.findByRole("tab", { name: pestana }));
  };
  const abrirDialogo = async (boton: string) => {
    fireEvent.click(await screen.findByRole("button", { name: boton }));
    return screen.findByRole("dialog");
  };
  // Un <input type="date"> no tiene rol «textbox»: la fecha se busca por su etiqueta.
  const campo = (dialogo: HTMLElement, nombre: string | RegExp) =>
    nombre === "Fecha de la cotización" ? within(dialogo).getByLabelText(nombre) : within(dialogo).getByRole("textbox", { name: nombre });
  const escribir = (dialogo: HTMLElement, nombre: string | RegExp, texto: string) =>
    fireEvent.change(campo(dialogo, nombre), { target: { value: texto } });
  const boton = (dialogo: HTMLElement, nombre: string) => within(dialogo).getByRole("button", { name: nombre });

  // --- 3d-F5: con cambios sin guardar no se ofrece nada ---------------------------------------------------------------------

  describe("3d-F5: con cambios sin guardar no se ofrecen cotizar, retirar ni convertir", () => {
    beforeEach(() => {
      cambiosSinGuardar = 3;
    });

    test("Parámetros: no se ofrece convertir la moneda (P:2081)", async () => {
      montar();
      await irA("Ajustes de costo");
      await screen.findByRole("textbox", { name: /^FCAS/ });
      expect(
        screen.getByText("Cambiar la moneda crea una versión nueva desde la guardada: guarde o descarte primero los 3 cambios pendientes."),
      ).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Convertir la moneda…" })).toBeNull();
    });

  });

  // --- 3d-F6: convertir -----------------------------------------------------------------------------------------------------

  describe("3d-F6: convertir la moneda (S5)", () => {
    test("la moneda destino excluye la actual; manda moneda, lado y fuente; abre la versión convertida", async () => {
      alOperacion = () => json({ codigo: "003", proyecto: "OF-001", mensaje: "Se guardó la versión 003, convertida a Bs." });
      montar();
      await irA("Ajustes de costo");
      await screen.findByRole("textbox", { name: /^FCAS/ });
      const dialogo = await abrirDialogo("Convertir la moneda…");
      expect(dialogo).toHaveAccessibleName("Convertir la moneda");
      expect(within(dialogo).getByText(/crea una versión convertida; la actual no cambia/)).toBeInTheDocument();
      const destino = within(dialogo).getByRole("combobox", { name: "Moneda destino" });
      expect(destino).toHaveFocus();
      expect(within(destino).getAllByRole("option").map((o) => o.textContent)).toEqual(["Bs"]);
      const lado = within(dialogo).getByRole("combobox", { name: "Tasa del BCV" });
      expect(within(lado).getAllByRole("option").map((o) => [o.textContent, (o as HTMLOptionElement).value])).toEqual([
        ["Venta", "venta"],
        ["Compra", "compra"],
      ]);
      expect(lado).toHaveValue("venta"); // por omisión, venta (S1-R1)
      expect(within(dialogo).getByText("Responsable: Ana Pérez <ana>")).toBeInTheDocument();
      const convertir = boton(dialogo, "Convertir la versión");
      expect(convertir).toBeDisabled();
      expect(within(dialogo).getByText("Escriba por qué se cambia la moneda (la fuente).")).toBeInTheDocument();
      escribir(dialogo, "Por qué se cambia la moneda (fuente)", "Pedido de la gerencia");
      await userEvent.selectOptions(lado, "compra");
      versiones = VERSIONES_CON_003;
      fireEvent.click(convertir);
      expect(await screen.findByText("Se guardó la versión 003, convertida a Bs.")).toBeInTheDocument();
      expect(enviados("/convertir")).toEqual([
        { proyecto: "OF-001", version: "002", moneda: "Bs", lado: "compra", fuente: "Pedido de la gerencia" },
      ]);
      await esperar(() => expect(aperturas().map((a) => a.version)).toEqual(["002", "003"]));
    });

    test("sin tasa del BCV (422): el texto del servidor tal cual, que ya empieza por «No se convirtio nada»", async () => {
      const detalle = "No se convirtio nada: no hay tasa del BCV en los 7 dias anteriores al 2026-10-20";
      alOperacion = () => json({ detalle }, 422);
      montar();
      await irA("Ajustes de costo");
      const dialogo = await abrirDialogo("Convertir la moneda…");
      escribir(dialogo, "Por qué se cambia la moneda (fuente)", "Gerencia");
      fireEvent.click(boton(dialogo, "Convertir la versión"));
      const alerta = await within(dialogo).findByRole("alert");
      expect(within(alerta).getByText("No se convirtió nada")).toBeInTheDocument();
      expect(within(alerta).getByText(detalle)).toBeInTheDocument();
      expect(screen.getByRole("dialog")).toBe(dialogo);
    });

    test("si el servidor dice que la cuenta no puede convertir, no se ofrece", async () => {
      parametros = { ...vistaParametros(), puede_convertir: false };
      montar();
      await irA("Ajustes de costo");
      await screen.findByRole("textbox", { name: /^FCAS/ });
      expect(screen.queryByRole("button", { name: "Convertir la moneda…" })).toBeNull();
    });
  });

  // --- 3e-3: el rev cambia con «Convertir la moneda» abierto (otra ventana) y la página no queda inerte ---------------------
  // Restaurar y cotizar se mudaron (Versiones y Mercado, con su 3e-3). Aquí queda convertir, que antes no estaba cubierto. A
  // diferencia de las pestañas de solo lectura (llevan `llave` y se vuelven a montar con cada `rev`), «Ajustes de costo» se
  // edita y lleva la `key` del borrador: un `rev` nuevo no la vuelve a montar y el diálogo sigue abierto, que es lo diseñado
  // (convertir parte de la versión GUARDADA, no del borrador). Si la otra ventana dejó cambios, el botón se va y el diálogo
  // con él.

  describe("3e-3: el rev cambia con «Convertir la moneda» abierto (otra ventana) y la página no queda [inert]", () => {
    const hacerQueElServidorTengaOtroRev = (cambios: number) => {
      const previa = fetchFalso.getMockImplementation();
      fetchFalso.mockImplementation(async (ruta, init) => {
        const url = new URL(String(ruta), "http://silice.local");
        if (url.pathname === `/v1/hoja/borradores/${ID}` && (init?.method ?? "GET") === "GET") {
          const b = borrador("002", { rev: 4, cambios });
          return json({ id: ID, base: b.base, resumen: b.resumen });
        }
        return previa!(ruta, init);
      });
    };
    const volverALaVentana = async () => {
      Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "visible" });
      await act(async () => {
        document.dispatchEvent(new Event("visibilitychange"));
      });
    };
    const relecturas = () => llamadas("GET", `/v1/hoja/borradores/${ID}`).length;

    test("sin cambios en la otra ventana: el diálogo sigue con lo escrito y, al cancelarlo, nada queda inerte", async () => {
      montar();
      await irA("Ajustes de costo");
      const dialogo = await abrirDialogo("Convertir la moneda…");
      escribir(dialogo, "Por qué se cambia la moneda (fuente)", "Pedido de la gerencia");
      expect(document.querySelector("[inert]")).not.toBeNull();
      const antes = relecturas();
      hacerQueElServidorTengaOtroRev(0);
      await volverALaVentana();
      await esperar(() => expect(relecturas()).toBeGreaterThan(antes));
      await act(async () => {
        await new Promise((r) => setTimeout(r, 30));
      });
      expect(screen.getByRole("dialog")).toBe(dialogo);
      expect(campo(dialogo, "Por qué se cambia la moneda (fuente)")).toHaveValue("Pedido de la gerencia");
      fireEvent.click(boton(dialogo, "Cancelar"));
      await esperar(() => expect(screen.queryByRole("dialog")).toBeNull());
      await esperar(() => expect(document.querySelector("[inert]")).toBeNull());
    });

    test("con cambios en la otra ventana: el botón se va, el diálogo se cierra con él y nada queda inerte ni se pierde el contador", async () => {
      montar();
      await irA("Ajustes de costo");
      await abrirDialogo("Convertir la moneda…");
      expect(document.querySelector("[inert]")).not.toBeNull();
      hacerQueElServidorTengaOtroRev(2);
      await volverALaVentana();
      expect(
        await screen.findByText("Cambiar la moneda crea una versión nueva desde la guardada: guarde o descarte primero los 2 cambios pendientes."),
      ).toBeInTheDocument();
      await esperar(() => expect(screen.queryByRole("dialog")).toBeNull());
      await esperar(() => expect(document.querySelector("[inert]")).toBeNull());
    });
  });

  // --- Estática ---------------------------------------------------------------------------------------------------------------

  test("los archivos de 3d-2 están bajo la prueba estática (sin Number, parseFloat, toFixed ni + unario)", () => {
    const fuentes = import.meta.glob("./*.{ts,tsx}", { query: "?raw", import: "default", eager: true }) as Record<string, string>;
    for (const ruta of [
      "./index.tsx",
      "./logicaVersiones.ts",
      "./DialogoDeOperacion.tsx",
      "./ConvertirMoneda.tsx",
      "./useOperacion.ts",
      "./useDialogoDeOperacion.ts",
      "./useGuardadoDeLaPagina.ts",
      "./useVersiones.ts",
      "./PestanaPrecios.tsx",
      "./PestanaParametros.tsx",
    ]) {
      expect(Object.keys(fuentes), ruta).toContain(ruta);
      expect(fuentes[ruta], ruta).not.toMatch(
        /\bNumber\s*\(|\bparseFloat\s*\(|\bparseInt\s*\(|\.toFixed\s*\(|(?:[=(,:?]|\breturn)\s*\+\s*[A-Za-z_$(]/,
      );
    }
  });
});
