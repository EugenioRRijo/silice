import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import { RECORRIDO_AUDITAR, iniciarRecorrido, recorridoEnCurso, terminarRecorrido } from "../../shell/recorrido";
import type { Aplicacion } from "../../shell/contexto";
import { tomarArchivoPendiente } from "../inicio/archivoPendiente";
import PaginaAuditoria from "./index";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { "Content-Type": "application/json" },
  });
}

// Quien arma (seguridad/permisos.py): audita y opera la arenera.
const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "leer_proyecto", "operar_arenera"],
  modo_entrega: false,
};

function auditoria(id: number, parcial: Record<string, unknown> = {}) {
  return {
    id,
    archivo: `presupuesto-${id}.xlsx`,
    fecha: "2026-10-18T14:32:00",
    tipo: "libro",
    errores: 2,
    advertencias: 5,
    ...parcial,
  };
}

describe("Inicio de auditoría", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let auditorias: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    auditorias = () => json([]);
    fetchFalso.mockImplementation(async (entrada) => {
      const ruta = String(entrada);
      if (ruta === "/v1/auditorias-libro?limite=5") return auditorias();
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    tomarArchivoPendiente();
    terminarRecorrido();
  });

  function montar(aplicacion: Partial<Aplicacion> = {}) {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: { nombre: "clinica", ruta_relativa: "data/clinica.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
      modulo: "auditoria",
      ...aplicacion,
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter initialEntries={["/auditoria"]}>
          <Routes>
            <Route path="/auditoria" element={<PaginaAuditoria />} />
            <Route path="/libros" element={<h1>Pantalla del libro</h1>} />
          </Routes>
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  function campoArchivo(): HTMLInputElement {
    return document.querySelector('input[type="file"]') as HTMLInputElement;
  }

  function rutasPedidas(): string[] {
    return fetchFalso.mock.calls.map((c) => String(c[0]));
  }

  test("su h1 es «Inicio de auditoría» y no trae «Herramientas principales» ni la arenera", async () => {
    montar();
    expect(screen.getByRole("heading", { level: 1, name: "Inicio de auditoría" })).toHaveClass("cds--type-heading-04");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.queryByText("Herramientas principales")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Arenera: lo que requiere atención" })).not.toBeInTheDocument();
    await waitFor(() => expect(rutasPedidas()).toContain("/v1/auditorias-libro?limite=5"));
    // La arenera vive en el inicio de Producción: aquí no se pide aunque la cuenta la opere.
    expect(rutasPedidas()).not.toContain("/v1/produccion/existencias");
  });

  describe("zona del Excel", () => {
    test("dice qué se hace con el libro y que no se guarda", () => {
      montar();
      expect(screen.getByRole("heading", { name: "Audite un presupuesto" })).toBeInTheDocument();
      expect(screen.getByText(/no se guarda/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Suelte aquí el libro \.xlsx/ })).toBeInTheDocument();
    });

    test("sin archivo no hay botones de auditar", () => {
      montar();
      expect(screen.queryByRole("button", { name: "Auditar con recorrido guiado" })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Auditar por mi cuenta" })).not.toBeInTheDocument();
    });

    test("con un archivo aparecen sus dos botones y el nombre del archivo", async () => {
      const usuario = userEvent.setup();
      montar();
      await usuario.upload(campoArchivo(), new File(["x"], "obra-norte.xlsx"));
      expect(screen.getByRole("status")).toHaveTextContent("Archivo elegido: obra-norte.xlsx");
      expect(screen.getByRole("button", { name: "Auditar con recorrido guiado" })).toBeEnabled();
      expect(screen.getByRole("button", { name: "Auditar por mi cuenta" })).toBeEnabled();
    });

    test("«Auditar con recorrido guiado» deja el archivo en modo guiado, pone en curso el recorrido y lleva al libro", async () => {
      const usuario = userEvent.setup();
      montar();
      const archivo = new File(["x"], "obra-norte.xlsx");
      expect(recorridoEnCurso()).toBeNull();
      await usuario.upload(campoArchivo(), archivo);
      await usuario.click(screen.getByRole("button", { name: "Auditar con recorrido guiado" }));
      expect(await screen.findByRole("heading", { name: "Pantalla del libro" })).toBeInTheDocument();
      const pendiente = tomarArchivoPendiente();
      expect(pendiente?.archivo).toBe(archivo);
      expect(pendiente?.modo).toBe("guiado");
      expect(recorridoEnCurso()).toBe(RECORRIDO_AUDITAR);
    });

    test("«Auditar por mi cuenta» lo deja en modo propio y lleva al libro, sin recorrido", async () => {
      const usuario = userEvent.setup();
      montar();
      const archivo = new File(["x"], "obra-norte.xlsx");
      await usuario.upload(campoArchivo(), archivo);
      await usuario.click(screen.getByRole("button", { name: "Auditar por mi cuenta" }));
      expect(await screen.findByRole("heading", { name: "Pantalla del libro" })).toBeInTheDocument();
      const pendiente = tomarArchivoPendiente();
      expect(pendiente?.archivo).toBe(archivo);
      expect(pendiente?.modo).toBe("propio");
      expect(recorridoEnCurso()).toBeNull();
    });

    test("un archivo inválido elegido después de uno válido deja intacto el anterior", async () => {
      const usuario = userEvent.setup({ applyAccept: false });
      montar();
      const archivo = new File(["x"], "obra-norte.xlsx");
      await usuario.upload(campoArchivo(), archivo);
      await usuario.upload(campoArchivo(), new File(["x"], "foto.png"));
      expect(screen.getByRole("status")).toHaveTextContent("Archivo elegido: obra-norte.xlsx");
      await usuario.click(screen.getByRole("button", { name: "Auditar por mi cuenta" }));
      expect(tomarArchivoPendiente()?.archivo).toBe(archivo);
    });

    test("un archivo que no es .xlsx no habilita nada", async () => {
      const usuario = userEvent.setup({ applyAccept: false });
      montar();
      await usuario.upload(campoArchivo(), new File(["x"], "foto.png"));
      expect(screen.getByRole("alert")).toHaveTextContent("Solo se aceptan archivos .xlsx.");
      expect(screen.queryByRole("button", { name: "Auditar por mi cuenta" })).not.toBeInTheDocument();
    });

    test("elegir otro archivo reemplaza al anterior", async () => {
      const usuario = userEvent.setup();
      montar();
      await usuario.upload(campoArchivo(), new File(["1"], "uno.xlsx"));
      await usuario.upload(campoArchivo(), new File(["2"], "dos.xlsx"));
      expect(screen.getByRole("status")).toHaveTextContent("Archivo elegido: dos.xlsx");
      expect(screen.queryByText(/uno\.xlsx/)).not.toBeInTheDocument();
    });
  });

  describe("últimas auditorías guardadas", () => {
    test("con un recorrido en curso lo dice y enlaza al paso que sigue", async () => {
      iniciarRecorrido(RECORRIDO_AUDITAR);
      montar();
      const seccion = await screen.findByRole("region", { name: "Últimas auditorías guardadas" });
      expect(within(seccion).getByText(/Recorrido en curso: Auditar un libro de la empresa/)).toBeInTheDocument();
      expect(
        within(seccion).getByRole("link", { name: "Seguir con el paso 2: Lea el resumen y los hallazgos" }),
      ).toHaveAttribute("href", "/libros");
    });

    test("no enlaza al paso siguiente si la cuenta no puede abrir esa pantalla", async () => {
      iniciarRecorrido(RECORRIDO_AUDITAR);
      // El paso siguiente (Libro) pide `leer_proyecto`, igual que la sección donde se anuncia el recorrido (VD-10).
      montar({ sesion: { ...SESION, acciones: ["revisar_paquete"] } });
      await screen.findByRole("heading", { name: "Inicio de auditoría" });
      expect(screen.queryByRole("region", { name: "Últimas auditorías guardadas" })).not.toBeInTheDocument();
      expect(screen.queryByRole("link", { name: /Seguir con el paso/ })).not.toBeInTheDocument();
    });

    test("sin recorrido en curso no dice nada de recorridos", async () => {
      montar();
      const seccion = await screen.findByRole("region", { name: "Últimas auditorías guardadas" });
      expect(within(seccion).queryByText(/Recorrido en curso/)).not.toBeInTheDocument();
    });

    test("dice la carpeta de trabajo abierta (no «caso»)", async () => {
      montar();
      const seccion = await screen.findByRole("region", { name: "Últimas auditorías guardadas" });
      expect(within(seccion).getByText(/Carpeta de trabajo: clinica/)).toBeInTheDocument();
      expect(within(seccion).queryByText(/\bcaso\b/i)).not.toBeInTheDocument();
    });

    test("dice la obra elegida por su nombre, no por su código", async () => {
      montar({ proyecto: "2", nombreProyecto: "Casa Demo" });
      const seccion = await screen.findByRole("region", { name: "Últimas auditorías guardadas" });
      expect(within(seccion).getByText(/Obra: Casa Demo/)).toBeInTheDocument();
      expect(within(seccion).queryByText(/Obra: 2/)).toBeNull();
    });

    test("sin el nombre de la obra muestra su código", async () => {
      montar({ proyecto: "P-01" });
      const seccion = await screen.findByRole("region", { name: "Últimas auditorías guardadas" });
      expect(within(seccion).getByText(/Obra: P-01/)).toBeInTheDocument();
    });

    test("lista las últimas auditorías con archivo, fecha y resultado", async () => {
      auditorias = () =>
        json([
          auditoria(7, { archivo: "obra-norte.xlsx", fecha: "2026-10-18T14:32:00", errores: 1, advertencias: 3 }),
          auditoria(6, { archivo: "galpon.xlsx", fecha: "2026-10-17T09:05:00", errores: 0, advertencias: 0 }),
        ]);
      montar();
      const seccion = await screen.findByRole("region", { name: "Últimas auditorías guardadas" });
      await within(seccion).findByText("obra-norte.xlsx");
      const filas = within(seccion).getAllByRole("row").slice(1);
      expect(filas[0]).toHaveTextContent("obra-norte.xlsx");
      expect(filas[0]).toHaveTextContent("18/10/2026 14:32");
      expect(filas[0]).toHaveTextContent("1 error, 3 advertencias");
      expect(filas[1]).toHaveTextContent("galpon.xlsx");
      expect(filas[1]).toHaveTextContent("17/10/2026 09:05");
      expect(filas[1]).toHaveTextContent("Sin errores ni advertencias");
    });

    test("sin auditorías guardadas, lo dice y enseña cómo empezar", async () => {
      montar();
      expect(await screen.findByText("Todavía no hay auditorías guardadas")).toBeInTheDocument();
    });

    test("si el historial aún no existe en la API, avisa sin romper la página", async () => {
      auditorias = () => json({ detalle: "No encontrado." }, 404);
      montar();
      expect(await screen.findByText("El historial de auditorías aún no está disponible")).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Audite un presupuesto" })).toBeInTheDocument();
    });

    test("mientras cargan, las auditorías lo dicen", () => {
      fetchFalso.mockImplementation(() => new Promise<Response>(() => {}));
      montar();
      expect(screen.getByLabelText("Cargando las auditorías")).toHaveAttribute("aria-busy", "true");
    });

    test("otro error de la API en las auditorías se muestra con su detalle", async () => {
      auditorias = () => json({ detalle: "El historial no responde." }, 500);
      montar();
      expect(await screen.findByRole("alert")).toHaveTextContent("El historial no responde.");
    });

    test("una respuesta 401 avisa que la sesión venció", async () => {
      const alExpirar = vi.fn();
      auditorias = () => json({ detalle: "Sesión vencida." }, 401);
      montar({ alExpirar });
      await waitFor(() => expect(alExpirar).toHaveBeenCalled());
    });
  });

  // VB-9: cada recurso se pide solo si la cuenta tiene la accion que lo permite; a quien no puede auditar no se le
  // ofrece auditar. Acciones a mano de seguridad/permisos.py.
  describe("según las acciones de la cuenta", () => {
    test("quien revisa conserva la zona del Excel y el historial", async () => {
      montar({ sesion: { ...SESION, login: "rita", roles: ["revisa"], acciones: ["leer_proyecto", "revisar_paquete"] } });
      expect(screen.getByRole("heading", { name: "Audite un presupuesto" })).toBeInTheDocument();
      expect(await screen.findByRole("region", { name: "Últimas auditorías guardadas" })).toBeInTheDocument();
      expect(rutasPedidas()).toEqual(["/v1/auditorias-libro?limite=5"]);
    });

    test("una cuenta sin la acción de auditar no ve la zona de soltar ni pide el historial", async () => {
      montar({ sesion: { ...SESION, roles: ["revisa"], acciones: ["revisar_paquete"] } });
      expect(await screen.findByText(/no tiene permiso para auditar presupuestos/i)).toBeInTheDocument();
      expect(document.querySelector('input[type="file"]')).toBeNull();
      expect(rutasPedidas()).toEqual([]);
    });
  });
});
