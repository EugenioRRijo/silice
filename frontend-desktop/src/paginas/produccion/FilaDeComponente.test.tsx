import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { FilaDeComponente } from "./FilaDeComponente";

// Segunda pasada de navegador (31-10): el subrayado de «Código» quedaba 10 px más alto que el de los demás campos de la fila
// porque el campo con búsqueda se pintaba en tamaño pequeño (32 px) junto a campos de 40 px.
describe("la fila de un componente de la receta", () => {
  test("el código mide lo mismo que los demás campos de la fila (tamaño mediano)", () => {
    render(
      <FilaDeComponente
        numero={1}
        base="r"
        fila={{ codigo: "", cantidad: "", unidad: "", tipo: "" }}
        sePuedeQuitar
        puedeMarcarLigante={false}
        alCambiar={() => {}}
        alQuitar={() => {}}
        alExpirar={() => {}}
      />,
    );
    const codigo = document.getElementById("r-codigo") as HTMLElement;
    expect(codigo.className).toContain("cds--text-input--md");
    expect(codigo.className).not.toContain("cds--text-input--sm");
    expect((document.getElementById("r-cantidad") as HTMLElement).className).toContain("cds--text-input");
  });

  // Tarea 16c: la casilla del ligante es un control con nombre y solo la ve quien puede registrar recetas.
  test.each([
    [true, 1],
    [false, 0],
  ])("con puedeMarcarLigante=%s hay %i casillas «Es el asfalto (ligante)»", (puede, cuantas) => {
    render(
      <FilaDeComponente
        numero={1}
        base="r"
        fila={{ codigo: "CA-30", cantidad: "", unidad: "t", tipo: "comprado", esLigante: true }}
        sePuedeQuitar
        puedeMarcarLigante={puede}
        alCambiar={() => {}}
        alQuitar={() => {}}
        alExpirar={() => {}}
      />,
    );
    const casillas = screen.queryAllByRole("checkbox", { name: "Es el asfalto (ligante)" });
    expect(casillas).toHaveLength(cuantas);
    if (puede) expect(casillas[0]).toBeChecked();
  });
});

// Prueba en vivo 2026-11-18 (frente D): el código de un componente ofrecía el propio producto de la receta (MEZ-A con
// MEZ-A), que el servidor ahora rechaza. La lista de sugerencias ya no lo ofrece. Materiales ficticios.
describe("las sugerencias del código de un componente", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("no ofrecen el propio producto de la receta, sí los demás materiales", async () => {
    const materiales = [
      { codigo: "MZP-01", nombre: "Mezcla asfáltica ficticia", unidad_venta: "t", activo: true },
      { codigo: "AGR-12", nombre: "Agregado grueso ficticio", unidad_venta: "t", activo: true },
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async (entrada) =>
        String(entrada) === "/v1/produccion/materiales"
          ? new Response(JSON.stringify(materiales), { status: 200 })
          : new Response(JSON.stringify({ tabla: "insumos", resultados: [], hay_mas: false }), { status: 200 }),
      ),
    );
    function Pagina() {
      const [codigo, setCodigo] = useState("");
      return (
        <FilaDeComponente
          numero={1}
          base="r"
          producto=" MZP-01 "
          fila={{ codigo, cantidad: "", unidad: "", tipo: "" }}
          sePuedeQuitar
          puedeMarcarLigante={false}
          alCambiar={(cambio) => setCodigo(cambio.codigo ?? codigo)}
          alQuitar={() => {}}
          alExpirar={() => {}}
        />
      );
    }
    render(<Pagina />);
    await userEvent.type(screen.getByRole("combobox", { name: /Código/ }), "fic");
    expect(await screen.findByRole("option", { name: /Agregado grueso ficticio/ })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /Mezcla asfáltica ficticia/ })).toBeNull();
  });
});
