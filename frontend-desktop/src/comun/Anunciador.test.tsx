import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { ProveedorDeAnuncios, useAnunciar } from "./Anunciador";
import { Dialogo } from "./Dialogo";

afterEach(() => {
  vi.useRealTimers();
});

function EmisorDePrueba() {
  const anunciar = useAnunciar();
  return (
    <div>
      <button type="button" onClick={() => anunciar("Total actualizado: 1.250,50 Bs")}>
        Anunciar cambio
      </button>
      <button type="button" onClick={() => anunciar("No se pudo guardar la versión", { urgente: true })}>
        Anunciar error urgente
      </button>
    </div>
  );
}

describe("Anunciador", () => {
  test("renderiza sus hijos y las dos regiones vivas ocultas sin role=alert ni atributo title", () => {
    const { container } = render(
      <ProveedorDeAnuncios>
        <p>Contenido de la obra</p>
      </ProveedorDeAnuncios>,
    );

    expect(screen.getByText("Contenido de la obra")).toBeInTheDocument();

    const cortes = screen.getByRole("status");
    expect(cortes).toHaveClass("cds--visually-hidden");
    expect(cortes).toHaveAttribute("aria-live", "polite");
    expect(cortes).toHaveTextContent("");

    const urgente = container.querySelector('[aria-live="assertive"]');
    expect(urgente).not.toBeNull();
    expect(urgente).toHaveClass("cds--visually-hidden");
    expect(urgente).toHaveAttribute("aria-atomic", "true");
    expect(urgente).not.toHaveAttribute("role");
    expect(screen.queryByRole("alert")).toBeNull();
    expect(urgente).toHaveTextContent("");

    expect(container.querySelectorAll("[title]")).toHaveLength(0);
  });

  test("por omisión escribe en la región polite y deja vacía la assertive", async () => {
    const u = userEvent.setup();
    const { container } = render(
      <ProveedorDeAnuncios>
        <EmisorDePrueba />
      </ProveedorDeAnuncios>,
    );

    await u.click(screen.getByRole("button", { name: "Anunciar cambio" }));

    expect(screen.getByRole("status")).toHaveTextContent("Total actualizado: 1.250,50 Bs");
    expect(container.querySelector('[aria-live="assertive"]')).toHaveTextContent("");
  });

  test("con urgente escribe en la región assertive y deja vacía la polite", async () => {
    const u = userEvent.setup();
    const { container } = render(
      <ProveedorDeAnuncios>
        <EmisorDePrueba />
      </ProveedorDeAnuncios>,
    );

    await u.click(screen.getByRole("button", { name: "Anunciar error urgente" }));

    expect(container.querySelector('[aria-live="assertive"]')).toHaveTextContent("No se pudo guardar la versión");
    expect(screen.getByRole("status")).toHaveTextContent("");
  });

  test("si el mismo texto se repite, vacía la región y lo vuelve a anunciar en el siguiente cuadro", () => {
    vi.useFakeTimers();
    const { container } = render(
      <ProveedorDeAnuncios>
        <EmisorDePrueba />
      </ProveedorDeAnuncios>,
    );

    const botonCortes = screen.getByRole("button", { name: "Anunciar cambio" });
    const regionCortes = screen.getByRole("status");

    fireEvent.click(botonCortes);
    expect(regionCortes).toHaveTextContent("Total actualizado: 1.250,50 Bs");

    fireEvent.click(botonCortes);
    expect(regionCortes).toHaveTextContent("");

    act(() => {
      vi.runAllTimers();
    });
    expect(regionCortes).toHaveTextContent("Total actualizado: 1.250,50 Bs");

    const botonUrgente = screen.getByRole("button", { name: "Anunciar error urgente" });
    const regionUrgente = container.querySelector('[aria-live="assertive"]');

    fireEvent.click(botonUrgente);
    expect(regionUrgente).toHaveTextContent("No se pudo guardar la versión");

    fireEvent.click(botonUrgente);
    expect(regionUrgente).toHaveTextContent("");

    act(() => {
      vi.runAllTimers();
    });
    expect(regionUrgente).toHaveTextContent("No se pudo guardar la versión");
  });

  test("fuera del proveedor, anunciar no rompe ni monta regiones", async () => {
    const u = userEvent.setup();
    const { container } = render(<EmisorDePrueba />);

    await u.click(screen.getByRole("button", { name: "Anunciar cambio" }));
    await u.click(screen.getByRole("button", { name: "Anunciar error urgente" }));

    expect(screen.queryByRole("status")).toBeNull();
    expect(container.querySelector("[aria-live]")).toBeNull();
  });

  test("al desmontar el proveedor limpia los temporizadores pendientes", () => {
    vi.useFakeTimers();
    const { unmount } = render(
      <ProveedorDeAnuncios>
        <EmisorDePrueba />
      </ProveedorDeAnuncios>,
    );

    const botonCortes = screen.getByRole("button", { name: "Anunciar cambio" });
    const botonUrgente = screen.getByRole("button", { name: "Anunciar error urgente" });

    fireEvent.click(botonCortes);
    fireEvent.click(botonCortes);
    fireEvent.click(botonUrgente);
    fireEvent.click(botonUrgente);

    expect(vi.getTimerCount()).toBe(2);

    unmount();

    expect(vi.getTimerCount()).toBe(0);
  });
});

function DialogoConEmisor({ abierto, nombre = "Guardar versión" }: { abierto: boolean; nombre?: string }) {
  return (
    <Dialogo abierto={abierto} titulo={nombre} alCerrar={() => {}}>
      <p>Contenido del diálogo</p>
    </Dialogo>
  );
}

function PruebaDeDialogo() {
  const [abierto, setAbierto] = useState(false);
  const anunciar = useAnunciar();
  return (
    <div>
      <button type="button" onClick={() => setAbierto((previo) => !previo)}>
        Alternar diálogo
      </button>
      <button type="button" onClick={() => anunciar("Guardado")}>
        Anunciar guardado
      </button>
      <button type="button" onClick={() => anunciar("Falló el envío", { urgente: true })}>
        Anunciar fallo
      </button>
      <DialogoConEmisor abierto={abierto} />
    </div>
  );
}

describe("Anunciador dentro de un diálogo modal", () => {
  test("con un diálogo abierto, el anuncio aparece dentro del <dialog> y no en la raíz; al cerrar vuelve a la raíz", () => {
    const { container } = render(
      <ProveedorDeAnuncios>
        <PruebaDeDialogo />
      </ProveedorDeAnuncios>,
    );
    const raiz = Array.from(container.querySelectorAll<HTMLElement>('[role="status"]'));
    expect(raiz).toHaveLength(1);

    fireEvent.click(screen.getByRole("button", { name: "Alternar diálogo" }));
    const dialogo = screen.getByRole("dialog");
    const regionDelDialogo = within(dialogo).getByRole("status");
    expect(regionDelDialogo).toHaveClass("cds--visually-hidden");
    expect(regionDelDialogo).toHaveAttribute("aria-live", "polite");
    expect(dialogo.querySelector('[aria-live="assertive"]')).toHaveAttribute("aria-atomic", "true");

    fireEvent.click(screen.getByRole("button", { name: "Anunciar guardado" }));
    expect(regionDelDialogo).toHaveTextContent("Guardado");
    expect(raiz[0]).toHaveTextContent("");

    fireEvent.click(screen.getByRole("button", { name: "Anunciar fallo" }));
    expect(dialogo.querySelector('[aria-live="assertive"]')).toHaveTextContent("Falló el envío");

    fireEvent.click(screen.getByRole("button", { name: "Alternar diálogo" }));
    fireEvent.click(screen.getByRole("button", { name: "Anunciar guardado" }));
    expect(raiz[0]).toHaveTextContent("Guardado");
  });

  test("sin ProveedorDeAnuncios, el diálogo funciona igual y no monta regiones vivas", () => {
    render(<DialogoConEmisor abierto />);
    const dialogo = screen.getByRole("dialog");
    expect(dialogo.querySelector("[aria-live]")).toBeNull();
  });

  test("con dos diálogos abiertos escribe en el más reciente y, al cerrarlo, en el anterior", () => {
    function Dos({ segundo }: { segundo: boolean }) {
      const anunciar = useAnunciar();
      return (
        <div>
          <button type="button" onClick={() => anunciar("Aviso")}>
            Avisar
          </button>
          <Dialogo abierto titulo="Primero" alCerrar={() => {}}>
            <p>uno</p>
          </Dialogo>
          <Dialogo abierto={segundo} titulo="Segundo" alCerrar={() => {}}>
            <p>dos</p>
          </Dialogo>
        </div>
      );
    }
    const { rerender } = render(
      <ProveedorDeAnuncios>
        <Dos segundo />
      </ProveedorDeAnuncios>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Avisar" }));
    expect(within(screen.getByRole("dialog", { name: "Segundo" })).getByRole("status")).toHaveTextContent("Aviso");
    expect(within(screen.getByRole("dialog", { name: "Primero" })).getByRole("status")).toHaveTextContent("");

    rerender(
      <ProveedorDeAnuncios>
        <Dos segundo={false} />
      </ProveedorDeAnuncios>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Avisar" }));
    expect(within(screen.getByRole("dialog", { name: "Primero" })).getByRole("status")).toHaveTextContent("Aviso");
  });
});
