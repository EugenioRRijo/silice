import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import Actividad from "./Actividad";
import type { ActividadRespuesta } from "./logica";

// Datos construidos (nunca reales). Octubre de 2026: el 19 (lunes) hubo dos acciones y el 20 una; el 1 es jueves.

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Demo",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja"],
  modo_entrega: false,
};

const ACTIVIDAD: ActividadRespuesta = {
  usuario: "ana",
  desde: "2026-10-01",
  hasta: "2026-10-31",
  dias: [
    { fecha: "2026-10-19", cuantos: 2 },
    { fecha: "2026-10-20", cuantos: 1 },
  ],
  cifras: { versiones_guardadas: 1, versiones_enviadas: 1, dictamenes: 0, auditorias: 1 },
  eventos: [
    { fecha: "2026-10-20T15:00:00", tipo: "auditoria", obra: "", archivo: "Presupuesto cliente A.xlsx", texto: "auditó Presupuesto cliente A.xlsx: 3 errores" },
    { fecha: "2026-10-19T10:00:00", tipo: "version_enviada", obra: "Vivienda Demo", archivo: "", texto: "envió la versión V1 de Vivienda Demo a aprobación" },
    { fecha: "2026-10-19T09:00:00", tipo: "version_guardada", obra: "Vivienda Demo", archivo: "", texto: "guardó la versión V1 de Vivienda Demo" },
  ],
  recortado: false,
};

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const fetchFalso = vi.fn<typeof fetch>();

function montar(usuario = "ana") {
  const valor: Aplicacion = { sesion: SESION, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() };
  return render(
    <ContextoAplicacion.Provider value={valor}>
      <Actividad usuario={usuario} />
    </ContextoAplicacion.Provider>,
  );
}

const calendario = () => screen.findByRole("group", { name: /Calendario de actividad/ });
const celda = async (nombre: string) => within(await calendario()).getByRole("button", { name: nombre });
const detalle = () => screen.getByRole("status");

beforeEach(() => {
  vi.stubGlobal("fetch", fetchFalso);
  fetchFalso.mockReset();
  fijarCsrf("tok");
  fetchFalso.mockImplementation(async () => json(ACTIVIDAD));
});
afterEach(() => {
  cleanup();
  fijarCsrf(null);
  vi.unstubAllGlobals();
});

describe("Actividad: lo que llega y lo que se pide", () => {
  test("pide la actividad de la cuenta, con su usuario codificado", async () => {
    montar("ana.perez");
    await calendario();
    expect(String(fetchFalso.mock.calls[0]?.[0])).toBe("/v1/actividad?usuario=ana.perez");
  });

  test("mientras carga dice que carga", () => {
    fetchFalso.mockImplementation(() => new Promise(() => undefined));
    montar();
    expect(screen.getByRole("status", { name: "Cargando la actividad" })).toBeInTheDocument();
  });

  test("las cifras del período salen con su nombre, en el orden de siempre", async () => {
    montar();
    await calendario();
    expect(screen.getByRole("heading", { level: 2, name: "Resumen del período" })).toBeInTheDocument();
    expect(screen.getByText("Del 01/10/2026 al 31/10/2026.")).toBeInTheDocument();
    const cifras = screen.getAllByRole("term").map((t) => [t.textContent, t.nextElementSibling?.textContent]);
    expect(cifras).toEqual([
      ["Versiones guardadas", "1"],
      ["Versiones enviadas", "1"],
      ["Dictámenes", "0"],
      ["Auditorías", "1"],
    ]);
  });

  test("quien no puede ver esa cuenta lee el motivo de la API, sin calendario", async () => {
    fetchFalso.mockImplementation(async () =>
      json({ detalle: "Solo puede ver su propia actividad, o la de todos si administra las cuentas." }, 403),
    );
    montar("rita");
    expect(await screen.findByRole("alert")).toHaveTextContent("Solo puede ver su propia actividad, o la de todos si administra las cuentas.");
    expect(screen.queryByRole("group", { name: /Calendario de actividad/ })).toBeNull();
  });

  test("una cuenta que no existe también dice el motivo", async () => {
    fetchFalso.mockImplementation(async () => json({ detalle: "No hay una cuenta con ese usuario." }, 404));
    montar("nadie");
    expect(await screen.findByRole("alert")).toHaveTextContent("No hay una cuenta con ese usuario.");
  });
});

describe("Actividad: el calendario", () => {
  test("un cuadro por día del período, cada uno con su fecha y cuántas acciones", async () => {
    montar();
    const dias = within(await calendario()).getAllByRole("button");
    expect(dias).toHaveLength(31);
    expect(dias[0]).toHaveAccessibleName("01/10/2026: sin actividad");
    expect(await celda("19/10/2026: 2 acciones")).toBeInTheDocument();
    expect(await celda("20/10/2026: 1 acción")).toBeInTheDocument();
    expect(dias[30]).toHaveAccessibleName("31/10/2026: sin actividad");
  });

  test("los niveles van de 0 (sin actividad) a 4 en una sola escala: más acciones, nivel más alto", async () => {
    montar();
    // Con dos días de 2 y 1 acciones los cortes son 1, 1 y 2: el de 2 es nivel 3, el de 1 es nivel 1 y el resto, 0.
    expect((await celda("19/10/2026: 2 acciones")).getAttribute("data-nivel")).toBe("3");
    expect((await celda("20/10/2026: 1 acción")).getAttribute("data-nivel")).toBe("1");
    expect((await celda("21/10/2026: sin actividad")).getAttribute("data-nivel")).toBe("0");
  });

  test("la leyenda va de «Menos» a «Más» con los cinco niveles", async () => {
    montar();
    await calendario();
    const leyenda = screen.getByText("Menos").parentElement!;
    expect(leyenda).toHaveTextContent("Menos");
    expect(leyenda).toHaveTextContent("Más");
    expect([...leyenda.querySelectorAll("[data-nivel]")].map((e) => e.getAttribute("data-nivel"))).toEqual(["0", "1", "2", "3", "4"]);
  });

  test("antes de elegir un día, el detalle da la pista", async () => {
    montar();
    await calendario();
    expect(detalle()).toHaveTextContent("Pase el cursor por un día, o muévase con las flechas, para ver lo que se hizo.");
  });

  test("al pasar el cursor por un día, el detalle dice la fecha y lo que se hizo", async () => {
    const u = userEvent.setup();
    montar();
    await u.hover(await celda("19/10/2026: 2 acciones"));
    expect(detalle()).toHaveTextContent("19/10/2026: 2 acciones");
    expect(within(detalle()).getAllByRole("listitem").map((i) => i.textContent)).toEqual([
      "Envió la versión V1 de Vivienda Demo a aprobación",
      "Guardó la versión V1 de Vivienda Demo",
    ]);
  });

  test("un día sin actividad lo dice y no lista nada", async () => {
    const u = userEvent.setup();
    montar();
    await u.hover(await celda("21/10/2026: sin actividad"));
    expect(detalle()).toHaveTextContent("21/10/2026: sin actividad");
    expect(within(detalle()).queryAllByRole("listitem")).toHaveLength(0);
  });

  test("al enfocar un día con el teclado también se ve el detalle, y las flechas se mueven por el calendario", async () => {
    const u = userEvent.setup();
    montar();
    // Tab entra al último día con actividad (el 20) y no a los treinta y uno.
    await calendario();
    await u.tab();
    expect(document.activeElement).toHaveAccessibleName("20/10/2026: 1 acción");
    expect(detalle()).toHaveTextContent("20/10/2026: 1 acción");
    await u.keyboard("{ArrowLeft}"); // una semana atrás: el 13
    expect(document.activeElement).toHaveAccessibleName("13/10/2026: sin actividad");
    await u.keyboard("{ArrowDown}"); // un día adelante: el 14
    expect(document.activeElement).toHaveAccessibleName("14/10/2026: sin actividad");
    expect(detalle()).toHaveTextContent("14/10/2026: sin actividad");
  });

  test("Tab sale del calendario después de un solo día", async () => {
    const u = userEvent.setup();
    montar();
    await calendario();
    await u.tab();
    await u.tab();
    expect(document.activeElement).toHaveAccessibleName("Ver como tabla");
  });
});

describe("Actividad: ver como tabla", () => {
  test("el botón dice si está activo y muestra los días con actividad como tabla", async () => {
    const u = userEvent.setup();
    montar();
    await calendario();
    const boton = screen.getByRole("button", { name: "Ver como tabla" });
    expect(boton).toHaveAttribute("aria-pressed", "false");
    expect(screen.queryByRole("table", { name: "Actividad por día" })).toBeNull();
    await u.click(boton);
    expect(boton).toHaveAttribute("aria-pressed", "true");
    const tabla = screen.getByRole("table", { name: "Actividad por día" });
    const filas = within(tabla).getAllByRole("row").slice(1);
    expect(filas.map((f) => within(f).getAllByRole("cell").map((c) => c.textContent))).toEqual([
      ["19/10/2026", "2"],
      ["20/10/2026", "1"],
    ]);
    await u.click(boton);
    expect(screen.queryByRole("table", { name: "Actividad por día" })).toBeNull();
  });
});

describe("Actividad: actividad reciente", () => {
  const items = () => within(screen.getByRole("region", { name: "Actividad reciente" })).getAllByRole("listitem").map((i) => i.textContent);

  test("lista lo más reciente primero, con fecha dd/mm/aaaa y hora", async () => {
    montar();
    await calendario();
    expect(items()).toEqual([
      "20/10/2026 15:00Auditó Presupuesto cliente A.xlsx: 3 errores",
      "19/10/2026 10:00Envió la versión V1 de Vivienda Demo a aprobación",
      "19/10/2026 09:00Guardó la versión V1 de Vivienda Demo",
    ]);
  });

  test("los filtros por tipo dicen cuál está activo y dejan solo ese tipo", async () => {
    const u = userEvent.setup();
    montar();
    await calendario();
    const filtros = screen.getByRole("group", { name: "Filtrar por tipo de acción" });
    const todo = within(filtros).getByRole("button", { name: "Todo" });
    const auditorias = within(filtros).getByRole("button", { name: "Auditorías" });
    expect(todo).toHaveAttribute("aria-pressed", "true");
    expect(auditorias).toHaveAttribute("aria-pressed", "false");
    await u.click(auditorias);
    expect(auditorias).toHaveAttribute("aria-pressed", "true");
    expect(todo).toHaveAttribute("aria-pressed", "false");
    expect(items()).toEqual(["20/10/2026 15:00Auditó Presupuesto cliente A.xlsx: 3 errores"]);
    await u.click(within(filtros).getByRole("button", { name: "Versiones guardadas" }));
    expect(items()).toEqual(["19/10/2026 09:00Guardó la versión V1 de Vivienda Demo"]);
    await u.click(todo);
    expect(items()).toHaveLength(3);
  });

  test("un tipo sin acciones dice que no hay", async () => {
    const u = userEvent.setup();
    montar();
    await calendario();
    await u.click(within(screen.getByRole("group", { name: "Filtrar por tipo de acción" })).getByRole("button", { name: "Dictámenes" }));
    expect(screen.getByText("No hay acciones de este tipo en el período.")).toBeInTheDocument();
  });

  test("sin ninguna actividad: cifras en cero, calendario vacío y un mensaje que lo dice", async () => {
    fetchFalso.mockImplementation(async () =>
      json({ ...ACTIVIDAD, dias: [], eventos: [], cifras: { versiones_guardadas: 0, versiones_enviadas: 0, dictamenes: 0, auditorias: 0 } }),
    );
    montar();
    await calendario();
    expect(screen.getByText("En este período no hay nada que mostrar.")).toBeInTheDocument();
    const dias = within(await calendario()).getAllByRole("button");
    expect(dias.every((d) => d.getAttribute("data-nivel") === "0")).toBe(true);
    // Con calendario vacío, Tab entra en el último día del período.
    await userEvent.setup().tab();
    expect(document.activeElement).toHaveAccessibleName("31/10/2026: sin actividad");
  });

  test("si hubo más acciones que las devueltas, lo avisa y dice que las cifras cuentan todas", async () => {
    fetchFalso.mockImplementation(async () => json({ ...ACTIVIDAD, recortado: true }));
    montar();
    await calendario();
    expect(screen.getByText("Se muestran las 3 acciones más recientes; las cifras de arriba cuentan todas.")).toBeInTheDocument();
  });

  test("sin recorte no pone ese aviso", async () => {
    montar();
    await calendario();
    expect(screen.queryByText(/Se muestran las/)).toBeNull();
  });
});

// T3 (2026-11-28): el calendario de un año salía cortado en la última columna. Ahora las celdas se ajustan al ancho de su
// caja (container query en actividad.scss) y para eso la caja necesita saber cuántas columnas hay; si aun así no caben
// (ventana muy angosta), se abre en la semana más reciente y no en la más antigua.
describe("Actividad: el calendario cabe en su caja", () => {
  test("la caja del calendario declara cuántas columnas (semanas) tiene", async () => {
    montar();
    const caja = (await calendario()).parentElement as HTMLElement;
    // Del 1/10/2026 (jueves) al 31/10/2026 (sábado): cinco semanas, de lunes a lunes.
    expect(caja.style.getPropertyValue("--silice-actividad-columnas")).toBe("5");
  });

  test("al abrir, la caja se desplaza hasta el final (lo más reciente a la vista)", async () => {
    // jsdom no desplaza nada: se espera lo que el componente ASIGNA a scrollLeft.
    const asignados: number[] = [];
    const ancho = vi.spyOn(HTMLElement.prototype, "scrollWidth", "get").mockReturnValue(900);
    const izquierda = vi.spyOn(Element.prototype, "scrollLeft", "set").mockImplementation((v: number) => {
      asignados.push(v);
    });
    try {
      montar();
      await calendario();
      expect(asignados).toContain(900);
    } finally {
      ancho.mockRestore();
      izquierda.mockRestore();
    }
  });
});
