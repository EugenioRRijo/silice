import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Pildora } from "./Pildora";

describe("Pildora", () => {
  it("muestra el número y se oculta a los lectores de pantalla (el nombre accesible lo dice el enlace)", () => {
    render(<Pildora valor={4} />);
    const p = screen.getByText("4");
    expect(p).toHaveClass("silice-pildora");
    expect(p).toHaveAttribute("aria-hidden", "true");
  });
});
