import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { alertaConTexto } from "../../test/ayudas";
import { catalogoDePrueba } from "../auditoria/datosDePrueba";
import PaginaHistorial from "./index";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["leer_proyecto"],
  modo_entrega: false,
};

const LISTA = [
  { id: 3, archivo: "presupuesto-c.xlsx", fecha: "2026-10-19T09:05:00", tipo: "libro", errores: 0, advertencias: 0 },
  { id: 2, archivo: "revision.pdf", fecha: "2026-10-18T14:32:07", tipo: "pdf", errores: 1, advertencias: 4 },
  { id: 1, archivo: "presupuesto-a.xlsx", fecha: "2026-10-17T08:00:00", tipo: "libro", errores: 0, advertencias: 2 },
];

const DETALLE_LIBRO = {
  ...LISTA[2],
  usuario: "Ana Pérez <ana>",
  sha256: "ab".repeat(32),
  fecha_libro: "2026-07-31",
  total_libro: "1234567.891000",
  total_silice: "1234500.5",
  informativos: 2,
  atipicos: 1,
  recortado: false,
  hallazgos: [
    { regla: "L4", hoja: "APU-02", celda: "G7", severidad: "ADVERTENCIA", mensaje: "El CD no cuadra con la suma." },
    { regla: "R2", hoja: "INSUMOS", celda: "E3", severidad: "INFO", mensaje: "Precio en bolívares." },
  ],
};

const DETALLE_PDF = {
  ...LISTA[1],
  usuario: "api (clave de API)",
  sha256: "cd".repeat(32),
  fecha_libro: null,
  total_libro: null,
  total_silice: null,
  informativos: 0,
  atipicos: 0,
  recortado: false,
  hallazgos: [],
};

function Ubicacion() {
  const { pathname } = useLocation();
  return <p data-testid="ubicacion">{pathname}</p>;
}

function dibujar(alExpirar = vi.fn()) {
  const valor: Aplicacion = { sesion: SESION, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar };
  render(
    <ContextoAplicacion.Provider value={valor}>
      <MemoryRouter>
        <PaginaHistorial />
        <Ubicacion />
      </MemoryRouter>
    </ContextoAplicacion.Provider>,
  );
  return alExpirar;
}

describe("Historial de auditorías", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let lista: () => Response;
  let detalle: (id: string) => Response;
  let queHacer: () => Response;

  beforeEach(() => {
    queHacer = () => json({ detalle: "no" }, 404);
    vi.stubGlobal("fetch", fetchFalso);
    lista = () => json(LISTA);
    detalle = (id) => json(id === "1" ? DETALLE_LIBRO : DETALLE_PDF);
    fetchFalso.mockImplementation(async (entrada) => {
      const ruta = typeof entrada === "string" ? entrada : entrada instanceof URL ? entrada.pathname : entrada.url;
      if (ruta === "/v1/auditorias-libro?limite=100") return lista();
      if (ruta === "/v1/libros/que-hacer") return queHacer();
      const m = /^\/v1\/auditorias-libro\/(\d+)$/.exec(ruta);
      if (m) return detalle(m[1]!);
      return json({ detalle: "no" }, 404);
    });
  });
  afterEach(() => {
    fetchFalso.mockReset();
    vi.unstubAllGlobals();
  });

  test("tiene un solo h1 desde el primer dibujo y pide las 100 más recientes", async () => {
    dibujar();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1, name: "Historial de auditorías" })).toBeInTheDocument();
    await screen.findByText("presupuesto-c.xlsx");
    expect(fetchFalso.mock.calls.map((c) => c[0])).toContain("/v1/auditorias-libro?limite=100");
  });

  test("lista cada auditoría con tipo, fecha es-VE y resultado en palabras", async () => {
    dibujar();
    const tabla = await screen.findByRole("table", { name: "Auditorías guardadas" });
    const filas = within(tabla).getAllByRole("row");
    expect(filas).toHaveLength(4); // cabecera y tres
    expect(within(filas[1]!).getByText("19/10/2026 09:05")).toBeInTheDocument();
    expect(within(filas[1]!).getByText("Libro")).toBeInTheDocument();
    expect(within(filas[1]!).getByText("Sin errores ni advertencias")).toBeInTheDocument();
    expect(within(filas[2]!).getByText("PDF")).toBeInTheDocument();
    expect(within(filas[2]!).getByText("1 error, 4 advertencias")).toBeInTheDocument();
    expect(screen.getByText("Mostrando 3 de 3 auditorías guardadas.")).toBeInTheDocument();
  });

  test("filtra por tipo y por resultado, y cuenta lo que muestra", async () => {
    const u = userEvent.setup();
    dibujar();
    await screen.findByText("presupuesto-c.xlsx");
    await u.selectOptions(screen.getByLabelText("Tipo"), "pdf");
    expect(screen.queryByText("presupuesto-c.xlsx")).not.toBeInTheDocument();
    expect(screen.getByText("revision.pdf")).toBeInTheDocument();
    expect(screen.getByText("Mostrando 1 de 3 auditorías guardadas.")).toBeInTheDocument();
    await u.selectOptions(screen.getByLabelText("Tipo"), "todos");
    await u.selectOptions(screen.getByLabelText("Resultado"), "solo_advertencias");
    expect(screen.getByText("presupuesto-a.xlsx")).toBeInTheDocument();
    expect(screen.queryByText("revision.pdf")).not.toBeInTheDocument();
  });

  test("los filtros de fecha son selectores de fecha (VB-19)", async () => {
    dibujar();
    await screen.findByText("presupuesto-c.xlsx");
    expect(screen.getByLabelText("Desde")).toHaveAttribute("type", "date");
    expect(screen.getByLabelText("Hasta")).toHaveAttribute("type", "date");
    expect(screen.queryByLabelText(/AAAA-MM-DD/)).toBeNull();
  });

  test("filtra por fechas y avisa de un rango invertido sin filtrar con él", async () => {
    const u = userEvent.setup();
    dibujar();
    await screen.findByText("presupuesto-c.xlsx");
    await u.type(screen.getByLabelText("Desde"), "2026-10-18");
    await u.type(screen.getByLabelText("Hasta"), "2026-10-18");
    expect(screen.getByText("revision.pdf")).toBeInTheDocument();
    expect(screen.queryByText("presupuesto-a.xlsx")).not.toBeInTheDocument();
    await u.clear(screen.getByLabelText("Hasta"));
    await u.type(screen.getByLabelText("Hasta"), "2026-10-01");
    expect(screen.getByText("La fecha «Desde» es posterior a «Hasta».")).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(4); // con un rango invertido no se filtra con él
  });

  test("sin coincidencias lo dice y ofrece quitar los filtros", async () => {
    const u = userEvent.setup();
    dibujar();
    await screen.findByText("presupuesto-c.xlsx");
    await u.type(screen.getByLabelText("Desde"), "2027-01-01");
    expect(screen.getByText("Ninguna auditoría coincide con esos filtros")).toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: "Quitar los filtros" }));
    expect(screen.getByText("presupuesto-c.xlsx")).toBeInTheDocument();
  });

  test("sin auditorías guardadas enseña cómo llenar el historial con botón principal", async () => {
    const u = userEvent.setup();
    lista = () => json([]);
    dibujar();
    expect(await screen.findByText("Todavía no hay auditorías guardadas")).toBeInTheDocument();
    const boton = screen.getByRole("button", { name: "Auditar un libro" });
    expect(boton).toHaveClass("cds--btn--primary");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    await u.click(boton);
    expect(screen.getByTestId("ubicacion")).toHaveTextContent("/auditoria/libros");
  });

  test("con auditorías guardadas ofrece el botón terciario «Auditar un libro» junto al h1", async () => {
    const u = userEvent.setup();
    dibujar();
    await screen.findByText("presupuesto-c.xlsx");
    const boton = screen.getByRole("button", { name: "Auditar un libro" });
    expect(boton).toHaveClass("cds--btn--tertiary");
    await u.click(boton);
    expect(screen.getByTestId("ubicacion")).toHaveTextContent("/auditoria/libros");
  });

  test("un error de la API se muestra con su detalle", async () => {
    lista = () => json({ detalle: "La base de la instalación no está disponible." }, 503);
    dibujar();
    const alerta = await alertaConTexto();
    expect(alerta).toHaveTextContent("No se pudo leer el historial");
    expect(alerta).toHaveTextContent("La base de la instalación no está disponible.");
  });

  test("sin permiso lo dice con el detalle de la API", async () => {
    lista = () => json({ detalle: "Su cuenta no tiene permiso para esta acción." }, 403);
    dibujar();
    expect(await alertaConTexto()).toHaveTextContent("Su cuenta no tiene permiso para esta acción.");
  });

  test("un 401 avisa de que la sesión venció", async () => {
    lista = () => json({ detalle: "Sesión ausente o vencida: entre de nuevo con su cuenta." }, 401);
    const alExpirar = dibujar();
    await alertaConTexto();
    expect(alExpirar).toHaveBeenCalled();
  });

  test("el detalle de un libro muestra resumen, totales es-VE con el exacto y hallazgos", async () => {
    const u = userEvent.setup();
    dibujar();
    await screen.findByText("presupuesto-a.xlsx");
    await u.click(screen.getByRole("button", { name: "Ver el detalle de presupuesto-a.xlsx" }));
    const panel = await screen.findByRole("region", { name: "Detalle de la auditoría" });
    expect(within(panel).getByRole("heading", { level: 2, name: "Detalle de la auditoría" })).toBeInTheDocument();
    const enlace = within(panel).getByRole("link", { name: "Ver la actividad de Ana Pérez" });
    expect(enlace).toHaveTextContent("Ana Pérez");
    expect(enlace).toHaveAttribute("href", "/cuenta/actividad?usuario=ana");
    expect(within(panel).getByText("Código de verificación del archivo (SHA-256)")).toBeInTheDocument();
    expect(within(panel).getByText("Sirve para comprobar que corresponde al mismo archivo original")).toBeInTheDocument();
    expect(within(panel).getByText("ab".repeat(32))).toBeInTheDocument();
    expect(within(panel).getByText("31/07/2026")).toBeInTheDocument();
    // VB-7: como el Libro, el total en centesimas y el exacto (en es-VE, sin redondear) en un Tooltip que se abre
    // con el teclado y es la descripcion accesible del valor
    const total = within(panel).getByRole("button", { name: "1.234.567,89" });
    expect(total).toHaveAccessibleDescription("Valor exacto: 1.234.567,891000");
    const silice = within(panel).getByRole("button", { name: "1.234.500,50" });
    expect(silice).toHaveAccessibleDescription("Valor exacto: 1.234.500,5");
    expect(within(panel).queryByText("1.234.567,891000", { selector: "button" })).toBeNull();
    const tabla = within(panel).getByRole("table", { name: "Hallazgos guardados" });
    expect(within(tabla).getByText("Qué revisó Sílice")).toBeInTheDocument();
    expect(within(tabla).getByText("El CD no cuadra con la suma.")).toBeInTheDocument();
    expect(within(tabla).getByText("APU-02")).toBeInTheDocument();
    expect(within(tabla).getByText("Advertencia")).toBeInTheDocument(); // la severidad con su nombre
  });

  test("los totales de la auditoria visual se leen en centesimas (VB-7)", async () => {
    detalle = () => json({ ...DETALLE_LIBRO, total_libro: "4876.56257", total_silice: "5055.521570000" });
    const u = userEvent.setup();
    dibujar();
    await screen.findByText("presupuesto-a.xlsx");
    await u.click(screen.getByRole("button", { name: "Ver el detalle de presupuesto-a.xlsx" }));
    const panel = await screen.findByRole("region", { name: "Detalle de la auditoría" });
    expect(within(panel).getByRole("button", { name: "4.876,56" })).toHaveAccessibleDescription(
      "Valor exacto: 4.876,56257",
    );
    expect(within(panel).getByRole("button", { name: "5.055,52" })).toHaveAccessibleDescription(
      "Valor exacto: 5.055,521570000",
    );
  });

  test("al abrir el detalle el foco pasa a su título", async () => {
    const u = userEvent.setup();
    dibujar();
    await screen.findByText("presupuesto-a.xlsx");
    await u.click(screen.getByRole("button", { name: "Ver el detalle de presupuesto-a.xlsx" }));
    await screen.findByRole("region", { name: "Detalle de la auditoría" });
    expect(screen.getByRole("heading", { level: 2, name: "Detalle de la auditoría" })).toHaveFocus();
  });

  test("el detalle de un PDF no inventa fecha ni totales y dice que no hay hallazgos", async () => {
    const u = userEvent.setup();
    dibujar();
    await screen.findByText("revision.pdf");
    await u.click(screen.getByRole("button", { name: "Ver el detalle de revision.pdf" }));
    const panel = await screen.findByRole("region", { name: "Detalle de la auditoría" });
    expect(await within(panel).findByText("api (clave de API)")).toBeInTheDocument();
    expect(within(panel).queryByRole("link")).toBeNull();
    expect(within(panel).queryByText("Fecha del libro")).not.toBeInTheDocument();
    expect(within(panel).queryByText("Total del libro")).not.toBeInTheDocument();
    expect(within(panel).getByText("Esta auditoría no dejó hallazgos guardados")).toBeInTheDocument();
  });

  test("si se recortaron los hallazgos lo dice con el número guardado", async () => {
    const guardados = Array.from({ length: 3 }, (_, i) => ({ ...DETALLE_LIBRO.hallazgos[0]!, celda: `G${i}` }));
    detalle = () => json({ ...DETALLE_LIBRO, recortado: true, errores: 600, hallazgos: guardados });
    const u = userEvent.setup();
    dibujar();
    await screen.findByText("presupuesto-a.xlsx");
    await u.click(screen.getByRole("button", { name: "Ver el detalle de presupuesto-a.xlsx" }));
    expect(await screen.findByText(/Solo se guardaron los primeros 3 hallazgos/)).toBeInTheDocument();
  });

  test("los conteos del detalle llevan punto de miles", async () => {
    detalle = () => json({ ...DETALLE_LIBRO, errores: 1234, advertencias: 5678, informativos: 9012, atipicos: 3456 });
    const u = userEvent.setup();
    dibujar();
    await screen.findByText("presupuesto-a.xlsx");
    await u.click(screen.getByRole("button", { name: "Ver el detalle de presupuesto-a.xlsx" }));
    const panel = await screen.findByRole("region", { name: "Detalle de la auditoría" });
    for (const [rotulo, valor] of [
      ["Errores", "1.234"],
      ["Advertencias", "5.678"],
      ["Informativos", "9.012"],
      ["Precios atípicos", "3.456"],
    ] as const) {
      expect((await within(panel).findByText(rotulo)).nextElementSibling).toHaveTextContent(valor);
    }
  });

  test("un detalle que ya no existe muestra el aviso de la API y se puede cerrar el panel", async () => {
    detalle = () => json({ detalle: "No hay una auditoría guardada con el número 1." }, 404);
    const u = userEvent.setup();
    dibujar();
    await screen.findByText("presupuesto-a.xlsx");
    await u.click(screen.getByRole("button", { name: "Ver el detalle de presupuesto-a.xlsx" }));
    const alerta = await alertaConTexto();
    expect(alerta).toHaveTextContent("No hay una auditoría guardada con el número 1.");
    await u.click(screen.getByRole("button", { name: "Cerrar el detalle" }));
    await waitFor(() =>
      expect(screen.queryByRole("region", { name: "Detalle de la auditoría" })).not.toBeInTheDocument(),
    );
  });

  test("el detalle muestra «Nombre (código)» si el hallazgo trae nombre_regla y solo el código si no", async () => {
    detalle = () =>
      json({
        ...DETALLE_LIBRO,
        hallazgos: [
          {
            regla: "L4",
            nombre_regla: "Costo directo incompleto",
            hoja: "APU-02",
            celda: "G7",
            severidad: "ADVERTENCIA",
            mensaje: "El CD no cuadra con la suma.",
          },
          { regla: "R2", hoja: "INSUMOS", celda: "E3", severidad: "INFO", mensaje: "Precio en bolívares." },
        ],
      });
    const u = userEvent.setup();
    dibujar();
    await screen.findByText("presupuesto-a.xlsx");
    await u.click(screen.getByRole("button", { name: "Ver el detalle de presupuesto-a.xlsx" }));
    const panel = await screen.findByRole("region", { name: "Detalle de la auditoría" });
    const tabla = within(panel).getByRole("table", { name: "Hallazgos guardados" });
    expect(within(tabla).getByText("Costo directo incompleto (L4)")).toBeInTheDocument();
    expect(within(tabla).getByText("R2")).toBeInTheDocument();
  });

  test("no ofrece descargar nada: el libro y el PDF no se guardan, y lo explica", async () => {
    dibujar();
    await screen.findByText("presupuesto-c.xlsx");
    expect(screen.queryByRole("button", { name: /descargar/i })).not.toBeInTheDocument();
    expect(screen.getByText(/El libro y el PDF no se guardan/)).toBeInTheDocument();
  });

  describe("«Qué hacer» en el detalle (B2)", () => {
    test("cada hallazgo guardado trae su «Qué hacer», cerrado, con la guía del servidor", async () => {
      queHacer = () => json(catalogoDePrueba());
      const u = userEvent.setup();
      dibujar();
      await screen.findByText("presupuesto-a.xlsx");
      await u.click(screen.getByRole("button", { name: "Ver el detalle de presupuesto-a.xlsx" }));
      const panel = await screen.findByRole("region", { name: "Detalle de la auditoría" });
      const tabla = within(panel).getByRole("table", { name: "Hallazgos guardados" });
      const boton = await within(tabla).findByRole("button", { name: "Qué hacer con «Componente fuera del total»" });
      expect(boton).toHaveAttribute("aria-expanded", "false");
      expect(within(tabla).queryByText("Corrija el rango de la suma.")).not.toBeInTheDocument();
      await u.click(boton);
      expect(within(tabla).getByText("Corrija el rango de la suma.")).toBeInTheDocument();
      expect(within(tabla).getByRole("button", { name: "Qué hacer con «Cierre de la curva de inversión»" })).toBeInTheDocument();
    });

    test("sin catálogo (el servidor no lo tiene) el detalle se ve igual, sin botones", async () => {
      const u = userEvent.setup();
      dibujar();
      await screen.findByText("presupuesto-a.xlsx");
      await u.click(screen.getByRole("button", { name: "Ver el detalle de presupuesto-a.xlsx" }));
      const panel = await screen.findByRole("region", { name: "Detalle de la auditoría" });
      expect(await within(panel).findByText("El CD no cuadra con la suma.")).toBeInTheDocument();
      expect(within(panel).queryByRole("button", { name: /Qué hacer/ })).not.toBeInTheDocument();
    });

    test("un detalle sin hallazgos no pide el catálogo en vano ni pinta botones", async () => {
      queHacer = () => json(catalogoDePrueba());
      const u = userEvent.setup();
      dibujar();
      await screen.findByText("revision.pdf");
      await u.click(screen.getByRole("button", { name: "Ver el detalle de revision.pdf" }));
      const panel = await screen.findByRole("region", { name: "Detalle de la auditoría" });
      expect(await within(panel).findByText("Esta auditoría no dejó hallazgos guardados")).toBeInTheDocument();
      expect(within(panel).queryByRole("button", { name: /Qué hacer/ })).not.toBeInTheDocument();
    });
  });
});

// C10b: filtro «Por persona» y enlaces a la actividad de quien auditó.
describe("Historial: filtro «Por persona» y enlaces a la actividad", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const CON_PERSONAS = [
    { id: 3, archivo: "presupuesto-c.xlsx", fecha: "2026-10-19T09:05:00", tipo: "libro", errores: 0, advertencias: 0, usuario: "Ana Pérez <ana>" },
    { id: 2, archivo: "revision.pdf", fecha: "2026-10-18T14:32:07", tipo: "pdf", errores: 1, advertencias: 4, usuario: "Luis Torres <luis>" },
    { id: 1, archivo: "presupuesto-a.xlsx", fecha: "2026-10-17T08:00:00", tipo: "libro", errores: 0, advertencias: 2, usuario: "api (clave de API)" },
  ];

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockImplementation(async (entrada) => {
      const ruta = typeof entrada === "string" ? entrada : entrada instanceof URL ? entrada.pathname : entrada.url;
      if (ruta === "/v1/auditorias-libro?limite=100") return json(CON_PERSONAS);
      return json({ detalle: "no" }, 404);
    });
  });

  afterEach(() => {
    fetchFalso.mockReset();
    vi.unstubAllGlobals();
  });

  test("filtra por persona, actualiza el contador y «Todas las personas» devuelve la lista", async () => {
    const u = userEvent.setup();
    dibujar();
    await screen.findByText("presupuesto-c.xlsx");
    const selector = screen.getByRole("combobox", { name: "Por persona" });
    expect(within(selector).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "Todas las personas",
      "Ana Pérez",
      "api (clave de API)",
      "Luis Torres",
    ]);
    expect(screen.getByText("Mostrando 3 de 3 auditorías guardadas.")).toBeInTheDocument();

    await u.selectOptions(selector, "Ana Pérez");
    expect(screen.getByText("presupuesto-c.xlsx")).toBeInTheDocument();
    expect(screen.queryByText("revision.pdf")).not.toBeInTheDocument();
    expect(screen.queryByText("presupuesto-a.xlsx")).not.toBeInTheDocument();
    expect(screen.getByText("Mostrando 1 de 3 auditorías guardadas.")).toBeInTheDocument();

    await u.selectOptions(selector, "Todas las personas");
    expect(screen.getByText("revision.pdf")).toBeInTheDocument();
    expect(screen.getByText("presupuesto-a.xlsx")).toBeInTheDocument();
    expect(screen.getByText("Mostrando 3 de 3 auditorías guardadas.")).toBeInTheDocument();
  });

  test("sin coincidencias al combinar filtros dice qué filtro está puesto y cómo quitarlo", async () => {
    const u = userEvent.setup();
    dibujar();
    await screen.findByText("presupuesto-c.xlsx");
    await u.selectOptions(screen.getByRole("combobox", { name: "Por persona" }), "Ana Pérez");
    await u.selectOptions(screen.getByRole("combobox", { name: "Tipo" }), "pdf");

    expect(screen.getByText("Ninguna auditoría coincide con esos filtros")).toBeInTheDocument();
    expect(screen.getByText(/Por persona: Ana Pérez/)).toBeInTheDocument();
    expect(screen.getByText(/Tipo: PDF/)).toBeInTheDocument();

    await u.click(screen.getByRole("button", { name: "Quitar los filtros" }));
    expect(screen.getByText("revision.pdf")).toBeInTheDocument();
    expect(screen.getByText("Mostrando 3 de 3 auditorías guardadas.")).toBeInTheDocument();
  });

  test("en la tabla, quien tiene usuario enlaza a su actividad y sin usuario queda como texto", async () => {
    dibujar();
    const tabla = await screen.findByRole("table", { name: "Auditorías guardadas" });
    const filas = within(tabla).getAllByRole("row");

    const enlaceAna = within(filas[1]!).getByRole("link", { name: "Ver la actividad de Ana Pérez" });
    expect(enlaceAna).toHaveTextContent("Ana Pérez");
    expect(enlaceAna).toHaveAttribute("href", "/cuenta/actividad?usuario=ana");

    const enlaceLuis = within(filas[2]!).getByRole("link", { name: "Ver la actividad de Luis Torres" });
    expect(enlaceLuis).toHaveTextContent("Luis Torres");
    expect(enlaceLuis).toHaveAttribute("href", "/cuenta/actividad?usuario=luis");

    expect(within(filas[3]!).getByText("api (clave de API)")).toBeInTheDocument();
    expect(within(filas[3]!).queryByRole("link")).toBeNull();
  });

});
