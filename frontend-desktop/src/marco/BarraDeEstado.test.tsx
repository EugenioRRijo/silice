import { fileURLToPath } from "node:url";
import { render, screen, within } from "@testing-library/react";
import * as sass from "sass";
import { describe, expect, test } from "vitest";
import { ProveedorDeNotificaciones, crearAlmacenEnMemoria } from "../comun/notificaciones/ProveedorDeNotificaciones";
import { BarraDeEstado, formatearUltimoGuardado } from "./BarraDeEstado";

describe("BarraDeEstado", () => {
  test("muestra la carpeta abierta, «Guardado hace …» y la campanita con sus sin leer", () => {
    const ahora = new Date("2026-11-26T14:10:00.000Z");
    const haceDosMin = new Date("2026-11-26T14:08:00.000Z");
    const almacen = crearAlmacenEnMemoria([
      { id: "1", gravedad: "listo", titulo: "Versión V2 guardada", creada: "2026-11-26T14:08:00.000Z", leida: false },
      { id: "2", gravedad: "advertencia", titulo: "Precio vencido", creada: "2026-11-26T13:50:00.000Z", leida: false },
    ]);

    render(
      <ProveedorDeNotificaciones almacen={almacen} ahora={() => ahora}>
        <BarraDeEstado carpeta="Obras 2026" ultimoGuardado={haceDosMin} ahora={ahora} />
      </ProveedorDeNotificaciones>,
    );

    const barra = screen.getByRole("contentinfo", { name: "Barra de estado" });
    expect(within(barra).getByText("Carpeta Obras 2026")).toBeInTheDocument();
    expect(within(barra).getByText("Guardado hace 2 min")).toBeInTheDocument();
    expect(within(barra).getByRole("button", { name: "Notificaciones, 2 sin leer" })).toBeInTheDocument();
  });

  test("no duplica la palabra «Carpeta» cuando el título ya empieza por ella", () => {
    render(
      <ProveedorDeNotificaciones>
        <BarraDeEstado carpeta="Carpeta de la empresa" />
      </ProveedorDeNotificaciones>,
    );

    const barra = screen.getByRole("contentinfo", { name: "Barra de estado" });
    expect(within(barra).getByText("Carpeta de la empresa")).toBeInTheDocument();
    expect(within(barra).queryByText(/Carpeta Carpeta/)).toBeNull();
    expect(within(barra).queryByText(/Guardado hace/)).toBeNull();
  });

  test("si no hay carpeta ni fecha de último guardado, omite esas partes y deja la campanita", () => {
    render(
      <ProveedorDeNotificaciones>
        <BarraDeEstado />
      </ProveedorDeNotificaciones>,
    );

    const barra = screen.getByRole("contentinfo", { name: "Barra de estado" });
    expect(within(barra).queryByText(/Carpeta/)).toBeNull();
    expect(within(barra).queryByText(/Guardado hace/)).toBeNull();
    expect(within(barra).getByRole("button", { name: "Notificaciones" })).toBeInTheDocument();
  });

  test("formatea segundos, horas y días con punto de miles cuando corresponde", () => {
    const ahora = new Date("2026-11-26T14:10:00.000Z");
    const haceDiezSeg = new Date(ahora.getTime() - 10_000);
    const { rerender } = render(
      <ProveedorDeNotificaciones>
        <BarraDeEstado carpeta="Obras 2026" ultimoGuardado={haceDiezSeg} ahora={ahora} />
      </ProveedorDeNotificaciones>,
    );
    expect(screen.getByText("Guardado hace 10 s")).toBeInTheDocument();

    const haceTresHoras = new Date(ahora.getTime() - 3 * 3_600_000);
    rerender(
      <ProveedorDeNotificaciones>
        <BarraDeEstado carpeta="Obras 2026" ultimoGuardado={haceTresHoras} ahora={ahora} />
      </ProveedorDeNotificaciones>,
    );
    expect(screen.getByText("Guardado hace 3 h")).toBeInTheDocument();
  });

  // T4 (mutantes B1, B3, B4): los bordes de cada tramo de «Guardado hace …».
  test.each([
    [0, "Guardado hace unos segundos"],
    [1, "Guardado hace 1 s"],
    [59, "Guardado hace 59 s"],
    [60, "Guardado hace 1 min"],
    [3_599, "Guardado hace 59 min"],
    [3_600, "Guardado hace 1 h"],
    [86_399, "Guardado hace 23 h"],
    [86_400, "Guardado hace 1 día"],
    [172_800, "Guardado hace 2 días"],
  ])("a los %i segundos dice «%s»", (segundos, esperado) => {
    const ahora = new Date("2026-11-26T14:10:00.000Z");
    expect(formatearUltimoGuardado(new Date(ahora.getTime() - segundos * 1_000), ahora)).toBe(esperado);
  });

  test("el SCSS usa solo tokens --silice-*, alto mínimo de 1,75 rem (28 px) y sin font-size en px", () => {
    // En una variable: con el texto literal, Vite reescribe new URL(...) como un recurso y deja de ser file:.
    const relativa = "./BarraDeEstado.scss";
    const ruta = fileURLToPath(new URL(relativa, import.meta.url));
    const css = sass.compile(ruta).css;
    expect(css).toMatch(/1\.75rem/);
    expect(css).not.toMatch(/font-size:\s*[\d.]+(px|pt)/);
    expect(css).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(css).not.toMatch(/\brgba?\(/);
  });
});
