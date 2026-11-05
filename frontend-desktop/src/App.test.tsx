import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "./api/cliente";
import { App } from "./App";
import oraculo from "../../tests/fixtures/replica/libro_minimo.json";
import type { LibroAuditadoRespuesta, LibroVisualRespuesta } from "./api/tipos";
import { crearHojaFalsa } from "./visor/hojaFalsa";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const sesion = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["leer_proyecto", "revisar_paquete", "aprobar_version", "cambiar_caso", "operar_arenera"],
  modo_entrega: false,
};

const casos = {
  actual: { nombre: "clinica", ruta_relativa: "data/clinica.db" },
  casos: [{ nombre: "clinica", ruta_relativa: "data/clinica.db" }],
};

describe("App", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  // Lo que contesta GET /v1/sesion; cada prueba lo cambia.
  let sesionActual: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf(null);
    window.location.hash = "";
    sesionActual = () => json(sesion);
    fetchFalso.mockImplementation(async (entrada, init) => {
      const ruta = String(entrada);
      const metodo = init?.method ?? "GET";
      if (ruta === "/v1/sesion" && metodo === "GET") return sesionActual();
      if (ruta === "/v1/sesion" && metodo === "DELETE") return new Response(null, { status: 204 });
      if (ruta === "/v1/casos") return json(casos);
      if (ruta === "/v1/proyectos") return json([]);
      // Lo que piden los inicios y Acerca, y el modulo recordado (MOD-1): sin esto caerian en el 401 de abajo y la
      // sesion se daria por vencida.
      if (ruta === "/v1/produccion/existencias") return json([]);
      // Lo que pide el marco (las obras de la barra lateral, el tema y la bandeja de Pendientes): sin esto caerian en el
      // 401 de abajo y la sesion se daria por vencida.
      if (ruta === "/v1/obras/todas") return json({ carpeta_actual: null, obras: [] });
      if (ruta === "/v1/obras/pendientes/todas") return json({ pendientes: [], carpetas_omitidas: 0 });
      if (ruta === "/v1/tema") return json({ acento: null, marco: null, lateral: null, tiene_logo: false, avisos: [] });
      if (metodo === "GET" && (ruta.startsWith("/v1/obras/") || ruta.startsWith("/v1/aprobaciones"))) {
        return json({ detalle: "No encontrado." }, 404);
      }
      if (ruta.startsWith("/v1/auditorias-libro")) return json([]);
      if (ruta === "/v1/acerca") return json({ detalle: "No encontrado." }, 404);
      if (ruta === "/v1/sesion/preferencias" && metodo === "PUT") return new Response(null, { status: 204 });
      return json({ detalle: "Sin sesión." }, 401);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("la cabecera dice Sílice", async () => {
    sesionActual = () => json({ detalle: "Sin sesión." }, 401);
    render(<App />);
    expect(screen.getByRole("banner")).toHaveTextContent("Sílice");
    await screen.findByRole("heading", { name: "Entrar" });
  });

  // Antes en Cabecera.test.tsx: la persona necesita leer la pantalla de entrada; sin sesion no hay cuenta ni menu.
  test("sin sesión la cabecera también trae el control de tamaño de letra, y no la cuenta ni el menú", async () => {
    sesionActual = () => json({ detalle: "Sin sesión." }, 401);
    render(<App />);
    await screen.findByRole("heading", { name: "Entrar" });
    const banner = screen.getByRole("banner");
    expect(within(banner).getByRole("group", { name: "Tamaño de letra" })).toBeInTheDocument();
    expect(within(banner).queryByRole("button", { name: /^Cuenta de/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Menú principal" })).not.toBeInTheDocument();
  });

  test("sin sesion muestra el formulario de entrada", async () => {
    sesionActual = () => json({ detalle: "Sin sesión." }, 401);
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.getByLabelText("Usuario")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Cuenta de/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Salir" })).not.toBeInTheDocument();
  });

  test("mientras comprueba la sesion no muestra el formulario", () => {
    fetchFalso.mockImplementation(() => new Promise<Response>(() => {}));
    render(<App />);
    expect(screen.queryByLabelText("Usuario")).not.toBeInTheDocument();
    expect(screen.getByText(/Comprobando su sesión/)).toBeInTheDocument();
  });

  test("con sesion vigente muestra el nombre, la cuenta con Salir, el marco y aterriza en Pendientes", async () => {
    const usuario = userEvent.setup();
    render(<App />);
    expect(await screen.findByText("Ana Pérez")).toBeInTheDocument();
    // El marco nuevo: buscador en la barra superior y la barra lateral con Pendientes, Obras y Empresa.
    const barra = screen.getByRole("banner");
    expect(within(barra).getByRole("button", { name: "Buscar una obra, sección o pantalla… (Ctrl+K)" })).toBeInTheDocument();
    const lateral = screen.getByRole("complementary", { name: "Barra lateral" });
    expect(within(lateral).getByRole("link", { name: "Pendientes" })).toHaveAttribute("href", "#/pendientes");
    expect(within(lateral).getByRole("navigation", { name: "Costos y producción" })).toBeInTheDocument();
    // Con la suite entera en marcha el marco tarda mas que el plazo por omision.
    expect(
      await screen.findByRole("heading", { level: 1, name: "Pendientes" }, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(window.location.hash).toBe("#/pendientes");
    // Ya no hay módulos ni nada que recordar de ellos.
    expect(screen.queryByRole("navigation", { name: "Menú principal" })).not.toBeInTheDocument();
    expect(fetchFalso.mock.calls.some((c) => String(c[0]) === "/v1/sesion/preferencias")).toBe(false);
    expect(screen.queryByRole("heading", { name: "Entrar" })).not.toBeInTheDocument();
    // La persona es un enlace a la Cuenta, donde está «Salir de la sesión».
    const persona = screen.getByRole("link", { name: "Cuenta de Ana Pérez" });
    expect(persona).toHaveAttribute("href", "#/cuenta/preferencias");
    await usuario.click(persona);
    expect(await screen.findByRole("button", { name: "Salir de la sesión" })).toBeInTheDocument();
  });

  // Cierre de F3 (H4): el color de la empresa vale en TODA la aplicacion, tambien antes de entrar. GET /v1/tema es
  // publico (no pide sesion), asi que se carga al arrancar y no solo dentro del marco. Colores inventados.
  describe("tema de la empresa", () => {
    const base = () => fetchFalso.getMockImplementation()!;
    const conTema = () => {
      const anterior = base();
      fetchFalso.mockImplementation(async (entrada, init) => {
        if (String(entrada) === "/v1/tema") {
          return json({ acento: "#123abc", marco: "#222222", lateral: null, tiene_logo: false, avisos: [] });
        }
        return anterior(entrada, init);
      });
    };
    const pedidosDelTema = () => fetchFalso.mock.calls.filter((c) => String(c[0]) === "/v1/tema").length;
    afterEach(() => {
      document.documentElement.removeAttribute("style");
    });

    test("la pantalla de entrada, sin sesion, aplica el tema", async () => {
      sesionActual = () => json({ detalle: "Sin sesión." }, 401);
      conTema();
      render(<App />);
      await screen.findByRole("heading", { name: "Entrar" });
      await waitFor(() => expect(document.documentElement.style.getPropertyValue("--silice-acento")).toBe("#123abc"));
      expect(document.documentElement.style.getPropertyValue("--silice-marco")).toBe("#222222");
    });

    test("con sesion el tema se pide una sola vez (el marco comparte el logo, no repite el pedido)", async () => {
      conTema();
      render(<App />);
      await screen.findByRole("complementary", { name: "Barra lateral" });
      await waitFor(() => expect(document.documentElement.style.getPropertyValue("--silice-acento")).toBe("#123abc"));
      expect(pedidosDelTema()).toBe(1);
    });
  });

  test("una direccion con #/libros abre esa pagina", async () => {
    window.location.hash = "#/libros";
    render(<App />);
    expect(
      await screen.findByRole("button", { name: /Suelte aquí el libro \.xlsx de la empresa/ }, { timeout: 5000 }),
    ).toBeInTheDocument();
  });

  test("una API anterior, sin acciones ni modo_entrega, no tumba la pantalla", async () => {
    sesionActual = () => json({ login: "ana", nombre: "Ana Pérez", roles: ["revisa"], csrf: "tok" });
    render(<App />);
    expect(await screen.findByText("Ana Pérez")).toBeInTheDocument();
    // Sin acciones aterriza en Pendientes, que toda cuenta ve.
    expect(
      await screen.findByRole("heading", { level: 1, name: "Pendientes" }, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(window.location.hash).toBe("#/pendientes");
    expect(screen.queryByRole("heading", { name: "Entrar" })).not.toBeInTheDocument();
  });

  test("entrar con una cuenta buena abre el shell y guarda el token solo en memoria", async () => {
    const usuario = userEvent.setup();
    const espia = vi.spyOn(Storage.prototype, "setItem");
    let entro = false;
    sesionActual = () => (entro ? json(sesion) : json({ detalle: "Sin sesión." }, 401));
    const base = fetchFalso.getMockImplementation()!;
    fetchFalso.mockImplementation(async (entrada, init) => {
      if (String(entrada) === "/v1/sesion" && init?.method === "POST") {
        entro = true;
        return json(sesion);
      }
      return base(entrada, init);
    });
    render(<App />);
    await usuario.type(await screen.findByLabelText("Usuario"), "ana");
    await usuario.type(screen.getByLabelText("Contraseña"), "clave");
    await usuario.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByText("Ana Pérez")).toBeInTheDocument();
    expect(espia).not.toHaveBeenCalled();
    espia.mockRestore();
  });

  test("Salir cierra la sesion con DELETE y vuelve al formulario", async () => {
    const usuario = userEvent.setup();
    render(<App />);
    await usuario.click(await screen.findByRole("link", { name: "Cuenta de Ana Pérez" }));
    await usuario.click(await screen.findByRole("button", { name: "Salir de la sesión" }));
    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
    const borrado = fetchFalso.mock.calls.find((c) => c[1]?.method === "DELETE");
    expect(new Headers(borrado?.[1]?.headers).get("X-Silice-CSRF")).toBe("tok");
  });

  describe("cambio de contrasena obligatorio", () => {
    const provisional = { ...sesion, debe_cambiar_clave: true, acciones: [] };

    test("con debe_cambiar_clave solo se ve el cambio de contrasena, sin menu ni pidiendo datos", async () => {
      sesionActual = () => json(provisional);
      render(<App />);
      expect(await screen.findByRole("heading", { name: "Cambie su contraseña" })).toBeInTheDocument();
      expect(screen.queryByRole("navigation", { name: "Menú principal" })).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Cuenta de Ana Pérez" })).toBeInTheDocument();
      expect(fetchFalso.mock.calls.some((c) => String(c[0]) === "/v1/casos")).toBe(false);
      expect(fetchFalso.mock.calls.some((c) => String(c[0]) === "/v1/proyectos")).toBe(false);
    });

    test("entrar con una cuenta provisional lleva al cambio", async () => {
      const usuario = userEvent.setup();
      sesionActual = () => json({ detalle: "Sin sesión." }, 401);
      const base = fetchFalso.getMockImplementation()!;
      fetchFalso.mockImplementation(async (entrada, init) => {
        if (String(entrada) === "/v1/sesion" && init?.method === "POST") return json(provisional);
        return base(entrada, init);
      });
      render(<App />);
      await usuario.type(await screen.findByLabelText("Usuario"), "ana");
      await usuario.type(screen.getByLabelText("Contraseña"), "provisional");
      await usuario.click(screen.getByRole("button", { name: "Entrar" }));
      expect(await screen.findByRole("heading", { name: "Cambie su contraseña" })).toBeInTheDocument();
    });

    test("al cambiarla manda actual y nueva con el token y entra al shell", async () => {
      const usuario = userEvent.setup();
      let cambiada = false;
      sesionActual = () => json(cambiada ? { ...sesion, csrf: "tok2" } : provisional);
      const base = fetchFalso.getMockImplementation()!;
      fetchFalso.mockImplementation(async (entrada, init) => {
        if (String(entrada) === "/v1/sesion/contrasena" && init?.method === "POST") {
          cambiada = true;
          return new Response(null, { status: 204 });
        }
        return base(entrada, init);
      });
      render(<App />);
      await usuario.type(await screen.findByLabelText("Contraseña actual"), "provisional");
      await usuario.type(screen.getByLabelText("Contraseña nueva"), "una-clave-larga-1");
      await usuario.type(screen.getByLabelText("Confirme la contraseña nueva"), "una-clave-larga-1");
      await usuario.click(screen.getByRole("button", { name: "Cambiar contraseña" }));

      expect(await screen.findByRole("complementary", { name: "Barra lateral" })).toBeInTheDocument();
      const llamada = fetchFalso.mock.calls.find((c) => String(c[0]) === "/v1/sesion/contrasena");
      expect(llamada?.[1]?.body).toBe(JSON.stringify({ actual: "provisional", nueva: "una-clave-larga-1" }));
      expect(new Headers(llamada?.[1]?.headers).get("X-Silice-CSRF")).toBe("tok");
      expect(screen.queryByRole("heading", { name: "Cambie su contraseña" })).not.toBeInTheDocument();
    });

    test("si la API rechaza la contrasena nueva sigue en el cambio y muestra el detalle", async () => {
      const usuario = userEvent.setup();
      sesionActual = () => json(provisional);
      const base = fetchFalso.getMockImplementation()!;
      fetchFalso.mockImplementation(async (entrada, init) => {
        if (String(entrada) === "/v1/sesion/contrasena") {
          return json({ detalle: "La contraseña nueva es demasiado corta." }, 422);
        }
        return base(entrada, init);
      });
      render(<App />);
      await usuario.type(await screen.findByLabelText("Contraseña actual"), "provisional");
      await usuario.type(screen.getByLabelText("Contraseña nueva"), "corta");
      await usuario.type(screen.getByLabelText("Confirme la contraseña nueva"), "corta");
      await usuario.click(screen.getByRole("button", { name: "Cambiar contraseña" }));
      expect(await screen.findByText("La contraseña nueva es demasiado corta.")).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Cambie su contraseña" })).toBeInTheDocument();
    });
  });

  describe("Libro de la empresa dentro del shell", () => {
    const replica = { ...oraculo, sha256: "a".repeat(64) } as unknown as LibroVisualRespuesta;
    const auditoria: LibroAuditadoRespuesta = {
      libro: { nombre: "libro_minimo.xlsx", sha256: "a".repeat(64) },
      fecha_libro: null,
      fecha_devolucion: "2026-10-18",
      cumple: false,
      por_severidad: { CRITICO: 1, ERROR: 1, ADVERTENCIA: 0, INFO: 0 },
      totales_libro: {},
      totales_silice: {},
      hallazgos: [
        { codigo: "L3", severidad: "CRITICO", descripcion: "El total no coincide", celda: "PLAN DE PAGOS!F12", impacto: null, accion: "x" },
        { codigo: "L5", severidad: "ERROR", descripcion: "Precio distinto al de INSUMOS", celda: "PORTADA!B2", impacto: null, accion: "x" },
      ],
      indicadores: [],
    };

    let sesionDeLibro = sesion;
    let vencida = false;
    let llamadasReplica = 0;

    function prepararApi() {
      sesionDeLibro = sesion;
      vencida = false;
      llamadasReplica = 0;
      window.location.hash = "#/libros";
      fetchFalso.mockImplementation(async (entrada, init) => {
        const ruta = String(entrada);
        const metodo = init?.method ?? "GET";
        if (ruta === "/v1/sesion" && metodo === "POST") {
          vencida = false;
          return json(sesionDeLibro);
        }
        if (ruta === "/v1/sesion" && metodo === "DELETE") return new Response(null, { status: 204 });
        if (ruta === "/v1/sesion") return vencida ? json({ detalle: "Sin sesión." }, 401) : json(sesionDeLibro);
        if (vencida) return json({ detalle: "Su sesión venció." }, 401);
        if (ruta === "/v1/casos") return json(casos);
        if (ruta === "/v1/proyectos") return json([]);
        if (ruta.endsWith("/replica")) {
          llamadasReplica += 1;
          return json(replica);
        }
        if (ruta.endsWith("/auditoria")) return json(auditoria);
        return json({ detalle: "ruta inesperada" }, 404);
      });
    }

    const libroXlsx = () =>
      new File([new Uint8Array([80, 75, 3, 4])], "libro_minimo.xlsx", {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });

    async function subirLibro(usuario: ReturnType<typeof userEvent.setup>) {
      const entrada = (await waitForInput()) as HTMLInputElement;
      await usuario.upload(entrada, libroXlsx());
      await screen.findByText("El total no coincide", {}, { timeout: 5000 });
    }

    async function waitForInput(): Promise<Element> {
      await screen.findByRole("button", { name: /Suelte aquí el libro \.xlsx de la empresa/ }, { timeout: 5000 });
      return document.querySelector('input[type="file"]') as Element;
    }

    async function cargarYVencer(usuario: ReturnType<typeof userEvent.setup>, hoja: ReturnType<typeof crearHojaFalsa>) {
      render(<App crearHoja={async () => hoja} />);
      await screen.findByText("Ana Pérez");
      await subirLibro(usuario);
      // El auditor elige una hoja y filtra por Critico.
      await usuario.click(await screen.findByRole("tab", { name: /^PLAN DE PAGOS/ }));
      await usuario.click(screen.getByRole("button", { name: /^Crítico/ }));
      // La sesion vence: la siguiente llamada (cambiar la fecha vuelve a auditar) da 401.
      vencida = true;
      const fecha = screen.getByLabelText("Fecha de devolución");
      await usuario.clear(fecha);
      await usuario.type(fecha, "2026-12-01");
      await screen.findByRole("heading", { name: "Entrar" });
    }

    async function volverAEntrar(usuario: ReturnType<typeof userEvent.setup>) {
      await usuario.type(screen.getByLabelText("Usuario"), "x");
      await usuario.type(screen.getByLabelText("Contraseña"), "clave");
      await usuario.click(screen.getByRole("button", { name: "Entrar" }));
    }

    test("la fecha de devolucion, el libro y Cambiar libro van en el cuerpo de la pagina, no en la cabecera (V-24)", async () => {
      const usuario = userEvent.setup();
      prepararApi();
      render(<App crearHoja={async () => crearHojaFalsa("PORTADA")} />);
      await screen.findByText("Ana Pérez");
      const cabecera = screen.getByRole("banner");
      const fecha = await screen.findByLabelText("Fecha de devolución");
      expect(cabecera).not.toContainElement(fecha);
      await subirLibro(usuario);
      expect(within(cabecera).queryByText("libro_minimo.xlsx")).toBeNull();
      expect(document.querySelector(".visor__barra")).toContainElement(screen.getByText("libro_minimo.xlsx"));
    });

    test("fuera de Libro de la empresa la cabecera no lleva los controles del libro", async () => {
      prepararApi();
      window.location.hash = "#/acerca";
      render(<App crearHoja={async () => crearHojaFalsa("PORTADA")} />);
      await screen.findByText("Ana Pérez");
      expect(screen.queryByLabelText("Fecha de devolución")).toBeNull();
    });

    test("un 401 muestra la entrada con el aviso Su sesion vencio", async () => {
      const usuario = userEvent.setup();
      prepararApi();
      await cargarYVencer(usuario, crearHojaFalsa("PORTADA"));
      expect(screen.getByText(/Su sesión venció/)).toBeInTheDocument();
    });

    test("401, entrar con la misma cuenta: el libro sigue, sin pedirlo otra vez (UC-26)", async () => {
      const usuario = userEvent.setup();
      prepararApi();
      const hoja = crearHojaFalsa("PORTADA");
      await cargarYVencer(usuario, hoja);
      await volverAEntrar(usuario);
      expect(await screen.findByText("El total no coincide", {}, { timeout: 5000 })).toBeInTheDocument();
      // El libro no se vuelve a pedir ni a subir.
      expect(llamadasReplica).toBe(1);
      // La hoja que se veia y el filtro siguen como estaban.
      expect(hoja.irAHoja).toHaveBeenCalledWith("PLAN DE PAGOS");
      expect(screen.queryByText("Precio distinto al de INSUMOS")).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: /^Crítico/ })).toHaveAttribute("aria-pressed", "true");
      expect(screen.getByText("libro_minimo.xlsx")).toBeInTheDocument();
    });

    test("si entra otra cuenta, el libro se descarta", async () => {
      const usuario = userEvent.setup();
      prepararApi();
      await cargarYVencer(usuario, crearHojaFalsa("PORTADA"));
      sesionDeLibro = { ...sesion, login: "otra", nombre: "Otra Persona" };
      await volverAEntrar(usuario);
      expect(await screen.findByText("Otra Persona")).toBeInTheDocument();
      expect(screen.queryByText("El total no coincide")).not.toBeInTheDocument();
      expect(
        await screen.findByRole("button", { name: /Suelte aquí el libro \.xlsx de la empresa/ }, { timeout: 5000 }),
      ).toBeInTheDocument();
    });

    test("Salir a proposito tambien descarta el libro", async () => {
      const usuario = userEvent.setup();
      prepararApi();
      render(<App crearHoja={async () => crearHojaFalsa("PORTADA")} />);
      await screen.findByText("Ana Pérez");
      await subirLibro(usuario);
      await usuario.click(screen.getByRole("link", { name: "Cuenta de Ana Pérez" }));
      await usuario.click(await screen.findByRole("button", { name: "Salir de la sesión" }));
      await screen.findByRole("heading", { name: "Entrar" });
      await volverAEntrar(usuario);
      await screen.findByText("Ana Pérez");
      expect(screen.queryByText("El total no coincide")).not.toBeInTheDocument();
    });

    test("el libro solo vive en memoria: nada va a localStorage ni sessionStorage", async () => {
      const usuario = userEvent.setup();
      const espia = vi.spyOn(Storage.prototype, "setItem");
      prepararApi();
      await cargarYVencer(usuario, crearHojaFalsa("PORTADA"));
      await volverAEntrar(usuario);
      await screen.findByText("El total no coincide", {}, { timeout: 5000 });
      expect(espia).not.toHaveBeenCalled();
      espia.mockRestore();
    });
  });
});
