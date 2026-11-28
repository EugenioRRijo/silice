import { fileURLToPath } from "node:url";
import { fireEvent, render, screen } from "@testing-library/react";
import * as sass from "sass";
import { describe, expect, test } from "vitest";
import { Campanita } from "./Campanita";
import { ProveedorDeNotificaciones, crearAlmacenEnMemoria, useNotificaciones } from "./ProveedorDeNotificaciones";

function ControlesDePrueba() {
  const { notificar, marcarTodasLeidas } = useNotificaciones();
  return (
    <div>
      <button type="button" onClick={() => notificar({ gravedad: "listo", titulo: "Versión guardada" })}>
        Agregar notificación
      </button>
      <button type="button" onClick={marcarTodasLeidas}>
        Leer todas
      </button>
      <Campanita />
    </div>
  );
}

describe("Campanita", () => {
  test("sin notificaciones no leídas usa «Notificaciones» como nombre accesible y no pinta cifra", () => {
    render(
      <ProveedorDeNotificaciones>
        <ControlesDePrueba />
      </ProveedorDeNotificaciones>,
    );

    const boton = screen.getByRole("button", { name: "Notificaciones" });
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(boton).toHaveAttribute("aria-controls", "panel-notif");
    expect(boton).toHaveTextContent("");
  });

  test("con notificaciones sin leer muestra la cifra y el nombre accesible «Notificaciones, N sin leer»", () => {
    const almacen = crearAlmacenEnMemoria([
      { id: "1", gravedad: "listo", titulo: "Uno", creada: "2026-11-26T10:00:00Z", leida: false },
      { id: "2", gravedad: "advertencia", titulo: "Dos", creada: "2026-11-26T10:05:00Z", leida: false },
      { id: "3", gravedad: "info", titulo: "Tres", creada: "2026-11-26T10:10:00Z", leida: true },
    ]);

    render(
      <ProveedorDeNotificaciones almacen={almacen} idPanel="mi-panel-notif">
        <ControlesDePrueba />
      </ProveedorDeNotificaciones>,
    );

    const boton = screen.getByRole("button", { name: "Notificaciones, 2 sin leer" });
    expect(boton).toHaveTextContent("2");
    expect(boton).toHaveAttribute("aria-controls", "mi-panel-notif");
    expect(boton).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(boton);
    expect(boton).toHaveAttribute("aria-expanded", "true");

    fireEvent.click(screen.getByRole("button", { name: "Agregar notificación" }));
    expect(screen.getByRole("button", { name: "Notificaciones, 3 sin leer" })).toHaveTextContent("3");

    fireEvent.click(screen.getByRole("button", { name: "Leer todas" }));
    const leido = screen.getByRole("button", { name: "Notificaciones" });
    expect(leido).toHaveTextContent("");
  });

  test("el SCSS de la campanita usa solo tokens --silice-* y rem", () => {
    // En una variable: con el texto literal, Vite reescribe new URL(...) como un recurso y deja de ser file:.
    const relativa = "./Campanita.scss";
    const ruta = fileURLToPath(new URL(relativa, import.meta.url));
    const css = sass.compile(ruta).css;
    expect(css).not.toMatch(/font-size:\s*[\d.]+(px|pt)/);
    expect(css).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(css).not.toMatch(/\brgba?\(/);
  });
});
