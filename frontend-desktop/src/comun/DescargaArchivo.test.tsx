import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../api/cliente";
import { alertaConTexto } from "../test/ayudas";
import { DescargaArchivo } from "./DescargaArchivo";

describe("DescargaArchivo", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const crearUrl = vi.fn(() => "blob:falso");
  const revocarUrl = vi.fn();
  let clics: { descarga: string; href: string }[];

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
    clics = [];
    Object.defineProperty(URL, "createObjectURL", { value: crearUrl, configurable: true });
    Object.defineProperty(URL, "revokeObjectURL", { value: revocarUrl, configurable: true });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      clics.push({ descarga: this.download, href: this.href });
    });
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    crearUrl.mockClear();
    revocarUrl.mockClear();
  });

  test("al hacer clic baja el archivo con el nombre del Content-Disposition", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValue(
      new Response("PK", { status: 200, headers: { "Content-Disposition": 'attachment; filename="paquete.zip"' } }),
    );
    render(<DescargaArchivo ruta="/v1/entrega" etiqueta="Descargar paquete" nombrePorOmision="paquete.bin" />);
    await usuario.click(screen.getByRole("button", { name: "Descargar paquete" }));
    await vi.waitFor(() => expect(clics).toHaveLength(1));
    expect(clics[0].descarga).toBe("paquete.zip");
    expect(crearUrl).toHaveBeenCalledOnce();
    expect(revocarUrl).toHaveBeenCalledWith("blob:falso");
  });

  test("un POST manda su cuerpo y el token anti-CSRF", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValue(new Response("x", { status: 200 }));
    render(
      <DescargaArchivo ruta="/v1/entrega" metodo="POST" cuerpo={{ proyecto: "P1" }} etiqueta="Entregar" nombrePorOmision="e.zip" />,
    );
    await usuario.click(screen.getByRole("button", { name: "Entregar" }));
    await vi.waitFor(() => expect(clics).toHaveLength(1));
    const init = fetchFalso.mock.calls[0][1];
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(JSON.stringify({ proyecto: "P1" }));
    expect(new Headers(init?.headers).get("X-Silice-CSRF")).toBe("tok");
    expect(clics[0].descarga).toBe("e.zip");
  });

  test("si la API falla muestra el detalle y no baja nada", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValue(
      new Response(JSON.stringify({ detalle: "El paquete tiene hallazgos críticos." }), {
        status: 409,
        headers: { "Content-Type": "application/json" },
      }),
    );
    render(<DescargaArchivo ruta="/v1/entrega" etiqueta="Descargar" nombrePorOmision="e.zip" />);
    await usuario.click(screen.getByRole("button", { name: "Descargar" }));
    expect(await alertaConTexto()).toHaveTextContent("El paquete tiene hallazgos críticos.");
    expect(clics).toHaveLength(0);
  });

  test("un 401 avisa que la sesion vencio", async () => {
    const usuario = userEvent.setup();
    const alExpirar = vi.fn();
    fetchFalso.mockResolvedValue(
      new Response(JSON.stringify({ detalle: "Sin sesión." }), { status: 401, headers: { "Content-Type": "application/json" } }),
    );
    render(<DescargaArchivo ruta="/v1/x" etiqueta="Descargar" nombrePorOmision="x" alExpirar={alExpirar} />);
    await usuario.click(screen.getByRole("button", { name: "Descargar" }));
    await vi.waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("mientras baja el boton queda deshabilitado, para no pedirlo dos veces", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockImplementation(() => new Promise<Response>(() => {}));
    render(<DescargaArchivo ruta="/v1/x" etiqueta="Descargar" nombrePorOmision="x" />);
    await usuario.click(screen.getByRole("button", { name: "Descargar" }));
    expect(screen.getByRole("button", { name: /Descargando/ })).toBeDisabled();
  });
});
