import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { App } from "./App";

describe("App", () => {
  test("la cabecera dice Sílice", () => {
    render(<App />);
    const cabecera = screen.getByRole("banner");
    expect(cabecera).toHaveTextContent("Sílice");
  });

  test("el estado inicial pide entrar", () => {
    render(<App />);
    expect(screen.getByRole("main")).toHaveTextContent("Entrar");
  });
});
