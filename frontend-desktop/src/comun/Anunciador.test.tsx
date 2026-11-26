import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";
import { ProveedorDeAnuncios, useAnunciar } from "./Anunciador";

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
