// Hallazgo 14 del recorrido del 01-11-2026: Carbon deja en inglés los textos que no se le pasan («Scroll left/right»,
// «Clear search input», «close notification», «error icon», «Click to sort rows by…», la paginación…). Estas pruebas
// dibujan los componentes de Sílice que los usan y buscan esos textos en lo que se ve y en lo que se lee (atributos y
// títulos de los íconos); la última lee el fuente y exige que esos componentes se importen del envoltorio en español.
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../api/cliente";
import type { SesionRespuesta } from "../api/tipos";
import PaginaCatalogo from "../paginas/catalogo";
import { TablaPaginada } from "../paginas/hoja/TablaPaginada";
import { ContextoAplicacion } from "../shell/contexto";
import type { Aplicacion } from "../shell/contexto";
import { AvisoError } from "./AvisoError";
import { TablaDensa } from "./TablaDensa";

const INGLES = [
  /Scroll (left|right)/i,
  /Clear search input/i,
  /close notification/i,
  /\b(error|info|info-square|success|warning|warning-alt) icon\b/i,
  /^loading$/i,
  /(Show|Hide) password/i,
  /(Previous|Next) page/i,
  /Items per page/i,
  /\bof \d+ pages?\b/i,
  /\bpage \d+\b/i,
  /Click to (un)?sort/i,
  /(Select|Unselect) (all )?rows?/i,
  /(Expand|Collapse) (all|current) rows?/i,
  /^Search$/,
];

// Todo lo que se ve o se lee de un nodo: su texto y los atributos que lee una lectora o muestra el navegador.
function textosDe(raiz: Element): string[] {
  const textos: string[] = [];
  for (const el of [raiz, ...raiz.querySelectorAll("*")]) {
    for (const atributo of ["aria-label", "title", "placeholder", "alt", "aria-description"]) {
      const valor = el.getAttribute(atributo);
      if (valor) textos.push(valor);
    }
    if (el.tagName.toLowerCase() === "title" && el.textContent) textos.push(el.textContent);
    for (const hijo of el.childNodes) {
      if (hijo.nodeType === Node.TEXT_NODE && hijo.textContent?.trim()) textos.push(hijo.textContent.trim());
    }
  }
  return textos;
}

function enIngles(raiz: Element): string[] {
  return textosDe(raiz).filter((t) => INGLES.some((r) => r.test(t)));
}

function json(cuerpo: unknown): Response {
  return new Response(JSON.stringify(cuerpo), { status: 200, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["lector"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["leer_proyecto"],
  modo_entrega: false,
};

describe("textos de Carbon en español", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  test("Catálogo: las pestañas y el buscador no dejan textos en inglés", async () => {
    fetchFalso.mockImplementation((ruta) =>
      Promise.resolve(
        json(
          String(ruta).endsWith("/partidas")
            ? [{ codigo: "CIV-001", descripcion: "Excavación ficticia", unidad: "m3", dominio: "civil" }]
            : [{ codigo: "INS-1", descripcion: "Cemento ficticio", tipo: "material", unidad: "saco", precio_vigente: "1.00" }],
        ),
      ),
    );
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: { nombre: "ficticio", ruta_relativa: "data/ficticio.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    const { container } = render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter>
          <PaginaCatalogo />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
    await screen.findByRole("table", { name: "Partidas" });
    expect(enIngles(container)).toEqual([]);
    expect(container.querySelector('button[aria-label="Desplazar las pestañas a la izquierda"]')).not.toBeNull();
    expect(container.querySelector('button[aria-label="Desplazar las pestañas a la derecha"]')).not.toBeNull();
    expect(screen.getByRole("button", { name: "Borrar la búsqueda" })).toBeInTheDocument();
  });

  test("una tabla ordenable describe el orden en español", () => {
    const { container } = render(
      <TablaDensa etiqueta="Prueba" columnas={[{ clave: "codigo", titulo: "Código" }]} filas={[{ id: "1", codigo: "A" }]} />,
    );
    expect(enIngles(container)).toEqual([]);
    expect(screen.getByText("Pulse para ordenar las filas por «Código» de menor a mayor")).toBeInTheDocument();
  });

  test("la paginación de las tablas largas de la Hoja va en español", () => {
    const filas = Array.from({ length: 120 }, (_, i) => ({ id: String(i), codigo: `P-${i}` }));
    const { container } = render(<TablaPaginada etiqueta="Larga" columnas={[{ clave: "codigo", titulo: "Código" }]} filas={filas} />);
    expect(enIngles(container)).toEqual([]);
    expect(screen.getByRole("button", { name: "Página siguiente" })).toBeInTheDocument();
  });

  test("un aviso de error que se puede cerrar nombra su ícono y su botón en español", () => {
    const { container } = render(<AvisoError error="Algo ficticio falló." alCerrar={() => undefined} />);
    expect(enIngles(container)).toEqual([]);
    expect(screen.getByRole("button", { name: "Cerrar el aviso" })).toBeInTheDocument();
  });

  test("los componentes con textos por defecto se importan del envoltorio en español", () => {
    const fuentes = import.meta.glob(["../**/*.tsx", "../**/*.ts", "!../**/*.test.tsx", "!../**/*.test.ts"], {
      query: "?raw",
      import: "default",
      eager: true,
    }) as Record<string, string>;
    const vigilados = ["TabList", "Search", "InlineNotification", "InlineLoading", "PasswordInput", "Pagination", "TableHeader"];
    const infractores: string[] = [];
    for (const [ruta, fuente] of Object.entries(fuentes)) {
      if (ruta.endsWith("carbonEs.tsx")) continue; // el envoltorio mismo
      for (const m of fuente.matchAll(/import\s*\{([^}]*)\}\s*from\s*"@carbon\/react"/g)) {
        const nombres = m[1]!.split(",").map((n) => n.trim().replace(/^type\s+/, "").split(/\s+as\s+/)[0]!);
        for (const n of nombres) if (vigilados.includes(n)) infractores.push(`${ruta}: ${n}`);
      }
    }
    expect(Object.keys(fuentes).length).toBeGreaterThan(50);
    expect(infractores).toEqual([]);
  });
});
