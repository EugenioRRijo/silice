import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import AvisosDelTema from "./AvisosDelTema";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "admin",
  nombre: "Admin de Prueba",
  roles: ["administrador"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["administrar_cuentas"],
  modo_entrega: false,
};
const TEMA = { acento: "#ffffff", marco: "#ffffff", lateral: null, tiene_logo: false };
// Textos inventados con la forma de los del servidor (coma decimal).
const A1 = "El texto del botón Nueva obra no se lee bien sobre el color de acento: 2,1:1, hace falta 4,5:1";
const A2 = "El texto del menú lateral no se lee bien sobre el color lateral: 1,1:1, hace falta 4,5:1";

describe("AvisosDelTema", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function montar(acciones: string[] = SESION.acciones) {
    const valor: Aplicacion = {
      sesion: { ...SESION, acciones },
      proyecto: null,
      caso: null,
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <AvisosDelTema />
      </ContextoAplicacion.Provider>,
    );
  }

  test("muestra cada aviso del servidor tal cual, como aviso y no como error", async () => {
    fetchFalso.mockResolvedValue(json({ ...TEMA, avisos: [A1, A2] }));
    montar();
    expect(await screen.findByText(A1)).toBeInTheDocument();
    expect(screen.getByText(A2)).toBeInTheDocument();
    expect(screen.getByText("Algunos colores de la empresa no se leen bien")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveClass("cds--inline-notification--warning");
  });

  test("sin avisos no dibuja nada", async () => {
    fetchFalso.mockResolvedValue(json({ ...TEMA, avisos: [] }));
    const { container } = montar();
    await waitFor(() => expect(fetchFalso).toHaveBeenCalledTimes(1));
    expect(container).toBeEmptyDOMElement();
  });

  test.each([
    ["sin el campo de avisos", TEMA],
    ["con avisos que no son una lista", { ...TEMA, avisos: "x" }],
  ])("una respuesta %s no dibuja nada ni falla", async (_caso, cuerpo) => {
    fetchFalso.mockResolvedValue(json(cuerpo));
    const { container } = montar();
    await waitFor(() => expect(fetchFalso).toHaveBeenCalledTimes(1));
    expect(container).toBeEmptyDOMElement();
  });

  test("si la petición falla no dibuja nada", async () => {
    fetchFalso.mockResolvedValue(json({}, 500));
    const { container } = montar();
    await waitFor(() => expect(fetchFalso).toHaveBeenCalledTimes(1));
    expect(container).toBeEmptyDOMElement();
  });

  test("a una cuenta sin permiso de administración no se le pide ni se le muestra nada", async () => {
    fetchFalso.mockResolvedValue(json({ ...TEMA, avisos: [A1] }));
    const { container } = montar(["leer_proyecto"]);
    expect(container).toBeEmptyDOMElement();
    expect(fetchFalso).not.toHaveBeenCalled();
  });
});
