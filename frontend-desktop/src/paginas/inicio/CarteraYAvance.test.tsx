import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, test } from "vitest";
import type { ResumenTodasRespuesta } from "../../api/tipos";
import { CarteraYAvance } from "./CarteraYAvance";

// Los gráficos de la Vista general (rediseño 2026-11-21) con la respuesta de `GET /v1/obras/resumen/todas` tal como llega:
// el avance con punto decimal («62.5»). La pantalla escribe esas cifras en es-VE y no calcula ninguna nueva: el anillo por
// estado cuenta las obras de la lista (la API no manda porcentajes por estado). Obras y cifras ficticias.
const CARTERA: ResumenTodasRespuesta = {
  hoy: "2026-11-05",
  por_moneda: [
    { moneda: "Bs", obras: 3, total: "334570.5", en_ejecucion: 2 },
    { moneda: "USD", obras: 1, total: "95066.6", en_ejecucion: 0 },
  ],
  obras: [
    obra(7, "Casa Demo", "en_ejecucion", "En ejecución", "62.5", "70.0"),
    obra(8, "Torre B", "en_elaboracion", "En elaboración", null, null),
    obra(3, "Galpón Sur", "atrasada", "Atrasada", "10.0", "25.5"),
    obra(9, "Puente Norte", "en_ejecucion", "En ejecución", "100.0", "100.0"),
  ],
  carpetas_omitidas: 0,
};

function obra(id: number, nombre: string, etapa: string, etapa_texto: string, real: string | null, plan: string | null) {
  return {
    carpeta: null,
    carpeta_titulo: "Carpeta de la empresa",
    obra_id: id,
    nombre,
    moneda: "Bs",
    etapa,
    etapa_texto,
    total: "1000.00",
    avance_real: real,
    avance_plan: plan,
  };
}

function montar(datos: ResumenTodasRespuesta = CARTERA) {
  return render(
    <MemoryRouter>
      <CarteraYAvance carga={{ estado: "listo", datos }} carpetas={new Map()} puedeCrear={false} />
    </MemoryRouter>,
  );
}

const avance = () => screen.getByRole("heading", { name: "Avance real frente al plan" }).parentElement!;
const porEstado = () => screen.getByRole("heading", { name: "Distribución de obras por estado" }).parentElement!;

describe("Vista general: el gráfico del avance real contra el plan", () => {
  test("cada barra dice el avance de la API en es-VE: «62.5» se lee 62,5 %", () => {
    montar();
    const g = avance();
    for (const t of ["62,5 %", "70,0 %", "10,0 %", "25,5 %"]) expect(within(g).getByText(t)).toBeInTheDocument();
    expect(g.textContent).not.toMatch(/62\.5|25\.5/);
  });

  test("solo las obras con avance: la obra sin avance no tiene barra ni un «0 %»", () => {
    montar();
    const g = avance();
    expect(within(g).queryByText("Torre B")).toBeNull();
    expect(g.textContent).not.toMatch(/(^|[^0-9,])0,0 %/);
  });

  test("el real va relleno y el plan en contorno (IBCS), sin colores en línea", () => {
    const { container } = montar();
    const g = avance();
    expect(g.querySelectorAll(".silice-barras-v__barra--real")).toHaveLength(3);
    expect(g.querySelectorAll(".silice-barras-v__barra--plan")).toHaveLength(3);
    for (const b of container.querySelectorAll<HTMLElement>(".silice-barras-v__barra")) expect(b.style.backgroundColor).toBe("");
  });
});

describe("Vista general: el anillo de obras por estado", () => {
  test("cuenta las obras de cada estado y no escribe porcentajes que la API no da", () => {
    montar();
    const g = porEstado();
    expect(within(g).getByRole("button", { name: "En ejecución 2" })).toBeInTheDocument();
    expect(within(g).getByRole("button", { name: "En elaboración 1" })).toBeInTheDocument();
    expect(within(g).getByRole("button", { name: "Atrasada 1" })).toBeInTheDocument();
    expect(g.textContent).not.toMatch(/%/);
    // El centro: las obras de la lista, contadas.
    expect(within(g).getByRole("img", { name: "Obras: 4" })).toBeInTheDocument();
  });

  test("los estados van en el orden de la obra (elaboración, aprobación, aprobada, ejecución, atrasada), no en el de la lista", () => {
    montar();
    const nombres = within(porEstado())
      .getAllByRole("button")
      .map((b) => b.textContent);
    expect(nombres).toEqual(["En elaboración1", "En ejecución2", "Atrasada1"]);
  });

  test("cada estado tiene su color fijo, del gráfico y no verde ni rojo IBCS; «atrasada» lleva el de su ícono", () => {
    const { container } = montar();
    const color = (id: string) => container.querySelector<SVGCircleElement>(`.silice-donut__segmento[data-id="${id}"]`)!.style.stroke;
    expect(color("atrasada")).toBe("var(--silice-sev-error)");
    const usados = [color("en_elaboracion"), color("en_ejecucion")];
    for (const c of usados) expect(c).not.toMatch(/168a4c|22, 138, 76|b91c1c|185, 28, 28|e5b21a|229, 178, 26/i);
    // Con otra lista el mismo estado conserva su color.
    const antes = color("en_ejecucion");
    container.remove();
    const otra = montar({ ...CARTERA, obras: CARTERA.obras.filter((o) => o.etapa === "en_ejecucion") });
    expect(otra.container.querySelector<SVGCircleElement>('.silice-donut__segmento[data-id="en_ejecucion"]')!.style.stroke).toBe(antes);
  });

  test("no pide pasar el cursor: se recorre con el teclado y el foco lo resalta", async () => {
    const usuario = userEvent.setup();
    montar();
    const g = porEstado();
    expect(g.textContent).not.toMatch(/cursor/i);
    await usuario.click(within(g).getByRole("button", { name: "En elaboración 1" }));
    await usuario.keyboard("{ArrowDown}");
    expect(within(g).getByRole("button", { name: "En ejecución 2" })).toHaveFocus();
  });
});
