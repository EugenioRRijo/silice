import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { MontoExacto } from "./MontoExacto";

describe("MontoExacto", () => {
  test("formatea miles con punto y decimales con coma, con unidad opcional y clase tabular silice-cifra", () => {
    const { rerender } = render(<MontoExacto texto="1250.50" exacto="1250.5037" />);
    const cifra = screen.getByText("1.250,50");
    expect(cifra).toBeInTheDocument();
    expect(cifra).toHaveClass("silice-cifra");

    rerender(<MontoExacto texto="9876543.20" exacto="9876543.2049" unidad="Bs" />);
    expect(screen.getByText("9.876.543,20 Bs")).toHaveClass("silice-cifra");
  });

  test("ningún elemento lleva el atributo title en ninguna variante", async () => {
    const u = userEvent.setup();
    const { container, rerender } = render(<MontoExacto texto="1250.50" exacto="1250.5037" unidad="Bs" />);
    expect(container.querySelectorAll("[title]")).toHaveLength(0);

    await u.click(screen.getByRole("button", { name: "Ver el valor exacto de 1.250,50 Bs" }));
    expect(container.querySelectorAll("[title]")).toHaveLength(0);

    rerender(<MontoExacto texto="1250.50" exacto="1250.50" unidad="Bs" />);
    expect(container.querySelectorAll("[title]")).toHaveLength(0);

    rerender(<MontoExacto texto="1250.50" exacto="1250.5037" unidad="Bs" enLinea />);
    expect(container.querySelectorAll("[title]")).toHaveLength(0);
  });

  test("cuando exacto difiere de texto sin nombre expone el botón con la cifra formateada y su unidad si la hay", () => {
    const { rerender } = render(<MontoExacto texto="1250.50" exacto="1250.5037" />);
    const boton = screen.getByRole("button", { name: "Ver el valor exacto de 1.250,50" });
    expect(boton).toBeInTheDocument();
    expect(boton).toHaveAttribute("aria-expanded", "false");

    rerender(<MontoExacto texto="1250.50" exacto="1250.5037" unidad="Bs" />);
    expect(screen.getByRole("button", { name: "Ver el valor exacto de 1.250,50 Bs" })).toBeInTheDocument();
  });

  test("cuando se pasa nombre, el botón lo usa como nombre accesible en lugar de la cifra", () => {
    render(<MontoExacto texto="1250.50" exacto="1250.5037" unidad="Bs" nombre="del total" />);
    const boton = screen.getByRole("button", { name: "Ver el valor exacto del total" });
    expect(boton).toBeInTheDocument();
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("button", { name: "Ver el valor exacto de 1.250,50 Bs" })).toBeNull();
  });

  test("dos montos distintos en la misma vista exponen botones con nombres distintos", () => {
    render(
      <div>
        <MontoExacto texto="1250.50" exacto="1250.5037" unidad="Bs" nombre="del libro" />
        <MontoExacto texto="1300.00" exacto="1300.0042" unidad="Bs" nombre="según Sílice" />
      </div>,
    );
    expect(screen.getAllByRole("button")).toHaveLength(2);
    const botonLibro = screen.getByRole("button", { name: "Ver el valor exacto del libro" });
    const botonSilice = screen.getByRole("button", { name: "Ver el valor exacto según Sílice" });
    expect(botonLibro).toBeInTheDocument();
    expect(botonSilice).toBeInTheDocument();
    expect(botonLibro).not.toBe(botonSilice);
  });

  test("se alcanza y se abre con el teclado usando Enter y muestra el valor exacto", async () => {
    const u = userEvent.setup();
    const { container } = render(<MontoExacto texto="1250.50" exacto="1250.5037" />);
    const boton = screen.getByRole("button", { name: "Ver el valor exacto de 1.250,50" });

    expect(container.querySelector(".cds--toggletip--open")).toBeNull();
    expect(boton).not.toHaveAttribute("aria-describedby");

    await u.tab();
    expect(boton).toHaveFocus();
    await u.keyboard("{Enter}");

    expect(boton).toHaveAttribute("aria-expanded", "true");
    expect(container.querySelector(".cds--toggletip--open")).not.toBeNull();
    expect(boton).toHaveAccessibleDescription("Valor exacto: 1.250,5037");
    expect(screen.getByText("Valor exacto: 1.250,5037")).toBeInTheDocument();
  });

  test("se alcanza y se abre con el teclado usando Espacio y muestra el valor exacto con su unidad", async () => {
    const u = userEvent.setup();
    const { container } = render(<MontoExacto texto="1250.50" exacto="1250.5037" unidad="USD" />);
    const boton = screen.getByRole("button", { name: "Ver el valor exacto de 1.250,50 USD" });

    await u.tab();
    expect(boton).toHaveFocus();
    await u.keyboard(" ");

    expect(boton).toHaveAttribute("aria-expanded", "true");
    expect(container.querySelector(".cds--toggletip--open")).not.toBeNull();
    expect(boton).toHaveAccessibleDescription("Valor exacto: 1.250,5037 USD");
    expect(screen.getByText("Valor exacto: 1.250,5037 USD")).toBeInTheDocument();
  });

  test("cuando exacto es igual a texto no monta ningún Toggletip", () => {
    render(<MontoExacto texto="1250.50" exacto="1250.50" unidad="Bs" />);
    expect(screen.getByText("1.250,50 Bs")).toHaveClass("silice-cifra");
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.queryByText(/Valor exacto/)).toBeNull();
  });

  test("en modo enLinea muestra el exacto a la vista sin botón cuando difieren, y solo la cifra cuando son iguales", () => {
    const { container, rerender } = render(<MontoExacto texto="1250.50" exacto="1250.5037" enLinea />);
    expect(screen.getByText("1.250,50 (exacto: 1.250,5037)")).toHaveClass("silice-cifra");
    expect(screen.queryByRole("button")).toBeNull();

    rerender(<MontoExacto texto="1250.50" exacto="1250.5037" unidad="Bs" enLinea />);
    expect(screen.getByText("1.250,50 Bs (exacto: 1.250,5037 Bs)")).toHaveClass("silice-cifra");
    expect(screen.queryByRole("button")).toBeNull();

    rerender(<MontoExacto texto="1250.50" exacto="1250.50" enLinea />);
    expect(container.textContent).toBe("1.250,50");
    expect(screen.getByText("1.250,50")).toHaveClass("silice-cifra");
    expect(screen.queryByRole("button")).toBeNull();
  });

  test("formatea valores negativos en vista y exacto tanto en modo botón como en línea", async () => {
    const u = userEvent.setup();
    const { rerender } = render(<MontoExacto texto="-1250.50" exacto="-1250.5037" />);
    expect(screen.getByText("-1.250,50")).toHaveClass("silice-cifra");

    const boton = screen.getByRole("button", { name: "Ver el valor exacto de -1.250,50" });
    await u.click(boton);
    expect(boton).toHaveAccessibleDescription("Valor exacto: -1.250,5037");
    expect(screen.getByText("Valor exacto: -1.250,5037")).toBeInTheDocument();

    rerender(<MontoExacto texto="-1250.50" exacto="-1250.5037" enLinea />);
    expect(screen.getByText("-1.250,50 (exacto: -1.250,5037)")).toHaveClass("silice-cifra");
    expect(screen.queryByRole("button")).toBeNull();
  });
});
