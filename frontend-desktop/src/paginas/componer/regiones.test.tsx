import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { Guardar } from "./Guardar";
import PaginaComponer from "./index";

// VD-6: el TextInput de Carbon monta siempre un <span class="cds--text-input__counter-alert" role="alert"> vacio.
// Componer usa CampoTexto (que la quita si no hay contador) sin que ningun campo pierda su nombre accesible.

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

const NOMBRES = [
  "Código",
  "Descripción",
  "Unidad",
  "Fecha",
  "Rendimiento: unidades por día",
  "Buscar en la referencia MaPreX (materiales)",
  "Buscar en la referencia MaPreX (equipos)",
  "Buscar en la referencia MaPreX (mano de obra)",
];

describe("Componer: regiones vivas vacías (VD-6)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fetchFalso.mockImplementation(async (entrada) => {
      const ruta = String(entrada);
      if (ruta === "/v1/composicion/opciones") return json({ dominios: ["civil"], modalidades: ["JORNAL"] });
      if (ruta === "/v1/composicion/evaluar")
        return json({ estado: "vacio", aviso: null, desglose: null, advertencias: [], requiere_justificacion: false, contraste: null });
      return json([]);
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  function montar() {
    const valor: Aplicacion = { sesion: SESION, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter>
          <PaginaComponer />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  test("la página no deja regiones role=alert ni contadores vacíos", async () => {
    const { container } = montar();
    await waitFor(() => expect(screen.getByLabelText("Dominio")).toHaveValue("civil"));
    expect(container.querySelectorAll('[role="alert"]:empty')).toHaveLength(0);
    expect(container.querySelectorAll("[class*=\"counter-alert\"][role]")).toHaveLength(0);
  });

  test.each(NOMBRES)("el campo «%s» conserva su nombre accesible", async (nombre) => {
    montar();
    await waitFor(() => expect(screen.getByLabelText("Dominio")).toHaveValue("civil"));
    expect(screen.getByLabelText(nombre)).toBeInstanceOf(HTMLInputElement);
  });

  test("la justificación conserva su nombre, su ayuda y no deja región viva vacía", () => {
    const { container } = render(
      <MemoryRouter>
        <Guardar sinCondiciones={false} requiereJustificacion guardando={false} resultado={null} error={null} alGuardar={vi.fn()} />
      </MemoryRouter>,
    );
    const campo = screen.getByRole("textbox", { name: "Justificación de la advertencia" });
    expect(campo).toHaveAttribute("id", "componer-justificacion");
    expect(campo).toHaveAccessibleDescription(/Opcional: el motivo/);
    expect(container.querySelectorAll('[role="alert"]:empty')).toHaveLength(0);
  });
});
