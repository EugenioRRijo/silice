import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BarraSuperior } from "./BarraSuperior";

const tema = vi.hoisted(() => ({ logo: null as string | null }));
vi.mock("./useTema", () => ({ useTema: () => tema }));

const TEXTO_BUSCAR = "Buscar una obra, sección o pantalla… (Ctrl+K)";

function pintar({ alAbrirBuscador = vi.fn(), carpeta = null as string | null, en = "/pendientes" } = {}) {
  const vista = render(
    <MemoryRouter initialEntries={[en]}>
      <BarraSuperior alAbrirBuscador={alAbrirBuscador} nombre="Ana" carpeta={carpeta} />
      <textarea aria-label="notas" />
    </MemoryRouter>,
  );
  return { alAbrirBuscador, ...vista };
}

beforeEach(() => {
  tema.logo = null;
});

describe("BarraSuperior: marca", () => {
  it("con logo muestra la imagen dentro de un enlace a la ruta índice", () => {
    tema.logo = "/v1/tema/logo";
    pintar();
    const enlace = screen.getByRole("link", { name: "Sílice — Ir al inicio" });
    expect(enlace).toHaveAttribute("href", "/");
    expect(screen.getByRole("img", { name: "Sílice — Ir al inicio" })).toHaveAttribute("src", "/v1/tema/logo");
  });

  it("sin logo, el nombre Sílice es un enlace a la ruta índice", () => {
    pintar();
    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.getByRole("link", { name: "Sílice" })).toHaveAttribute("href", "/");
  });
});

describe("BarraSuperior: contexto limpio y modo ventana dedicada", () => {
  it("no trae migas de navegacion ni expone el chip tecnico Carpeta activa", () => {
    pintar({ en: "/obra/a.db/1/presupuesto", carpeta: "s1" });
    expect(screen.queryByRole("navigation", { name: "Ruta" })).toBeNull();
    expect(screen.getByRole("banner").querySelector(".silice-marco-barra__migas")).toBeNull();
    expect(screen.queryByText(/Carpeta activa/)).toBeNull();
  });

  it("muestra la miga contextual limpia cuando se provee", () => {
    render(
      <MemoryRouter initialEntries={["/obra/a.db/1/resumen"]}>
        <BarraSuperior alAbrirBuscador={vi.fn()} nombre="Ana" migaContextual="Obras / Galpón Sur" />
      </MemoryRouter>,
    );
    expect(screen.getByText("Obras / Galpón Sur")).toBeInTheDocument();
  });

  it("en ventana dedicada muestra Volver a Obras y el selector 01/02/03", () => {
    render(
      <MemoryRouter initialEntries={["/auditoria/subir"]}>
        <BarraSuperior
          alAbrirBuscador={vi.fn()}
          nombre="Ana"
          enVentanaDedicada
          espacioActivo="auditoria"
          espacios={[
            { id: "auditoria", titulo: "Auditar un presupuesto", ruta: "/auditoria/subir" },
            { id: "precios", titulo: "Precios y catálogo", ruta: "/precios/catalogo" },
            { id: "produccion", titulo: "Costos de producción", ruta: "/produccion/resumen" },
          ]}
        />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "Volver a Obras" })).toHaveAttribute("href", "/inicio/general");
    const selector = screen.getByRole("navigation", { name: "Selector de herramientas dedicadas" });
    expect(selector).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "01 · Auditoría" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "02 · Precios y Catálogo" })).toHaveAttribute("href", "/precios/catalogo");
    expect(screen.getByRole("link", { name: "03 · Producción" })).toHaveAttribute("href", "/produccion/resumen");
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

  it.each(["plaintext-only", "", "true"])(
    "Ctrl+K sobre el propio destino con contenteditable=\"%s\" no lo llama",
    (valor) => {
      const { alAbrirBuscador } = pintar();
      const editable = document.createElement("div");
      editable.setAttribute("contenteditable", valor);
      document.body.appendChild(editable);
      fireEvent.keyDown(editable, { key: "k", ctrlKey: true });
      editable.remove();
      expect(alAbrirBuscador).not.toHaveBeenCalled();
    },
  );

  it("Ctrl+K sobre un contenteditable=\"false\" sí lo llama", () => {
    const { alAbrirBuscador } = pintar();
    const fijo = document.createElement("div");
    fijo.setAttribute("contenteditable", "false");
    document.body.appendChild(fijo);
    fireEvent.keyDown(fijo, { key: "k", ctrlKey: true });
    fijo.remove();
    expect(alAbrirBuscador).toHaveBeenCalledTimes(1);
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

describe("BarraSuperior: la persona y el tamaño de letra", () => {
  it("el botón de la persona es un enlace a /cuenta/preferencias, con las iniciales", () => {
    pintar();
    const enlace = screen.getByRole("link", { name: "Cuenta de Ana" });
    expect(enlace).toHaveAttribute("href", "/cuenta/preferencias");
    expect(enlace).toHaveAttribute("title", "Ana");
    expect(enlace).not.toHaveAttribute("aria-current");
    expect(enlace.querySelector(".silice-cuenta__iniciales")).toHaveTextContent("A");
    expect(screen.queryByRole("button", { name: "Cuenta de Ana" })).toBeNull();
  });

  it.each(["/cuenta/preferencias", "/cuenta/cuentas", "/cuenta/ayuda"])("en %s el enlace de la persona es la página actual", (en) => {
    pintar({ en });
    expect(screen.getByRole("link", { name: "Cuenta de Ana" })).toHaveAttribute("aria-current", "page");
  });

  it("fuera de la Cuenta, y en una ruta que solo se le parece, no lo es", () => {
    pintar({ en: "/cuentas-por-cobrar" });
    expect(screen.getByRole("link", { name: "Cuenta de Ana" })).not.toHaveAttribute("aria-current");
  });

  it("el tamaño de letra ya no está en la barra de arriba: vive en la Cuenta", () => {
    pintar();
    expect(screen.queryByRole("group", { name: "Tamaño de letra" })).toBeNull();
  });

  it("ningún texto visible usa módulo, área ni Streamlit", () => {
    pintar({ carpeta: "Carpeta Norte" });
    expect(document.body.textContent).not.toMatch(/m[oó]dulo|[aá]rea|streamlit/i);
  });
});
