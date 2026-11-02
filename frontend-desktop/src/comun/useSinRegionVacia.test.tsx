import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { useSinRegionVacia } from "./useSinRegionVacia";

function Prueba({ conContador }: { conContador: boolean }) {
  const raiz = useSinRegionVacia<HTMLDivElement>(".region", conContador);
  return (
    <div ref={raiz}>
      <span className="region" role="alert" aria-live="polite" aria-atomic="true" />
      <span className="otra" role="alert" />
    </div>
  );
}

describe("useSinRegionVacia", () => {
  test("sin contador quita role, aria-live y aria-atomic de las regiones que coinciden con el selector, y solo de ellas", () => {
    const { container } = render(<Prueba conContador={false} />);
    const region = container.querySelector(".region")!;
    expect(region.hasAttribute("role")).toBe(false);
    expect(region.hasAttribute("aria-live")).toBe(false);
    expect(region.hasAttribute("aria-atomic")).toBe(false);
    expect(container.querySelector(".otra")).toHaveAttribute("role", "alert");
  });

  test("con contador las deja como estan", () => {
    const { container } = render(<Prueba conContador />);
    expect(container.querySelector(".region")).toHaveAttribute("role", "alert");
  });
});
