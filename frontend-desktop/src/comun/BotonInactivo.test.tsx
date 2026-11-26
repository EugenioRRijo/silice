import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { FormEvent } from "react";
import { describe, expect, test, vi } from "vitest";
import { BotonInactivo } from "./BotonInactivo";

const MOTIVO = "Complete primero el precio unitario de las 2 partidas pendientes.";

describe("BotonInactivo", () => {
  test("existe por rol y nombre con aria-disabled='true', sin atributo disabled y con la variante pedida", () => {
    render(
      <BotonInactivo kind="secondary" motivo={MOTIVO}>
        Aprobar presupuesto
      </BotonInactivo>,
    );

    const boton = screen.getByRole("button", { name: "Aprobar presupuesto" });
    expect(boton).toHaveAttribute("aria-disabled", "true");
    expect(boton).not.toHaveAttribute("disabled");
    expect(boton).not.toBeDisabled();
    expect(boton).toHaveClass("cds--btn--secondary");
    expect(screen.queryByText(MOTIVO)).toBeNull();
  });

  test("permanece en el orden de tabulación y recibe el foco con Tab", async () => {
    const u = userEvent.setup();
    render(
      <div>
        <BotonInactivo motivo={MOTIVO}>Aprobar presupuesto</BotonInactivo>
        <button type="button">Volver a las partidas</button>
      </div>,
    );

    await u.tab();
    expect(screen.getByRole("button", { name: "Aprobar presupuesto" })).toHaveFocus();
  });

  test("al hacer clic muestra y anuncia el motivo sin ejecutar ninguna acción del formulario", async () => {
    const u = userEvent.setup();
    const alEnviar = vi.fn((evento: FormEvent<HTMLFormElement>) => evento.preventDefault());

    render(
      <form onSubmit={alEnviar}>
        <BotonInactivo motivo={MOTIVO}>Aprobar presupuesto</BotonInactivo>
      </form>,
    );

    const boton = screen.getByRole("button", { name: "Aprobar presupuesto" });
    await u.click(boton);

    expect(screen.getByText(MOTIVO)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(MOTIVO);
    expect(boton).toHaveAttribute("aria-expanded", "true");
    expect(boton).toHaveAttribute("aria-describedby");
    expect(alEnviar).not.toHaveBeenCalled();
  });

  test("muestra el motivo con Intro o Espacio y lo cierra con Escape conservando el foco", async () => {
    const u = userEvent.setup();
    const alEnviar = vi.fn((evento: FormEvent<HTMLFormElement>) => evento.preventDefault());

    render(
      <form onSubmit={alEnviar}>
        <BotonInactivo motivo={MOTIVO}>Entregar paquete</BotonInactivo>
      </form>,
    );

    const boton = screen.getByRole("button", { name: "Entregar paquete" });
    await u.tab();
    expect(boton).toHaveFocus();

    await u.keyboard("{Enter}");
    expect(screen.getByText(MOTIVO)).toBeInTheDocument();
    expect(alEnviar).not.toHaveBeenCalled();

    await u.keyboard("{Escape}");
    expect(screen.queryByText(MOTIVO)).toBeNull();
    expect(boton).toHaveFocus();

    await u.keyboard(" ");
    expect(screen.getByText(MOTIVO)).toBeInTheDocument();
    expect(alEnviar).not.toHaveBeenCalled();
  });
});
