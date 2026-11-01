import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { MarcoDeDialogo } from "./MarcoDeDialogo";

// jsdom no mide: se fijan las alturas del cuerpo para probar la señal de «hay más debajo» (segunda pasada de navegador,
// 31-10: «Registrar un costo» tenía el campo «Fuente» tapado por el pie y ninguna señal de desplazamiento).
function medidas(total: number, visible: number) {
  vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockReturnValue(total);
  vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(visible);
}

function dibujar() {
  render(
    <MarcoDeDialogo titulo="Registrar un costo" alCerrar={() => {}} pie={<button type="button">Aceptar</button>}>
      <input aria-label="Fuente" />
    </MarcoDeDialogo>,
  );
  const zona = document.querySelector(".silice-dialogo__zona") as HTMLElement;
  const cuerpo = document.querySelector(".silice-dialogo__cuerpo") as HTMLElement;
  return { zona, cuerpo };
}

afterEach(() => vi.restoreAllMocks());

describe("el cuerpo de un diálogo avisa cuando hay más contenido debajo", () => {
  test("con contenido que no cabe, la zona lleva la marca de «hay más abajo»", () => {
    medidas(500, 200);
    const { zona } = dibujar();
    expect(zona).toHaveClass("silice-dialogo__zona--mas-abajo");
    expect(screen.getByLabelText("Fuente")).toBeInTheDocument();
  });

  test("al llegar al final del desplazamiento la marca se va", () => {
    medidas(500, 200);
    const { zona, cuerpo } = dibujar();
    vi.spyOn(cuerpo, "scrollTop", "get").mockReturnValue(300);
    fireEvent.scroll(cuerpo);
    expect(zona).not.toHaveClass("silice-dialogo__zona--mas-abajo");
  });

  test("si todo cabe, no hay marca", () => {
    medidas(200, 200);
    const { zona } = dibujar();
    expect(zona).not.toHaveClass("silice-dialogo__zona--mas-abajo");
  });
});
