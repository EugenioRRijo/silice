import { render, screen } from "@testing-library/react";
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

const sesion = { login: "ana", nombre: "Ana Pérez", roles: ["revisa"], csrf: "tok" };

describe("App", () => {
  const fetchFalso = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf(null);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("la cabecera dice Sílice", async () => {
    fetchFalso.mockImplementation(async () => json({ detalle: "Sin sesión." }, 401));
    render(<App />);
    expect(screen.getByRole("banner")).toHaveTextContent("Sílice");
    await screen.findByRole("heading", { name: "Entrar" });
  });

  test("sin sesion muestra el formulario de entrada", async () => {
    fetchFalso.mockImplementation(async () => json({ detalle: "Sin sesión." }, 401));
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.getByLabelText("Usuario")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Salir" })).not.toBeInTheDocument();
  });

  test("mientras comprueba la sesion no muestra el formulario", () => {
    fetchFalso.mockImplementation(() => new Promise<Response>(() => {}));
    render(<App />);
    expect(screen.queryByLabelText("Usuario")).not.toBeInTheDocument();
    expect(screen.getByText(/Comprobando su sesión/)).toBeInTheDocument();
  });

  test("con sesion vigente muestra el nombre, Salir y el visor", async () => {
    fetchFalso.mockImplementation(async () => json(sesion));
    render(<App />);
    expect(await screen.findByText("Ana Pérez")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salir" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Suelte aquí el libro \.xlsx de la empresa/ })).toBeInTheDocument();
  });

  test("entrar con una cuenta buena abre el visor y guarda el token solo en memoria", async () => {
    const usuario = userEvent.setup();
    const espia = vi.spyOn(Storage.prototype, "setItem");
    fetchFalso.mockImplementation(async (entrada, init) => {
      if (String(entrada) === "/v1/sesion" && init?.method === "POST") return json(sesion);
      return json({ detalle: "Sin sesión." }, 401);
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
    fetchFalso.mockImplementation(async (_entrada, init) => {
      if (init?.method === "DELETE") return new Response(null, { status: 204 });
      return json(sesion);
    });
    render(<App />);
    await usuario.click(await screen.findByRole("button", { name: "Salir" }));
    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
    const borrado = fetchFalso.mock.calls.find((c) => c[1]?.method === "DELETE");
    expect(new Headers(borrado?.[1]?.headers).get("X-Silice-CSRF")).toBe("tok");
  });

  describe("la sesion vencida no pierde el libro (UC-26)", () => {
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

    let sesionActual = sesion;
    let vencida = false;
    let llamadasReplica = 0;

    function prepararApi() {
      sesionActual = sesion;
      vencida = false;
      llamadasReplica = 0;
      fetchFalso.mockImplementation(async (entrada, init) => {
        const ruta = String(entrada);
        if (ruta === "/v1/sesion" && init?.method === "POST") {
          vencida = false;
          return json(sesionActual);
        }
        if (ruta === "/v1/sesion" && init?.method === "DELETE") return new Response(null, { status: 204 });
        if (ruta === "/v1/sesion") return vencida ? json({ detalle: "Sin sesión." }, 401) : json(sesionActual);
        if (vencida) return json({ detalle: "Su sesión venció." }, 401);
        if (ruta.endsWith("/replica")) {
          llamadasReplica += 1;
          return json(replica);
        }
        if (ruta.endsWith("/auditoria")) return json(auditoria);
        return json({ detalle: "ruta inesperada" }, 404);
      });
    }

    async function cargarYVencer(usuario: ReturnType<typeof userEvent.setup>, hoja: ReturnType<typeof crearHojaFalsa>) {
      render(<App crearHoja={async () => hoja} />);
      await screen.findByText("Ana Pérez");
      const entrada = document.querySelector('input[type="file"]') as HTMLInputElement;
      await usuario.upload(
        entrada,
        new File([new Uint8Array([80, 75, 3, 4])], "libro_minimo.xlsx", {
          type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }),
      );
      await screen.findByText("El total no coincide");
      // El auditor elige una hoja y filtra por Critico.
      await usuario.click(await screen.findByRole("tab", { name: "PLAN DE PAGOS" }));
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

    test("un 401 muestra la entrada con el aviso Su sesion vencio", async () => {
      const usuario = userEvent.setup();
      prepararApi();
      await cargarYVencer(usuario, crearHojaFalsa("PORTADA"));
      expect(screen.getByText(/Su sesión venció/)).toBeInTheDocument();
    });

    test("al entrar con la misma cuenta el visor reaparece tal cual, sin pedir otra vez el libro", async () => {
      const usuario = userEvent.setup();
      prepararApi();
      const hoja = crearHojaFalsa("PORTADA");
      await cargarYVencer(usuario, hoja);
      await volverAEntrar(usuario);
      expect(await screen.findByText("El total no coincide")).toBeInTheDocument();
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
      sesionActual = { ...sesion, login: "otra", nombre: "Otra Persona" };
      await volverAEntrar(usuario);
      expect(await screen.findByText("Otra Persona")).toBeInTheDocument();
      expect(screen.queryByText("El total no coincide")).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Suelte aquí el libro \.xlsx de la empresa/ })).toBeInTheDocument();
    });

    test("Salir a proposito tambien descarta el libro", async () => {
      const usuario = userEvent.setup();
      prepararApi();
      render(<App crearHoja={async () => crearHojaFalsa("PORTADA")} />);
      await screen.findByText("Ana Pérez");
      const entrada = document.querySelector('input[type="file"]') as HTMLInputElement;
      await usuario.upload(entrada, new File([new Uint8Array([80, 75, 3, 4])], "libro_minimo.xlsx"));
      await screen.findByText("El total no coincide");
      await usuario.click(screen.getByRole("button", { name: "Salir" }));
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
      await screen.findByText("El total no coincide");
      expect(espia).not.toHaveBeenCalled();
      espia.mockRestore();
    });
  });
});
