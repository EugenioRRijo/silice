import { configure, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { BotonExcel } from "./BotonExcel";
import { BotonPdfDelApu } from "./BotonPdf";
import { NOMBRE_PDF_APU_POR_OMISION, NOMBRE_PDF_POR_OMISION, rutaDelPdf } from "./logicaPdf";

// RF-213 (ola 2, línea 4): «Descargar PDF» al lado de «Descargar Excel», en el mismo grupo «Exportar la hoja». Pide
// `GET /v1/hoja/borradores/{id}/pdf` y guarda el archivo con el nombre del servidor; un error se muestra tal cual. La
// interfaz no arma ni calcula nada del PDF: lo hace el servidor. Servidor simulado; caso ficticio OF-001.
configure({ asyncUtilTimeout: 5000 });

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja"],
  modo_entrega: false,
};
const ID = "id-borrador-aaaaaaaaaaaa";

function pdf(nombre: string): Response {
  return new Response(new Uint8Array([37, 80, 68, 70]), {
    status: 200,
    headers: { "Content-Type": "application/pdf", "Content-Disposition": `attachment; filename="${nombre}"` },
  });
}

describe("Botón «Descargar PDF» de la hoja (RF-213)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const guardados: string[] = [];

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    guardados.length = 0;
    URL.createObjectURL = vi.fn(() => "blob:falso");
    URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      guardados.push(this.download);
    });
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  function montar(elemento: ReactNode = <BotonExcel id={ID} />) {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: "OF-001",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    return render(<ContextoAplicacion.Provider value={valor}>{elemento}</ContextoAplicacion.Provider>);
  }

  test("la ruta es la del PDF del borrador y el id viaja codificado", () => {
    expect(rutaDelPdf(ID)).toBe("/v1/hoja/borradores/id-borrador-aaaaaaaaaaaa/pdf");
    expect(rutaDelPdf("a/b?c")).toBe("/v1/hoja/borradores/a%2Fb%3Fc/pdf");
    expect(rutaDelPdf(ID, "AF-CODO-1/2")).toBe("/v1/hoja/borradores/id-borrador-aaaaaaaaaaaa/pdf?partida=AF-CODO-1%2F2");
    expect(NOMBRE_PDF_POR_OMISION).toBe("presupuesto_borrador.pdf");
    expect(NOMBRE_PDF_APU_POR_OMISION).toBe("apu_borrador.pdf");
  });

  test("va en el grupo «Exportar la hoja», después de «Descargar Excel», y no es el principal", () => {
    montar();
    const grupo = screen.getByRole("group", { name: "Exportar la hoja" });
    const botones = within(grupo).getAllByRole("button");
    expect(botones.map((b) => b.textContent)).toEqual(["Descargar Excel", "Descargar PDF"]);
    expect(botones[1]).not.toHaveClass("cds--btn--primary");
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("al pulsar pide el PDF con GET y lo guarda con el nombre del servidor", async () => {
    fetchFalso.mockResolvedValue(pdf("presupuesto_001.pdf"));
    montar();
    await userEvent.click(screen.getByRole("button", { name: "Descargar PDF" }));
    await waitFor(() => expect(guardados).toEqual(["presupuesto_001.pdf"]));
    const [ruta, init] = fetchFalso.mock.calls[0]!;
    expect(String(ruta)).toBe(`/v1/hoja/borradores/${ID}/pdf`);
    expect(init?.method ?? "GET").toBe("GET");
    expect(init?.body).toBeUndefined();
  });

  test("sin nombre del servidor usa presupuesto_borrador.pdf", async () => {
    fetchFalso.mockResolvedValue(new Response(new Uint8Array([1]), { status: 200 }));
    montar();
    await userEvent.click(screen.getByRole("button", { name: "Descargar PDF" }));
    await waitFor(() => expect(guardados).toEqual(["presupuesto_borrador.pdf"]));
  });

  test("un error de la API se muestra tal cual y no guarda nada", async () => {
    const detalle =
      "Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). Lo que no guardó se perdió: abra la versión otra vez.";
    fetchFalso.mockResolvedValue(
      new Response(JSON.stringify({ detalle }), { status: 404, headers: { "Content-Type": "application/json" } }),
    );
    montar();
    await userEvent.click(screen.getByRole("button", { name: "Descargar PDF" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(detalle);
    expect(guardados).toEqual([]);
  });

  test("el botón del APU pide ?partida= codificado y guarda con el nombre del servidor", async () => {
    fetchFalso.mockResolvedValue(pdf("apu_AF-CODO-1_2.pdf"));
    montar(<BotonPdfDelApu id={ID} partida="AF-CODO-1/2" />);
    const boton = screen.getByRole("button", { name: "PDF de este APU" });
    expect(boton).not.toHaveClass("cds--btn--primary");
    await userEvent.click(boton);
    await waitFor(() => expect(guardados).toEqual(["apu_AF-CODO-1_2.pdf"]));
    const [ruta, init] = fetchFalso.mock.calls[0]!;
    expect(String(ruta)).toBe(`/v1/hoja/borradores/${ID}/pdf?partida=AF-CODO-1%2F2`);
    expect(init?.method ?? "GET").toBe("GET");
    expect(init?.body).toBeUndefined();
  });

  test("el botón del APU sin nombre del servidor usa apu_borrador.pdf", async () => {
    fetchFalso.mockResolvedValue(new Response(new Uint8Array([1]), { status: 200 }));
    montar(<BotonPdfDelApu id={ID} partida="AF-CODO-1/2" />);
    await userEvent.click(screen.getByRole("button", { name: "PDF de este APU" }));
    await waitFor(() => expect(guardados).toEqual(["apu_borrador.pdf"]));
  });

  test("un 404 al pedir el PDF de un APU muestra el detalle del servidor tal cual y no guarda nada", async () => {
    const detalle = "La partida «AF-CODO-1/2» no tiene APU en el borrador.";
    fetchFalso.mockResolvedValue(
      new Response(JSON.stringify({ detalle }), { status: 404, headers: { "Content-Type": "application/json" } }),
    );
    montar(<BotonPdfDelApu id={ID} partida="AF-CODO-1/2" />);
    await userEvent.click(screen.getByRole("button", { name: "PDF de este APU" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(detalle);
    expect(guardados).toEqual([]);
  });
});
