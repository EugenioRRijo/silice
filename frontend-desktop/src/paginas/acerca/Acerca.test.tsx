import { render, screen } from "@testing-library/react";
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

  function montar() {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: null,
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter>
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
    expect(h1).toHaveTextContent("Acerca de Sílice");
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
});
