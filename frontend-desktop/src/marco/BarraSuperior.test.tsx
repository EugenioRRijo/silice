import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BarraSuperior } from "./BarraSuperior";
import type { Miga } from "./Migas";

const tema = vi.hoisted(() => ({ logo: null as string | null }));
vi.mock("./useTema", () => ({ useTema: () => tema }));

const TEXTO_BUSCAR = "Buscar una obra, sección o pantalla… (Ctrl+K)";
const MIGAS: Miga[] = [
  { texto: "Mis obras", ruta: "/pendientes" },
  { texto: "Clínica Las Mercedes", ruta: "/obra/a.db/1/resumen" },
  { texto: "Presupuesto" },
];

function pintar(migas: Miga[] = MIGAS, alAbrirBuscador = vi.fn()) {
  const alSalir = vi.fn();
  const vista = render(
    <MemoryRouter>
      <BarraSuperior migas={migas} alAbrirBuscador={alAbrirBuscador} nombre="Ana" alSalir={alSalir} />
      <textarea aria-label="notas" />
    </MemoryRouter>,
  );
  return { alAbrirBuscador, alSalir, ...vista };
}

beforeEach(() => {
  tema.logo = null;
});

describe("BarraSuperior: marca", () => {
  it("con logo muestra la imagen con su texto alternativo", () => {
    tema.logo = "/v1/tema/logo";
    pintar();
    const img = screen.getByRole("img", { name: "Logo de la empresa" });
    expect(img).toHaveAttribute("src", "/v1/tema/logo");
  });

  it("sin logo muestra el nombre Sílice", () => {
    pintar();
    expect(screen.queryByRole("img", { name: "Logo de la empresa" })).toBeNull();
    expect(screen.getByText("Sílice")).toBeInTheDocument();
  });
});

describe("BarraSuperior: migas", () => {
  it("las anteriores son enlaces y la última es la página actual", () => {
    pintar();
    const migas = screen.getByRole("navigation", { name: "Ruta" });
    const enlaces = within(migas).getAllByRole("link");
    expect(enlaces.map((e) => e.textContent)).toEqual(["Mis obras", "Clínica Las Mercedes"]);
    expect(enlaces[1]).toHaveAttribute("href", "/obra/a.db/1/resumen");
    const actual = within(migas).getByText("Presupuesto");
    expect(actual).toHaveAttribute("aria-current", "page");
    expect(within(migas).queryByRole("link", { name: "Presupuesto" })).toBeNull();
  });

  it("los separadores son decorativos", () => {
    pintar();
    const separadores = screen.getByRole("navigation", { name: "Ruta" }).querySelectorAll('[aria-hidden="true"]');
    expect(separadores).toHaveLength(2);
    expect([...separadores].every((s) => s.textContent === "/")).toBe(true);
  });
});

describe("BarraSuperior: buscador", () => {
  it("el clic llama a alAbrirBuscador una vez", async () => {
    const { alAbrirBuscador } = pintar();
    await userEvent.click(screen.getByRole("button", { name: TEXTO_BUSCAR }));
    expect(alAbrirBuscador).toHaveBeenCalledTimes(1);
  });

  it("Ctrl+K y Cmd+K lo llaman desde cualquier parte", () => {
    const { alAbrirBuscador } = pintar();
    fireEvent.keyDown(document.body, { key: "k", ctrlKey: true });
    fireEvent.keyDown(document.body, { key: "K", metaKey: true });
    expect(alAbrirBuscador).toHaveBeenCalledTimes(2);
  });

  it("Ctrl+K dentro de un textarea no lo llama", () => {
    const { alAbrirBuscador } = pintar();
    fireEvent.keyDown(screen.getByLabelText("notas"), { key: "k", ctrlKey: true });
    expect(alAbrirBuscador).not.toHaveBeenCalled();
  });

  it("K sin Ctrl no hace nada", () => {
    const { alAbrirBuscador } = pintar();
    fireEvent.keyDown(document.body, { key: "k" });
    expect(alAbrirBuscador).not.toHaveBeenCalled();
  });

  it("deja de escuchar al desmontarse", () => {
    const { alAbrirBuscador, unmount } = pintar();
    unmount();
    fireEvent.keyDown(document.body, { key: "k", ctrlKey: true });
    expect(alAbrirBuscador).not.toHaveBeenCalled();
  });

  it("el nombre accesible es el texto visible completo, también en modo icono, y anuncia el atajo", () => {
    pintar();
    const boton = screen.getByRole("button", { name: TEXTO_BUSCAR });
    expect(boton).not.toHaveAttribute("aria-label");
    expect(boton).toHaveAttribute("aria-keyshortcuts", "Control+K");
    expect(boton).toHaveClass("silice-marco-barra__buscar");
    expect(boton.querySelector(".silice-marco-barra__buscar-texto")).toHaveTextContent(TEXTO_BUSCAR);
    expect(boton.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });

  it("Ctrl+K dentro de un campo contenteditable no lo llama", () => {
    const { alAbrirBuscador } = pintar();
    const editable = document.createElement("div");
    editable.setAttribute("contenteditable", "true");
    const hijo = document.createElement("span");
    editable.appendChild(hijo);
    document.body.appendChild(editable);
    fireEvent.keyDown(hijo, { key: "k", ctrlKey: true });
    editable.remove();
    expect(alAbrirBuscador).not.toHaveBeenCalled();
  });
});

describe("BarraSuperior: controles y vocabulario", () => {
  it("incluye el tamaño de letra y la cuenta", () => {
    pintar();
    expect(screen.getByRole("group", { name: "Tamaño de letra" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cuenta de Ana" })).toBeInTheDocument();
  });

  it("ningún texto visible usa módulo, área ni Streamlit", () => {
    pintar();
    expect(document.body.textContent).not.toMatch(/m[oó]dulo|[aá]rea|streamlit/i);
  });
});
