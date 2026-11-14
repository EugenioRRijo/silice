import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaAcerca from "./index";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: [],
  modo_entrega: false,
};

const DATOS = {
  version: "1.2.0.dev0",
  semver: "1.2.0-dev0",
  revision_instalacion: "ins_0003_auditoria_libro",
  head_instalacion: "ins_0003_auditoria_libro",
  revision_caso: "caso_0008",
  head_caso: "caso_0009_s3_paquete",
  carpeta_datos: "D:/datos-ficticios",
  modulos: [
    { nombre: "Planos DXF", instalado: true },
    { nombre: "Asistente de IA", instalado: false },
  ],
};

describe("Acerca de Sílice", () => {
  const fetchFalso = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  function montar({ en = "/cuenta/ayuda", sesion = SESION }: { en?: string; sesion?: SesionRespuesta } = {}) {
    const valor: Aplicacion = {
      sesion,
      proyecto: null,
      caso: null,
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter initialEntries={[en]}>
          <PaginaAcerca />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  test("muestra version, bases, carpeta y modulos", async () => {
    fetchFalso.mockResolvedValue(json(DATOS));
    montar();
    expect(await screen.findByText("Sílice 1.2.0-dev0")).toBeInTheDocument();
    // VB-20: sin nombres de migracion; al dia o el numero de version (de «ins_0003_…» a 3).
    expect(screen.getByText("Al día (versión 3)")).toBeInTheDocument();
    expect(screen.getByText("Versión 8; la última es la 9")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/ins_0003|caso_000|auditoria_libro|s3_paquete/);
    expect(screen.getByText("D:/datos-ficticios")).toBeInTheDocument();
    // Revisión final del árbitro (MENOR 3): la persona ve «carpeta», no «caso».
    expect(screen.getByText("Base de la carpeta abierta")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/caso abierto/);
    expect(screen.getByText("Planos DXF")).toBeInTheDocument();
    expect(screen.getByText("instalado")).toBeInTheDocument();
    expect(screen.getByText("no instalado")).toBeInTheDocument();
    expect(fetchFalso.mock.calls[0][0]).toBe("/v1/acerca");
  });

  test("sin carpeta de datos (quien no administra) no dibuja la fila", async () => {
    fetchFalso.mockResolvedValue(json({ ...DATOS, carpeta_datos: null }));
    montar();
    await screen.findByText("Sílice 1.2.0-dev0");
    expect(screen.queryByText("Carpeta de datos")).not.toBeInTheDocument();
  });

  test("sigue el marco de las páginas: h1, sin jerga de archivos y dentro de la clase de página", async () => {
    fetchFalso.mockResolvedValue(json(DATOS));
    const { container } = montar();
    const h1 = await screen.findByRole("heading", { level: 1 });
    expect(h1).toHaveTextContent("Ayuda y acerca de Sílice");
    expect(screen.queryByText(/pyproject/)).not.toBeInTheDocument();
    expect(screen.getByText(/^Versión:/)).toBeInTheDocument();
    expect(container.querySelector(".silice-pagina")).not.toBeNull();
  });

  test("una base ausente o ilegible se dice en palabras, sin el código interno", async () => {
    fetchFalso.mockResolvedValue(json({ ...DATOS, revision_instalacion: "sin base", revision_caso: "ilegible" }));
    montar();
    await screen.findByText("Sílice 1.2.0-dev0");
    expect(screen.getByText("Sin base")).toBeInTheDocument();
    expect(screen.getByText("Ilegible")).toBeInTheDocument();
  });

  // Punto 6 de la ronda 1: ni el nombre crudo de una migracion ni «alembic_version» llegan a la persona.
  test("sin dato de la última versión se dice solo la versión en que va; «sin alembic_version» se explica", async () => {
    fetchFalso.mockResolvedValue(
      json({ ...DATOS, revision_caso: "caso_0008_s3_paquete", head_caso: "sin revisiones", revision_instalacion: "sin alembic_version" }),
    );
    montar();
    await screen.findByText("Sílice 1.2.0-dev0");
    expect(screen.getByText("Versión 8")).toBeInTheDocument();
    expect(screen.getByText("Sin información de versión")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/alembic|Caso_0008|s3_paquete/i);
  });

  // F7 (Ayuda), tareas A2 a A4: la Ayuda de la Cuenta reúne «Empieza aquí», las guías por tarea y el glosario, y se puede
  // enlazar a cada parte con `?tema=`. Oráculos a mano: los títulos y los ids que fija el plan.
  describe("la ayuda", () => {
    test("bajo el h1 van «Empieza aquí», «Guías por tarea» y «Glosario», con las cuatro guías, antes de la versión", async () => {
      fetchFalso.mockResolvedValue(json(DATOS));
      montar();
      await screen.findByText("Sílice 1.2.0-dev0");
      const h2 = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
      expect(h2.slice(0, 3)).toEqual(["Empieza aquí", "Guías por tarea", "Glosario"]);
      expect(h2.indexOf("Sílice 1.2.0-dev0")).toBeGreaterThan(2);
      const guias = within(screen.getByRole("region", { name: "Guías por tarea" }));
      expect(guias.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual([
        "Montar un presupuesto",
        "Enviarlo a aprobación",
        "Actualizar precios",
        "Auditar un libro",
      ]);
      const glosario = screen.getByRole("region", { name: "Glosario" });
      expect(within(glosario).getByText("FCAS (factor de costos asociados al salario)")).toBeInTheDocument();
    });

    test("«Empieza aquí» explica la primera vez: el código de instalación, la cuenta del administrador y cómo recuperarla", async () => {
      fetchFalso.mockResolvedValue(json(DATOS));
      montar();
      const empieza = await screen.findByRole("region", { name: "Empieza aquí" });
      expect(empieza).toHaveTextContent("código de instalación");
      expect(empieza).toHaveTextContent("«Crear la cuenta y entrar»");
      expect(empieza).toHaveTextContent("«Perdí el acceso de administrador»");
    });

    test("los enlaces a la Cuenta solo se ofrecen a quien administra", async () => {
      fetchFalso.mockResolvedValue(json(DATOS));
      montar();
      const empieza = await screen.findByRole("region", { name: "Empieza aquí" });
      expect(within(empieza).queryByRole("link", { name: "Ir a Cuentas y permisos" })).toBeNull();
    });

    test("quien administra ve el enlace a «Cuentas y permisos»", async () => {
      fetchFalso.mockResolvedValue(json(DATOS));
      montar({ sesion: { ...SESION, acciones: ["administrar_cuentas", "administrar_empresa"] } });
      const empieza = await screen.findByRole("region", { name: "Empieza aquí" });
      expect(within(empieza).getByRole("link", { name: "Ir a Cuentas y permisos" })).toHaveAttribute("href", "/cuenta/cuentas");
    });

    test("con ?tema= el foco va a esa parte (un término del glosario), y el índice de arriba mueve el foco a otra", async () => {
      const u = userEvent.setup();
      fetchFalso.mockResolvedValue(json(DATOS));
      montar({ en: "/cuenta/ayuda?tema=glosario-fcas" });
      const termino = await screen.findByText("FCAS (factor de costos asociados al salario)");
      await waitFor(() => expect(termino).toHaveFocus());
      const indice = screen.getByRole("navigation", { name: "En esta ayuda" });
      await u.click(within(indice).getByRole("link", { name: "Guías por tarea" }));
      await waitFor(() => expect(screen.getByRole("heading", { level: 2, name: "Guías por tarea" })).toHaveFocus());
    });

    test("si no se puede leer la versión, la ayuda se ve igual y el error queda en su parte", async () => {
      fetchFalso.mockResolvedValue(json({ detalle: "La base no responde." }, 500));
      montar();
      expect(await screen.findByRole("heading", { level: 1, name: "Ayuda y acerca de Sílice" })).toBeInTheDocument();
      expect(screen.getByRole("region", { name: "Guías por tarea" })).toBeInTheDocument();
      expect(await screen.findByText("No se pudo cargar la información")).toBeInTheDocument();
    });
  });
});
