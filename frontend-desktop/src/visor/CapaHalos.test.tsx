import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import type { HallazgoLibroRespuesta } from "../api/tipos";
import { CapaHalos } from "./CapaHalos";
import { construirHalos } from "./halos";
import { clave, crearHojaFalsa } from "./hojaFalsa";

const hallazgos: HallazgoLibroRespuesta[] = [
  {
    codigo: "L3",
    severidad: "CRITICO",
    descripcion: "El total no coincide",
    celda: "PRESUPUESTO!F12",
    impacto: "238.407",
    accion: "Corregir",
  },
  {
    codigo: "L5",
    severidad: "ADVERTENCIA",
    descripcion: "Precio distinto",
    celda: "APU-01!G48",
    impacto: null,
    accion: "Igualar",
  },
  {
    codigo: "ATIPICO",
    severidad: "INFO",
    descripcion: "Precio atipico",
    celda: "PRESUPUESTO!B3",
    impacto: null,
    accion: "Revisar",
  },
];

function montar() {
  const hoja = crearHojaFalsa("PRESUPUESTO");
  hoja.posiciones.set(clave({ hoja: "PRESUPUESTO", fila0: 11, columna0: 5 }), { x: 300, y: 120, ancho: 80, alto: 20 });
  hoja.posiciones.set(clave({ hoja: "PRESUPUESTO", fila0: 2, columna0: 1 }), { x: 100, y: 60, ancho: 80, alto: 20 });
  hoja.posiciones.set(clave({ hoja: "APU-01", fila0: 47, columna0: 6 }), { x: 200, y: 200, ancho: 80, alto: 20 });
  const { halos } = construirHalos(hallazgos);
  const onElegir = vi.fn();
  const vista = render(
    <CapaHalos halos={halos} hallazgos={hallazgos} visor={hoja} seleccionado={null} onElegir={onElegir} />,
  );
  return { hoja, onElegir, vista };
}

describe("CapaHalos", () => {
  test("pone un halo con texto accesible solo en las celdas de la hoja que se ve", () => {
    montar();
    expect(screen.getByRole("img", { name: /Crítico.*PRESUPUESTO!F12/ })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Atípico.*PRESUPUESTO!B3/ })).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: /APU-01!G48/ })).not.toBeInTheDocument();
  });

  test("el halo se posiciona con el rectangulo de la celda menos el origen del area de celdas", () => {
    montar();
    const halo = screen.getByRole("img", { name: /Crítico.*PRESUPUESTO!F12/ }).closest(".halo") as HTMLElement;
    // area() empieza en (46, 20): 300 - 46 y 120 - 20.
    expect(halo.style.left).toBe("254px");
    expect(halo.style.top).toBe("100px");
    expect(halo.style.width).toBe("80px");
    expect(halo.style.height).toBe("20px");
  });

  test("el color sale del token de severidad y el atipico del morado", () => {
    montar();
    const critico = screen.getByRole("img", { name: /Crítico/ }).closest(".halo") as HTMLElement;
    const atipico = screen.getByRole("img", { name: /Atípico/ }).closest(".halo") as HTMLElement;
    expect(critico.style.getPropertyValue("--halo-color")).toBe("var(--silice-sev-critico)");
    expect(atipico.style.getPropertyValue("--halo-color")).toBe("var(--silice-atipico)");
  });

  test("al desplazar, la capa se recalcula con la posicion nueva", () => {
    const { hoja } = montar();
    hoja.posiciones.set(clave({ hoja: "PRESUPUESTO", fila0: 11, columna0: 5 }), { x: 300, y: 80, ancho: 80, alto: 20 });
    act(() => hoja.cambiar());
    const halo = screen.getByRole("img", { name: /Crítico/ }).closest(".halo") as HTMLElement;
    expect(halo.style.top).toBe("60px");
  });

  test("si la celda sale del desplazamiento, su halo desaparece", () => {
    const { hoja } = montar();
    hoja.posiciones.set(clave({ hoja: "PRESUPUESTO", fila0: 11, columna0: 5 }), null);
    act(() => hoja.cambiar());
    expect(screen.queryByRole("img", { name: /Crítico/ })).not.toBeInTheDocument();
  });

  test("al cambiar de hoja salen los halos de la otra hoja", () => {
    const { hoja } = montar();
    hoja.fijarHoja("APU-01");
    act(() => hoja.cambiar());
    expect(screen.getByRole("img", { name: /Advertencia.*APU-01!G48/ })).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: /Crítico/ })).not.toBeInTheDocument();
  });

  test("el halo elegido se marca y lo dice con aria-current", () => {
    const hoja = crearHojaFalsa("PRESUPUESTO");
    hoja.posiciones.set(clave({ hoja: "PRESUPUESTO", fila0: 11, columna0: 5 }), { x: 300, y: 120, ancho: 80, alto: 20 });
    const { halos } = construirHalos(hallazgos);
    render(<CapaHalos halos={halos} hallazgos={hallazgos} visor={hoja} seleccionado={0} onElegir={vi.fn()} />);
    expect(screen.getByRole("img", { name: /Crítico/ }).closest(".halo")).toHaveAttribute("aria-current", "true");
  });

  test("clic en la insignia elige el hallazgo", async () => {
    const usuario = userEvent.setup();
    const { onElegir } = montar();
    await usuario.click(screen.getByRole("img", { name: /Crítico/ }));
    expect(onElegir).toHaveBeenCalledWith(0);
  });

  test("sin visor no pinta nada", () => {
    const { halos } = construirHalos(hallazgos);
    const { container } = render(
      <CapaHalos halos={halos} hallazgos={hallazgos} visor={null} seleccionado={null} onElegir={vi.fn()} />,
    );
    expect(container.querySelector(".halo")).toBeNull();
  });

  test("deja de escuchar al desmontarse", () => {
    const hoja = crearHojaFalsa();
    const { halos } = construirHalos(hallazgos);
    const { unmount } = render(
      <CapaHalos halos={halos} hallazgos={hallazgos} visor={hoja} seleccionado={null} onElegir={vi.fn()} />,
    );
    unmount();
    expect(() => hoja.cambiar()).not.toThrow();
  });
});
