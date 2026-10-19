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
  revision_instalacion: "ins_0002",
  head_instalacion: "ins_0002",
  revision_caso: "caso_0008",
  head_caso: "caso_0008",
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
    expect(screen.getByText("caso_0008 (la última es caso_0008)")).toBeInTheDocument();
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
});
