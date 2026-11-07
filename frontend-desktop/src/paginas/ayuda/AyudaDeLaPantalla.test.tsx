import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import { json, montarMarco, servidorFalso, sesionDe } from "../../shell/obras/datosDePrueba";
import { PAGINAS } from "../../shell/rutas";
import { cancelarSalida } from "../../shell/salida";
import { olvidarFormularios } from "../../shell/sucio";
import { AyudaDeLaPantalla } from "./AyudaDeLaPantalla";
import { AYUDA_DE_PANTALLAS } from "./textos";

// F7, tarea A1: el «¿Qué es esto?» de cada pantalla de la obra y de los espacios. Es el mismo `QueEsEsto` de las pestañas
// del Presupuesto (DESIGN.md, «Secciones de la obra»), con enlaces a su guía y a los términos del glosario. Oráculos a mano:
// el nombre de la región es el título de la pantalla y los enlaces llevan a `#/cuenta/ayuda?tema=…`.

describe("AyudaDeLaPantalla", () => {
  function montar(pagina: string) {
    return render(
      <MemoryRouter>
        <AyudaDeLaPantalla pagina={pagina} />
      </MemoryRouter>,
    );
  }

  test("empieza plegada y, al abrirla, dice qué es la pantalla y enlaza su guía y los términos", async () => {
    const u = userEvent.setup();
    montar("aprobar");
    const boton = screen.getByRole("button", { name: "¿Qué es esto?" });
    expect(boton).toHaveAttribute("aria-expanded", "false");
    await u.click(boton);
    const region = screen.getByRole("region", { name: "Aprobar una versión" });
    expect(region).toHaveTextContent("dictamen");
    expect(within(region).getByRole("link", { name: "Guía «Enviarlo a aprobación»" })).toHaveAttribute("href", "/cuenta/ayuda?tema=guia-aprobacion");
    expect(within(region).getByRole("link", { name: "Dictamen" })).toHaveAttribute("href", "/cuenta/ayuda?tema=glosario-dictamen");
  });

  test("el Presupuesto no lleva una segunda ayuda (cada pestaña tiene la suya) y una pantalla sin texto no pinta nada", () => {
    const { container } = montar("hoja");
    expect(container).toBeEmptyDOMElement();
    const otra = montar("no-existe");
    expect(otra.container).toBeEmptyDOMElement();
  });

  test("el nombre de la región es el título de la pantalla (el mismo de su h1)", () => {
    for (const p of PAGINAS) {
      const ayuda = AYUDA_DE_PANTALLAS[p.id];
      if (ayuda !== undefined) expect(ayuda.titulo, p.id).toBe(p.titulo);
    }
    expect(AYUDA_DE_PANTALLAS.pendientes?.titulo).toBe("Pendientes");
  });
});

describe("el marco pone la ayuda encima de cada pantalla", () => {
  beforeEach(() => {
    const servidor = servidorFalso(undefined, (metodo, ruta) => {
      if (metodo === "GET" && ruta === "/v1/tema") return json({ acento: null, marco: null, lateral: null, tiene_logo: false, avisos: [] });
      return undefined;
    });
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    fijarCsrf("tok");
  });
  afterEach(() => {
    cancelarSalida();
    olvidarFormularios();
    vi.unstubAllGlobals();
    fijarCsrf(null);
  });

  const titulo = (nombre: string) => screen.findByRole("heading", { level: 1, name: nombre }, { timeout: 3000 });
  const SIGUE = Node.DOCUMENT_POSITION_FOLLOWING;

  test("en una sección de la obra: tras la barra de vistas y antes del h1, y abre la ayuda de esa pantalla", async () => {
    const u = userEvent.setup();
    montarMarco(sesionDe("ana"), "/obra/empresa/7/control/reajuste");
    const h1 = await titulo("Reajuste de precios");
    const boton = screen.getByRole("button", { name: "¿Qué es esto?" });
    const vistas = screen.getByRole("navigation", { name: "Vistas de Control de obra" });
    expect(vistas.compareDocumentPosition(boton) & SIGUE).toBeTruthy();
    expect(boton.compareDocumentPosition(h1) & SIGUE).toBeTruthy();
    await u.click(boton);
    expect(screen.getByRole("region", { name: "Reajuste de precios" })).toHaveTextContent("Gaceta");
  });

  test("en el Presupuesto no hay «¿Qué es esto?» de la pantalla", async () => {
    montarMarco(sesionDe("ana"), "/obra/empresa/7/presupuesto");
    await titulo("Presupuesto");
    expect(screen.queryByRole("button", { name: "¿Qué es esto?" })).toBeNull();
  });

  test("en una herramienta de un espacio de la empresa y en la bandeja de Pendientes", async () => {
    const u = userEvent.setup();
    const { unmount } = montarMarco(sesionDe("ana"), "/precios/catalogo");
    await titulo("Catálogo de partidas e insumos");
    await u.click(screen.getByRole("button", { name: "¿Qué es esto?" }));
    expect(screen.getByRole("region", { name: "Catálogo de partidas e insumos" })).toHaveTextContent("solo se consulta");
    unmount();
    montarMarco(sesionDe("ana"), "/inicio/pendientes");
    await screen.findByRole("heading", { level: 1, name: "Pendientes" }, { timeout: 3000 });
    expect(screen.getByRole("button", { name: "¿Qué es esto?" })).toBeInTheDocument();
  });

  test("una pantalla que la cuenta no puede usar dice «Sin permiso» y no ofrece ayuda", async () => {
    montarMarco(sesionDe("rita"), "/obra/empresa/7/control");
    await titulo("Sin permiso");
    expect(screen.queryByRole("button", { name: "¿Qué es esto?" })).toBeNull();
  });
});
