import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import oraculo from "../../../tests/fixtures/replica/libro_minimo.json";
import type { LibroAuditadoRespuesta, LibroVisualRespuesta } from "../api/tipos";
import { fijarCsrf } from "../api/cliente";
import { alertaConTexto } from "../test/ayudas";
import { clave, crearHojaFalsa } from "./hojaFalsa";
import { Visor } from "./Visor";

const replica = { ...oraculo, sha256: "a".repeat(64) } as unknown as LibroVisualRespuesta;

const auditoria: LibroAuditadoRespuesta = {
  libro: { nombre: "libro_minimo.xlsx", sha256: "a".repeat(64) },
  fecha_libro: "2026-10-18",
  fecha_devolucion: "2026-10-18",
  cumple: false,
  por_severidad: { CRITICO: 1, ERROR: 0, ADVERTENCIA: 1, INFO: 0 },
  totales_libro: { TOTALGEN: "1738.407" },
  totales_silice: { TOTALGEN: "1500.00" },
  hallazgos: [
    {
      codigo: "L3",
      severidad: "CRITICO",
      descripcion: "El total no coincide con la suma",
      celda: "PLAN DE PAGOS!F12",
      impacto: "238.407",
      accion: "Corregir",
    },
    {
      codigo: "L7",
      severidad: "ADVERTENCIA",
      descripcion: "Falta la fecha de la portada",
      celda: "",
      impacto: null,
      accion: "Completar",
    },
  ],
  indicadores: [
    {
      clave: "TOTALGEN",
      titulo: "Total general",
      actual: "1738.407",
      meta: "1500.00",
      delta: "238.407",
      delta_pct: "15.89",
      sentido: "costo",
    },
  ],
};

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const libroXlsx = () =>
  new File([new Uint8Array([80, 75, 3, 4])], "libro_minimo.xlsx", {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });

async function soltar(usuario: ReturnType<typeof userEvent.setup>, archivo = libroXlsx()) {
  const entrada = document.querySelector('input[type="file"]') as HTMLInputElement;
  await usuario.upload(entrada, archivo);
}

describe("Visor", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const hoja = crearHojaFalsa("PORTADA");
  const crearHoja = vi.fn(async () => hoja);

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("csrf-de-prueba");
    hoja.posiciones.clear();
    hoja.posiciones.set(clave({ hoja: "PLAN DE PAGOS", fila0: 11, columna0: 5 }), { x: 300, y: 120, ancho: 80, alto: 20 });
    hoja.fijarHoja("PORTADA");
    crearHoja.mockClear();
    hoja.irA.mockClear();
    hoja.destruir.mockClear();
    fetchFalso.mockImplementation(async (entrada) => {
      const ruta = String(entrada);
      if (ruta.endsWith("/v1/libros/replica")) return json(replica);
      if (ruta.endsWith("/v1/libros/auditoria")) return json(auditoria);
      return json({ detalle: "ruta inesperada" }, 404);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  test("al principio invita a soltar el libro .xlsx y no muestra la hoja", () => {
    render(<Visor crearHoja={crearHoja} />);
    expect(screen.getByRole("button", { name: /Suelte aquí el libro \.xlsx de la empresa/ })).toBeInTheDocument();
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("la fecha de devolucion empieza en hoy y se puede editar", async () => {
    vi.useFakeTimers({ toFake: ["Date"], now: new Date(2026, 9, 18, 9, 30) });
    render(<Visor crearHoja={crearHoja} />);
    const campo = screen.getByLabelText("Fecha de devolución") as HTMLInputElement;
    expect(campo.value).toBe("2026-10-18");
    vi.useRealTimers();
    const usuario = userEvent.setup();
    await usuario.clear(campo);
    await usuario.type(campo, "2026-11-02");
    expect(campo.value).toBe("2026-11-02");
  });

  test("al soltar el libro llama a replica y a auditoria en paralelo con el libro y la fecha", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockImplementation(() => new Promise<Response>(() => {}));
    render(<Visor crearHoja={crearHoja} />);
    const campo = screen.getByLabelText("Fecha de devolución");
    await usuario.clear(campo);
    await usuario.type(campo, "2026-11-02");
    await soltar(usuario);

    // Las dos llamadas salen antes de que alguna conteste.
    await waitFor(() => expect(fetchFalso).toHaveBeenCalledTimes(2));
    const rutas = fetchFalso.mock.calls.map((c) => String(c[0])).sort();
    expect(rutas).toEqual(["/v1/libros/auditoria", "/v1/libros/replica"]);
    for (const [, init] of fetchFalso.mock.calls) {
      expect(init?.method).toBe("POST");
      expect(new Headers(init?.headers).get("X-Silice-CSRF")).toBe("csrf-de-prueba");
      const cuerpo = init?.body as FormData;
      expect((cuerpo.get("libro") as File).name).toBe("libro_minimo.xlsx");
    }
    const auditar = fetchFalso.mock.calls.find((c) => String(c[0]).endsWith("auditoria"));
    expect((auditar?.[1]?.body as FormData).get("fecha_devolucion")).toBe("2026-11-02");
  });

  test("mientras carga muestra esqueletos y avisa que esta ocupado", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockImplementation(() => new Promise<Response>(() => {}));
    render(<Visor crearHoja={crearHoja} />);
    await soltar(usuario);
    const zona = await screen.findByRole("status", { name: /Cargando el libro/ });
    expect(zona).toHaveAttribute("aria-busy", "true");
    expect(document.querySelector("[class*=\"cds--skeleton\"]")).not.toBeNull();
  });

  test("con la respuesta muestra los indicadores, los conteos y la lista de hallazgos", async () => {
    const usuario = userEvent.setup();
    render(<Visor crearHoja={crearHoja} />);
    await soltar(usuario);
    const franja = await screen.findByRole("region", { name: "Indicadores del libro" });
    expect(within(franja).getByText("1738.407")).toBeInTheDocument();
    expect(within(franja).getByRole("group", { name: "Hallazgos por severidad" })).toBeInTheDocument();
    expect(screen.getByText("El total no coincide con la suma")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /Sin celda en el libro/ })).toBeInTheDocument();
    expect(crearHoja).toHaveBeenCalledTimes(1);
  });

  test("las hojas visibles tienen su pestana y la oculta no", async () => {
    const usuario = userEvent.setup();
    render(<Visor crearHoja={crearHoja} />);
    await soltar(usuario);
    await screen.findByRole("tablist", { name: "Hojas del libro" });
    expect(screen.getByRole("tab", { name: "PORTADA" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "PLAN DE PAGOS" })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "AUX" })).not.toBeInTheDocument();
  });

  test("un hallazgo en una hoja oculta va al grupo sin celda", async () => {
    const usuario = userEvent.setup();
    const conOculta = {
      ...auditoria,
      hallazgos: [{ ...auditoria.hallazgos[0], descripcion: "Error en la hoja auxiliar", celda: "AUX!A1" }],
    };
    fetchFalso.mockImplementation(async (entrada) =>
      String(entrada).endsWith("/replica") ? json(replica) : json(conOculta),
    );
    render(<Visor crearHoja={crearHoja} />);
    await soltar(usuario);
    const grupo = await screen.findByRole("region", { name: /Sin celda en el libro/ });
    expect(within(grupo).getByText("Error en la hoja auxiliar")).toBeInTheDocument();
  });

  test("elegir una pestana cambia de hoja", async () => {
    const usuario = userEvent.setup();
    render(<Visor crearHoja={crearHoja} />);
    await soltar(usuario);
    await usuario.click(await screen.findByRole("tab", { name: "PLAN DE PAGOS" }));
    expect(hoja.irAHoja).toHaveBeenCalledWith("PLAN DE PAGOS");
  });

  test("clic en un hallazgo lleva la hoja a su celda", async () => {
    const usuario = userEvent.setup();
    render(<Visor crearHoja={crearHoja} />);
    await soltar(usuario);
    await usuario.click(await screen.findByText("El total no coincide con la suma"));
    expect(hoja.irA).toHaveBeenCalledWith({ hoja: "PLAN DE PAGOS", fila0: 11, columna0: 5 });
  });

  test("clic en una celda marcada resalta la fila de la lista y le da el foco", async () => {
    const usuario = userEvent.setup();
    render(<Visor crearHoja={crearHoja} />);
    await soltar(usuario);
    await screen.findByText("El total no coincide con la suma");
    act(() => hoja.seleccionar({ hoja: "PLAN DE PAGOS", fila0: 11, columna0: 5 }));
    const fila = screen.getByText("El total no coincide con la suma").closest("tr");
    expect(fila).toHaveAttribute("aria-current", "true");
    expect(fila).toHaveFocus();
  });

  test("clic en una celda sin hallazgo no cambia la seleccion de la lista", async () => {
    const usuario = userEvent.setup();
    render(<Visor crearHoja={crearHoja} />);
    await soltar(usuario);
    await screen.findByText("El total no coincide con la suma");
    act(() => hoja.seleccionar({ hoja: "PORTADA", fila0: 0, columna0: 0 }));
    expect(screen.getByText("El total no coincide con la suma").closest("tr")).not.toHaveAttribute("aria-current");
  });

  test("pinta el halo del hallazgo sobre su celda cuando esa hoja esta a la vista", async () => {
    const usuario = userEvent.setup();
    render(<Visor crearHoja={crearHoja} />);
    await soltar(usuario);
    await screen.findByText("El total no coincide con la suma");
    expect(screen.queryByRole("img", { name: /PLAN DE PAGOS!F12/ })).not.toBeInTheDocument();
    hoja.fijarHoja("PLAN DE PAGOS");
    act(() => hoja.cambiar());
    expect(screen.getByRole("img", { name: /Crítico.*PLAN DE PAGOS!F12/ })).toBeInTheDocument();
  });

  test("un error de la API se muestra con su detalle tal cual", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockImplementation(async (entrada) => {
      if (String(entrada).endsWith("/replica")) return json(replica);
      return json({ detalle: "El archivo no es un libro de Excel válido." }, 422);
    });
    render(<Visor crearHoja={crearHoja} />);
    await soltar(usuario);
    expect(await alertaConTexto()).toHaveTextContent("El archivo no es un libro de Excel válido.");
    expect(screen.getByRole("button", { name: /Suelte aquí el libro \.xlsx de la empresa/ })).toBeInTheDocument();
  });

  test("un archivo que no es .xlsx ni se envia", async () => {
    const usuario = userEvent.setup({ applyAccept: false });
    render(<Visor crearHoja={crearHoja} />);
    await soltar(usuario, new File(["x"], "notas.txt", { type: "text/plain" }));
    expect(await alertaConTexto()).toHaveTextContent(/\.xlsx/);
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("cambiar la fecha con un libro cargado vuelve a auditar sin pedir otra vez la replica", async () => {
    const usuario = userEvent.setup();
    render(<Visor crearHoja={crearHoja} />);
    await soltar(usuario);
    await screen.findByText("El total no coincide con la suma");
    fetchFalso.mockClear();
    const campo = screen.getByLabelText("Fecha de devolución");
    await usuario.clear(campo);
    await usuario.type(campo, "2026-12-01");
    await waitFor(() => expect(fetchFalso).toHaveBeenCalled());
    const rutas = fetchFalso.mock.calls.map((c) => String(c[0]));
    expect(rutas.every((r) => r.endsWith("/auditoria"))).toBe(true);
    const ultima = fetchFalso.mock.calls[fetchFalso.mock.calls.length - 1];
    expect((ultima[1]?.body as FormData).get("fecha_devolucion")).toBe("2026-12-01");
  });

  test("una API sin el campo indicadores no rompe la franja", async () => {
    const usuario = userEvent.setup();
    const sin = { ...auditoria, indicadores: undefined };
    fetchFalso.mockImplementation(async (entrada) =>
      String(entrada).endsWith("/replica") ? json(replica) : json(sin),
    );
    render(<Visor crearHoja={crearHoja} />);
    await soltar(usuario);
    expect(await screen.findByRole("region", { name: "Indicadores del libro" })).toBeInTheDocument();
  });

  test("mientras Univer prepara la hoja, el lienzo muestra un esqueleto", async () => {
    const usuario = userEvent.setup();
    const lenta = vi.fn(() => new Promise<never>(() => {}));
    render(<Visor crearHoja={lenta} />);
    await soltar(usuario);
    await screen.findByText("El total no coincide con la suma");
    expect(document.querySelector(".visor__lienzo .visor__esqueleto-sobre")).not.toBeNull();
  });

  test("si la hoja no se puede dibujar lo dice en la alerta", async () => {
    const usuario = userEvent.setup();
    const rota = vi.fn(() => Promise.reject(new Error("sin canvas")));
    render(<Visor crearHoja={rota} />);
    await soltar(usuario);
    expect(await alertaConTexto()).toHaveTextContent(/no se pudo dibujar la hoja/i);
  });

  test("un 401 de la API avisa que la sesion vencio", async () => {
    const usuario = userEvent.setup();
    const alExpirar = vi.fn();
    fetchFalso.mockImplementation(async () => json({ detalle: "Sesión vencida." }, 401));
    render(<Visor crearHoja={crearHoja} alExpirar={alExpirar} />);
    await soltar(usuario);
    await alertaConTexto();
    expect(alExpirar).toHaveBeenCalled();
  });

  test("al desmontarse destruye el visor de la hoja", async () => {
    const usuario = userEvent.setup();
    const vista = render(<Visor crearHoja={crearHoja} />);
    await soltar(usuario);
    await screen.findByText("El total no coincide con la suma");
    vista.unmount();
    expect(hoja.destruir).toHaveBeenCalled();
  });
});
