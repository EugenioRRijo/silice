import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { pedir } from "../../api/cliente";
import { ContextoAplicacion } from "../../shell/contexto";
import { sesionDe } from "../../shell/obras/datosDePrueba";
import Especialidades from "./Especialidades";

vi.mock("../../api/cliente", async (importarOriginal) => ({
  ...(await importarOriginal<typeof import("../../api/cliente")>()),
  pedir: vi.fn(),
}));
const pedirFalso = vi.mocked(pedir);

// Plan vial, Tarea 19. Estado ficticio: el servidor lo guarda en `activos`.
const NOMBRES: Record<string, string> = { produccion: "producción", vial: "vial", edificacion: "edificación", riesgo: "riesgo" };
let activos: Record<string, boolean>;
const lista = () => ({
  modulos: Object.keys(NOMBRES).map((clave) => ({ clave, nombre: NOMBRES[clave], activo: activos[clave], cambiado_por: null, cambiado_el: null })),
});

beforeEach(() => {
  activos = { produccion: true, vial: true, edificacion: true, riesgo: true };
  pedirFalso.mockReset();
  pedirFalso.mockImplementation(async (ruta: string, opciones?: { metodo?: string; cuerpo?: unknown }) => {
    if (ruta === "/v1/modulos") return lista();
    const m = /^\/v1\/modulos\/(\w+)$/.exec(ruta);
    if (m && opciones?.metodo === "PUT") {
      activos[m[1]] = (opciones.cuerpo as { activo: boolean }).activo;
      return lista();
    }
    throw new Error(`petición inesperada: ${ruta}`);
  });
});

function pintar(alCambiar = vi.fn()) {
  return render(
    <ContextoAplicacion.Provider value={{ sesion: sesionDe("admin"), proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn(), recargarModulos: alCambiar }}>
      <Especialidades />
    </ContextoAplicacion.Provider>,
  );
}

describe("Administración › Especialidades", () => {
  it("lista las cuatro y las muestra encendidas", async () => {
    pintar();
    for (const nombre of ["Producción", "Vial", "Edificación", "Riesgo"]) {
      expect(await screen.findByRole("switch", { name: nombre })).toBeChecked();
    }
  });

  it("apagar una la guarda en la instalación y avisa al marco para que la oculte", async () => {
    const alCambiar = vi.fn();
    pintar(alCambiar);
    await userEvent.click(await screen.findByRole("switch", { name: "Vial" }));
    await waitFor(() => expect(activos["vial"]).toBe(false));
    expect(alCambiar).toHaveBeenCalled();
    expect(await screen.findByRole("switch", { name: "Vial" })).not.toBeChecked();
    expect(screen.getByRole("switch", { name: "Riesgo" })).toBeChecked();
  });

  it("dice que apagar no borra los datos", async () => {
    pintar();
    expect(await screen.findByText(/no borra nada/i)).toBeInTheDocument();
  });
});
