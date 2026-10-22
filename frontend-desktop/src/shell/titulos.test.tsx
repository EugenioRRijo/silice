import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../api/tipos";
import { ContextoAplicacion } from "./contexto";
import type { Aplicacion } from "./contexto";
import { PAGINAS } from "./rutas";

// Importar cada página en frío (Carbon, Univer) tarda más de 20 s en una máquina cargada: solo este archivo espera 60 s.
vi.setConfig({ testTimeout: 60_000 });

// Recorre el registro: cada pagina migrada se dibuja con exactamente un h1 en heading-04, y ningun h2 de las
// paginas usa otro tamano que heading-compact-02 (V-8 de la auditoria visual).
const ACCIONES = [...new Set(PAGINAS.flatMap((p) => (p.accion ? [p.accion] : [])))];
const SESION: SesionRespuesta = {
  login: "admin",
  nombre: "Admin",
  roles: ["administrador"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ACCIONES,
  modo_entrega: false,
};

const FUENTES = import.meta.glob("../paginas/**/*.tsx", { query: "?raw", import: "default", eager: true }) as Record<
  string,
  string
>;

describe("Títulos de las páginas migradas", () => {
  beforeEach(() => {
    // La API nunca contesta: se ve el primer dibujo de cada pagina.
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(() => {})));
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  for (const pagina of PAGINAS.filter((p) => p.cargar)) {
    test(`${pagina.id}: un solo h1 en heading-04`, async () => {
      const Pagina = (await pagina.cargar!()).default;
      const valor: Aplicacion = {
        sesion: SESION,
        proyecto: null,
        caso: null,
        recargarProyectos: vi.fn(),
        alExpirar: vi.fn(),
      };
      const { container } = render(
        <ContextoAplicacion.Provider value={valor}>
          <MemoryRouter>
            <Pagina />
          </MemoryRouter>
        </ContextoAplicacion.Provider>,
      );
      const h1 = container.querySelectorAll("h1");
      expect(h1).toHaveLength(1);
      expect(h1[0].className).toContain("cds--type-heading-04");
      // V-6: el marco comun de pagina (libros trae el suyo, con el visor a alto completo).
      if (pagina.id !== "libros") expect(container.querySelector(".silice-pagina")).not.toBeNull();
    });
  }

  test("los h2 de las páginas usan heading-compact-02", () => {
    const malos: string[] = [];
    for (const [ruta, texto] of Object.entries(FUENTES)) {
      if (/\.test\.tsx$/.test(ruta)) continue;
      for (const m of texto.matchAll(/<h2\b[^>]*>/g)) {
        if (!m[0].includes("cds--type-heading-compact-02")) malos.push(`${ruta}: ${m[0]}`);
      }
    }
    expect(malos).toEqual([]);
  });
});
