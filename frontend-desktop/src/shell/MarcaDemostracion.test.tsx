import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../api/cliente";
import { MarcaDemostracion } from "./MarcaDemostracion";
import { caso, estadoInicial, ligeras, montarMarco, servidorFalso, sesionDe } from "./obras/datosDePrueba";
import { cancelarSalida } from "./salida";
import { olvidarFormularios, useFormularioSucio } from "./sucio";

// Plan de modulos, MOD-3b (diseno de modulos §7 y §12.2): en la carpeta de demostracion la barra lo dice con texto e
// icono y ofrece «Volver a la carpeta de la empresa» (`DELETE /v1/casos/actual`), que pasa por la misma confirmacion
// que cambiar de carpeta porque descarta los borradores de la Hoja (`caso_web.olvidar`).

function Ubicacion() {
  const { pathname, search } = useLocation();
  return <span data-testid="ruta">{`${pathname}${search}`}</span>;
}

describe("MarcaDemostracion", () => {
  test("fuera de la demostración no pinta nada", () => {
    const { container } = render(
      <MemoryRouter>
        <MarcaDemostracion activa={false} puedeVolver alVolver={vi.fn()} />
      </MemoryRouter>,
    );
    expect(container).toBeEmptyDOMElement();
  });

  test("dice «Demostración» con un ícono y abre «Está viendo datos inventados.» con «Volver a la carpeta de la empresa»", async () => {
    const u = userEvent.setup();
    const alVolver = vi.fn();
    render(
      <MemoryRouter>
        <MarcaDemostracion activa puedeVolver alVolver={alVolver} />
      </MemoryRouter>,
    );
    const boton = screen.getByRole("button", { name: /^Demostración/ });
    expect(boton).toHaveTextContent("Demostración");
    expect(boton.querySelector("svg")).not.toBeNull();
    expect(boton).toHaveAttribute("aria-expanded", "false");
    await u.click(boton);
    expect(boton).toHaveAttribute("aria-expanded", "true");
    const panel = screen.getByRole("region", { name: "Demostración" });
    expect(within(panel).getByText("Está viendo datos inventados.")).toBeInTheDocument();
    await u.click(within(panel).getByRole("button", { name: "Volver a la carpeta de la empresa" }));
    expect(alVolver).toHaveBeenCalled();
  });

  test("«Ver los recorridos guiados» es un botón terciario que cierra el panel y lleva a los recorridos en la Ayuda", async () => {
    const u = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/auditoria/libros"]}>
        <MarcaDemostracion activa puedeVolver alVolver={vi.fn()} />
        <Ubicacion />
      </MemoryRouter>,
    );
    const boton = screen.getByRole("button", { name: /^Demostración/ });
    await u.click(boton);
    const ir = within(screen.getByRole("region", { name: "Demostración" })).getByRole("button", {
      name: "Ver los recorridos guiados",
    });
    expect(ir).toHaveClass("cds--btn--tertiary");
    await u.click(ir);
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("region", { name: "Demostración" })).not.toBeInTheDocument();
    expect(screen.getByTestId("ruta")).toHaveTextContent("/cuenta/ayuda?tema=recorridos");
  });

  test("sin poder cambiar de carpeta (rita) se ve la marca con recorridos y sin el botón de volver", async () => {
    const u = userEvent.setup();
    render(
      <MemoryRouter>
        <MarcaDemostracion activa puedeVolver={false} alVolver={vi.fn()} />
      </MemoryRouter>,
    );
    await u.click(screen.getByRole("button", { name: /^Demostración/ }));
    expect(screen.getByText("Está viendo datos inventados.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ver los recorridos guiados" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Volver a la carpeta de la empresa" })).not.toBeInTheDocument();
  });

  test("Esc cierra el panel y devuelve el foco a la marca", async () => {
    const u = userEvent.setup();
    render(
      <MemoryRouter>
        <MarcaDemostracion activa puedeVolver alVolver={vi.fn()} />
      </MemoryRouter>,
    );
    const boton = screen.getByRole("button", { name: /^Demostración/ });
    await u.click(boton);
    await u.keyboard("{Escape}");
    expect(screen.queryByText("Está viendo datos inventados.")).not.toBeInTheDocument();
    expect(boton).toHaveFocus();
  });

  test("ninguna cadena visible de la marca dice «caso» ni «proyecto»", async () => {
    const u = userEvent.setup();
    render(
      <MemoryRouter>
        <MarcaDemostracion activa puedeVolver alVolver={vi.fn()} />
      </MemoryRouter>,
    );
    await u.click(screen.getByRole("button", { name: /^Demostración/ }));
    for (const patron of [/\bcaso\b/i, /\bproyecto\b/i]) {
      expect(screen.queryByText(patron)).toBeNull();
      expect(screen.queryByRole("button", { name: patron })).toBeNull();
    }
  });
});

describe("MarcaDemostracion en el armazón", () => {
  let servidor: ReturnType<typeof servidorFalso>;

  function enDemostracion() {
    const estado = estadoInicial();
    const demo = caso("demostracion.db");
    estado.casos = [...estado.casos, demo];
    estado.actual = demo;
    return estado;
  }

  beforeEach(() => {
    servidor = servidorFalso(enDemostracion());
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    fijarCsrf("tok");
  });
  afterEach(() => {
    cancelarSalida();
    olvidarFormularios();
    vi.unstubAllGlobals();
    fijarCsrf(null);
  });

  const marca = () => within(screen.getByRole("banner")).findByRole("button", { name: /^Demostración/ });

  test.each(["/auditoria/libros", "/hoja", "/produccion/existencias"])("con es_demostracion la barra dice «Demostración» en %s", async (ruta) => {
    montarMarco(sesionDe("ana"), ruta);
    expect(await marca()).toHaveTextContent("Demostración");
  });

  test("fuera de la demostración la barra no la muestra", async () => {
    servidor = servidorFalso();
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    montarMarco(sesionDe("ana"), "/inicio/pendientes");
    await screen.findByRole("heading", { level: 1, name: "Pendientes" });
    await waitFor(() => expect(servidor.de("GET", "/v1/casos").length).toBeGreaterThan(0));
    expect(within(screen.getByRole("banner")).queryByRole("button", { name: /^Demostración/ })).toBeNull();
  });

  test("«Volver a la carpeta de la empresa» llama DELETE /v1/casos/actual, avisa y la marca se va", async () => {
    const u = userEvent.setup();
    montarMarco(sesionDe("ana"), "/auditoria/libros");
    await u.click(await marca());
    await u.click(screen.getByRole("button", { name: "Volver a la carpeta de la empresa" }));
    await waitFor(() => expect(servidor.de("DELETE", "/v1/casos/actual")).toHaveLength(1));
    expect(await screen.findByText("Ahora trabaja con la carpeta «silice».")).toBeInTheDocument();
    await waitFor(() => expect(within(screen.getByRole("banner")).queryByRole("button", { name: /^Demostración/ })).toBeNull());
  });

  test("con Componer a medio llenar, volver pregunta como al cambiar de carpeta; «Quedarme» no llama DELETE", async () => {
    const u = userEvent.setup();
    function ComponerSucio() {
      useFormularioSucio("componer", true);
      return <h1>Componer una partida</h1>;
    }
    // F6, T5: Componer es una subvista de Presupuesto; `/componer` sin obra ya no se abre en su sitio.
    montarMarco(sesionDe("ana"), "/obra/demostracion.db/7/presupuesto/componer", ligeras({ componer: ComponerSucio }));
    await screen.findByRole("heading", { level: 1, name: "Componer una partida" });
    await u.click(await marca());
    await u.click(screen.getByRole("button", { name: "Volver a la carpeta de la empresa" }));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    expect(pregunta).toHaveAccessibleDescription(
      "Tiene cambios sin guardar en Componer una partida. Si cambia de carpeta, se perderán.",
    );
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    await new Promise((r) => setTimeout(r, 30));
    expect(servidor.de("DELETE", "/v1/casos/actual")).toEqual([]);
  });

  test("rita (revisa, con abrir_carpeta desde el 2026-11-05) en la demostración puede volver a la carpeta de la empresa", async () => {
    const u = userEvent.setup();
    montarMarco(sesionDe("rita"), "/auditoria/libros");
    await u.click(await marca());
    expect(screen.getByText("Está viendo datos inventados.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Volver a la carpeta de la empresa" })).toBeInTheDocument();
  });

  test("una cuenta sin abrir_carpeta en la demostración ve la marca sin el botón de volver", async () => {
    const u = userEvent.setup();
    montarMarco(sesionDe("rita", { acciones: sesionDe("rita").acciones.filter((a) => a !== "abrir_carpeta") }), "/auditoria/libros");
    await u.click(await marca());
    expect(screen.getByText("Está viendo datos inventados.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ver los recorridos guiados" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Volver a la carpeta de la empresa" })).not.toBeInTheDocument();
  });

  test("«Ver los recorridos guiados» cierra el panel y abre los recorridos guiados en la Ayuda", async () => {
    const u = userEvent.setup();
    montarMarco(sesionDe("ana"), "/auditoria/libros");
    const boton = await marca();
    await u.click(boton);
    await u.click(screen.getByRole("button", { name: "Ver los recorridos guiados" }));
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("region", { name: "Demostración" })).not.toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 1, name: "Ayuda y acerca de Sílice" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 2, name: "Recorridos guiados" })).toBeInTheDocument();
  });

  test("con Componer a medio llenar, «Ver los recorridos guiados» pregunta antes de salir; «Quedarme» deja la pantalla", async () => {
    const u = userEvent.setup();
    function ComponerSucio() {
      useFormularioSucio("componer", true);
      return <h1>Componer una partida</h1>;
    }
    montarMarco(sesionDe("ana"), "/obra/demostracion.db/7/presupuesto/componer", ligeras({ componer: ComponerSucio }));
    await screen.findByRole("heading", { level: 1, name: "Componer una partida" });
    await u.click(await marca());
    await u.click(screen.getByRole("button", { name: "Ver los recorridos guiados" }));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    expect(screen.getByRole("heading", { level: 1, name: "Componer una partida" })).toBeInTheDocument();
  });
});
