import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { MemoryRouter, useLocation } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { pedir } from "../api/cliente";
import type { ObraDeCarpetaRespuesta, SesionRespuesta } from "../api/tipos";
import { ContextoAplicacion } from "../shell/contexto";
import { sesionDe } from "../shell/obras/datosDePrueba";
import { Buscador } from "./Buscador";

vi.mock("../api/cliente", async (importarOriginal) => ({
  ...(await importarOriginal<typeof import("../api/cliente")>()),
  pedir: vi.fn(),
}));
const pedirFalso = vi.mocked(pedir);

// Carpetas y obras inventadas.
const NORTE = "Carpeta Norte.db";
const SUR = "Carpeta Sur.db";
function obra(carpeta: string, obra_id: number, nombre: string): ObraDeCarpetaRespuesta {
  return { carpeta, carpeta_titulo: carpeta.replace(/\.db$/, ""), obra_id, obra: nombre, version_codigo: null };
}
const OBRAS = [obra(NORTE, 1, "Clínica Las Mercedes"), obra(NORTE, 2, "Torre B"), obra(SUR, 3, "Galpón Sur")];

beforeEach(() => {
  pedirFalso.mockReset();
  pedirFalso.mockImplementation(async (ruta: string) => {
    if (ruta === "/v1/obras/todas") return { carpeta_actual: NORTE, obras: OBRAS };
    throw new Error(`petición inesperada: ${ruta}`);
  });
});

function Ubicacion() {
  return <span data-testid="ruta">{useLocation().pathname}</span>;
}
function Arnes({ inicialAbierto }: { inicialAbierto: boolean }) {
  const [abierto, setAbierto] = useState(inicialAbierto);
  return (
    <>
      <button type="button" aria-keyshortcuts="Control+K" onClick={() => setAbierto(true)}>
        Abrir buscador
      </button>
      <Buscador abierto={abierto} alCerrar={() => setAbierto(false)} />
      <Ubicacion />
      <main id="contenido" tabIndex={-1}>
        Contenido
      </main>
    </>
  );
}
function pintar(sesion: SesionRespuesta = sesionDe("ana"), inicialAbierto = true) {
  return render(
    <MemoryRouter initialEntries={["/pendientes"]}>
      <ContextoAplicacion.Provider
        value={{ sesion, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() }}
      >
        <Arnes inicialAbierto={inicialAbierto} />
      </ContextoAplicacion.Provider>
    </MemoryRouter>,
  );
}
const campo = () => screen.findByRole("combobox");
const opciones = () => screen.queryAllByRole("option").map((o) => o.textContent ?? "");
const estado = () => screen.getByRole("status").textContent;

describe("Buscador", () => {
  it("cerrado no pinta nada y no pide obras", () => {
    pintar(sesionDe("ana"), false);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(pedirFalso).not.toHaveBeenCalled();
  });

  it("abierto es un diálogo con un combobox enfocado y un listbox", async () => {
    pintar();
    const c = await campo();
    expect(screen.getByRole("dialog", { name: "Buscar" })).toBeTruthy();
    expect(c).toHaveFocus();
    expect(c.getAttribute("aria-expanded")).toBe("true");
    expect(c.getAttribute("aria-controls")).toBe(screen.getByRole("listbox").id);
  });

  it("aria-expanded dice si la lista tiene resultados", async () => {
    pintar();
    const c = await campo();
    await waitFor(() => expect(opciones()).toHaveLength(3));
    expect(c).toHaveAttribute("aria-expanded", "true");
    await userEvent.type(c, "zzzz");
    expect(estado()).toBe("Sin resultados");
    expect(c).toHaveAttribute("aria-expanded", "false");
    await userEvent.clear(c);
    expect(c).toHaveAttribute("aria-expanded", "true");
  });

  it("Tab y Mayús+Tab no sacan el foco del diálogo", async () => {
    pintar();
    const c = await campo();
    await userEvent.tab();
    expect(c).toHaveFocus();
    await userEvent.tab({ shift: true });
    expect(c).toHaveFocus();
  });

  it("al elegir un resultado el foco va al contenido, no de vuelta al botón", async () => {
    pintar(sesionDe("ana"), false);
    await userEvent.click(screen.getByRole("button", { name: "Abrir buscador" }));
    await campo();
    await waitFor(() => expect(opciones()).toHaveLength(3));
    await userEvent.keyboard("{Enter}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.getElementById("contenido")).toHaveFocus();
  });

  it("escribir filtra y anuncia cuántos resultados hay", async () => {
    pintar();
    const c = await campo();
    await waitFor(() => expect(opciones()).toHaveLength(3));
    expect(estado()).toBe("3 resultados");
    await userEvent.type(c, "clin pres");
    expect(opciones()).toHaveLength(1);
    expect(opciones()[0]).toContain("Clínica Las Mercedes › Presupuesto");
    expect(estado()).toBe("1 resultado");
    await userEvent.clear(c);
    await userEvent.type(c, "zzzz");
    expect(estado()).toBe("Sin resultados");
    expect(opciones()).toHaveLength(0);
  });

  it("las flechas mueven la selección con aria-activedescendant y aria-selected", async () => {
    pintar();
    const c = await campo();
    await waitFor(() => expect(opciones()).toHaveLength(3));
    const lista = () => screen.getAllByRole("option");
    expect(lista()[0]?.getAttribute("aria-selected")).toBe("true");
    expect(c.getAttribute("aria-activedescendant")).toBe(lista()[0]?.id);
    await userEvent.keyboard("{ArrowDown}");
    expect(lista()[1]?.getAttribute("aria-selected")).toBe("true");
    expect(lista()[0]?.getAttribute("aria-selected")).toBe("false");
    expect(c.getAttribute("aria-activedescendant")).toBe(lista()[1]?.id);
    await userEvent.keyboard("{ArrowUp}{ArrowUp}");
    expect(lista()[2]?.getAttribute("aria-selected")).toBe("true");
  });

  it("Enter navega a la ruta del seleccionado y cierra", async () => {
    pintar();
    await campo();
    await waitFor(() => expect(opciones()).toHaveLength(3));
    await userEvent.keyboard("{ArrowDown}{Enter}");
    expect(screen.getByTestId("ruta").textContent).toBe("/obra/Carpeta%20Norte.db/2/resumen");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("clic en un resultado navega", async () => {
    pintar();
    await campo();
    await waitFor(() => expect(opciones()).toHaveLength(3));
    await userEvent.click(screen.getByRole("option", { name: /Galpón Sur/ }));
    expect(screen.getByTestId("ruta").textContent).toBe("/obra/Carpeta%20Sur.db/3/resumen");
  });

  it("Esc cierra y devuelve el foco al botón que lo abrió", async () => {
    pintar(sesionDe("ana"), false);
    const boton = screen.getByRole("button", { name: "Abrir buscador" });
    await userEvent.click(boton);
    await campo();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(boton).toHaveFocus();
  });

  it("una cuenta sin cambiar_caso solo encuentra obras de su carpeta abierta", async () => {
    const sin = sesionDe("ana", { acciones: sesionDe("ana").acciones.filter((a) => a !== "cambiar_caso") });
    pintar(sin);
    await campo();
    await waitFor(() => expect(opciones()).toHaveLength(2));
    expect(opciones().join()).not.toContain("Galpón Sur");
  });

  it("no ofrece lo que la cuenta no puede usar ni secciones sin pantalla", async () => {
    pintar(sesionDe("ana", { acciones: ["cambiar_caso"] }));
    const c = await campo();
    await userEvent.type(c, "archivos");
    expect(estado()).toBe("Sin resultados");
    await userEvent.clear(c);
    await userEvent.type(c, "personas");
    expect(estado()).toBe("Sin resultados");
  });

  it("no usa las palabras prohibidas en sus textos visibles", async () => {
    pintar();
    await campo();
    await waitFor(() => expect(opciones()).toHaveLength(3));
    const visible = (document.body.textContent ?? "").toLowerCase();
    for (const prohibida of ["módulo", "área", "página", "carpeta de trabajo", "streamlit"]) {
      expect(visible).not.toContain(prohibida);
    }
  });

  it("si no se pueden cargar las obras avisa y sigue ofreciendo lo demás", async () => {
    pedirFalso.mockRejectedValue(new Error("caído"));
    pintar();
    const c = await campo();
    await userEvent.type(c, "precios");
    expect(await screen.findByRole("alert")).toHaveTextContent("No se pudieron cargar las obras");
    // Desde F6 (T4) «precios» encuentra las herramientas del espacio «Precios y catálogo»; la primera es el Catálogo.
    expect(opciones()[0]).toContain("Catálogo de partidas e insumos");
  });
});

describe("Buscador con módulos apagados (plan vial, Tarea 19)", () => {
  function pintarConApagados(apagados: string[]) {
    return render(
      <MemoryRouter initialEntries={["/pendientes"]}>
        <ContextoAplicacion.Provider
          value={{ sesion: sesionDe("ana"), proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn(), modulosApagados: apagados }}
        >
          <Arnes inicialAbierto />
        </ContextoAplicacion.Provider>
      </MemoryRouter>,
    );
  }

  it("encendido, «tramos» encuentra la sección Tramos de cada obra, no una pantalla sin obra", async () => {
    pintarConApagados([]);
    await userEvent.type(await campo(), "tramos");
    await waitFor(() => expect(opciones().join("|")).toContain("› Tramos"));
    expect(opciones().join("|")).not.toContain("Tramos de la vía");
  });

  it("con vial apagado, «tramos» ya no la encuentra", async () => {
    pintarConApagados(["vial"]);
    await userEvent.type(await campo(), "tramos");
    await waitFor(() => expect(estado()).toBe("Sin resultados"));
    expect(opciones().join("|")).not.toContain("Tramos de la vía");
  });
});
