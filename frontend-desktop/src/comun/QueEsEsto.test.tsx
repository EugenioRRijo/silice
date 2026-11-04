import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { QueEsEsto } from "./QueEsEsto";

// F4, Tarea 4 (baja 25): el texto largo de cada pestaña ya no va encima; queda tras un «¿Qué es esto?» plegado. Lo usan las
// siete pestañas del Presupuesto y F6 lo convertirá en el panel de ayuda. Datos ficticios.

function montar() {
  return render(
    <div>
      <QueEsEsto titulo="Partidas">
        <p>Las cantidades salen de las partidas que agrega.</p>
      </QueEsEsto>
      <button type="button">Otro control</button>
    </div>,
  );
}

describe("¿Qué es esto?", () => {
  test("empieza plegado: el botón dice que no está expandido y el texto no está en la página", () => {
    montar();
    const boton = screen.getByRole("button", { name: "¿Qué es esto?" });
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Las cantidades salen de las partidas que agrega.")).toBeNull();
  });

  test("al pulsarlo se ve el texto, en una región con el nombre del título, y el botón queda expandido", async () => {
    const u = userEvent.setup();
    montar();
    const boton = screen.getByRole("button", { name: "¿Qué es esto?" });
    await u.click(boton);
    expect(boton).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("region", { name: "Partidas" })).toHaveTextContent("Las cantidades salen de las partidas que agrega.");
    expect(boton).toHaveAttribute("aria-controls", screen.getByRole("region", { name: "Partidas" }).id);
  });

  test("Esc lo cierra y el foco vuelve al botón", async () => {
    const u = userEvent.setup();
    montar();
    const boton = screen.getByRole("button", { name: "¿Qué es esto?" });
    await u.click(boton);
    await u.keyboard("{Escape}");
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Las cantidades salen de las partidas que agrega.")).toBeNull();
    expect(boton).toHaveFocus();
  });

  test("se alcanza y se abre con el teclado", async () => {
    const u = userEvent.setup();
    montar();
    await u.tab();
    expect(screen.getByRole("button", { name: "¿Qué es esto?" })).toHaveFocus();
    await u.keyboard("{Enter}");
    expect(screen.getByText("Las cantidades salen de las partidas que agrega.")).toBeInTheDocument();
  });
});
