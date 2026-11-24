import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import {
  buscadorDeInsumos,
  convertidasConLaTasa,
  cotizacionEsVe,
  deObservaciones,
  diasValidos,
  enumeracion,
  rutaDelEstudio,
  sinTasaDelDia,
  textoDeAfectados,
} from "./logica";

// Estudio de mercado (plan de montar un presupuesto, Tarea 15). Oraculos escritos a mano; insumos ficticios.

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

describe("textos del estudio de mercado", () => {
  test("enumeracion en espanol: uno, dos con «y», tres con comas y «y»", () => {
    expect(enumeracion(["OBRA-02"])).toBe("OBRA-02");
    expect(enumeracion(["OBRA-02", "OBRA-04"])).toBe("OBRA-02 y OBRA-04");
    expect(enumeracion(["OBRA-01", "OBRA-02", "OBRA-04"])).toBe("OBRA-01, OBRA-02 y OBRA-04");
  });

  test("lo que cambiara al usar un precio de compra", () => {
    expect(textoDeAfectados(["OBRA-02", "OBRA-04"])).toBe("Cambiará el precio en OBRA-02 y OBRA-04.");
    expect(textoDeAfectados([])).toBe("Ninguna partida del catálogo usa este insumo: no cambiará el precio de ninguna.");
  });

  test("de cuantas observaciones sale una cifra, en singular y plural", () => {
    expect(deObservaciones(1)).toBe("de 1 observación");
    expect(deObservaciones(5)).toBe("de 5 observaciones");
  });

  test("la ventana de dias va de 1 a 3.650, entera y sin ceros a la izquierda", () => {
    for (const bueno of ["1", "30", "90", "365", "1.000", "3650"]) expect(diasValidos(bueno), bueno).toBe(true);
    for (const malo of ["", "0", "-5", "3651", "9999", "12,5", "090", "abc", " 90"]) {
      expect(diasValidos(malo), malo).toBe(false);
    }
  });

  test("la ruta del estudio: lado, codigo escapado, dias y la obra abierta solo si la hay", () => {
    expect(rutaDelEstudio("compra", "CEM-GRIS", "90", null)).toBe("/v1/mercado/compra/CEM-GRIS?dias=90");
    expect(rutaDelEstudio("cobro", "OBRA-04", "30", "VIV-001")).toBe("/v1/mercado/cobro/OBRA-04?dias=30&proyecto=VIV-001");
    expect(rutaDelEstudio("compra", "A/B 1", "90", null)).toBe("/v1/mercado/compra/A%2FB%201?dias=90");
  });
});

describe("buscador de insumos (lista del catalogo, filtrada en el navegador)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const INSUMOS = [
    { codigo: "CEM-GRIS", descripcion: "Cemento gris ficticio, saco de 42,5 kg", tipo: "material", unidad: "saco", precio_vigente: "18.00" },
    { codigo: "ARE-LAV", descripcion: "Arena lavada ficticia", tipo: "material", unidad: "m3", precio_vigente: null },
    { codigo: "MEZ-01", descripcion: "Mezcladora de concreto ficticia", tipo: "equipo", unidad: null, precio_vigente: "5.00" },
    { codigo: "ALB-01", descripcion: "Albañil de primera", tipo: "mano_obra", unidad: "día", precio_vigente: "30.00" },
  ];

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fetchFalso.mockImplementation(async () => json(INSUMOS));
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("busca por palabras de la descripcion o del codigo, sin tildes ni mayusculas", async () => {
    const buscar = buscadorDeInsumos();
    const [grupo] = await buscar("cemento", new AbortController().signal, 8);
    expect(grupo.rotulo).toBe("Insumos del catálogo");
    expect(grupo.opciones.map((o) => o.valor.codigo)).toEqual(["CEM-GRIS"]);
    expect(grupo.opciones[0]).toMatchObject({
      clave: "insumo:CEM-GRIS",
      principal: "Cemento gris ficticio, saco de 42,5 kg",
      secundaria: ["CEM-GRIS", "saco", "material"],
    });
    const [porCodigo] = await buscar("are-l", new AbortController().signal, 8);
    expect(porCodigo.opciones.map((o) => o.valor.codigo)).toEqual(["ARE-LAV"]);
    const [sinTilde] = await buscar("ALBANIL", new AbortController().signal, 8);
    expect(sinTilde.opciones.map((o) => o.valor.codigo)).toEqual(["ALB-01"]);
    expect(sinTilde.opciones[0].secundaria).toEqual(["ALB-01", "día", "mano de obra"]);
    const [dosPalabras] = await buscar("ficticia concreto", new AbortController().signal, 8);
    expect(dosPalabras.opciones.map((o) => o.valor.codigo)).toEqual(["MEZ-01"]);
    expect(dosPalabras.opciones[0].secundaria).toEqual(["MEZ-01", "equipo"]);
  });

  test("pide la lista una sola vez y respeta el limite con «hay mas»", async () => {
    const buscar = buscadorDeInsumos();
    const [uno] = await buscar("fictici", new AbortController().signal, 2);
    expect(uno.opciones.map((o) => o.valor.codigo)).toEqual(["CEM-GRIS", "ARE-LAV"]);
    expect(uno.hayMas).toBe(true);
    const [todos] = await buscar("fictici", new AbortController().signal, 20);
    expect(todos.opciones).toHaveLength(3);
    expect(todos.hayMas).toBe(false);
    expect(fetchFalso).toHaveBeenCalledTimes(1);
    expect(fetchFalso.mock.calls[0][0]).toBe("/insumos");
  });

  test("una busqueda abortada no entrega resultados", async () => {
    const buscar = buscadorDeInsumos();
    const control = new AbortController();
    control.abort();
    await expect(buscar("cemento", control.signal, 8)).rejects.toMatchObject({ name: "AbortError" });
  });

  test("si la lista no se pudo pedir, la siguiente busqueda la vuelve a pedir", async () => {
    fetchFalso.mockImplementationOnce(async () => json({ detail: "No se pudo leer el catálogo." }, 503));
    const buscar = buscadorDeInsumos();
    await expect(buscar("cemento", new AbortController().signal, 8)).rejects.toMatchObject({ estado: 503 });
    const [grupo] = await buscar("cemento", new AbortController().signal, 8);
    expect(grupo.opciones).toHaveLength(1);
    expect(fetchFalso).toHaveBeenCalledTimes(2);
  });
});

// Prueba en vivo del 2026-11-18, hallazgo 8: la columna «Cotización» decía la fecha en ISO («2026-11-18»). El núcleo la
// arma como «proveedor, número, AAAA-MM-DD» (core/catalog/origen.py): solo la fecha final, la del sistema, cambia de forma.
describe("la cotización de un precio", () => {
  test("la fecha final va en dd/mm/aaaa y el proveedor y el número quedan tal cual", () => {
    expect(cotizacionEsVe("Ferretería Demo, COT-17, 2026-11-18")).toBe("Ferretería Demo, COT-17, 18/11/2026");
    expect(cotizacionEsVe("Proveedor 2026-01-02, N.º 2026-03-04, 2026-11-18")).toBe(
      "Proveedor 2026-01-02, N.º 2026-03-04, 18/11/2026",
    );
  });

  test("un texto sin la fecha final del sistema no cambia", () => {
    expect(cotizacionEsVe("")).toBe("");
    expect(cotizacionEsVe("COT-17 · Ferretería Demo")).toBe("COT-17 · Ferretería Demo");
    expect(cotizacionEsVe("2026-11-18")).toBe("2026-11-18");
  });
});

describe("F7: días con punto de miles y conteos en es-VE", () => {
  test("diasValidos acepta formato es-VE como 3.650", () => {
    expect(diasValidos("3.650")).toBe(true);
    expect(diasValidos("1.000")).toBe(true);
    expect(diasValidos("3.651")).toBe(false);
  });

  test("deObservaciones, sinTasaDelDia y convertidasConLaTasa formatean >= 1000 con punto de miles", () => {
    expect(deObservaciones(1000)).toBe("de 1.000 observaciones");
    expect(sinTasaDelDia(1250)).toContain("1.250 observaciones");
    expect(convertidasConLaTasa(1200)).toBe("1.200 de las observaciones estaban en otra moneda y se convirtieron con la tasa del BCV de su día.");
  });
});

