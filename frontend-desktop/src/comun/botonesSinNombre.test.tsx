// D10 de la tanda de detalles (hallazgo 19 del recorrido del 01-11-2026): botones sin nombre accesible.
// Los botones internos ocultos (aria-hidden) de Carbon no tienen nombre accesible según AccName §2A y no constituyen
// un defecto de WCAG 2.1 AA. Aquí se comprueban los controles interactivos reales (como el botón para mostrar la
// contraseña en «Entrar») y que las flechas de desplazamiento de pestañas preserven sus oyentes de interacción (la
// flecha izquierda no debe perder sus oyentes al fijar los textos en español).
import { Tab, Tabs } from "@carbon/react";
import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { Entrar } from "../sesion/Entrar";
import { TabList } from "./carbonEs";

describe("botones sin nombre accesible (D10)", () => {
  test("«Entrar»: el control de la contraseña se encuentra por rol y nombre", () => {
    render(<Entrar onEntrar={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Mostrar la contraseña" })).toBeInTheDocument();
  });

  test("las flechas de desplazamiento de las pestañas registran los mismos oyentes de interacción (la izquierda no pierde eventos)", () => {
    const eventosPorElemento = new Map<EventTarget, string[]>();
    const agregarOriginal = EventTarget.prototype.addEventListener;
    const espia = vi.spyOn(EventTarget.prototype, "addEventListener").mockImplementation(function (
      this: EventTarget,
      tipo: string,
      oyente: EventListenerOrEventListenerObject | null,
      opciones?: boolean | AddEventListenerOptions,
    ) {
      const tipos = eventosPorElemento.get(this) ?? [];
      tipos.push(tipo);
      eventosPorElemento.set(this, tipos);
      agregarOriginal.call(this, tipo, oyente, opciones);
    });

    try {
      const hojas = ["PORTADA", "PLAN DE PAGOS", "AUX", "METRADOS", "PRECIOS", "INSUMOS", "CRONOGRAMA", "FÓRMULA"];
      const { container } = render(
        <Tabs>
          <TabList aria-label="Hojas" contained>
            {hojas.map((n) => (
              <Tab key={n}>{n}</Tab>
            ))}
          </TabList>
        </Tabs>,
      );

      const botonIzquierda = container.querySelector<HTMLButtonElement>(".cds--tab--overflow-nav-button--previous");
      const botonDerecha = container.querySelector<HTMLButtonElement>(".cds--tab--overflow-nav-button--next");

      expect(botonIzquierda).toBeInstanceOf(HTMLButtonElement);
      expect(botonDerecha).toBeInstanceOf(HTMLButtonElement);

      const eventosIzquierda = eventosPorElemento.get(botonIzquierda!) ?? [];
      const eventosDerecha = eventosPorElemento.get(botonDerecha!) ?? [];

      expect(eventosDerecha).toContain("click");
      expect(eventosDerecha).toContain("pointerdown");
      expect(eventosIzquierda).toContain("click");
      expect(eventosIzquierda).toContain("pointerdown");
      expect(eventosIzquierda).toEqual(eventosDerecha);
    } finally {
      espia.mockRestore();
    }
  });
});
