import { describe, expect, test, vi } from "vitest";
import { almacenDeLaApi, type PedirNotificaciones } from "./almacenDeLaApi";
import type { Notificacion } from "./modelo";

// C11: el almacén del proveedor guarda la lista entera; la API (f7520d3b) recibe una notificación nueva por POST y marca
// las leídas aparte. El adaptador traduce sin mandar dos veces lo mismo.

const DEL_SERVIDOR = {
  notificaciones: [
    {
      id: 7,
      gravedad: "advertencia",
      titulo: "Precio vencido",
      detalle: "",
      enlace: { texto: "Ver en Precios de la empresa", ruta: "/precios" },
      creada: "2026-11-26T09:15:00",
      leida: false,
    },
    { id: 3, gravedad: "info", titulo: "Lista cargada", detalle: "MaPreX", enlace: null, creada: "2026-11-25T16:05:00", leida: true },
  ],
  sin_leer: 1,
  retencion_dias: 30,
  maximo: 200,
};

function servidorFalso() {
  let siguiente = 100;
  const pedir = vi.fn<PedirNotificaciones>(async (ruta, opciones) => {
    if (ruta === "/v1/notificaciones" && (opciones?.metodo ?? "GET") === "GET") return DEL_SERVIDOR;
    if (ruta === "/v1/notificaciones" && opciones?.metodo === "POST") {
      const cuerpo = opciones.cuerpo as { titulo: string };
      return { id: siguiente++, gravedad: "listo", titulo: cuerpo.titulo, detalle: "", enlace: null, creada: "2026-11-26T10:00:00", leida: false };
    }
    if (ruta === "/v1/notificaciones/leidas") return { marcadas: 1, sin_leer: 0 };
    throw new Error(`ruta inesperada ${ruta}`);
  });
  return pedir;
}

const local = (parcial: Partial<Notificacion>): Notificacion => ({
  id: "local-1",
  gravedad: "listo",
  titulo: "Versión V2 guardada",
  creada: "2026-11-26T10:00:00",
  leida: false,
  ...parcial,
});

describe("almacenDeLaApi", () => {
  test("cargar trae las del servidor con id propio, sin detalle ni enlace vacíos", async () => {
    const almacen = almacenDeLaApi(servidorFalso());
    const lista = await almacen.cargar();
    expect(lista).toEqual([
      {
        id: "api:7",
        gravedad: "advertencia",
        titulo: "Precio vencido",
        enlace: { texto: "Ver en Precios de la empresa", ruta: "/precios" },
        creada: "2026-11-26T09:15:00",
        leida: false,
      },
      { id: "api:3", gravedad: "info", titulo: "Lista cargada", detalle: "MaPreX", creada: "2026-11-25T16:05:00", leida: true },
    ]);
  });

  test("guardar manda por POST solo las nuevas, una sola vez aunque se guarde de nuevo", async () => {
    const pedir = servidorFalso();
    const almacen = almacenDeLaApi(pedir);
    const cargadas = await almacen.cargar();
    const nueva = local({});
    await almacen.guardar([nueva, ...cargadas]);
    await almacen.guardar([nueva, ...cargadas]);
    const posts = pedir.mock.calls.filter(([ruta, op]) => ruta === "/v1/notificaciones" && op?.metodo === "POST");
    expect(posts).toHaveLength(1);
    expect(posts[0]![1]!.cuerpo).toEqual({ gravedad: "listo", titulo: "Versión V2 guardada", detalle: "" });
  });

  test("guardar marca como leídas en el servidor las que pasaron a leídas, también las nuevas ya enviadas", async () => {
    const pedir = servidorFalso();
    const almacen = almacenDeLaApi(pedir);
    const cargadas = await almacen.cargar();
    const nueva = local({});
    await almacen.guardar([nueva, ...cargadas]);
    await almacen.guardar([{ ...nueva, leida: true }, ...cargadas.map((n) => ({ ...n, leida: true }))]);
    const leidas = pedir.mock.calls.filter(([ruta]) => ruta === "/v1/notificaciones/leidas");
    expect(leidas).toHaveLength(1);
    expect(leidas[0]![1]).toEqual({ metodo: "POST", cuerpo: { ids: [100, 7] } });
    // La 3 ya venía leída: no se vuelve a marcar.
    await almacen.guardar([{ ...nueva, leida: true }, ...cargadas.map((n) => ({ ...n, leida: true }))]);
    expect(pedir.mock.calls.filter(([ruta]) => ruta === "/v1/notificaciones/leidas")).toHaveLength(1);
  });

  test("un enlace se manda solo si su ruta es interna", async () => {
    const pedir = servidorFalso();
    const almacen = almacenDeLaApi(pedir);
    await almacen.cargar();
    await almacen.guardar([local({ id: "a", enlace: { texto: "Ver la obra", ruta: "/obras/1" } })]);
    await almacen.guardar([local({ id: "b", enlace: { texto: "Fuera", ruta: "https://ejemplo.com" } })]);
    const cuerpos = pedir.mock.calls.filter(([, op]) => op?.metodo === "POST" && op.cuerpo && "titulo" in op.cuerpo).map(([, op]) => op!.cuerpo);
    expect(cuerpos[0]).toEqual({ gravedad: "listo", titulo: "Versión V2 guardada", detalle: "", enlace: { texto: "Ver la obra", ruta: "/obras/1" } });
    expect(cuerpos[1]).toEqual({ gravedad: "listo", titulo: "Versión V2 guardada", detalle: "" });
  });
});
