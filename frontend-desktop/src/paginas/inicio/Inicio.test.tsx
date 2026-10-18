import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { tomarArchivoPendiente } from "./archivoPendiente";
import PaginaInicio from "./index";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "leer_proyecto"],
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
      expect(screen.getByText("obra-norte.xlsx")).toBeInTheDocument();
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
      expect(tomarArchivoPendiente()).toEqual({ archivo, modo: "guiado" });
    });

    test("«Auditar por mi cuenta» lo deja en modo propio y lleva al libro", async () => {
      const usuario = userEvent.setup();
      montar();
      const archivo = new File(["x"], "obra-norte.xlsx");
      await usuario.upload(campoArchivo(), archivo);
      await usuario.click(screen.getByRole("button", { name: "Auditar por mi cuenta" }));
      expect(await screen.findByRole("heading", { name: "Pantalla del libro" })).toBeInTheDocument();
      expect(tomarArchivoPendiente()).toEqual({ archivo, modo: "propio" });
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
      expect(screen.queryByText("uno.xlsx")).not.toBeInTheDocument();
      expect(screen.getByText("dos.xlsx")).toBeInTheDocument();
    });
  });

  describe("arenera", () => {
    test("lista solo lo que pide atención, lo negativo primero, con ícono y texto", async () => {
      existencias = () =>
        json([
          existencia("ARENA"),
          existencia("PIEDRA", { existencia: "30", minima: "50", queda_poco: true }),
          existencia("GRAVA", { existencia: "-4.5", minima: "20", queda_poco: true, negativa: true }),
        ]);
      montar();
      const seccion = await screen.findByRole("region", { name: "Arenera: lo que requiere atención" });
      const filas = within(seccion).getAllByRole("row").slice(1); // sin el encabezado
      expect(filas).toHaveLength(2);
      expect(filas[0]).toHaveTextContent("Material GRAVA");
      expect(filas[0]).toHaveTextContent("-4.5 m3");
      expect(filas[0]).toHaveTextContent("Existencia negativa: falta registrar producción o conteo");
      expect(filas[1]).toHaveTextContent("Material PIEDRA");
      expect(filas[1]).toHaveTextContent("Queda poco");
      expect(within(seccion).queryByText("Material ARENA")).not.toBeInTheDocument();
      // La severidad nunca va solo en color: cada fila lleva un ícono con nombre accesible.
      expect(within(filas[0]).getByTitle("Error")).toBeInTheDocument();
      expect(within(filas[1]).getByTitle("Advertencia")).toBeInTheDocument();
    });

    test("muestra el mínimo junto a la existencia, con las cifras tal como vienen", async () => {
      existencias = () => json([existencia("PIEDRA", { existencia: "30.00", minima: "50.000", queda_poco: true })]);
      montar();
      const seccion = await screen.findByRole("region", { name: "Arenera: lo que requiere atención" });
      expect(within(seccion).getByText("30.00 m3")).toBeInTheDocument();
      expect(within(seccion).getByText("50.000 m3")).toBeInTheDocument();
    });

    test("si todo está sobre el mínimo, lo dice", async () => {
      montar();
      expect(await screen.findByText("Todo sobre el mínimo")).toBeInTheDocument();
    });

    test("sin materiales, enseña a registrarlos y enlaza a Existencias", async () => {
      existencias = () => json([]);
      const usuario = userEvent.setup();
      montar();
      expect(await screen.findByText("Aún no hay materiales")).toBeInTheDocument();
      await usuario.click(screen.getByRole("link", { name: "Registrar materiales en Producción" }));
      expect(await screen.findByRole("heading", { name: "Pantalla de existencias" })).toBeInTheDocument();
    });

    test("una cuenta sin permiso para la arenera lo ve como «sin datos», no como un error", async () => {
      existencias = () => json({ detalle: "Su cuenta no puede hacer esto." }, 403);
      montar();
      const seccion = await screen.findByRole("region", { name: "Arenera: lo que requiere atención" });
      expect(await within(seccion).findByText("Sin datos de la arenera para su cuenta")).toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    test("otro error de la API se muestra con su detalle", async () => {
      existencias = () => json({ detalle: "La base de la instalación no responde." }, 500);
      montar();
      expect(await screen.findByRole("alert")).toHaveTextContent("La base de la instalación no responde.");
    });
  });

  describe("seguir donde quedó", () => {
    test("muestra el caso abierto", async () => {
      montar();
      const seccion = await screen.findByRole("region", { name: "Seguir donde quedó" });
      expect(within(seccion).getByText(/Caso abierto: clinica/)).toBeInTheDocument();
    });

    test("muestra el proyecto elegido si lo hay", async () => {
      montar({ proyecto: "P-01" });
      const seccion = await screen.findByRole("region", { name: "Seguir donde quedó" });
      expect(within(seccion).getByText(/Proyecto: P-01/)).toBeInTheDocument();
    });

    test("lista las últimas auditorías con archivo, fecha y resultado", async () => {
      auditorias = () =>
        json([
          auditoria(7, { archivo: "obra-norte.xlsx", fecha: "2026-10-18T14:32:00", errores: 1, advertencias: 3 }),
          auditoria(6, { archivo: "galpon.xlsx", fecha: "2026-10-17T09:05:00", errores: 0, advertencias: 0 }),
        ]);
      montar();
      const seccion = await screen.findByRole("region", { name: "Seguir donde quedó" });
      await within(seccion).findByText("obra-norte.xlsx");
      const filas = within(seccion).getAllByRole("row").slice(1);
      expect(filas[0]).toHaveTextContent("obra-norte.xlsx");
      expect(filas[0]).toHaveTextContent("2026-10-18 14:32");
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

    test("una respuesta 401 avisa que la sesión venció", async () => {
      const alExpirar = vi.fn();
      auditorias = () => json({ detalle: "Sesión vencida." }, 401);
      montar({ alExpirar });
      await waitFor(() => expect(alExpirar).toHaveBeenCalled());
    });
  });
});
