import { fileURLToPath } from "node:url";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import * as sass from "sass";
import { describe, expect, test } from "vitest";
import { Campanita } from "./Campanita";
import { PanelDeNotificaciones, RUTA_DE_PREFERENCIAS } from "./PanelDeNotificaciones";
import { ProveedorDeNotificaciones, crearAlmacenEnMemoria } from "./ProveedorDeNotificaciones";
import type { Notificacion } from "./modelo";

const AHORA = new Date(2026, 10, 26, 14, 0, 0);

const SEMILLA: Notificacion[] = [
  {
    id: "h-1",
    gravedad: "listo",
    titulo: "Versión V2 guardada",
    detalle: "Vialidad Tramo 3",
    creada: new Date(2026, 10, 26, 10, 42, 0).toISOString(),
    leida: false,
  },
  {
    id: "h-2",
    gravedad: "advertencia",
    titulo: "Precio vencido",
    detalle: "El aditivo plastificante venció el 31/10/2026",
    enlace: { texto: "Ver en Precios de la empresa", ruta: "/precios/empresa" },
    creada: new Date(2026, 10, 26, 9, 15, 0).toISOString(),
    leida: false,
  },
  {
    id: "h-3",
    gravedad: "error",
    titulo: "2 errores abiertos en la auditoría",
    detalle: "Vialidad Tramo 3",
    enlace: { texto: "Ver los problemas", ruta: "/auditoria" },
    creada: new Date(2026, 10, 26, 8, 30, 0).toISOString(),
    leida: false,
  },
  {
    id: "a-1",
    gravedad: "info",
    titulo: "Auditoría de «Presupuesto cliente A.xlsx» terminada",
    detalle: "6 hallazgos",
    creada: new Date(2026, 10, 25, 16, 5, 0).toISOString(),
    leida: true,
  },
  {
    id: "v-1",
    gravedad: "info",
    titulo: "Respaldo antiguo descartado",
    creada: new Date(2026, 9, 10, 11, 0, 0).toISOString(),
    leida: true,
  },
];

function montarPanel(semilla: Notificacion[] = SEMILLA, extra: ReactNode = null) {
  const almacen = crearAlmacenEnMemoria(semilla);
  return render(
    <MemoryRouter>
      <ProveedorDeNotificaciones almacen={almacen} ahora={() => AHORA}>
        <Campanita />
        <PanelDeNotificaciones ahora={AHORA} />
        {extra}
      </ProveedorDeNotificaciones>
    </MemoryRouter>,
  );
}

describe("PanelDeNotificaciones", () => {
  test("abre desde la campanita como aside no modal, descarta las de >30 días, agrupa Hoy/Ayer y muestra gravedad, enlace y pie", async () => {
    const usuario = userEvent.setup();
    montarPanel();

    expect(screen.queryByRole("complementary", { name: "Notificaciones" })).toBeNull();

    const campanita = screen.getByRole("button", { name: "Notificaciones, 3 sin leer" });
    await usuario.click(campanita);

    const panel = screen.getByRole("complementary", { name: "Notificaciones" });
    expect(panel.tagName).toBe("ASIDE");
    expect(panel).toHaveAttribute("id", campanita.getAttribute("aria-controls"));

    expect(within(panel).queryByText("Respaldo antiguo descartado")).toBeNull();

    const hoy = within(panel).getByRole("region", { name: "Hoy" });
    expect(within(hoy).getByText("Listo")).toBeInTheDocument();
    expect(within(hoy).getByText("Advertencia")).toBeInTheDocument();
    expect(within(hoy).getByText("Error")).toBeInTheDocument();
    expect(within(hoy).getByRole("link", { name: "Ver en Precios de la empresa" })).toHaveAttribute(
      "href",
      "/precios/empresa",
    );

    const ayer = within(panel).getByRole("region", { name: "Ayer" });
    expect(within(ayer).getByText("Información")).toBeInTheDocument();
    expect(within(ayer).getByText("Auditoría de «Presupuesto cliente A.xlsx» terminada")).toBeInTheDocument();

    expect(within(panel).getByText("Las notificaciones se guardan 30 días.")).toBeInTheDocument();
  });

  test("filtra entre «Todas» y «Sin leer» con aria-pressed y su cifra, y marca todas como leídas", async () => {
    const usuario = userEvent.setup();
    montarPanel();

    await usuario.click(screen.getByRole("button", { name: "Notificaciones, 3 sin leer" }));
    const panel = screen.getByRole("complementary", { name: "Notificaciones" });

    const botonTodas = within(panel).getByRole("button", { name: /^Todas\s+4$/ });
    const botonSinLeer = within(panel).getByRole("button", { name: /^Sin leer\s+3$/ });
    expect(botonTodas).toHaveAttribute("aria-pressed", "true");
    expect(botonSinLeer).toHaveAttribute("aria-pressed", "false");

    await usuario.click(botonSinLeer);
    expect(botonTodas).toHaveAttribute("aria-pressed", "false");
    expect(botonSinLeer).toHaveAttribute("aria-pressed", "true");
    expect(within(panel).queryByRole("heading", { name: "Ayer" })).toBeNull();
    expect(within(panel).getByText("Versión V2 guardada")).toBeInTheDocument();

    await usuario.click(within(panel).getByRole("button", { name: "Marcar todas como leídas" }));
    expect(within(panel).getByRole("button", { name: /^Sin leer\s+0$/ })).toBeInTheDocument();
    expect(within(panel).getByText("No tiene notificaciones sin leer.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Notificaciones" })).toBeInTheDocument();

    await usuario.click(within(panel).getByRole("button", { name: /^Todas\s+4$/ }));
    expect(within(panel).getByText("Auditoría de «Presupuesto cliente A.xlsx» terminada")).toBeInTheDocument();
  });

  test("Esc cierra el panel y devuelve el foco a la campanita", async () => {
    const usuario = userEvent.setup();
    montarPanel();

    const campanita = screen.getByRole("button", { name: "Notificaciones, 3 sin leer" });
    await usuario.click(campanita);

    const panel = screen.getByRole("complementary", { name: "Notificaciones" });
    expect(panel).toBeInTheDocument();

    fireEvent.keyDown(panel, { key: "Escape" });
    expect(screen.queryByRole("complementary", { name: "Notificaciones" })).toBeNull();
    expect(campanita).toHaveFocus();
    expect(campanita).toHaveAttribute("aria-expanded", "false");
  });

  // T4 (mutante PN3): con un diálogo modal abierto, Esc es del diálogo y el panel de al lado no se cierra.
  test("Esc con un diálogo modal abierto no cierra el panel", async () => {
    const usuario = userEvent.setup();
    montarPanel(
      SEMILLA,
      <div role="dialog" aria-modal="true" aria-label="Confirmar entrega">
        Revise antes de entregar.
      </div>,
    );
    await usuario.click(screen.getByRole("button", { name: "Notificaciones, 3 sin leer" }));
    expect(screen.getByRole("complementary", { name: "Notificaciones" })).toBeInTheDocument();

    fireEvent.keyDown(document.body, { key: "Escape" });
    expect(screen.getByRole("complementary", { name: "Notificaciones" })).toBeInTheDocument();
  });

  // T4 (mutante PN2): el mensaje del filtro «Sin leer» distingue «todas leídas» de «no hay ninguna».
  test("sin ninguna notificación, «Sin leer» dice que no hay recientes y no que todas están leídas", async () => {
    const usuario = userEvent.setup();
    montarPanel([]);
    await usuario.click(screen.getByRole("button", { name: "Notificaciones" }));
    const panel = screen.getByRole("complementary", { name: "Notificaciones" });
    await usuario.click(within(panel).getByRole("button", { name: /^Sin leer\s+0$/ }));
    expect(within(panel).getByText("No tiene notificaciones recientes.")).toBeInTheDocument();
    expect(within(panel).queryByText("No tiene notificaciones sin leer.")).toBeNull();
  });

  test("el pie enlaza a «Elegir qué notificaciones recibir», la pantalla de preferencias de la Cuenta", async () => {
    const usuario = userEvent.setup();
    montarPanel();

    await usuario.click(screen.getByRole("button", { name: "Notificaciones, 3 sin leer" }));
    const panel = screen.getByRole("complementary", { name: "Notificaciones" });

    expect(RUTA_DE_PREFERENCIAS).toBe("/cuenta/notificaciones");
    expect(within(panel).getByRole("link", { name: "Elegir qué notificaciones recibir" })).toHaveAttribute(
      "href",
      "/cuenta/notificaciones",
    );
    expect(within(panel).getByText("Las notificaciones se guardan 30 días.")).toBeInTheDocument();
  });

  test("el SCSS del panel usa solo tokens --silice-*, ancho de 23,75 rem (380 px) y sin font-size en px", () => {
    // En una variable: con el texto literal, Vite reescribe new URL(...) como un recurso y deja de ser file:.
    const relativa = "./PanelDeNotificaciones.scss";
    const ruta = fileURLToPath(new URL(relativa, import.meta.url));
    const css = sass.compile(ruta).css;
    expect(css).toMatch(/23\.75rem/);
    expect(css).not.toMatch(/font-size:\s*[\d.]+(px|pt)/);
    expect(css).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(css).not.toMatch(/\brgba?\(/);
  });
});
