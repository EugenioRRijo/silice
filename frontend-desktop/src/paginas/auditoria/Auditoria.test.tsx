import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import { RECORRIDO_AUDITAR, iniciarRecorrido, recorridoEnCurso, terminarRecorrido } from "../../shell/recorrido";
import type { Aplicacion } from "../../shell/contexto";
import { tomarArchivoPendiente } from "../inicio/archivoPendiente";
import { auditoriaDePrueba, catalogoDePrueba } from "./datosDePrueba";
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
      ...aplicacion,
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter initialEntries={["/auditoria"]}>
          <Routes>
            <Route path="/auditoria" element={<PaginaAuditoria />} />
            <Route path="/auditoria/libros" element={<h1>Pantalla del libro</h1>} />
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

  test("su h1 es «Auditar un libro» y no trae «Herramientas principales» ni la arenera", async () => {
    montar();
    expect(screen.getByRole("heading", { level: 1, name: "Auditar un libro" })).toHaveClass("cds--type-heading-04");
    expect(screen.getByText("Suba un presupuesto en Excel para recalcular sus partidas y detectar errores")).toBeInTheDocument();
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
      expect(screen.getByRole("heading", { name: "Suba el libro" })).toBeInTheDocument();
      expect(screen.getByText(/no se modifica ni se guarda/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Suelte aquí el libro \.xlsx/ })).toBeInTheDocument();
    });

    test("sin archivo hay un solo principal, inactivo, y el recorrido guiado queda en «Más opciones», deshabilitado", () => {
      montar();
      const principal = screen.getByRole("button", { name: "Auditar el libro" });
      expect(principal).toHaveAttribute("aria-disabled", "true");
      expect(principal).toHaveClass("cds--btn--primary");
      const guiado = screen.getByRole("button", { name: "Auditar con recorrido guiado" });
      expect(guiado).toBeDisabled();
      expect(guiado.closest("details")).not.toHaveAttribute("open");
      expect(screen.queryByRole("button", { name: "Auditar por mi cuenta" })).not.toBeInTheDocument();
    });

    test("a la vista, antes de auditar, solo dos pliegues: más opciones y el libro con un APU por hoja", () => {
      montar();
      const resumenes = [...document.querySelectorAll("summary")].map((r) => r.textContent);
      expect(resumenes).toEqual(["Más opciones", "Otro tipo de libro: un APU por hoja"]);
      expect([...document.querySelectorAll("details")].every((d) => !d.hasAttribute("open"))).toBe(true);
    });

    test("con un archivo aparece su nombre y el principal se activa", async () => {
      const usuario = userEvent.setup();
      montar();
      await usuario.upload(campoArchivo(), new File(["x"], "obra-norte.xlsx"));
      expect(screen.getByRole("status")).toHaveTextContent("Archivo elegido: obra-norte.xlsx");
      expect(screen.getByRole("button", { name: "Auditar el libro" })).not.toHaveAttribute("aria-disabled");
      expect(screen.getByRole("button", { name: "Auditar con recorrido guiado" })).toBeEnabled();
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

    test("un archivo inválido elegido después de uno válido deja intacto el anterior", async () => {
      const usuario = userEvent.setup({ applyAccept: false });
      montar();
      const archivo = new File(["x"], "obra-norte.xlsx");
      await usuario.upload(campoArchivo(), archivo);
      await usuario.upload(campoArchivo(), new File(["x"], "foto.png"));
      expect(screen.getByRole("status")).toHaveTextContent("Archivo elegido: obra-norte.xlsx");
      await usuario.click(screen.getByRole("button", { name: "Auditar con recorrido guiado" }));
      expect(tomarArchivoPendiente()?.archivo).toBe(archivo);
    });

    test("un archivo que no es .xlsx no habilita nada", async () => {
      const usuario = userEvent.setup({ applyAccept: false });
      montar();
      await usuario.upload(campoArchivo(), new File(["x"], "foto.png"));
      expect(screen.getByRole("alert")).toHaveTextContent("Solo se aceptan archivos .xlsx.");
      expect(screen.getByRole("button", { name: "Auditar con recorrido guiado" })).toBeDisabled();
      expect(screen.getByRole("button", { name: "Auditar el libro" })).toHaveAttribute("aria-disabled", "true");
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
      ).toHaveAttribute("href", "/auditoria/libros");
    });

    test("no enlaza al paso siguiente si la cuenta no puede abrir esa pantalla", async () => {
      iniciarRecorrido(RECORRIDO_AUDITAR);
      // El paso siguiente (Libro) pide `leer_proyecto`, igual que la sección donde se anuncia el recorrido (VD-10).
      montar({ sesion: { ...SESION, acciones: ["revisar_paquete"] } });
      await screen.findByRole("heading", { name: "Auditar un libro" });
      expect(screen.queryByRole("region", { name: "Últimas auditorías guardadas" })).not.toBeInTheDocument();
      expect(screen.queryByRole("link", { name: /Seguir con el paso/ })).not.toBeInTheDocument();
    });

    test("sin recorrido en curso no dice nada de recorridos", async () => {
      montar();
      const seccion = await screen.findByRole("region", { name: "Últimas auditorías guardadas" });
      expect(within(seccion).queryByText(/Recorrido en curso/)).not.toBeInTheDocument();
    });

    test("dice la carpeta abierta sin extensión .db (no «caso»)", async () => {
      montar({ caso: { nombre: "clinica.db", ruta_relativa: "data/clinica.db" } });
      const seccion = await screen.findByRole("region", { name: "Últimas auditorías guardadas" });
      expect(within(seccion).getByText("Carpeta: clinica")).toBeInTheDocument();
      expect(within(seccion).queryByText(/\.db/)).not.toBeInTheDocument();
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
      // En Auditoría sí hay una zona arriba donde soltar el Excel (en la Vista general no: allí el texto manda a Auditoría).
      expect(screen.getByText("Suelte arriba el Excel de un presupuesto: el resumen y los hallazgos quedarán aquí.")).toBeInTheDocument();
    });

    test("si el historial aún no existe en la API, avisa sin romper la página", async () => {
      auditorias = () => json({ detalle: "No encontrado." }, 404);
      montar();
      expect(await screen.findByText("El historial de auditorías aún no está disponible")).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Suba el libro" })).toBeInTheDocument();
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

    test("al auditar un libro que se guarda, refresca «Últimas auditorías guardadas» sin recargar", async () => {
      let lista = [auditoria(6, { archivo: "previa.xlsx", errores: 1, advertencias: 0 })];
      fetchFalso.mockImplementation(async (entrada) => {
        const ruta = String(entrada);
        if (ruta === "/v1/auditorias-libro?limite=5") return json(lista);
        if (ruta === "/v1/libros/auditoria") {
          lista = [auditoria(7, { archivo: "obra-nueva.xlsx", errores: 8, advertencias: 0 }), ...lista];
          return json(auditoriaDePrueba());
        }
        if (ruta === "/v1/libros/que-hacer") return json(catalogoDePrueba());
        if (ruta === "/v1/libros/perfiles-apu-por-hoja") return json([]);
        return json({ detalle: "No encontrado." }, 404);
      });
      const usuario = userEvent.setup();
      montar();
      const seccion = await screen.findByRole("region", { name: "Últimas auditorías guardadas" });
      await within(seccion).findByRole("row", { name: /previa\.xlsx/ });

      await usuario.upload(campoArchivo(), new File(["x"], "obra-nueva.xlsx"));
      await usuario.click(screen.getByRole("button", { name: "Auditar el libro" }));

      await screen.findByRole("heading", { level: 2, name: "8 hallazgos en el libro" });
      const filaNueva = await within(seccion).findByRole("row", { name: /obra-nueva\.xlsx/ });
      expect(filaNueva).toHaveTextContent("8 errores, 0 advertencias");
      expect(rutasPedidas().filter((r) => r === "/v1/auditorias-libro?limite=5")).toHaveLength(2);
    });

    test("un error al auditar el libro no refresca «Últimas auditorías guardadas»", async () => {
      fetchFalso.mockImplementation(async (entrada) => {
        const ruta = String(entrada);
        if (ruta === "/v1/auditorias-libro?limite=5") return json([auditoria(6, { archivo: "previa.xlsx" })]);
        if (ruta === "/v1/libros/auditoria") return json({ detalle: "El libro no se pudo interpretar." }, 422);
        if (ruta === "/v1/libros/perfiles-apu-por-hoja") return json([]);
        return json({ detalle: "No encontrado." }, 404);
      });
      const usuario = userEvent.setup();
      montar();
      const seccion = await screen.findByRole("region", { name: "Últimas auditorías guardadas" });
      await within(seccion).findByRole("row", { name: /previa\.xlsx/ });

      await usuario.upload(campoArchivo(), new File(["x"], "roto.xlsx"));
      await usuario.click(screen.getByRole("button", { name: "Auditar el libro" }));

      expect(await screen.findByRole("alert")).toHaveTextContent("El libro no se pudo interpretar.");
      expect(rutasPedidas().filter((r) => r === "/v1/auditorias-libro?limite=5")).toHaveLength(1);
      expect(within(seccion).getByRole("row", { name: /previa\.xlsx/ })).toBeInTheDocument();
    });

    test("si el servidor avisa que no quedó en el historial, no refresca «Últimas auditorías guardadas»", async () => {
      fetchFalso.mockImplementation(async (entrada) => {
        const ruta = String(entrada);
        if (ruta === "/v1/auditorias-libro?limite=5") return json([auditoria(6, { archivo: "previa.xlsx" })]);
        if (ruta === "/v1/libros/auditoria") {
          return json(auditoriaDePrueba({ aviso_historial: "No se pudo guardar la auditoría en el historial." }));
        }
        if (ruta === "/v1/libros/que-hacer") return json(catalogoDePrueba());
        if (ruta === "/v1/libros/perfiles-apu-por-hoja") return json([]);
        return json({ detalle: "No encontrado." }, 404);
      });
      const usuario = userEvent.setup();
      montar();
      const seccion = await screen.findByRole("region", { name: "Últimas auditorías guardadas" });
      await within(seccion).findByRole("row", { name: /previa\.xlsx/ });

      await usuario.upload(campoArchivo(), new File(["x"], "obra-nueva.xlsx"));
      await usuario.click(screen.getByRole("button", { name: "Auditar el libro" }));

      await screen.findByRole("heading", { level: 2, name: "8 hallazgos en el libro" });
      expect(screen.getByText("No se pudo guardar la auditoría en el historial.")).toBeInTheDocument();
      expect(rutasPedidas().filter((r) => r === "/v1/auditorias-libro?limite=5")).toHaveLength(1);
    });
  });

  // VB-9: cada recurso se pide solo si la cuenta tiene la accion que lo permite; a quien no puede auditar no se le
  // ofrece auditar. Acciones a mano de seguridad/permisos.py.
  describe("según las acciones de la cuenta", () => {
    test("quien revisa conserva la zona del Excel y el historial", async () => {
      montar({ sesion: { ...SESION, login: "rita", roles: ["revisa"], acciones: ["leer_proyecto", "revisar_paquete", "aprobar_version"] } });
      expect(screen.getByRole("heading", { name: "Suba el libro" })).toBeInTheDocument();
      expect(await screen.findByRole("region", { name: "Últimas auditorías guardadas" })).toBeInTheDocument();
      // E2E-2: el bloque del libro con un APU por hoja pide además la lista de perfiles.
      expect([...rutasPedidas()].sort()).toEqual(["/v1/auditorias-libro?limite=5", "/v1/libros/perfiles-apu-por-hoja"]);
    });

    test("una cuenta sin la acción de auditar no ve la zona de soltar ni pide el historial", async () => {
      montar({ sesion: { ...SESION, roles: ["revisa"], acciones: ["revisar_paquete"] } });
      expect(await screen.findByText(/no tiene permiso para auditar presupuestos/i)).toBeInTheDocument();
      expect(document.querySelector('input[type="file"]')).toBeNull();
      expect(rutasPedidas()).toEqual([]);
    });
  });
});
