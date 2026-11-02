import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, test } from "vitest";
import { PanelRecorrido } from "./PanelRecorrido";
import { RECORRIDO_AUDITAR, iniciarRecorrido, recorridoEnCurso, terminarRecorrido } from "./recorrido";
import type { PaginaDef } from "./rutas";

const migrada = async () => ({ default: () => null });
const PAGINAS: PaginaDef[] = [
  { id: "auditoria", titulo: "Inicio de auditoría", enUnaLinea: "Pantalla de prueba", seccion: "Revisión", accion: null, cargar: migrada },
  { id: "libros", titulo: "Libro de la empresa", enUnaLinea: "Pantalla de prueba", seccion: "Revisión", accion: "leer_proyecto", cargar: migrada },
  { id: "historial", titulo: "Historial de auditorías", enUnaLinea: "Pantalla de prueba", seccion: "Revisión", accion: "leer_proyecto", cargar: migrada },
  { id: "tablero", titulo: "Tablero del proyecto", enUnaLinea: "Pantalla de prueba", seccion: "Trabajo", accion: "leer_proyecto", cargar: migrada },
];

function montar(ruta: string, paginas: readonly PaginaDef[] = PAGINAS, acciones: string[] = ["leer_proyecto"]) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <PanelRecorrido paginas={paginas} acciones={acciones} modoEntrega={false} />
    </MemoryRouter>,
  );
}

describe("PanelRecorrido", () => {
  afterEach(() => terminarRecorrido());

  test("sin recorrido en curso no pinta nada", () => {
    const { container } = montar("/auditoria");
    expect(container).toBeEmptyDOMElement();
  });

  test("en el paso 1 muestra el titulo, «Paso 1 de 3», que hacer y cuando se sabe que termino", () => {
    iniciarRecorrido(RECORRIDO_AUDITAR);
    montar("/auditoria");
    const region = screen.getByRole("region", { name: "Recorrido en curso" });
    expect(within(region).getByText("Auditar un libro de la empresa")).toBeInTheDocument();
    expect(within(region).getByText("Paso 1 de 3")).toBeInTheDocument();
    expect(within(region).getByText(/Pulse «Auditar con recorrido guiado»/)).toBeInTheDocument();
    expect(within(region).getByText(/^Sabrá que terminó cuando se abra/)).toBeInTheDocument();
    // Solo el paso actual muestra su detalle.
    expect(within(region).queryByText(/Compare el total del libro/)).not.toBeInTheDocument();
  });

  test("marca el paso actual con aria-current=step y enlaza a los otros", () => {
    iniciarRecorrido(RECORRIDO_AUDITAR);
    montar("/libros");
    const region = screen.getByRole("region", { name: "Recorrido en curso" });
    expect(within(region).getByText("Paso 2 de 3")).toBeInTheDocument();
    expect(within(region).getByText("Lea el resumen y los hallazgos").closest("li")).toHaveAttribute("aria-current", "step");
    expect(within(region).getByRole("link", { name: "Suba el libro" })).toHaveAttribute("href", "/auditoria");
    expect(within(region).getByRole("link", { name: "Compruebe que quedó guardada" })).toHaveAttribute("href", "/historial");
  });

  test("fuera de las pantallas del recorrido no hay paso actual, pero sigue a la vista", () => {
    iniciarRecorrido(RECORRIDO_AUDITAR);
    montar("/tablero");
    const region = screen.getByRole("region", { name: "Recorrido en curso" });
    expect(within(region).queryByText(/Paso \d de 3/)).not.toBeInTheDocument();
    expect(region.querySelector("[aria-current]")).toBeNull();
    expect(within(region).getAllByRole("link")).toHaveLength(3);
  });

  test("un paso cuya pantalla no esta disponible se ve como texto, sin enlace", () => {
    iniciarRecorrido(RECORRIDO_AUDITAR);
    montar("/libros", PAGINAS.filter((p) => p.id !== "historial"));
    const region = screen.getByRole("region", { name: "Recorrido en curso" });
    expect(within(region).queryByRole("link", { name: "Compruebe que quedó guardada" })).not.toBeInTheDocument();
    expect(within(region).getByText("Compruebe que quedó guardada")).toBeInTheDocument();
  });

  test("«Terminar recorrido» lo cierra y el panel desaparece", async () => {
    const usuario = userEvent.setup();
    iniciarRecorrido(RECORRIDO_AUDITAR);
    montar("/libros");
    await usuario.click(screen.getByRole("button", { name: "Terminar recorrido" }));
    expect(recorridoEnCurso()).toBeNull();
    expect(screen.queryByRole("region", { name: "Recorrido en curso" })).not.toBeInTheDocument();
  });

  test("aparece cuando se inicia con el panel ya montado", () => {
    montar("/auditoria");
    expect(screen.queryByRole("region", { name: "Recorrido en curso" })).not.toBeInTheDocument();
    act(() => iniciarRecorrido(RECORRIDO_AUDITAR));
    expect(screen.getByRole("region", { name: "Recorrido en curso" })).toBeInTheDocument();
  });

  test("«Terminar recorrido» manda el foco al h1 de la pagina", async () => {
    const usuario = userEvent.setup();
    iniciarRecorrido(RECORRIDO_AUDITAR);
    render(
      <MemoryRouter initialEntries={["/libros"]}>
        <PanelRecorrido paginas={PAGINAS} acciones={["leer_proyecto"]} modoEntrega={false} />
        <main id="contenido">
          <h1>Libro de la empresa</h1>
        </main>
      </MemoryRouter>,
    );
    await usuario.click(screen.getByRole("button", { name: "Terminar recorrido" }));
    expect(screen.getByRole("heading", { level: 1, name: "Libro de la empresa" })).toHaveFocus();
  });
});
