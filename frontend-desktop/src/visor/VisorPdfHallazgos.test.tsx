import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import oraculo from "../../../tests/fixtures/replica/libro_minimo.json";
import type { LibroAuditadoRespuesta, LibroVisualRespuesta } from "../api/tipos";
import { fijarCsrf } from "../api/cliente";
import { alertaConTexto } from "../test/ayudas";
import { crearHojaFalsa } from "./hojaFalsa";
import { Visor } from "./Visor";

// Decision P2 (2026-11-19): «Descargar PDF de hallazgos» en el resultado de la auditoria de un libro. El servidor
// dibuja el PDF (POST /v1/libros/auditoria/pdf con el mismo libro y la misma fecha de devolucion que la pantalla); la
// interfaz solo lo pide y lo guarda.
const replica = { ...oraculo, sha256: "a".repeat(64) } as unknown as LibroVisualRespuesta;

const auditoria: LibroAuditadoRespuesta = {
  libro: { nombre: "libro_minimo.xlsx", sha256: "a".repeat(64) },
  fecha_libro: "2026-10-18",
  fecha_devolucion: "2026-10-13",
  cumple: false,
  por_severidad: { CRITICO: 0, ERROR: 1, ADVERTENCIA: 0, INFO: 0 },
  totales_libro: { TOTALGEN: "4876.56257" },
  totales_silice: { TOTALGEN: "5055.52157" },
  hallazgos: [
    {
      codigo: "L4",
      severidad: "ERROR",
      descripcion: "El costo directo omite equipos",
      celda: "PLAN DE PAGOS!F12",
      impacto: "154.28",
      accion: "corregido",
    },
  ],
  indicadores: [],
};

const json = (cuerpo: unknown, estado = 200) =>
  new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });

const BOTON = { name: "Descargar PDF de hallazgos" };

describe("Visor: Descargar PDF de hallazgos", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const crearHoja = vi.fn(async () => crearHojaFalsa("PORTADA"));
  const crearUrl = vi.fn(() => "blob:falso");
  const revocarUrl = vi.fn();
  let clics: { descarga: string }[];

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("csrf-de-prueba");
    clics = [];
    Object.defineProperty(URL, "createObjectURL", { value: crearUrl, configurable: true });
    Object.defineProperty(URL, "revokeObjectURL", { value: revocarUrl, configurable: true });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      clics.push({ descarga: this.download });
    });
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  async function abrir(alExpirar?: () => void) {
    render(<Visor crearHoja={crearHoja} alExpirar={alExpirar} />);
    const usuario = userEvent.setup();
    const entrada = document.querySelector('input[type="file"]') as HTMLInputElement;
    await usuario.upload(entrada, new File([new Uint8Array([80, 75, 3, 4])], "libro_minimo.xlsx"));
    await screen.findByRole("region", { name: "Hoja del libro" });
    return usuario;
  }

  const responderAuditoria = () =>
    fetchFalso.mockImplementation(async (entrada) => {
      const ruta = String(entrada);
      if (ruta.endsWith("/v1/libros/replica")) return json(replica);
      if (ruta.endsWith("/v1/libros/auditoria")) return json(auditoria);
      return json({ detalle: "ruta inesperada" }, 404);
    });

  test("sin resultado no hay boton", () => {
    render(<Visor crearHoja={crearHoja} />);
    expect(screen.queryByRole("button", BOTON)).toBeNull();
  });

  test("con el resultado en pantalla aparece el boton", async () => {
    responderAuditoria();
    await abrir();
    expect(screen.getByRole("button", BOTON)).toBeEnabled();
  });

  test("al pulsarlo pide el PDF a la ruta del servidor con el libro y la fecha del resultado y lo guarda", async () => {
    responderAuditoria();
    const usuario = await abrir();
    fetchFalso.mockClear();
    fetchFalso.mockResolvedValue(
      new Response("%PDF-1.4", {
        status: 200,
        headers: { "Content-Disposition": 'attachment; filename="hallazgos_libro_minimo.pdf"' },
      }),
    );
    // Se esta tecleando otra fecha (incompleta, asi que aun no se vuelve a auditar): el PDF lleva la del resultado.
    const campo = screen.getByLabelText("Fecha de devolución");
    await usuario.clear(campo);
    await usuario.type(campo, "2026-1");
    await usuario.click(screen.getByRole("button", BOTON));
    await vi.waitFor(() => expect(clics).toHaveLength(1));
    expect(clics[0].descarga).toBe("hallazgos_libro_minimo.pdf");
    expect(crearUrl).toHaveBeenCalledOnce();
    expect(revocarUrl).toHaveBeenCalledWith("blob:falso");
    expect(fetchFalso).toHaveBeenCalledTimes(1);
    const [ruta, init] = fetchFalso.mock.calls[0];
    expect(String(ruta)).toBe("/v1/libros/auditoria/pdf");
    expect(init?.method).toBe("POST");
    expect(new Headers(init?.headers).get("X-Silice-CSRF")).toBe("csrf-de-prueba");
    const cuerpo = init?.body as FormData;
    expect((cuerpo.get("libro") as File).name).toBe("libro_minimo.xlsx");
    // La fecha con la que se audito lo que se ve, no la que se este tecleando.
    expect(cuerpo.get("fecha_devolucion")).toBe("2026-10-13");
  });

  test("mientras baja lo dice y se deshabilita", async () => {
    responderAuditoria();
    const usuario = await abrir();
    let resolver: (r: Response) => void = () => {};
    fetchFalso.mockImplementation(() => new Promise<Response>((fin) => (resolver = fin)));
    await usuario.click(screen.getByRole("button", BOTON));
    expect(await screen.findByRole("button", { name: "Descargando…" })).toBeDisabled();
    resolver(new Response("%PDF-1.4", { status: 200 }));
    expect(await screen.findByRole("button", BOTON)).toBeEnabled();
    expect(clics).toHaveLength(1);
  });

  test("el error de un libro anterior no queda cuando el resultado cambia", async () => {
    fetchFalso.mockImplementation(async (entrada, init) => {
      const ruta = String(entrada);
      if (ruta.endsWith("/v1/libros/replica")) return json(replica);
      if (ruta.endsWith("/v1/libros/auditoria")) {
        const fecha = (init?.body as FormData).get("fecha_devolucion") as string;
        return json({ ...auditoria, fecha_devolucion: fecha });
      }
      return json({ detalle: "No se pudo preparar el PDF de hallazgos." }, 500);
    });
    render(<Visor crearHoja={crearHoja} />);
    const usuario = userEvent.setup();
    const entrada = document.querySelector('input[type="file"]') as HTMLInputElement;
    await usuario.upload(entrada, new File([new Uint8Array([80, 75, 3, 4])], "libro_minimo.xlsx"));
    await screen.findByRole("region", { name: "Hoja del libro" });
    await usuario.click(screen.getByRole("button", BOTON));
    expect(await alertaConTexto()).toHaveTextContent("No se pudo preparar");
    // Otra fecha valida: se audita de nuevo y el resultado es otro; el aviso de antes ya no corresponde.
    const campo = screen.getByLabelText("Fecha de devolución");
    await usuario.clear(campo);
    await usuario.type(campo, "2026-11-02");
    await vi.waitFor(() => expect(screen.queryByText(/No se pudo preparar el PDF/)).toBeNull());
    expect(screen.getByRole("button", BOTON)).toBeEnabled();
  });

  test("si el servidor falla anuncia el detalle y no baja nada", async () => {
    responderAuditoria();
    const usuario = await abrir();
    fetchFalso.mockResolvedValue(json({ detalle: "No se pudo preparar el PDF de hallazgos." }, 500));
    await usuario.click(screen.getByRole("button", BOTON));
    expect(await alertaConTexto()).toHaveTextContent("No se pudo preparar el PDF de hallazgos.");
    expect(clics).toHaveLength(0);
  });

  test("un 401 avisa que la sesion vencio", async () => {
    responderAuditoria();
    const alExpirar = vi.fn();
    const usuario = await abrir(alExpirar);
    fetchFalso.mockResolvedValue(json({ detalle: "Sin sesión." }, 401));
    await usuario.click(screen.getByRole("button", BOTON));
    await vi.waitFor(() => expect(alExpirar).toHaveBeenCalledOnce());
  });
});
