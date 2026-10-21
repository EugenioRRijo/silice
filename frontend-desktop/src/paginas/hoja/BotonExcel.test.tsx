import { act, configure, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { BotonExcel } from "./BotonExcel";
import { NOMBRE_POR_OMISION, rutaDelExcel } from "./logicaExcel";

// Rebanada 3e-1 (3e-F4): «Descargar Excel» usa DescargaArchivo (GET) sobre X1 `GET /v1/hoja/borradores/{id}/excel`
// y muestra el error «No se pudo preparar el Excel: …» con el detalle de la API tal cual. Servidor simulado con la forma
// del contrato (docs/bitacora/2026-10-20-hoja-3e-contrato-rutas.md). Caso ficticio OF-001.
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
const TIPO = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

function libro(nombre: string): Response {
  return new Response(new Uint8Array([80, 75, 3, 4, 1, 2, 3]), {
    status: 200,
    headers: { "Content-Type": TIPO, "Content-Disposition": `attachment; filename="${nombre}"` },
  });
}
function error(estado: number, detalle: string): Response {
  return new Response(JSON.stringify({ detalle }), { status: estado, headers: { "Content-Type": "application/json" } });
}

describe("Botón «Descargar Excel» de la hoja (3e-F4)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();
  const guardados: string[] = [];

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
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

  function montar(id = ID) {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: "OF-001",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <BotonExcel id={id} />
      </ContextoAplicacion.Provider>,
    );
  }
  const boton = () => screen.getByRole("button", { name: /Descargar Excel|Descargando/ });

  test("la ruta es la de X1 y el id viaja codificado", () => {
    expect(rutaDelExcel(ID)).toBe("/v1/hoja/borradores/id-borrador-aaaaaaaaaaaa/excel");
    expect(rutaDelExcel("a/b?c")).toBe("/v1/hoja/borradores/a%2Fb%3Fc/excel");
    expect(NOMBRE_POR_OMISION).toBe("hoja_borrador.xlsx");
  });

  test("tiene nombre accesible «Descargar Excel», y no pide nada hasta pulsarlo", () => {
    montar();
    expect(screen.getByRole("button", { name: "Descargar Excel" })).toBeEnabled();
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("al pulsar pide el libro con GET, sin cuerpo, y guarda el archivo con el nombre del servidor", async () => {
    fetchFalso.mockResolvedValue(libro("hoja_001.xlsx"));
    montar();
    await userEvent.click(boton());
    await waitFor(() => expect(guardados).toEqual(["hoja_001.xlsx"]));
    expect(fetchFalso).toHaveBeenCalledTimes(1);
    const [ruta, init] = fetchFalso.mock.calls[0]!;
    expect(String(ruta)).toBe(`/v1/hoja/borradores/${ID}/excel`);
    expect(init?.method ?? "GET").toBe("GET");
    expect(init?.body).toBeUndefined();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  test("respeta el nombre del servidor aunque traiga una ruta, y usa el de respaldo si falta", async () => {
    fetchFalso.mockResolvedValueOnce(libro("..\..\hoja_001.xlsx"));
    fetchFalso.mockResolvedValueOnce(new Response(new Uint8Array([1]), { status: 200 }));
    montar();
    await userEvent.click(boton());
    await waitFor(() => expect(guardados).toEqual(["hoja_001.xlsx"]));
    await userEvent.click(boton());
    await waitFor(() => expect(guardados).toEqual(["hoja_001.xlsx", "hoja_borrador.xlsx"]));
  });

  test("mientras descarga queda deshabilitado, no manda dos peticiones y luego se habilita", async () => {
    let entregar: (r: Response) => void = () => undefined;
    fetchFalso.mockImplementation(() => new Promise<Response>((resolver) => (entregar = resolver)));
    montar();
    await userEvent.click(boton());
    await waitFor(() => expect(boton()).toBeDisabled());
    expect(boton()).toHaveTextContent("Descargando");
    await userEvent.click(boton());
    expect(fetchFalso).toHaveBeenCalledTimes(1);
    await act(async () => entregar(libro("hoja_001.xlsx")));
    await waitFor(() => expect(screen.getByRole("button", { name: "Descargar Excel" })).toBeEnabled());
  });

  test.each([
    [422, "No se pudo preparar el Excel: la hoja «Precios» no cabe"],
    [404, "Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). Lo que no guardó se perdió: abra la versión otra vez."],
    [503, "No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro programa."],
    [409, "El caso cambió desde que abrió este borrador: ábralo de nuevo en el caso actual."],
  ])("un %i muestra el detalle de la API tal cual, en un aviso, y no guarda nada", async (estado, detalle) => {
    fetchFalso.mockResolvedValue(error(estado, detalle));
    montar();
    await userEvent.click(boton());
    const aviso = await screen.findByRole("alert");
    expect(aviso).toHaveTextContent(detalle);
    expect(guardados).toEqual([]);
    expect(screen.getByRole("button", { name: "Descargar Excel" })).toBeEnabled();
    expect(alExpirar).not.toHaveBeenCalled();
  });

  test("un 401 avisa que la sesión venció", async () => {
    fetchFalso.mockResolvedValue(error(401, "Inicie sesión."));
    montar();
    await userEvent.click(boton());
    await screen.findByRole("alert");
    expect(alExpirar).toHaveBeenCalledTimes(1);
  });

  test("si no hay conexión muestra el aviso del cliente y se puede reintentar", async () => {
    fetchFalso.mockRejectedValueOnce(new TypeError("red"));
    fetchFalso.mockResolvedValueOnce(libro("hoja_001.xlsx"));
    montar();
    await userEvent.click(boton());
    expect(await screen.findByRole("alert")).toHaveTextContent("No se pudo hablar con el programa de Sílice");
    await userEvent.click(boton());
    await waitFor(() => expect(guardados).toEqual(["hoja_001.xlsx"]));
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
