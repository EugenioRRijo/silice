import { act, configure, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { atipicosRespuesta, cuerpoDeVista, preciosRespuesta, vistaParametros } from "./datosDePrueba";
import PaginaHoja from "./index";
import { versionAbierta } from "./rutaDePrueba";
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

    test("Precios: ni cotizar ni retirar; dice cuántos cambios hay (P:1946)", async () => {
      montar();
      await irA("Precios");
      await screen.findByRole("table", { name: "Precios" });
      expect(
        screen.getByText("Cotizar crea una versión nueva desde la guardada: guarde o descarte primero los 3 cambios pendientes."),
      ).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Registrar una cotización…" })).toBeNull();
      expect(screen.queryByRole("button", { name: "Retirar una cotización…" })).toBeNull();
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

    test("al descartar los cambios (sin cambios) las acciones aparecen", async () => {
      cambiosSinGuardar = 0;
      montar();
      await irA("Precios");
      expect(await screen.findByRole("button", { name: "Registrar una cotización…" })).toBeInTheDocument();
    });
  });

  // --- 3d-F6: cotizar -------------------------------------------------------------------------------------------------------

  describe("3d-F6: registrar una cotización (S3)", () => {
    const abrir = async () => {
      montar();
      await irA("Precios");
      return abrirDialogo("Registrar una cotización…");
    };
    const llenar = (dialogo: HTMLElement) => {
      fireEvent.change(within(dialogo).getByRole("combobox", { name: "Insumo" }), { target: { value: "MAT-001" } });
      escribir(dialogo, "Precio cotizado", "1.003,50");
      escribir(dialogo, "Proveedor", "Ferretería Demo, C.A.");
      escribir(dialogo, "Número de la cotización", "COT-18");
      fireEvent.change(campo(dialogo, "Fecha de la cotización"), { target: { value: "2026-10-18" } });
    };

    test("es un diálogo con foco adentro, el resto inerte, sus campos y el responsable de solo lectura", async () => {
      const dialogo = await abrir();
      expect(dialogo).toHaveAttribute("aria-modal", "true");
      expect(dialogo).toHaveAccessibleName("Registrar una cotización");
      expect(dialogo.contains(document.activeElement)).toBe(true);
      expect(dialogo.closest("[inert]")).toBeNull();
      expect(screen.getByRole("tab", { name: "Precios", hidden: true }).closest("[inert]")).not.toBeNull();
      const insumo = within(dialogo).getByRole("combobox", { name: "Insumo" });
      expect(insumo).toHaveFocus();
      expect(within(dialogo).getAllByRole("option").map((o) => o.textContent)).toEqual([
        "MAT-001 · Tubo PVC 1/2",
        "MAT-002 · Llave de paso",
      ]);
      for (const nombre of ["Precio cotizado", "Proveedor", "Número de la cotización", "Fecha de la cotización", "Evidencia (opcional: archivo, enlace, nota)"]) {
        expect(campo(dialogo, nombre)).toBeInTheDocument();
      }
      // La fecha por omisión es hoy (como `date.today()` de la clásica), AAAA-MM-DD.
      expect(campo(dialogo, "Fecha de la cotización")).toHaveValue(new Date().toLocaleDateString("en-CA"));
      expect(campo(dialogo, "Fecha de la cotización")).toHaveAttribute("type", "date");
      expect(within(dialogo).getByText("Responsable: Ana Pérez <ana>")).toBeInTheDocument();
      // La ayuda del precio dice la regla de las cifras (Eugenio, 2026-10-25), no «Decimales con punto».
      expect(within(dialogo).getByText("Escriba los decimales con coma: 2,5; el punto separa los miles: 1.234,56.")).toBeInTheDocument();
      expect(within(dialogo).queryByRole("textbox", { name: /Responsable/ })).toBeNull();
    });

    test("falta algo: «Cotizar» queda deshabilitado y dice qué falta, en el orden del formulario", async () => {
      const dialogo = await abrir();
      const cotizar = boton(dialogo, "Cotizar");
      expect(cotizar).toBeDisabled();
      expect(within(dialogo).getByText("Escriba el precio cotizado.")).toBeInTheDocument();
      expect(cotizar).toHaveAccessibleDescription("Escriba el precio cotizado.");
      escribir(dialogo, "Precio cotizado", "1.003,50");
      expect(within(dialogo).getByText("Escriba el proveedor de la cotización.")).toBeInTheDocument();
      escribir(dialogo, "Proveedor", "Ferretería Demo, C.A.");
      expect(within(dialogo).getByText("Escriba el número de la cotización.")).toBeInTheDocument();
      escribir(dialogo, "Número de la cotización", "COT-18");
      expect(cotizar).toBeEnabled();
    });

    test("manda el precio como texto, sin responsable, y la evidencia vacía como null; dice el mensaje del servidor y abre la 003", async () => {
      alOperacion = () => json({ codigo: "003", proyecto: "OF-001", mensaje: "Se guardó la versión 003 con la cotización de MAT-001." });
      const dialogo = await abrir();
      llenar(dialogo);
      versiones = VERSIONES_CON_003;
      fireEvent.click(boton(dialogo, "Cotizar"));
      expect(await screen.findByText("Se guardó la versión 003 con la cotización de MAT-001.")).toBeInTheDocument();
      expect(enviados("/cotizar")).toEqual([
        {
          proyecto: "OF-001",
          version: "002",
          insumo: "MAT-001",
          precio: "1.003,50", // tal cual: lo lee el servidor (coma decimal, punto de miles)
          proveedor: "Ferretería Demo, C.A.",
          numero: "COT-18",
          fecha: "2026-10-18",
          evidencia: null,
        },
      ]);
      expect(typeof enviados("/cotizar")[0]!["precio"]).toBe("string");
      await esperar(() => expect(aperturas().map((a) => a.version)).toEqual(["002", "003"]));
      await esperar(() => expect(versionAbierta()).toBe("003"));
      expect(screen.queryByRole("dialog")).toBeNull();
      // La lista de versiones se volvió a pedir y el foco queda en el selector de versión.
      await esperar(() => expect(screen.getByRole("heading", { level: 1, name: "Presupuesto" })).toHaveFocus());
    });

    test("con evidencia, la manda tal cual", async () => {
      const dialogo = await abrir();
      llenar(dialogo);
      escribir(dialogo, /^Evidencia/, "correo del 18");
      fireEvent.click(boton(dialogo, "Cotizar"));
      await esperar(() => expect(enviados("/cotizar")).toHaveLength(1));
      expect(enviados("/cotizar")[0]!["evidencia"]).toBe("correo del 18");
    });

    test("un precio inválido (422): el texto del servidor tal cual, el diálogo sigue abierto y no se pierde lo escrito", async () => {
      alOperacion = () => json({ detalle: "precio: 'tres' no es un numero decimal valido" }, 422);
      const dialogo = await abrir();
      llenar(dialogo);
      escribir(dialogo, "Precio cotizado", "tres");
      fireEvent.click(boton(dialogo, "Cotizar"));
      const alerta = await within(dialogo).findByRole("alert");
      expect(within(alerta).getByText("No se guardó nada")).toBeInTheDocument();
      expect(within(alerta).getByText("precio: 'tres' no es un numero decimal valido")).toBeInTheDocument();
      expect(screen.getByRole("dialog")).toBe(dialogo);
      expect(campo(dialogo, "Precio cotizado")).toHaveValue("tres");
      expect(campo(dialogo, "Proveedor")).toHaveValue("Ferretería Demo, C.A.");
      expect(boton(dialogo, "Cotizar")).toBeEnabled(); // se puede corregir y reintentar
      expect(aperturas().map((a) => a.version)).toEqual(["002"]); // no se abrió nada
    });

    test.each([
      [404, "El proyecto «OF-001» no existe en este caso."],
      [409, "No se guardó nada: la composición de la partida AF-LLAVE ya no está vigente."],
      [403, "Su cuenta no tiene permiso para esta acción."],
      [503, "No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro programa."],
    ])("un %i muestra el texto del servidor tal cual y no cierra el diálogo", async (estado, detalle) => {
      alOperacion = () => json({ detalle }, estado);
      const dialogo = await abrir();
      llenar(dialogo);
      fireEvent.click(boton(dialogo, "Cotizar"));
      expect(await within(dialogo).findByText(detalle)).toBeInTheDocument();
      expect(screen.getByRole("dialog")).toBe(dialogo);
    });

    test("un 401 avisa al marco para que pida la sesión de nuevo", async () => {
      alOperacion = () => json({ detalle: "Sesión vencida." }, 401);
      const dialogo = await abrir();
      llenar(dialogo);
      fireEvent.click(boton(dialogo, "Cotizar"));
      await esperar(() => expect(alExpirar).toHaveBeenCalled());
    });

    test("una sola petición en vuelo: todo queda deshabilitado, Esc no cierra y el error no se pierde", async () => {
      let contestar: (r: Response) => void = () => undefined;
      alOperacion = () =>
        new Promise<Response>((resolver) => {
          contestar = resolver;
        });
      const dialogo = await abrir();
      llenar(dialogo);
      const cotizar = boton(dialogo, "Cotizar");
      fireEvent.click(cotizar);
      await esperar(() => expect(enviados("/cotizar")).toHaveLength(1));
      expect(cotizar).toBeDisabled();
      expect(boton(dialogo, "Cancelar")).toBeDisabled();
      fireEvent.click(cotizar);
      await userEvent.keyboard("{Escape}");
      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(within(dialogo).getByText("Guardando la versión…").closest("[aria-live='polite']")).not.toBeNull();
      await act(async () => contestar(json({ detalle: "precio: '' no es un numero decimal valido" }, 422)));
      expect(await within(screen.getByRole("dialog")).findByText("precio: '' no es un numero decimal valido")).toBeInTheDocument();
      expect(enviados("/cotizar")).toHaveLength(1);
      await userEvent.keyboard("{Escape}");
      expect(screen.queryByRole("dialog")).toBeNull();
    });

    test.each([
      ["Esc", async () => userEvent.keyboard("{Escape}")],
      ["Cancelar", async () => fireEvent.click(await screen.findByRole("button", { name: "Cancelar" }))],
    ])("%s cierra sin enviar y el foco vuelve al botón DESPUÉS de quitar el inert", async (_n, cerrar) => {
      await abrir();
      const enfocados: Array<{ inerte: boolean }> = [];
      const original = HTMLElement.prototype.focus;
      HTMLElement.prototype.focus = function (this: HTMLElement, ...args: Parameters<HTMLElement["focus"]>) {
        if (this.textContent === "Registrar una cotización…") enfocados.push({ inerte: this.closest("[inert]") !== null });
        return original.apply(this, args);
      };
      try {
        await cerrar();
        await esperar(() => expect(enfocados.length).toBeGreaterThan(0));
        expect(enfocados.every((e) => !e.inerte)).toBe(true);
      } finally {
        HTMLElement.prototype.focus = original;
      }
      expect(screen.queryByRole("dialog")).toBeNull();
      expect(screen.getByRole("button", { name: "Registrar una cotización…" })).toHaveFocus();
      expect(enviados("/cotizar")).toHaveLength(0);
      expect(document.querySelector("[inert]")).toBeNull();
    });

    test("Tab no sale del diálogo y Mayús+Tab hace lo inverso", async () => {
      const dialogo = await abrir();
      llenar(dialogo);
      const u = userEvent.setup({ delay: null });
      const cotizar = boton(dialogo, "Cotizar");
      cotizar.focus();
      await u.tab();
      expect(within(dialogo).getByRole("combobox", { name: "Insumo" })).toHaveFocus();
      await u.tab({ shift: true });
      expect(cotizar).toHaveFocus();
    });
  });

  // --- 3d-F6: retirar -------------------------------------------------------------------------------------------------------

  describe("3d-F6: retirar una cotización (S4)", () => {
    test("solo se ofrece si algún insumo tiene cotización", async () => {
      precios = preciosRespuesta();
      montar();
      await irA("Precios");
      await screen.findByRole("button", { name: "Registrar una cotización…" });
      expect(screen.queryByRole("button", { name: "Retirar una cotización…" })).toBeNull();
    });

    test("ofrece los insumos cotizados, pide el motivo y manda insumo y motivo (sin responsable)", async () => {
      alOperacion = () => json({ codigo: "003", proyecto: "OF-001", mensaje: "Se guardó la versión 003 sin la cotización." });
      montar();
      await irA("Precios");
      const dialogo = await abrirDialogo("Retirar una cotización…");
      expect(dialogo).toHaveAccessibleName("Retirar una cotización");
      expect(within(dialogo).getAllByRole("option").map((o) => o.textContent)).toEqual(["MAT-002 · Llave de paso (COT-17 · Ferretería Demo)"]);
      expect(within(dialogo).getByRole("combobox", { name: "Insumo cotizado" })).toHaveFocus();
      const retirar = boton(dialogo, "Retirar cotización");
      expect(retirar).toBeDisabled();
      expect(within(dialogo).getByText("Escriba por qué se retira la cotización.")).toBeInTheDocument();
      escribir(dialogo, "Por qué se retira", "La cotización venció");
      expect(retirar).toBeEnabled();
      versiones = VERSIONES_CON_003;
      fireEvent.click(retirar);
      expect(await screen.findByText("Se guardó la versión 003 sin la cotización.")).toBeInTheDocument();
      expect(enviados("/retirar-cotizacion")).toEqual([{ proyecto: "OF-001", version: "002", insumo: "MAT-002", motivo: "La cotización venció" }]);
      await esperar(() => expect(aperturas().map((a) => a.version)).toEqual(["002", "003"]));
    });

    test("un 422 del servidor se muestra tal cual con el título «No se guardó nada»", async () => {
      alOperacion = () => json({ detalle: "la version '002' no tiene cotizacion del insumo MAT-002" }, 422);
      montar();
      await irA("Precios");
      const dialogo = await abrirDialogo("Retirar una cotización…");
      escribir(dialogo, "Por qué se retira", "venció");
      fireEvent.click(boton(dialogo, "Retirar cotización"));
      const alerta = await within(dialogo).findByRole("alert");
      expect(within(alerta).getByText("No se guardó nada")).toBeInTheDocument();
      expect(within(alerta).getByText("la version '002' no tiene cotizacion del insumo MAT-002")).toBeInTheDocument();
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

  // --- 3e-3: un diálogo abierto cuyo panel se vuelve a montar por un cambio de rev no deja la página inerte ----------------

  describe("3e-3: el rev cambia con un diálogo abierto (otra ventana) y la página no queda [inert]", () => {
    const hacerQueElServidorTengaOtroRev = () => {
      const previa = fetchFalso.getMockImplementation();
      fetchFalso.mockImplementation(async (ruta, init) => {
        const url = new URL(String(ruta), "http://silice.local");
        if (url.pathname === `/v1/hoja/borradores/${ID}` && (init?.method ?? "GET") === "GET") {
          const b = borrador("002", { rev: 4, cambios: 0 });
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

    test.each([
      ["Precios", "Registrar una cotización…", "Registrar una cotización"],
    ])("%s: el diálogo se cierra con el panel y nada queda inerte ni se pierde el contador", async (pestana, boton, nombre) => {
      montar();
      await irA(pestana);
      const dialogo = await abrirDialogo(boton);
      expect(dialogo).toHaveAccessibleName(nombre);
      expect(document.querySelector("[inert]")).not.toBeNull();
      hacerQueElServidorTengaOtroRev();
      await volverALaVentana();
      await esperar(() => expect(screen.queryByRole("dialog")).toBeNull());
      await esperar(() => expect(document.querySelector("[inert]")).toBeNull());
      // la página sigue usable: el mismo botón abre otro diálogo y Cancelar vuelve a dejarla libre
      const otro = await abrirDialogo(boton);
      expect(otro.closest("[inert]")).toBeNull();
      fireEvent.click(await screen.findByRole("button", { name: "Cancelar" }));
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
      "./OperacionesDePrecios.tsx",
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
