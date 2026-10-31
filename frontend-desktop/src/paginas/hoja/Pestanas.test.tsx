import { configure, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { atipicosRespuesta, cuerpoDeVista, preciosRespuesta, trazabilidadRespuesta, vistaPlan } from "./datosDePrueba";
import PaginaHoja from "./index";
import type { BorradorAbierto, VersionesRespuesta } from "./logica";
import { ProveedorDeLaHoja, useHojaDeLaObra } from "./ProveedorDeLaHoja";

// Tarea 4 del plan F4: el Presupuesto pasa de nueve pestañas a las del plan (bajas 7, 8, 10, 11, 12, 23 y 25). Datos
// ficticios; los textos esperados están escritos a mano a partir del plan, no tomados del código.
configure({ asyncUtilTimeout: 5000 });

vi.mock("../../comun/GraficoCarbon", () => ({
  default: ({ datos }: { datos: unknown[] }) => <div data-testid="grafico" data-filas={datos.length} />,
}));

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const EDITA: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "leer_proyecto"],
  modo_entrega: false,
};
const REVISA: SesionRespuesta = { ...EDITA, login: "rita", nombre: "Rita Gómez", roles: ["revisa"], acciones: ["leer_proyecto"] };

const VERSIONES: VersionesRespuesta = {
  proyecto: "OF-001",
  moneda: "USD",
  por_omision: "001",
  versiones: [{ codigo: "001", fecha: "2026-10-05", motivo: "", origen: "", vigente: true, descartada: false, cambios: 0 }],
};

function borrador(espacioVacio: boolean): BorradorAbierto {
  return {
    id: "id-borrador-aaaaaaaaaaaa",
    base: { proyecto: "OF-001", version: "001", vigente: "001", lista: "Lista", espacio_de: "001", solo_lectura: false, moneda: "USD" },
    resumen: {
      rev: 0,
      moneda: "USD",
      total: { texto: "2703.86", exacto: "2703.860232344044033333333333" },
      cambios: 0,
      pendientes_catalogo: 0,
      hallazgos: [],
      hay_plan: true,
      version_mas_nueva: null,
      guardado_como: null,
      espacio_vacio: espacioVacio,
    },
    instantanea: { creadas: 0, mensaje: null },
  };
}

const TITULOS_DE_UNA_OBRA_CIVIL = [
  "Partidas",
  "Análisis de precio (APU)",
  "Plan y equilibrio",
  "Precios",
  "Revisión",
  "Ajustes de costo",
  "Trazabilidad",
];

describe("Presupuesto: las pestañas de la Tarea 4", () => {
  const fetchFalso = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    localStorage.clear();
    sessionStorage.clear();
  });
  afterEach(() => vi.unstubAllGlobals());

  function servidor(espacioVacio: boolean, vistas: Record<string, () => Response> = {}) {
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/hoja/versiones")) return json(VERSIONES);
      if (url === "/v1/hoja/borradores" && metodo === "POST") return json(borrador(espacioVacio), 201);
      if (url.includes("/vistas/")) {
        const nombre = /\/vistas\/([a-z]+)/.exec(url)![1]!;
        return vistas[nombre]?.() ?? json(cuerpoDeVista(url));
      }
      if (url.startsWith("/v1/hoja/precios/atipicos")) return json(atipicosRespuesta());
      if (url.startsWith("/v1/hoja/precios")) return json(preciosRespuesta());
      if (url.startsWith("/v1/hoja/trazabilidad")) return json(trazabilidadRespuesta());
      return new Response(null, { status: 204 });
    });
  }

  function aplicacion(sesion: SesionRespuesta, proyecto: string | null = "OF-001"): Aplicacion {
    return { sesion, proyecto, caso: { nombre: "obra", ruta_relativa: "data/obra.db" }, recargarProyectos: vi.fn(), alExpirar: vi.fn() };
  }

  function montar(sesion: SesionRespuesta = EDITA) {
    return render(
      <ContextoAplicacion.Provider value={aplicacion(sesion)}>
        <PaginaHoja />
      </ContextoAplicacion.Provider>,
    );
  }

  async function irA(titulo: string) {
    await screen.findByRole("region", { name: "Estado del borrador" });
    await userEvent.click(await screen.findByRole("tab", { name: titulo }));
  }

  test("baja 7: el título de la pantalla es «Presupuesto» y no «Hoja de la obra»", async () => {
    servidor(true);
    montar();
    expect(screen.getByRole("heading", { level: 1, name: "Presupuesto" })).toBeInTheDocument();
    expect(screen.queryByText("Hoja de la obra")).toBeNull();
    await screen.findByRole("region", { name: "Estado del borrador" });
  });

  test("una obra civil ve siete pestañas, con los títulos del plan y en su orden", async () => {
    servidor(true);
    montar();
    const lista = await screen.findByRole("tablist", { name: "Secciones del presupuesto" });
    expect(within(lista).getAllByRole("tab").map((t) => t.textContent)).toEqual(TITULOS_DE_UNA_OBRA_CIVIL);
    expect(await screen.findByRole("tab", { name: "Partidas", selected: true })).toBeInTheDocument();
  });

  test("una obra con espacio ve además «Espacio y metrajes», primera y abierta", async () => {
    servidor(false);
    montar();
    const lista = await screen.findByRole("tablist", { name: "Secciones del presupuesto" });
    expect(within(lista).getAllByRole("tab").map((t) => t.textContent)).toEqual(["Espacio y metrajes", ...TITULOS_DE_UNA_OBRA_CIVIL]);
    expect(await screen.findByRole("tab", { name: "Espacio y metrajes", selected: true })).toBeInTheDocument();
  });

  test("baja 8: sin obra no se dice «Use el selector de obra de la cabecera»", () => {
    servidor(true);
    render(
      <ContextoAplicacion.Provider value={aplicacion(EDITA, null)}>
        <PaginaHoja />
      </ContextoAplicacion.Provider>,
    );
    expect(screen.queryByText(/Use el selector de obra de la cabecera/)).toBeNull();
    expect(screen.getByRole("heading", { level: 1, name: "Presupuesto" })).toBeInTheDocument();
  });

  test("baja 10: en «Análisis de precio (APU)» no hay «Factores de la versión»", async () => {
    servidor(true);
    montar();
    await irA("Análisis de precio (APU)");
    expect(await screen.findByRole("heading", { level: 3, name: "Cierre de partida" })).toBeInTheDocument();
    expect(screen.queryByText("Factores de la versión")).toBeNull();
  });

  test("baja 11: en «Plan y equilibrio» no hay «Crear plan secuencial», y sí los bloques «Plan desde los rendimientos» y «Punto de equilibrio»", async () => {
    servidor(true, { plan: () => json(vistaPlan({ hay_plan: false, filas: [], etiquetas: [], curva: [], mensaje: "Esta versión no tiene plan." })) });
    montar();
    await irA("Plan y equilibrio");
    expect(await screen.findByRole("heading", { level: 2, name: "Plan desde los rendimientos" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 2, name: "Punto de equilibrio" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Crear plan secuencial/ })).toBeNull();
    expect(screen.queryByRole("tab", { name: "Punto de equilibrio" })).toBeNull();
  });

  test("baja 23: el equilibrio va debajo del plan, en la misma pestaña, y el plan sigue ahí", async () => {
    servidor(true);
    montar();
    await irA("Plan y equilibrio");
    const plan = await screen.findByRole("heading", { level: 2, name: "Curva de inversión" });
    const equilibrio = await screen.findByRole("heading", { level: 2, name: "Punto de equilibrio" });
    expect(plan.compareDocumentPosition(equilibrio) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(await screen.findByText("Ventas (contrato)")).toBeInTheDocument();
  });

  test("baja 12: «Ajustes de costo» y «Espacio y metrajes» no repiten el total ni la moneda del proyecto", async () => {
    servidor(false);
    montar();
    await screen.findByRole("heading", { level: 3, name: "Ambientes" });
    expect(screen.queryByText(/Total del presupuesto/)).toBeNull();
    await userEvent.click(screen.getByRole("tab", { name: "Ajustes de costo" }));
    expect(await screen.findByRole("textbox", { name: /^FCAS/ })).toBeInTheDocument();
    expect(screen.queryByText(/Total del presupuesto/)).toBeNull();
    expect(screen.queryByText(/Moneda del proyecto/)).toBeNull();
    // El total sigue en un solo lugar: bajo la tabla de «Partidas».
    await userEvent.click(screen.getByRole("tab", { name: "Partidas" }));
    expect(await screen.findByText(/Total del presupuesto/)).toBeInTheDocument();
  });

  test("baja 12: «Ajustes de costo» conserva «Convertir la moneda…» para quien puede convertir", async () => {
    servidor(true);
    const sesion = { ...EDITA, acciones: [...EDITA.acciones, "convertir_y_reajustar"] };
    montar(sesion);
    await irA("Ajustes de costo");
    expect(await screen.findByRole("button", { name: /Convertir la moneda/ })).toBeInTheDocument();
  });

  test("baja 25: el texto largo de «Partidas» solo aparece tras «¿Qué es esto?»", async () => {
    servidor(true);
    montar();
    await screen.findByRole("table", { name: "Presupuesto" });
    const frase = /se aplican al borrador cuando deja de escribir/;
    expect(screen.queryByText(frase)).toBeNull();
    const boton = screen.getByRole("button", { name: "¿Qué es esto?" });
    expect(boton).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(boton);
    expect(await screen.findByText(frase)).toBeInTheDocument();
  });

  test.each([
    ["Partidas", /se aplican al borrador cuando deja de escribir/],
    ["Plan y equilibrio", /Reparta cada partida entre los períodos/],
    ["Ajustes de costo", /Cambiarlos recalcula todos los APU/],
    ["Precios", /erosión/],
  ])("baja 25: «%s» tiene su «¿Qué es esto?» plegado", async (titulo, frase) => {
    servidor(true);
    montar();
    await irA(titulo as string);
    const boton = await screen.findByRole("button", { name: "¿Qué es esto?" });
    expect(boton).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(boton);
    expect(within(screen.getByRole("region", { name: titulo as string })).getByText(frase as RegExp)).toBeInTheDocument();
  });

  test("«Ver en Revisión» de una fila lleva a la pestaña «Revisión» con el filtro de la fila", async () => {
    servidor(false);
    montar();
    const tabla = await screen.findByRole("table", { name: "Fuentes" });
    expect(within(tabla).queryByRole("button", { name: /Ver en Auditoría/ })).toBeNull();
    await userEvent.click(within(tabla).getByRole("button", { name: "Ver en Revisión: Fuente F1" }));
    expect(await screen.findByRole("tab", { name: "Revisión", selected: true })).toBeInTheDocument();
    expect(await screen.findByText("Hallazgos de Fuente F1")).toBeInTheDocument();
  });

  test("«Revisión» es la pestaña del informe, sin filtro cuando se llega a mano", async () => {
    servidor(true);
    montar();
    await irA("Revisión");
    expect(await screen.findByRole("region", { name: "Informe de auditoría" })).toBeInTheDocument();
  });

  test("cuenta que revisa: ve las siete pestañas y cada «¿Qué es esto?», y ningún control que escriba", async () => {
    servidor(true);
    montar(REVISA);
    const lista = await screen.findByRole("tablist", { name: "Secciones del presupuesto" });
    expect(within(lista).getAllByRole("tab").map((t) => t.textContent)).toEqual(TITULOS_DE_UNA_OBRA_CIVIL);
    await screen.findByRole("table", { name: "Presupuesto" });
    expect(screen.getByRole("button", { name: "¿Qué es esto?" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Agregar partida" })).toBeNull();
    expect(screen.queryByRole("button", { name: /Guardar/ })).toBeNull();
  });

  test("la pestaña elegida vive en el proveedor: al ir a otra sección y volver sigue donde estaba", async () => {
    servidor(true);
    function Relleno() {
      const { pestana } = useHojaDeLaObra();
      return <p>{`En Versiones, la pestaña guardada es ${pestana}`}</p>;
    }
    function Alternar() {
      const [en, setEn] = useState<"presupuesto" | "versiones">("presupuesto");
      return (
        <>
          <button type="button" onClick={() => setEn(en === "presupuesto" ? "versiones" : "presupuesto")}>
            Cambiar de sección
          </button>
          {en === "presupuesto" ? <PaginaHoja /> : <Relleno />}
        </>
      );
    }
    render(
      <ContextoAplicacion.Provider value={aplicacion(EDITA)}>
        <ProveedorDeLaHoja>
          <Alternar />
        </ProveedorDeLaHoja>
      </ContextoAplicacion.Provider>,
    );
    await irA("Precios");
    await userEvent.click(screen.getByRole("button", { name: "Cambiar de sección" }));
    expect(await screen.findByText("En Versiones, la pestaña guardada es precios")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Cambiar de sección" }));
    expect(await screen.findByRole("tab", { name: "Precios", selected: true })).toBeInTheDocument();
  });
});
