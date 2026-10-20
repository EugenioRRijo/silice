import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaHoja from "./index";
import type { BorradorAbierto, VersionesRespuesta } from "./logica";

const fuentes = import.meta.glob("./*.{ts,tsx}", { query: "?raw", import: "default", eager: true }) as Record<
  string,
  string
>;

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja"],
  modo_entrega: false,
};

const FALTA =
  "Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). Lo que no guardó se perdió: abra la versión otra vez.";

function version(codigo: string, extra: Record<string, unknown> = {}) {
  return { codigo, fecha: "2026-10-05", motivo: "", origen: "", vigente: false, descartada: false, cambios: 0, ...extra };
}

const VERSIONES: VersionesRespuesta = {
  proyecto: "OF-001",
  moneda: "USD",
  por_omision: "002",
  versiones: [version("001"), version("002", { vigente: true }), version("003", { descartada: true })],
};

function borrador(id: string, codigo: string | null, extra: Record<string, unknown> = {}): BorradorAbierto {
  return {
    id,
    base: {
      proyecto: "OF-001",
      version: codigo,
      vigente: "002",
      lista: codigo ? "Lista MaPreX" : null,
      espacio_de: codigo,
      solo_lectura: false,
      moneda: "USD",
    },
    resumen: {
      rev: 0,
      moneda: "USD",
      total: { texto: "2703.86", exacto: "2703.856" },
      cambios: 0,
      pendientes_catalogo: 0,
      hallazgos: [],
      hay_plan: true,
      version_mas_nueva: null,
      guardado_como: null,
      ...extra,
    },
    instantanea: { creadas: 0, mensaje: null },
  };
}

describe("Hoja del proyecto (marco, 3b-1)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    localStorage.clear();
    sessionStorage.clear();
  });
  afterEach(() => vi.unstubAllGlobals());

  function llamadas(metodo: string, trozo: string): Array<[string, RequestInit | undefined]> {
    return fetchFalso.mock.calls
      .map(([ruta, init]) => [String(ruta), init] as [string, RequestInit | undefined])
      .filter(([ruta, init]) => ruta.includes(trozo) && (init?.method ?? "GET") === metodo);
  }

  // Un servidor de mentira: versiones por GET, borrador por POST (el id lleva la versión) y DELETE en 204.
  function servidor(versiones: VersionesRespuesta = VERSIONES, extra: Record<string, unknown> = {}) {
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/hoja/versiones")) return json(versiones);
      if (url === "/v1/hoja/borradores" && metodo === "POST") {
        const cuerpo = JSON.parse(String(init?.body)) as { version: string | null };
        return json(borrador(`id-${cuerpo.version ?? "blanco"}-aaaaaaaaaa`, cuerpo.version, extra), 201);
      }
      if (url.startsWith("/v1/hoja/borradores/") && metodo === "DELETE") return new Response(null, { status: 204 });
      return json({ detalle: "ruta inesperada" }, 500);
    });
  }

  function montar(proyecto: string | null = "OF-001") {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto,
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <PaginaHoja />
      </ContextoAplicacion.Provider>,
    );
  }

  test("3b-F1: un solo h1 «Hoja del proyecto» con heading-04", async () => {
    servidor();
    montar();
    await screen.findByRole("region", { name: "Estado del borrador" }, { timeout: 5000 });
    const h1 = screen.getAllByRole("heading", { level: 1 });
    expect(h1).toHaveLength(1);
    expect(h1[0]).toHaveTextContent("Hoja del proyecto");
    expect(h1[0]).toHaveClass("cds--type-heading-04");
    expect(screen.getByRole("heading", { level: 2, name: "Estado del borrador" })).toHaveClass(
      "cds--type-heading-compact-02",
    );
  });

  test("3b-F2: sin proyecto en la cabecera pide elegir uno y no llama a la API", () => {
    montar(null);
    expect(screen.getByRole("heading", { level: 1, name: "Hoja del proyecto" })).toBeInTheDocument();
    expect(screen.getByText("Elija un proyecto")).toBeInTheDocument();
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("3b-F2: un proyecto sin versiones lo dice y abre un borrador en blanco", async () => {
    servidor({ proyecto: "Nuevo", moneda: "USD", por_omision: null, versiones: [] });
    montar("Nuevo");
    expect(await screen.findByText("Este proyecto aún no tiene versiones")).toBeInTheDocument();
    await screen.findByRole("region", { name: "Estado del borrador" });
    const [[, init]] = llamadas("POST", "/v1/hoja/borradores");
    expect(JSON.parse(String(init?.body))).toEqual({ proyecto: "Nuevo", version: null });
  });

  test("3b-F3: las nueve pestañas, en el orden de la clásica, con las flechas", async () => {
    servidor();
    montar();
    const lista = await screen.findByRole("tablist");
    const pestanas = within(lista).getAllByRole("tab");
    expect(pestanas.map((p) => p.textContent)).toEqual([
      "Espacio y metrajes",
      "APU",
      "Presupuesto",
      "Plan y curva",
      "Punto de equilibrio",
      "Precios",
      "Parámetros",
      "Auditoría",
      "Trazabilidad",
    ]);
    expect(screen.getAllByRole("tabpanel").length).toBeGreaterThan(0);
    pestanas[0]!.focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(pestanas[1]).toHaveFocus();
  });

  test("3b-F4: el selector ofrece las no descartadas, marca la vigente y preselecciona por_omision", async () => {
    servidor();
    montar();
    const selector = await screen.findByRole("combobox", { name: "Versión" });
    const opciones = within(selector).getAllByRole("option").map((o) => o.textContent);
    expect(opciones).toEqual(["001", "002 (vigente)"]);
    expect(selector).toHaveValue("002");
    await waitFor(() => expect(llamadas("POST", "/v1/hoja/borradores")).toHaveLength(1));
    expect(JSON.parse(String(llamadas("POST", "/v1/hoja/borradores")[0]![1]?.body))).toEqual({
      proyecto: "OF-001",
      version: "002",
    });
  });

  test("cambiar de versión abre otro borrador y descarta el anterior (sin cambios)", async () => {
    servidor();
    montar();
    const selector = await screen.findByRole("combobox", { name: "Versión" });
    await screen.findByRole("region", { name: "Estado del borrador" });
    await userEvent.selectOptions(selector, "001");
    await waitFor(() => expect(llamadas("POST", "/v1/hoja/borradores")).toHaveLength(2));
    expect(JSON.parse(String(llamadas("POST", "/v1/hoja/borradores")[1]![1]?.body)).version).toBe("001");
    await waitFor(() => expect(llamadas("DELETE", "/v1/hoja/borradores/id-002-aaaaaaaaaa")).toHaveLength(1));
  });

  test("3b-F5: el total sale en es-VE con el exacto en el title y en un texto accesible", async () => {
    servidor();
    montar();
    const estado = await screen.findByRole("region", { name: "Estado del borrador" });
    const total = await within(estado).findByTitle("2703.856");
    expect(total).toHaveTextContent("2.703,86 USD");
    expect(within(estado).getByText("Valor exacto 2703.856")).toBeInTheDocument();
    expect(within(estado).getByText(/Sin cambios sin guardar/)).toBeInTheDocument();
  });

  test("3b-F5: un total de 30 cifras no pierde ninguna", async () => {
    const largo = "123456789012345678901234567890";
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      if (url.startsWith("/v1/hoja/versiones")) return json(VERSIONES);
      if ((init?.method ?? "GET") === "POST") {
        const b = borrador("id-largo-aaaaaaaaaaaa", "002");
        b.resumen.total = { texto: `${largo}.12`, exacto: `${largo}.1234` };
        return json(b, 201);
      }
      return new Response(null, { status: 204 });
    });
    montar();
    const estado = await screen.findByRole("region", { name: "Estado del borrador" });
    expect(await within(estado).findByTitle(`${largo}.1234`)).toHaveTextContent(
      "123.456.789.012.345.678.901.234.567.890,12 USD",
    );
  });

  test("3b-F5: el código de la página no convierte montos en números", () => {
    const propios = Object.entries(fuentes).filter(([ruta]) => !/\.test\.tsx?$/.test(ruta));
    expect(propios.length).toBeGreaterThanOrEqual(3);
    for (const [ruta, fuente] of propios) {
      expect(fuente, ruta).not.toMatch(/\bNumber\s*\(|\bparseFloat\s*\(|\bparseInt\s*\(|\bunary\b/);
    }
  });

  test("avisa de que abrir la versión creó su instantánea", async () => {
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      if (url.startsWith("/v1/hoja/versiones")) return json(VERSIONES);
      if ((init?.method ?? "GET") === "POST") {
        const b = borrador("id-instantanea-aaaaaaa", "002");
        b.instantanea = { creadas: 4, mensaje: "Se creó y registró la instantánea (4 partidas)." };
        return json(b, 201);
      }
      return new Response(null, { status: 204 });
    });
    montar();
    expect(await screen.findByText(/Se creó y registró la instantánea \(4 partidas\)\./)).toBeInTheDocument();
  });

  test("hay una región del asistente, oculta y vacía, fuera de las pestañas", async () => {
    servidor();
    const { container } = montar();
    await screen.findByRole("region", { name: "Estado del borrador" });
    const aside = container.querySelector('aside[aria-label="Asistente de IA"]');
    expect(aside).not.toBeNull();
    expect(aside).toHaveAttribute("hidden");
    expect(aside?.textContent).toBe("");
  });

  test("3b-F13: un 401 llama a alExpirar", async () => {
    fetchFalso.mockImplementation(async () => json({ detalle: "Sesión ausente o vencida." }, 401));
    montar();
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("3b-F13: un error al abrir muestra el detalle tal cual", async () => {
    fetchFalso.mockImplementation(async (ruta, init) => {
      if (String(ruta).startsWith("/v1/hoja/versiones")) return json(VERSIONES);
      if ((init?.method ?? "GET") === "POST") return json({ detalle: "El proyecto «Z» no existe en este caso." }, 404);
      return new Response(null, { status: 204 });
    });
    montar();
    expect(await screen.findByText("El proyecto «Z» no existe en este caso.")).toBeInTheDocument();
  });

  test("3b-F13: un borrador que ya no está (reinicio) muestra el aviso y deja abrir de nuevo", async () => {
    let abiertos = 0;
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/hoja/versiones")) return json(VERSIONES);
      if (url === "/v1/hoja/borradores" && metodo === "POST") {
        abiertos += 1;
        return json(borrador(`id-${abiertos}-aaaaaaaaaaaaaa`, "002"), 201);
      }
      if (url.startsWith("/v1/hoja/borradores/") && metodo === "GET") return json({ detalle: FALTA }, 404);
      return new Response(null, { status: 204 });
    });
    montar();
    await screen.findByRole("region", { name: "Estado del borrador" });
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(await screen.findByText(FALTA)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Abrir de nuevo" }));
    await screen.findByRole("region", { name: "Estado del borrador" });
    expect(abiertos).toBe(2);
  });

  test("3b-F14: no se escribe nada en localStorage ni sessionStorage y no hay campos de contraseña", async () => {
    servidor();
    const { container } = montar();
    await screen.findByRole("region", { name: "Estado del borrador" });
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    expect(container.querySelector('input[type="password"]')).toBeNull();
  });

  test("3b-F15: al desmontar sin cambios se descarta el borrador", async () => {
    servidor();
    const { unmount } = montar();
    await screen.findByRole("region", { name: "Estado del borrador" });
    unmount();
    await waitFor(() => expect(llamadas("DELETE", "/v1/hoja/borradores/id-002-aaaaaaaaaa")).toHaveLength(1));
  });

  test("3b-F15: con cambios el borrador se conserva al desmontar", async () => {
    servidor(VERSIONES, { cambios: 2 });
    const { unmount } = montar();
    const estado = await screen.findByRole("region", { name: "Estado del borrador" });
    expect(within(estado).getByText(/2 cambios sin guardar/)).toBeInTheDocument();
    unmount();
    await Promise.resolve();
    expect(llamadas("DELETE", "/v1/hoja/borradores")).toHaveLength(0);
  });

  test("un borrador cuya apertura llegó tarde (la persona ya cambió de versión) se descarta", async () => {
    let soltar: (r: Response) => void = () => {};
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/hoja/versiones")) return json(VERSIONES);
      if (url === "/v1/hoja/borradores" && metodo === "POST") {
        const cuerpo = JSON.parse(String(init?.body)) as { version: string };
        if (cuerpo.version === "002") return new Promise<Response>((r) => (soltar = r));
        return json(borrador("id-001-aaaaaaaaaaaaaaa", "001"), 201);
      }
      return new Response(null, { status: 204 });
    });
    montar();
    const selector = await screen.findByRole("combobox", { name: "Versión" });
    fireEvent.change(selector, { target: { value: "001" } });
    await screen.findByRole("region", { name: "Estado del borrador" });
    await act(async () => soltar(json(borrador("id-002-tardio-aaaaaaa", "002"), 201)));
    await waitFor(() => expect(llamadas("DELETE", "/v1/hoja/borradores/id-002-tardio-aaaaaaa")).toHaveLength(1));
  });
});
