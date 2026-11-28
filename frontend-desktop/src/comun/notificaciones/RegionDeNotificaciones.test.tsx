import { fileURLToPath } from "node:url";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { MemoryRouter } from "react-router";
import * as sass from "sass";
import { afterEach, describe, expect, test, vi } from "vitest";
import { ProveedorDeAnuncios } from "../Anunciador";
import { Dialogo } from "../Dialogo";
import { ProveedorDeNotificaciones, useNotificaciones } from "./ProveedorDeNotificaciones";
import { RegionDeNotificaciones } from "./RegionDeNotificaciones";

afterEach(() => {
  vi.useRealTimers();
});

function Disparadores() {
  const { notificar } = useNotificaciones();
  return (
    <div>
      <button type="button">Control de trabajo</button>
      <button
        type="button"
        onClick={() =>
          notificar({
            id: "conf-1",
            gravedad: "listo",
            titulo: "Versión V2 guardada",
            detalle: "Vialidad Tramo 3 · 1.284.560,00 Bs sin IVA",
          })
        }
      >
        Guardar versión
      </button>
      <button
        type="button"
        onClick={() =>
          notificar({
            id: "info-1",
            gravedad: "info",
            titulo: "Lista de precios cargada",
          })
        }
      >
        Avisar lista
      </button>
      <button
        type="button"
        onClick={() =>
          notificar({
            id: "adv-1",
            gravedad: "advertencia",
            titulo: "Precio vencido",
            detalle: "El aditivo plastificante de la lista de julio venció el 31/10/2026.",
            enlace: { texto: "Ver en Precios de la empresa", ruta: "/precios/empresa" },
          })
        }
      >
        Avisar vencimiento
      </button>
    </div>
  );
}

function montarEscena() {
  return render(
    <MemoryRouter>
      <ProveedorDeAnuncios>
        <ProveedorDeNotificaciones>
          <Disparadores />
          <RegionDeNotificaciones />
        </ProveedorDeNotificaciones>
      </ProveedorDeAnuncios>
    </MemoryRouter>,
  );
}

describe("RegionDeNotificaciones", () => {
  test("pinta la región «Notificaciones nuevas» sin robar el foco, con gravedad en palabra, detalle, enlace y botón Cerrar", () => {
    const { container } = montarEscena();
    const control = screen.getByRole("button", { name: "Control de trabajo" });
    control.focus();
    expect(control).toHaveFocus();

    fireEvent.click(screen.getByRole("button", { name: "Avisar vencimiento" }));
    expect(control).toHaveFocus();

    const region = screen.getByRole("region", { name: "Notificaciones nuevas" });
    expect(region).not.toHaveAttribute("aria-live");
    expect(within(region).getByText("Advertencia")).toBeInTheDocument();
    expect(within(region).getByText("Precio vencido")).toBeInTheDocument();
    expect(
      within(region).getByText("El aditivo plastificante de la lista de julio venció el 31/10/2026."),
    ).toBeInTheDocument();
    expect(within(region).getByRole("link", { name: "Ver en Precios de la empresa" })).toHaveAttribute(
      "href",
      "/precios/empresa",
    );

    const cerrar = within(region).getByRole("button", { name: /Cerrar.*Precio vencido/i });
    fireEvent.click(cerrar);
    expect(within(region).queryByText("Precio vencido")).toBeNull();
    expect(container.querySelectorAll('[aria-live]')).toHaveLength(2);
  });

  test("la confirmación sigue visible a los 179 s y desaparece a los 180 s", () => {
    vi.useFakeTimers();
    montarEscena();

    fireEvent.click(screen.getByRole("button", { name: "Guardar versión" }));
    const region = screen.getByRole("region", { name: "Notificaciones nuevas" });
    expect(within(region).getByText("Listo")).toBeInTheDocument();
    expect(within(region).getByText("Versión V2 guardada")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(179_000);
    });
    expect(within(region).getByText("Versión V2 guardada")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1_000);
    });
    expect(within(region).queryByText("Versión V2 guardada")).toBeNull();
  });

  test("pausa el temporizador con el cursor encima y lo reanuda con el tiempo restante al salir", () => {
    vi.useFakeTimers();
    montarEscena();

    fireEvent.click(screen.getByRole("button", { name: "Guardar versión" }));
    const region = screen.getByRole("region", { name: "Notificaciones nuevas" });

    act(() => {
      vi.advanceTimersByTime(100_000);
    });
    const tarjeta = within(region).getByText("Versión V2 guardada").closest("article")!;
    fireEvent.mouseEnter(tarjeta);

    act(() => {
      vi.advanceTimersByTime(300_000);
    });
    expect(within(region).getByText("Versión V2 guardada")).toBeInTheDocument();

    fireEvent.mouseLeave(tarjeta);

    act(() => {
      vi.advanceTimersByTime(79_000);
    });
    expect(within(region).getByText("Versión V2 guardada")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1_000);
    });
    expect(within(region).queryByText("Versión V2 guardada")).toBeNull();
  });

  test("pausa el temporizador cuando el foco entra en la notificación y lo reanuda al salir el foco", () => {
    vi.useFakeTimers();
    montarEscena();

    fireEvent.click(screen.getByRole("button", { name: "Guardar versión" }));
    const region = screen.getByRole("region", { name: "Notificaciones nuevas" });

    act(() => {
      vi.advanceTimersByTime(120_000);
    });

    const botonCerrar = within(region).getByRole("button", { name: /Cerrar.*Versión V2 guardada/i });
    act(() => {
      botonCerrar.focus();
    });

    act(() => {
      vi.advanceTimersByTime(250_000);
    });
    expect(within(region).getByText("Versión V2 guardada")).toBeInTheDocument();

    const otroControl = screen.getByRole("button", { name: "Control de trabajo" });
    act(() => {
      otroControl.focus();
    });

    act(() => {
      vi.advanceTimersByTime(59_000);
    });
    expect(within(region).getByText("Versión V2 guardada")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1_000);
    });
    expect(within(region).queryByText("Versión V2 guardada")).toBeNull();
  });

  test("la advertencia no se cierra sola aunque pasen más de 3 minutos", () => {
    vi.useFakeTimers();
    montarEscena();

    fireEvent.click(screen.getByRole("button", { name: "Avisar vencimiento" }));
    const region = screen.getByRole("region", { name: "Notificaciones nuevas" });

    act(() => {
      vi.advanceTimersByTime(600_000);
    });
    expect(within(region).getByText("Precio vencido")).toBeInTheDocument();
  });

  test("nada emerge mientras hay un diálogo modal abierto y sale al cerrarlo", async () => {
    vi.useFakeTimers();

    function ConModal() {
      const [modal, setModal] = useState(true);
      return (
        <MemoryRouter>
          <ProveedorDeAnuncios>
            <ProveedorDeNotificaciones>
              <button type="button" onClick={() => setModal(false)}>
                Terminar modal
              </button>
              <Disparadores />
              <RegionDeNotificaciones />
              <Dialogo abierto={modal} titulo="Subir archivo" alCerrar={() => setModal(false)}>
                <p>Seleccione el archivo.</p>
              </Dialogo>
            </ProveedorDeNotificaciones>
          </ProveedorDeAnuncios>
        </MemoryRouter>
      );
    }

    render(<ConModal />);
    fireEvent.click(screen.getByRole("button", { name: "Guardar versión", hidden: true }));

    const regionOculta = screen.getByRole("region", { name: "Notificaciones nuevas", hidden: true });
    expect(within(regionOculta).queryByText("Versión V2 guardada")).toBeNull();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Terminar modal", hidden: true }));
    });

    const region = screen.getByRole("region", { name: "Notificaciones nuevas" });
    expect(within(region).getByText("Versión V2 guardada")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(179_000);
    });
    expect(within(region).getByText("Versión V2 guardada")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1_000);
    });
    expect(within(region).queryByText("Versión V2 guardada")).toBeNull();
  });

  test("al cerrar manualmente una notificación enfocada, pasa el foco a la siguiente o lo devuelve al control previo", () => {
    montarEscena();
    const controlPrevio = screen.getByRole("button", { name: "Control de trabajo" });
    fireEvent.click(screen.getByRole("button", { name: "Guardar versión" }));
    fireEvent.click(screen.getByRole("button", { name: "Avisar vencimiento" }));

    const region = screen.getByRole("region", { name: "Notificaciones nuevas" });
    controlPrevio.focus();

    const cerrarPrimera = within(region).getByRole("button", { name: /Cerrar.*Versión V2 guardada/i });
    const cerrarSegunda = within(region).getByRole("button", { name: /Cerrar.*Precio vencido/i });

    fireEvent.focus(cerrarPrimera, { relatedTarget: controlPrevio });
    cerrarPrimera.focus();
    fireEvent.click(cerrarPrimera);
    expect(cerrarSegunda).toHaveFocus();

    fireEvent.click(cerrarSegunda);
    expect(controlPrevio).toHaveFocus();
  });

  // T4 (mutante RG1): al cerrar una tarjeta del medio el foco pasa a la que le sigue, no a la anterior.
  test("al cerrar la del medio el foco pasa a la siguiente", () => {
    montarEscena();
    fireEvent.click(screen.getByRole("button", { name: "Guardar versión" }));
    fireEvent.click(screen.getByRole("button", { name: "Avisar lista" }));
    fireEvent.click(screen.getByRole("button", { name: "Avisar vencimiento" }));

    const region = screen.getByRole("region", { name: "Notificaciones nuevas" });
    const cerrarMedio = within(region).getByRole("button", { name: /Cerrar.*Lista de precios cargada/i });
    const cerrarSiguiente = within(region).getByRole("button", { name: /Cerrar.*Precio vencido/i });
    cerrarMedio.focus();
    fireEvent.click(cerrarMedio);
    expect(cerrarSiguiente).toHaveFocus();
  });

  // T4 (mutante RG3): con un diálogo modal abierto el reloj de las confirmaciones se detiene.
  test("el reloj de una confirmación se detiene mientras hay un diálogo modal abierto", async () => {
    vi.useFakeTimers();
    function ConModalPosterior() {
      const [modal, setModal] = useState(false);
      return (
        <MemoryRouter>
          <ProveedorDeAnuncios>
            <ProveedorDeNotificaciones>
              <button type="button" onClick={() => setModal(true)}>
                Abrir modal
              </button>
              <button type="button" onClick={() => setModal(false)}>
                Terminar modal
              </button>
              <Disparadores />
              <RegionDeNotificaciones />
              <Dialogo abierto={modal} titulo="Subir archivo" alCerrar={() => setModal(false)}>
                <p>Seleccione el archivo.</p>
              </Dialogo>
            </ProveedorDeNotificaciones>
          </ProveedorDeAnuncios>
        </MemoryRouter>
      );
    }
    render(<ConModalPosterior />);
    fireEvent.click(screen.getByRole("button", { name: "Guardar versión" }));
    act(() => {
      vi.advanceTimersByTime(100_000);
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Abrir modal" }));
    });
    act(() => {
      vi.advanceTimersByTime(300_000);
    });
    const region = screen.getByRole("region", { name: "Notificaciones nuevas", hidden: true });
    expect(within(region).getByText("Versión V2 guardada")).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Terminar modal", hidden: true }));
    });
    act(() => {
      vi.advanceTimersByTime(79_000);
    });
    expect(within(region).getByText("Versión V2 guardada")).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(1_000);
    });
    expect(within(region).queryByText("Versión V2 guardada")).toBeNull();
  });

  test("el SCSS compila, usa solo tokens --silice-*, sin font-size en px y respeta prefers-reduced-motion", () => {
    // En una variable: con el texto literal, Vite reescribe new URL(...) como un recurso y deja de ser file:.
    const relativa = "./RegionDeNotificaciones.scss";
    const ruta = fileURLToPath(new URL(relativa, import.meta.url));
    const css = sass.compile(ruta).css;
    expect(css).toMatch(/21\.25rem/);
    expect(css).toMatch(/prefers-reduced-motion:\s*no-preference/);
    expect(css).toMatch(/prefers-reduced-motion:\s*reduce/);
    expect(css).not.toMatch(/font-size:\s*[\d.]+(px|pt)/);
    expect(css).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(css).not.toMatch(/\brgba?\(/);
  });
});
