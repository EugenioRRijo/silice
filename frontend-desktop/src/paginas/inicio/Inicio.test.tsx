import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import { RECORRIDO_AUDITAR, iniciarRecorrido, recorridoEnCurso, terminarRecorrido } from "../../shell/recorrido";
import type { Aplicacion } from "../../shell/contexto";
import { tomarArchivoPendiente } from "./archivoPendiente";
import PaginaInicio from "./index";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { "Content-Type": "application/json" },
  });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "leer_proyecto", "operar_arenera"],
  modo_entrega: false,
};

function existencia(codigo: string, parcial: Record<string, unknown> = {}) {
  return {
    codigo,
    nombre: `Material ${codigo}`,
    unidad_venta: "m3",
    existencia: "120.5",
    minima: "50",
    queda_poco: false,
    negativa: false,
    ...parcial,
  };
}

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

describe("Inicio, panel del día", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let existencias: () => Response;
  let auditorias: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    existencias = () => json([existencia("ARENA")]);
    auditorias = () => json([]);
    fetchFalso.mockImplementation(async (entrada) => {
      const ruta = String(entrada);
      if (ruta === "/v1/produccion/existencias") return existencias();
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
        <MemoryRouter initialEntries={["/inicio"]}>
          <Routes>
            <Route path="/inicio" element={<PaginaInicio />} />
            <Route path="/libros" element={<h1>Pantalla del libro</h1>} />
            <Route path="/existencias" element={<h1>Pantalla de existencias</h1>} />
          </Routes>
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  function campoArchivo(): HTMLInputElement {
    return document.querySelector('input[type="file"]') as HTMLInputElement;
  }

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

    test("«Auditar con recorrido guiado» deja el archivo en modo guiado y lleva al libro", async () => {
      const usuario = userEvent.setup();
      montar();
      const archivo = new File(["x"], "obra-norte.xlsx");
      await usuario.upload(campoArchivo(), archivo);
      await usuario.click(screen.getByRole("button", { name: "Auditar con recorrido guiado" }));
      expect(await screen.findByRole("heading", { name: "Pantalla del libro" })).toBeInTheDocument();
      const pendiente = tomarArchivoPendiente();
      expect(pendiente?.archivo).toBe(archivo);
      expect(pendiente?.modo).toBe("guiado");
    });

    test("«Auditar con recorrido guiado» además pone en curso el recorrido «Auditar un libro de la empresa»", async () => {
      const usuario = userEvent.setup();
      montar();
      expect(recorridoEnCurso()).toBeNull();
      await usuario.upload(campoArchivo(), new File(["x"], "obra-norte.xlsx"));
      await usuario.click(screen.getByRole("button", { name: "Auditar con recorrido guiado" }));
      expect(recorridoEnCurso()).toBe(RECORRIDO_AUDITAR);
    });

    test("«Auditar por mi cuenta» lo deja en modo propio y lleva al libro", async () => {
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

  describe("arenera", () => {
    test("lista solo lo que pide atención, lo negativo primero, con ícono y texto", async () => {
      existencias = () =>
        json([
          existencia("ARENA"),
          existencia("PIEDRA", {
            existencia: "30",
            minima: "50",
            queda_poco: true,
          }),
          existencia("GRAVA", {
            existencia: "-4.5",
            minima: "20",
            queda_poco: true,
            negativa: true,
          }),
        ]);
      montar();
      const seccion = await screen.findByRole("region", {
        name: "Arenera: lo que requiere atención",
      });
      const filas = within(seccion).getAllByRole("row").slice(1); // sin el encabezado
      expect(filas).toHaveLength(2);
      expect(filas[0]).toHaveTextContent("Material GRAVA");
      expect(filas[0]).toHaveTextContent("-4.5 m3");
      expect(filas[0]).toHaveTextContent("Existencia negativa: falta registrar producción o conteo");
      expect(filas[1]).toHaveTextContent("Material PIEDRA");
      expect(filas[1]).toHaveTextContent("Queda poco");
      expect(within(seccion).queryByText("Material ARENA")).not.toBeInTheDocument();
      // La severidad nunca va solo en color: cada fila lleva un ícono (decorativo) y el texto del estado.
      expect(filas[0].querySelector("svg")).toHaveAttribute("aria-hidden", "true");
      expect(filas[1].querySelector("svg")).toHaveAttribute("aria-hidden", "true");
      // Debajo de la tabla, el paso siguiente.
      expect(
        within(seccion).getByRole("link", {
          name: "Ver todas las existencias",
        }),
      ).toHaveAttribute("href", "/existencias");
    });

    test("una existencia negativa aparece aunque no esté por debajo del mínimo", async () => {
      existencias = () => json([existencia("ZINC", { existencia: "-1", minima: "0", negativa: true })]);
      montar();
      const seccion = await screen.findByRole("region", {
        name: "Arenera: lo que requiere atención",
      });
      const filas = within(seccion).getAllByRole("row").slice(1);
      expect(filas).toHaveLength(1);
      expect(filas[0]).toHaveTextContent("Material ZINC");
      expect(filas[0]).toHaveTextContent("Existencia negativa: falta registrar producción o conteo");
    });

    test("muestra el mínimo junto a la existencia, con las cifras tal como vienen", async () => {
      existencias = () =>
        json([
          existencia("PIEDRA", {
            existencia: "30.00",
            minima: "50.000",
            queda_poco: true,
          }),
        ]);
      montar();
      const seccion = await screen.findByRole("region", {
        name: "Arenera: lo que requiere atención",
      });
      expect(within(seccion).getByText("30.00 m3")).toBeInTheDocument();
      expect(within(seccion).getByText("50.000 m3")).toBeInTheDocument();
    });

    test("si todo está sobre el mínimo, lo dice", async () => {
      montar();
      expect(await screen.findByText("Todo sobre el mínimo")).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Ver todas las existencias" })).toBeInTheDocument();
    });

    test("sin materiales, enseña a registrarlos y enlaza a Existencias", async () => {
      existencias = () => json([]);
      const usuario = userEvent.setup();
      montar();
      expect(await screen.findByText("Aún no hay materiales")).toBeInTheDocument();
      await usuario.click(
        screen.getByRole("link", {
          name: "Registrar materiales en Producción",
        }),
      );
      expect(await screen.findByRole("heading", { name: "Pantalla de existencias" })).toBeInTheDocument();
    });

    test("una cuenta sin permiso para la arenera lo ve como «sin datos», no como un error", async () => {
      existencias = () => json({ detalle: "Su cuenta no puede hacer esto." }, 403);
      montar();
      const seccion = await screen.findByRole("region", {
        name: "Arenera: lo que requiere atención",
      });
      expect(await within(seccion).findByText("Sin datos de la arenera para su cuenta")).toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    test("mientras carga, la arenera lo dice", () => {
      fetchFalso.mockImplementation(() => new Promise<Response>(() => {}));
      montar();
      expect(screen.getByLabelText("Cargando la arenera")).toHaveAttribute("aria-busy", "true");
    });

    test("si la arenera aún no existe en la API (404), avisa sin romper la página", async () => {
      existencias = () => json({ detalle: "No encontrado." }, 404);
      montar();
      expect(await screen.findByText("Sin datos de la arenera en esta instalación")).toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    test("una instalación sin las rutas de la arenera ni del historial (404 de FastAPI, a veces sin JSON) no muestra errores", async () => {
      existencias = () => json({ detail: "Not Found" }, 404);
      auditorias = () => new Response("<html>no encontrado</html>", { status: 404 });
      const alExpirar = vi.fn();
      montar({ alExpirar });
      expect(await screen.findByText("Sin datos de la arenera en esta instalación")).toBeInTheDocument();
      expect(await screen.findByText("El historial de auditorías aún no está disponible")).toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(alExpirar).not.toHaveBeenCalled();
      expect(screen.getByRole("heading", { name: "Audite un presupuesto" })).toBeInTheDocument();
    });

    test("una respuesta 401 en la arenera avisa que la sesión venció y deja el bloque en error", async () => {
      const alExpirar = vi.fn();
      existencias = () => json({ detalle: "Sesión vencida." }, 401);
      montar({ alExpirar });
      await waitFor(() => expect(alExpirar).toHaveBeenCalled());
      expect(await screen.findByRole("alert")).toHaveTextContent("Sesión vencida.");
    });

    test("otro error de la API se muestra con su detalle", async () => {
      existencias = () => json({ detalle: "La base de la instalación no responde." }, 500);
      montar();
      expect(await screen.findByRole("alert")).toHaveTextContent("La base de la instalación no responde.");
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
      // El paso siguiente (Libro) pide `leer_proyecto`, igual que la sección donde se anuncia el recorrido (VD-10): sin
      // la acción la sección se omite y no hay enlace que lleve a una pantalla sin permiso.
      montar({ sesion: { ...SESION, acciones: ["editar_hoja"] } });
      await screen.findByRole("heading", { name: "Inicio" });
      expect(screen.queryByRole("region", { name: "Últimas auditorías guardadas" })).not.toBeInTheDocument();
      expect(screen.queryByRole("link", { name: /Seguir con el paso/ })).not.toBeInTheDocument();
    });

    test("sin recorrido en curso no dice nada de recorridos", async () => {
      montar();
      const seccion = await screen.findByRole("region", { name: "Últimas auditorías guardadas" });
      expect(within(seccion).queryByText(/Recorrido en curso/)).not.toBeInTheDocument();
    });

    test("muestra el caso abierto", async () => {
      montar();
      const seccion = await screen.findByRole("region", {
        name: "Últimas auditorías guardadas",
      });
      expect(within(seccion).getByText(/Caso abierto: clinica/)).toBeInTheDocument();
    });

    test("muestra el proyecto elegido si lo hay", async () => {
      montar({ proyecto: "P-01" });
      const seccion = await screen.findByRole("region", {
        name: "Últimas auditorías guardadas",
      });
      expect(within(seccion).getByText(/Proyecto: P-01/)).toBeInTheDocument();
    });

    test("muestra el nombre del proyecto y no su código cuando el contexto lo trae (V-23)", async () => {
      montar({ proyecto: "2", nombreProyecto: "Clínica Demo" });
      const seccion = await screen.findByRole("region", {
        name: "Últimas auditorías guardadas",
      });
      expect(within(seccion).getByText(/Proyecto: Clínica Demo/)).toBeInTheDocument();
      expect(within(seccion).queryByText(/Proyecto: 2/)).toBeNull();
    });

    test("lista las últimas auditorías con archivo, fecha y resultado", async () => {
      auditorias = () =>
        json([
          auditoria(7, {
            archivo: "obra-norte.xlsx",
            fecha: "2026-10-18T14:32:00",
            errores: 1,
            advertencias: 3,
          }),
          auditoria(6, {
            archivo: "galpon.xlsx",
            fecha: "2026-10-17T09:05:00",
            errores: 0,
            advertencias: 0,
          }),
        ]);
      montar();
      const seccion = await screen.findByRole("region", {
        name: "Últimas auditorías guardadas",
      });
      await within(seccion).findByText("obra-norte.xlsx");
      const filas = within(seccion).getAllByRole("row").slice(1);
      expect(filas[0]).toHaveTextContent("obra-norte.xlsx");
      // VD-3: la misma fecha y hora que Historial («dd/mm/aaaa hh:mm»), no la ISO.
      expect(filas[0]).toHaveTextContent("18/10/2026 14:32");
      expect(filas[0]).not.toHaveTextContent("2026-10-18");
      expect(filas[1]).toHaveTextContent("17/10/2026 09:05");
      expect(filas[0]).toHaveTextContent("1 error, 3 advertencias");
      expect(filas[1]).toHaveTextContent("galpon.xlsx");
      expect(filas[1]).toHaveTextContent("Sin errores ni advertencias");
    });

    test("una auditoría de solo PDF se rotula como tal", async () => {
      auditorias = () => json([auditoria(3, { archivo: "oferta.pdf", tipo: "pdf" })]);
      montar();
      expect(await screen.findByText("PDF")).toBeInTheDocument();
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

    test("una cuenta sin permiso para las auditorías lo ve como «sin datos», no como un error", async () => {
      auditorias = () => json({ detalle: "Su cuenta no puede hacer esto." }, 403);
      montar();
      await waitFor(() => expect(screen.queryByLabelText("Cargando las auditorías")).toBeNull());
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
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
  // VB-9 (auditoria visual del bloque B): cada recurso se pide solo si la cuenta tiene la accion que lo permite, y a
  // quien no puede auditar no se le ofrece auditar. Las acciones salen de seguridad/permisos.py (a mano): el
  // administrador tiene operar_arenera y no leer_proyecto; quien revisa tiene leer_proyecto y no operar_arenera.
  describe("lo que ofrece y lo que pide según las acciones de la cuenta", () => {
    const ADMIN = { ...SESION, login: "admin", roles: ["administrador"], acciones: ["administrar_cuentas", "operar_arenera", "cambiar_caso"] };
    const REVISA = { ...SESION, login: "rita", roles: ["revisa"], acciones: ["leer_proyecto", "revisar_paquete"] };

    function rutasPedidas(): string[] {
      return fetchFalso.mock.calls.map((c) => String(c[0]));
    }

    test("el administrador no ve «Audite un presupuesto» ni la zona de soltar, y se le dice quién audita", async () => {
      montar({ sesion: ADMIN });
      expect(await screen.findByText(/audita quien arma o revisa presupuestos/i)).toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: "Audite un presupuesto" })).not.toBeInTheDocument();
      expect(document.querySelector('input[type="file"]')).toBeNull();
    });

    test("el administrador no pide el historial de auditorías (daría 403) pero sí la arenera", async () => {
      montar({ sesion: ADMIN });
      expect(await screen.findByText("Todo sobre el mínimo")).toBeInTheDocument();
      expect(rutasPedidas()).toContain("/v1/produccion/existencias");
      expect(rutasPedidas().some((r) => r.startsWith("/v1/auditorias-libro"))).toBe(false);
      // VD-10: la sección que la cuenta no puede usar se omite, no se muestra vacía.
      expect(screen.queryByText("Sin historial de auditorías para su cuenta")).not.toBeInTheDocument();
      expect(screen.queryByRole("region", { name: "Últimas auditorías guardadas" })).not.toBeInTheDocument();
      expect(screen.getByRole("region", { name: "Arenera: lo que requiere atención" })).toBeInTheDocument();
    });

    test("quien revisa conserva la zona del Excel y el historial, y no pide la arenera (daría 403)", async () => {
      montar({ sesion: REVISA });
      expect(screen.getByRole("heading", { name: "Audite un presupuesto" })).toBeInTheDocument();
      await waitFor(() => expect(rutasPedidas()).toContain("/v1/auditorias-libro?limite=5"));
      // VD-10: sin `operar_arenera` la sección de la arenera no existe (ni vacía ni con «Sin datos»).
      expect(screen.queryByText("Sin datos de la arenera para su cuenta")).not.toBeInTheDocument();
      expect(screen.queryByRole("region", { name: "Arenera: lo que requiere atención" })).not.toBeInTheDocument();
      expect(screen.getByRole("region", { name: "Últimas auditorías guardadas" })).toBeInTheDocument();
      expect(rutasPedidas()).not.toContain("/v1/produccion/existencias");
    });

    // Sin `leer_proyecto` no siempre es el administrador (una API anterior no manda acciones): el texto de
    // «administra Sílice» es solo para quien tiene ese rol.
    test("una cuenta sin la acción de auditar que no es administradora recibe un texto neutro", async () => {
      montar({ sesion: { ...SESION, roles: ["arma"], acciones: [] } });
      expect(await screen.findByText(/no tiene permiso para auditar presupuestos/i)).toBeInTheDocument();
      expect(screen.queryByText(/administra Sílice/)).not.toBeInTheDocument();
    });

    test("quien arma lo pide todo", async () => {
      montar();
      expect(screen.getByRole("heading", { name: "Audite un presupuesto" })).toBeInTheDocument();
      await waitFor(() => {
        expect(rutasPedidas()).toContain("/v1/produccion/existencias");
        expect(rutasPedidas()).toContain("/v1/auditorias-libro?limite=5");
      });
    });
  });
});
