import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BarraSuperior } from "./BarraSuperior";
import { abrirNuevaObra } from "./nuevaObra";

const tema = vi.hoisted(() => ({ logo: null as string | null }));
vi.mock("./useTema", () => ({ useTema: () => tema }));
vi.mock("./nuevaObra", () => ({ abrirNuevaObra: vi.fn() }));

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
  vi.mocked(abrirNuevaObra).mockClear();
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

describe("BarraSuperior: la carpeta activa, el contexto y el modo ventana dedicada", () => {
  it("no trae la navegación de migas de antes (ni la ruta ni enlaces de camino)", () => {
    pintar({ en: "/obra/a.db/1/presupuesto" });
    expect(screen.queryByRole("navigation", { name: "Ruta" })).toBeNull();
    expect(screen.getByRole("banner").querySelector(".silice-marco-barra__migas")).toBeNull();
  });

  it("dice la carpeta activa", () => {
    pintar({ carpeta: "Carpeta de la empresa" });
    const carpeta = screen.getByTitle("Carpeta activa: Carpeta de la empresa");
    expect(carpeta).toHaveClass("silice-marco-barra__carpeta");
    expect(carpeta).toHaveTextContent("Carpeta activa: Carpeta de la empresa");
    expect(carpeta.querySelector(".silice-marco-barra__carpeta-rotulo")?.textContent).toBe("Carpeta activa: ");
  });

  it("sin carpeta que decir no pinta el rótulo vacío", () => {
    pintar({ carpeta: null });
    expect(screen.queryByText(/Carpeta activa/)).toBeNull();
  });

  it("la carpeta activa y el contexto van juntos: dónde se trabaja y en qué", () => {
    render(
      <MemoryRouter initialEntries={["/obra/a.db/1/resumen"]}>
        <BarraSuperior alAbrirBuscador={vi.fn()} nombre="Ana" carpeta="Carpeta Sur" migaContextual="Obras / Galpón Sur" />
      </MemoryRouter>,
    );
    expect(screen.getByTitle("Carpeta activa: Carpeta Sur")).toHaveTextContent("Carpeta activa: Carpeta Sur");
    expect(screen.getByText("Obras / Galpón Sur")).toBeInTheDocument();
  });

  it("muestra la miga contextual limpia cuando se provee", () => {
    render(
      <MemoryRouter initialEntries={["/obra/a.db/1/resumen"]}>
        <BarraSuperior alAbrirBuscador={vi.fn()} nombre="Ana" carpeta={null} migaContextual="Obras / Galpón Sur" />
      </MemoryRouter>,
    );
    expect(screen.getByText("Obras / Galpón Sur")).toBeInTheDocument();
  });

  it("en ventana dedicada dice la carpeta y no trae el contexto de texto", () => {
    render(
      <MemoryRouter initialEntries={["/auditoria/subir"]}>
        <BarraSuperior
          alAbrirBuscador={vi.fn()}
          nombre="Ana"
          carpeta="Carpeta de la empresa"
          migaContextual="Obras / Galpón Sur"
          enVentanaDedicada
          espacioActivo="auditoria"
          espacios={ESPACIOS_OFRECIDOS}
        />
      </MemoryRouter>,
    );
    // Auditoría, Precios y Producción trabajan con la carpeta abierta: la ventana dedicada también la dice.
    expect(screen.getByTitle("Carpeta activa: Carpeta de la empresa")).toHaveTextContent("Carpeta activa: Carpeta de la empresa");
    expect(screen.queryByText("Obras / Galpón Sur")).toBeNull();
  });
});

const ESPACIOS_OFRECIDOS = [
  { id: "auditoria", titulo: "Auditar un presupuesto", ruta: "/auditoria/subir" },
  { id: "precios", titulo: "Precios y catálogo", ruta: "/precios/catalogo" },
  { id: "produccion", titulo: "Costos de producción", ruta: "/produccion/resumen" },
] as const;

// Lote C3 de la reestructuración (cara «Papel y resaltador», 2026-11-26): la barra de arriba es una franja global fina
// (marca, buscador, «Nueva obra» y cuenta). Los espacios de la empresa (Obras, Auditar un libro, Precios y catálogo y
// Producción) pasaron a la barra lateral, y «Volver a obras» y el selector de la cara anterior ya no existen aquí.
describe("BarraSuperior: franja global, sin los espacios de la empresa", () => {
  function conEspacios(propiedades: Partial<Parameters<typeof BarraSuperior>[0]> = {}, en = "/inicio/general") {
    return render(
      <MemoryRouter initialEntries={[en]}>
        <BarraSuperior alAbrirBuscador={vi.fn()} nombre="Ana" carpeta={null} espacios={ESPACIOS_OFRECIDOS} {...propiedades} />
      </MemoryRouter>,
    );
  }

  it("no trae ninguna navegación de espacios, aunque se le pasen", () => {
    conEspacios();
    expect(screen.queryByRole("navigation")).toBeNull();
    for (const nombre of ["Obras", "Auditar un libro", "Precios y catálogo", "Producción"]) {
      expect(screen.queryByRole("link", { name: nombre })).toBeNull();
    }
  });

  it("ya no trae «Volver a obras» ni el selector de herramientas dedicadas, tampoco en una ventana dedicada", () => {
    conEspacios({ enVentanaDedicada: true, espacioActivo: "auditoria" }, "/auditoria/subir");
    expect(screen.queryByRole("link", { name: "Volver a obras" })).toBeNull();
    expect(screen.queryByRole("navigation", { name: "Selector de herramientas dedicadas" })).toBeNull();
  });

  it("la marca, el buscador, Nueva obra y la persona siguen en la barra, también en un espacio", () => {
    conEspacios({ enVentanaDedicada: true, espacioActivo: "auditoria" }, "/auditoria/subir");
    expect(screen.getByRole("link", { name: "Sílice" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: TEXTO_BUSCAR })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Nueva obra" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Cuenta de Ana" })).toBeInTheDocument();
  });
});

describe("BarraSuperior: Nueva obra", () => {
  it("es un botón amarillo con el icono de más (16 px) que abre el diálogo de nueva obra", async () => {
    pintar();
    const boton = screen.getByRole("button", { name: "Nueva obra" });
    expect(boton).toHaveClass("silice-boton-nueva-obra");
    const icono = boton.querySelector("svg");
    expect(icono).not.toBeNull();
    expect(icono).toHaveAttribute("width", "16");
    expect(icono).toHaveAttribute("aria-hidden", "true");
    await userEvent.click(boton);
    expect(abrirNuevaObra).toHaveBeenCalledTimes(1);
  });

  it("va antes del buscador", () => {
    pintar();
    const nueva = screen.getByRole("button", { name: "Nueva obra" });
    const buscar = screen.getByRole("button", { name: TEXTO_BUSCAR });
    expect(nueva.compareDocumentPosition(buscar) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});

// La interfaz es la suite de escritorio (start.py abre /app/): la portada web de `GET /` no existirá en el producto y la
// barra no la enlaza, ni dentro ni fuera de la ventana dedicada (Eugenio, 2026-11-22).
describe("BarraSuperior: sin enlace a la portada web", () => {
  it.each([false, true])("con ventana dedicada %s no hay enlace «Portada» ni a «/» fuera del enrutador", (enVentanaDedicada) => {
    render(
      <MemoryRouter initialEntries={["/auditoria/subir"]}>
        <BarraSuperior
          alAbrirBuscador={vi.fn()}
          nombre="Ana"
          carpeta={null}
          enVentanaDedicada={enVentanaDedicada}
          espacioActivo="auditoria"
          espacios={[{ id: "auditoria", titulo: "Auditar un presupuesto", ruta: "/auditoria/subir" }]}
        />
      </MemoryRouter>,
    );
    expect(screen.queryByRole("link", { name: /portada/i })).toBeNull();
    expect(screen.getByRole("banner").querySelector(".silice-marco-barra__portada")).toBeNull();
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

  it("el botón va en una ranura que mide su ancho: si no cabe el texto completo queda en su ícono (T3, 2026-11-28)", () => {
    pintar();
    const boton = screen.getByRole("button", { name: TEXTO_BUSCAR });
    expect(boton.parentElement).toHaveClass("silice-marco-barra__buscar-ranura");
    // «Nueva obra» comparte la ranura: las dos piezas quedan pegadas a la derecha y la consulta mide el conjunto.
    expect(boton.parentElement).toContainElement(screen.getByRole("button", { name: "Nueva obra" }));
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
