import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ESPACIOS } from "./espacios";
import { ModeTransitionOverlay } from "./ModeTransitionOverlay";

// La cortina entre Obras y las ventanas dedicadas se queda (Eugenio, 2026-11-22: «déjame las animaciones»), pero dura lo
// suyo desde la navegación, no desde el último dibujo de Marco, y no pinta un porcentaje que no mide ninguna carga.

const matchMediaOriginal = window.matchMedia;

function movimientoReducido(reducido: boolean) {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: (consulta: string) => ({
      matches: reducido && consulta.includes("prefers-reduced-motion"),
      media: consulta,
      onchange: null,
      addEventListener() {},
      removeEventListener() {},
      addListener() {},
      removeListener() {},
      dispatchEvent: () => false,
    }),
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  movimientoReducido(false);
});

afterEach(() => {
  vi.useRealTimers();
  Object.defineProperty(window, "matchMedia", { configurable: true, value: matchMediaOriginal });
});

describe("ModeTransitionOverlay", () => {
  test("cierra a su tiempo aunque Marco se repinte y le pase otra función alTerminar", () => {
    const llamadas: string[] = [];
    const { rerender } = render(<ModeTransitionOverlay destino="auditoria" alTerminar={() => llamadas.push("1")} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    // Marco se vuelve a dibujar (carga de obras, pendientes, módulos) con una función nueva en cada dibujo.
    for (const n of ["2", "3", "4"]) {
      act(() => {
        vi.advanceTimersByTime(100);
      });
      rerender(<ModeTransitionOverlay destino="auditoria" alTerminar={() => llamadas.push(n)} />);
    }
    // 300 ms desde la navegación: todavía no termina; a los 340 ms sí, una sola vez y con la función vigente.
    expect(llamadas).toEqual([]);
    act(() => {
      vi.advanceTimersByTime(40);
    });
    expect(llamadas).toEqual(["4"]);
  });

  test("no pinta un porcentaje inventado; la barra animada se queda", () => {
    const { container } = render(<ModeTransitionOverlay destino="precios" alTerminar={vi.fn()} />);
    const cortina = screen.getByRole("status");
    expect(cortina.textContent).not.toMatch(/\d+\s*%/);
    expect(container.querySelector(".silice-transicion__porcentaje")).toBeNull();
    expect(container.querySelector(".silice-transicion__progreso")).not.toBeNull();
  });

  test("dice el mismo nombre del espacio que la barra lateral y el selector, sin numeración ni «Ventana dedicada»", () => {
    const { container } = render(<ModeTransitionOverlay destino="precios" alTerminar={vi.fn()} />);
    const cortina = screen.getByRole("status");
    expect(cortina).toHaveAccessibleName(`Cargando ${ESPACIOS.precios.titulo}`);
    expect(screen.getAllByText(ESPACIOS.precios.titulo)).toHaveLength(1);
    expect(cortina.textContent).not.toMatch(/ventana dedicada|\b0[123]\s*·/i);
    expect(container.querySelector(".silice-transicion__codigo")).toBeNull();
    expect(container.querySelector(".silice-transicion__cabecera")).toBeNull();
  });

  test("con movimiento reducido no anima: no pinta la cortina y termina enseguida", () => {
    movimientoReducido(true);
    const alTerminar = vi.fn();
    const { container } = render(<ModeTransitionOverlay destino="produccion" alTerminar={alTerminar} />);
    expect(container).toBeEmptyDOMElement();
    act(() => {
      vi.advanceTimersByTime(0);
    });
    expect(alTerminar).toHaveBeenCalledTimes(1);
  });

  test("sin destino no pinta nada", () => {
    const { container } = render(<ModeTransitionOverlay destino={null} alTerminar={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});
