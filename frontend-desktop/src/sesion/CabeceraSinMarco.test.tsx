import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import { CabeceraSinMarco } from "./CabeceraSinMarco";

afterEach(cleanup);

// T3 (2026-11-28): el cuadro «S» y la palabra «Sílice» quedaban a 2 px aunque el CSS dijera `gap: 0.5rem`. Causa: el `gap`
// iba en `.cds--header__name`, pero Carbon mete el contenido de HeaderName en un `<span>` único, así que el gap separaba
// ese span de nada. El gap tiene que estar en el elemento que es padre directo del sello y de la palabra.
describe("CabeceraSinMarco: la marca", () => {
  test("el sello «S» y la palabra «Sílice» son hijos directos del mismo elemento de marca (el que lleva el gap)", () => {
    const { container } = render(<CabeceraSinMarco alSalir={() => undefined} />);
    const sello = container.querySelector(".silice-sin-marco__sello") as HTMLElement;
    const marca = sello.parentElement as HTMLElement;
    expect(marca).toHaveClass("silice-sin-marco__marca");
    expect(Array.from(marca.children).map((h) => h.textContent)).toEqual(["S", "Sílice"]);
  });

  test("sigue siendo el enlace a la raíz, con el nombre accesible «Sílice» (el sello está oculto a los lectores)", () => {
    render(<CabeceraSinMarco alSalir={() => undefined} />);
    expect(screen.getByRole("link", { name: "Sílice" })).toHaveAttribute("href", "#/");
  });
});
