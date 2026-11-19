import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Valuaciones } from "./logica";
import { PestanaValuaciones } from "./PestanaValuaciones";

// Datos ficticios (los de Control.test.tsx). Estas pruebas miran lo que la pestaña manda cuando la lista que tiene a la
// vista ya cambió: tras anular, o mientras un archivo todavía se está leyendo.
function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["control_de_obra"],
  modo_entrega: false,
};

const V01 = { id: 7, rotulo: "V-01 (02/11/2026 a 06/11/2026)" };
const V02 = { id: 8, rotulo: "V-02 (09/11/2026 a 13/11/2026)" };

function valuaciones(anulables: Valuaciones["anulables"]): Valuaciones {
  return {
    tiene_linea_base: true,
    filas: [],
    impuestos: { subtotal: "0", iva: "0", total: "0", alicuota: "0.16", fuente_alicuota: "Decreto ficticio" },
    perspectiva: "costo",
    aviso: "",
    anulables,
    corte_por_defecto: "2026-11-13",
    causas: [],
  };
}

// La pestaña vuelve a leer las valuaciones cuando sube su `clave`: aquí sube con cada escritura, como en la página.
function Envoltura() {
  const [clave, setClave] = useState(0);
  return <PestanaValuaciones proyecto="OB-S2" clave={clave} alCambiar={() => setClave((c) => c + 1)} />;
}

function campoArchivo(): HTMLInputElement {
  return document.querySelector('input[type="file"]') as HTMLInputElement;
}

describe("Pestaña de valuaciones", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let anulables: Valuaciones["anulables"];
  let informe: (cuerpo: FormData) => Response | Promise<Response>;
  let importar: () => Response | Promise<Response>;
  let registro: unknown;
  let hallazgosDeLaLista: Valuaciones["hallazgos"];
  let costos: Record<string, string>[];

  function montar() {
    render(
      <ContextoAplicacion.Provider
        value={{ sesion: SESION, proyecto: "OB-S2", caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() }}
      >
        <Envoltura />
      </ContextoAplicacion.Provider>,
    );
    return userEvent.setup();
  }

  function anulacionesPedidas(): string[] {
    return fetchFalso.mock.calls.map(([u]) => String(u)).filter((u) => u.endsWith("/anular"));
  }

  beforeEach(() => {
    fijarCsrf("tok");
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    anulables = [V01, V02];
    informe = () => json({ informe: ["sin novedades"] });
    importar = () => json({ importadas: 1 });
    registro = { corte: "2026-11-13", hallazgos: 0, errores: 0, detalle: [] };
    hallazgosDeLaLista = [];
    costos = [];
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = String(entrada);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/control/valuaciones?") && metodo === "GET") return json({ ...valuaciones(anulables), hallazgos: hallazgosDeLaLista });
      if (url === "/v1/control/valuaciones" && metodo === "POST") return json(registro);
      if (url.startsWith("/v1/control/costos?") && metodo === "GET") return json({ filas: costos });
      const anular = /^\/v1\/control\/valuaciones\/(\d+)\/anular$/.exec(url);
      if (anular && metodo === "POST") {
        anulables = anulables.filter((a) => String(a.id) !== anular[1]);
        return json({ anulada: Number(anular[1]) });
      }
      if (url === "/v1/control/importar/informe") return informe(init?.body as FormData);
      if (url === "/v1/control/importar") return importar();
      return json({ detalle: `ruta inesperada ${metodo} ${url}` }, 500);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    fijarCsrf(null);
  });

  // Tras anular V-02 la lista ya no la trae y el selector muestra V-01; el segundo «Anular» mandaba otra vez V-02.
  test("tras anular una valuación, el siguiente «Anular» manda la que muestra el selector", async () => {
    const u = montar();
    const selector = await screen.findByLabelText("Valuación");
    await u.selectOptions(selector, String(V02.id));
    await u.click(screen.getByRole("button", { name: "Anular" }));
    expect(await screen.findByText("Valuación anulada: se conserva y ya no cuenta.")).toBeInTheDocument();
    await waitFor(() => expect(within(screen.getByLabelText("Valuación")).getAllByRole("option")).toHaveLength(1));
    expect(screen.getByLabelText("Valuación")).toHaveValue(String(V01.id));
    await u.click(screen.getByRole("button", { name: "Anular" }));
    await waitFor(() => expect(anulacionesPedidas()).toHaveLength(2));
    expect(anulacionesPedidas()).toEqual([`/v1/control/valuaciones/${V02.id}/anular`, `/v1/control/valuaciones/${V01.id}/anular`]);
  });

  // El informe previo dice de qué archivo es: el de un archivo que tardó no puede quedar rotulado con el que se eligió
  // después.
  test("el informe previo nunca queda rotulado con otro archivo", async () => {
    const pendientes: Record<string, (r: Response) => void> = {};
    informe = (cuerpo) => {
      const nombre = (cuerpo.get("archivo") as File).name;
      if (nombre === "val2.xlsx") return json({ informe: ["Informe de val2"] });
      return new Promise<Response>((resolver) => (pendientes[nombre] = resolver));
    };
    const u = montar();
    await screen.findByLabelText("Valuación");
    await u.upload(campoArchivo(), new File(["x"], "val1.xlsx"));
    await u.upload(campoArchivo(), new File(["x"], "val2.xlsx"));
    // El de val1 responde el último; se deja que su respuesta termine de llegar antes de mirar.
    pendientes["val1.xlsx"]?.(json({ informe: ["Informe de val1"] }));
    await screen.findByText(/^Informe de val/);
    await act(() => new Promise((resolver) => setTimeout(resolver, 50)));
    const de = /Informe previo de (val\d)\.xlsx:/.exec(screen.getByText(/^Informe previo de /).textContent ?? "")?.[1];
    expect(screen.getByText(/^Informe de val/)).toHaveTextContent(`Informe de ${de}`);
  });

  test("mientras se lee el archivo no se puede elegir otro", async () => {
    let soltar: (r: Response) => void = () => undefined;
    informe = () => new Promise<Response>((resolver) => (soltar = resolver));
    const u = montar();
    await screen.findByLabelText("Valuación");
    await u.upload(campoArchivo(), new File(["x"], "val1.xlsx"));
    expect(campoArchivo()).toBeDisabled();
    soltar(json({ informe: ["Informe de val1"] }));
    await screen.findByText("Informe de val1");
    expect(campoArchivo()).toBeEnabled();
  });

  test("mientras se importa no se puede elegir otro archivo", async () => {
    let soltar: (r: Response) => void = () => undefined;
    importar = () => new Promise<Response>((resolver) => (soltar = resolver));
    const u = montar();
    await screen.findByLabelText("Valuación");
    await u.upload(campoArchivo(), new File(["x"], "val1.xlsx"));
    await screen.findByText("sin novedades");
    await u.click(screen.getByRole("button", { name: "Importar" }));
    expect(campoArchivo()).toBeDisabled();
    soltar(json({ importadas: 1 }));
    expect(await screen.findByText("1 valuación(es) importada(s).")).toBeInTheDocument();
    expect(campoArchivo()).toBeEnabled();
  });

  // Prueba en vivo del 2026-11-18, hallazgo 2: con errores el aviso no es verde de éxito y dice cuáles son.
  test("registrar con errores avisa en ámbar y lista cada hallazgo con su mensaje", async () => {
    registro = {
      corte: "2026-11-13",
      hallazgos: 2,
      errores: 1,
      detalle: [
        { valuacion: "V-03", regla: "R14", severidad: "Error", mensaje: "La valuación V-03 no tiene inspector." },
        { valuacion: "V-03", regla: "R14", severidad: "Información", mensaje: "Entre las valuaciones V-02 y V-03 hay 1 día(s) hábil(es) sin cubrir (16/11/2026 a 16/11/2026)." },
      ],
    };
    const u = montar();
    await screen.findByLabelText("Valuación");
    const regionViva = document.getElementById("val-resultado");
    expect(regionViva).toHaveAttribute("aria-live", "polite");
    await u.type(screen.getByLabelText("Número"), "V-03");
    await u.type(screen.getByLabelText("Partida 1"), "OB-A");
    await u.type(screen.getByLabelText("Cantidad 1"), "5");
    await u.click(screen.getByRole("button", { name: "Registrar y controlar" }));
    const aviso = await screen.findByText(/la revisión encontró 1 error/);
    expect(aviso.textContent).toBe("Valuación registrada (corte 13/11/2026), pero la revisión encontró 1 error.");
    const notificacion = aviso.closest(".cds--inline-notification");
    expect(notificacion).toHaveClass("cds--inline-notification--warning");
    // Arbitraje, punto 9: el resumen breve se anuncia en una región viva que ya estaba en el DOM; la lista no es parte
    // del anuncio (ni de un role="alert"): va debajo, con su nombre.
    expect(screen.queryByRole("alert")).toBeNull();
    expect(aviso.closest("#val-resultado")).toBe(regionViva);
    expect(within(notificacion as HTMLElement).queryByRole("list")).toBeNull();
    const lista = screen.getByRole("list", { name: "Hallazgos de la revisión de la valuación registrada" });
    expect(within(lista).getByText("Error (R14): La valuación V-03 no tiene inspector.")).toBeInTheDocument();
    expect(within(lista).getByText(/^Información \(R14\): Entre las valuaciones/)).toBeInTheDocument();
    expect(screen.queryByText(/^Valuación registrada: corte/)).toBeNull();
  });

  test("registrar sin hallazgos dice el corte en verde", async () => {
    const u = montar();
    await screen.findByLabelText("Valuación");
    await u.type(screen.getByLabelText("Partida 1"), "OB-A");
    await u.type(screen.getByLabelText("Cantidad 1"), "5");
    await u.click(screen.getByRole("button", { name: "Registrar y controlar" }));
    expect(await screen.findByText("Valuación registrada: corte 13/11/2026, sin hallazgos en la revisión.")).toBeInTheDocument();
  });

  test("los hallazgos de las valuaciones guardadas se leen junto a la tabla", async () => {
    hallazgosDeLaLista = [{ valuacion: "V-02", regla: "R14", severidad: "Error", mensaje: "La valuación V-02 no tiene inspector." }];
    montar();
    const lista = await screen.findByRole("list", { name: "Hallazgos de la revisión de las valuaciones" });
    expect(within(lista).getByText("V-02 · Error (R14): La valuación V-02 no tiene inspector.")).toBeInTheDocument();
  });

  // Prueba en vivo del 2026-11-18, hallazgo 3: un costo anotado no se podía ver.
  test("los costos anotados se ven en una tabla con el monto en es-VE", async () => {
    costos = [
      { Fecha: "13/11/2026", Monto: "1280.00", Moneda: "USD", Partida: "", Fuente: "libro de obra ficticio", Responsable: "Residente Ficticio" },
    ];
    montar();
    const tabla = await screen.findByRole("table", { name: "Costos incurridos anotados" });
    expect(within(tabla).getByText("13/11/2026")).toBeInTheDocument();
    expect(within(tabla).getByText("1.280,00")).toBeInTheDocument();
    expect(within(tabla).getByText("libro de obra ficticio")).toBeInTheDocument();
  });

  // Arbitraje, punto 10: el monto viaja exacto; se lee a dos decimales y el exacto queda en el title.
  test("el monto de un costo se lee a dos decimales con el exacto en el title", async () => {
    costos = [{ Fecha: "12/11/2026", Monto: "100.005", Moneda: "USD", Partida: "OB-A", Fuente: "factura 12", Responsable: "Ana" }];
    montar();
    const tabla = await screen.findByRole("table", { name: "Costos incurridos anotados" });
    expect(within(tabla).getByText("100,01")).toHaveAttribute("title", "100.005");
  });
});
