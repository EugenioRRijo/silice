import { describe, expect, test } from "vitest";
import {
  DIAS_DE_RETENCION,
  DURACION_CONFIRMACION_MS,
  agruparPorDia,
  contarSinLeer,
  descartarVencidas,
  duracionDeNotificacion,
  gravedadEnPalabra,
  horaDeNotificacion,
  marcarTodasComoLeidas,
  textoDeAnuncio,
} from "./modelo";
import type { Notificacion } from "./modelo";

function crearNotificacion(parcial: Partial<Notificacion> & Pick<Notificacion, "id" | "titulo">): Notificacion {
  return {
    gravedad: "info",
    creada: "2026-11-26T10:00:00-04:00",
    leida: false,
    ...parcial,
  };
}

describe("modelo de notificaciones", () => {
  test("traduce cada gravedad a su palabra en español", () => {
    expect(gravedadEnPalabra("listo")).toBe("Listo");
    expect(gravedadEnPalabra("info")).toBe("Información");
    expect(gravedadEnPalabra("advertencia")).toBe("Advertencia");
    expect(gravedadEnPalabra("error")).toBe("Error");
  });

  test("fija 180.000 ms para listo e info, y permanencia hasta cerrar para advertencia y error", () => {
    expect(DURACION_CONFIRMACION_MS).toBe(180_000);
    expect(duracionDeNotificacion("listo")).toBe(180_000);
    expect(duracionDeNotificacion("info")).toBe(180_000);
    expect(duracionDeNotificacion("advertencia")).toBeNull();
    expect(duracionDeNotificacion("error")).toBeNull();
  });

  test("cuenta las notificaciones sin leer y marca todas como leídas sin mutar la entrada", () => {
    const original: Notificacion[] = [
      crearNotificacion({ id: "1", titulo: "Versión V2 guardada", gravedad: "listo", leida: false }),
      crearNotificacion({ id: "2", titulo: "Auditoría terminada", gravedad: "info", leida: true }),
      crearNotificacion({ id: "3", titulo: "Precio vencido", gravedad: "advertencia", leida: false }),
    ];

    expect(contarSinLeer(original)).toBe(2);
    expect(contarSinLeer([])).toBe(0);

    const leidas = marcarTodasComoLeidas(original);
    expect(contarSinLeer(leidas)).toBe(0);
    expect(leidas.every((n) => n.leida)).toBe(true);
    expect(original[0]?.leida).toBe(false);
    expect(original[2]?.leida).toBe(false);
  });

  test("descarta las notificaciones de más de 30 días y conserva la de exactamente 30 días", () => {
    expect(DIAS_DE_RETENCION).toBe(30);
    const ahora = new Date("2026-11-26T12:00:00.000Z");
    const hace30Exactos = new Date(ahora.getTime() - 30 * 24 * 60 * 60 * 1_000).toISOString();
    const hace30YUnSegundo = new Date(ahora.getTime() - (30 * 24 * 60 * 60 * 1_000 + 1_000)).toISOString();
    const hace45Dias = "2026-10-12T12:00:00.000Z";

    const lista: Notificacion[] = [
      crearNotificacion({ id: "reciente", titulo: "Reciente", creada: "2026-11-26T10:00:00.000Z" }),
      crearNotificacion({ id: "limite", titulo: "En el límite de 30 días", creada: hace30Exactos }),
      crearNotificacion({ id: "vencida-1", titulo: "Pasada por 1 s", creada: hace30YUnSegundo }),
      crearNotificacion({ id: "vencida-2", titulo: "De hace 45 días", creada: hace45Dias }),
    ];

    const vigentes = descartarVencidas(lista, ahora);
    expect(vigentes.map((n) => n.id)).toEqual(["reciente", "limite"]);
  });

  test("agrupa por Hoy, Ayer y fecha dd/mm/aaaa en orden descendente", () => {
    const ahora = new Date(2026, 10, 26, 15, 30, 0);
    const hoyTemprano = new Date(2026, 10, 26, 8, 30, 0).toISOString();
    const hoyTarde = new Date(2026, 10, 26, 10, 42, 0).toISOString();
    const ayerManana = new Date(2026, 10, 25, 11, 20, 0).toISOString();
    const ayerTarde = new Date(2026, 10, 25, 16, 5, 0).toISOString();
    const anterior = new Date(2026, 10, 18, 9, 15, 0).toISOString();

    const grupos = agruparPorDia(
      [
        crearNotificacion({ id: "a", titulo: "Antigua", creada: anterior }),
        crearNotificacion({ id: "h1", titulo: "Hoy temprano", creada: hoyTemprano }),
        crearNotificacion({ id: "y1", titulo: "Ayer mañana", creada: ayerManana }),
        crearNotificacion({ id: "h2", titulo: "Hoy más reciente", creada: hoyTarde }),
        crearNotificacion({ id: "y2", titulo: "Ayer tarde", creada: ayerTarde }),
      ],
      ahora,
    );

    expect(grupos.map((g) => g.etiqueta)).toEqual(["Hoy", "Ayer", "18/11/2026"]);
    expect(grupos[0]?.items.map((n) => n.id)).toEqual(["h2", "h1"]);
    expect(grupos[1]?.items.map((n) => n.id)).toEqual(["y2", "y1"]);
    expect(grupos[2]?.items.map((n) => n.id)).toEqual(["a"]);
  });

  test("extrae la hora HH:MM de una marca ISO con hora y deja vacía una fecha sola", () => {
    const marca = new Date(2026, 10, 26, 9, 5, 0).toISOString();
    expect(horaDeNotificacion(marca)).toBe("09:05");
    expect(horaDeNotificacion("2026-11-26")).toBe("");
  });

  test("arma el texto de anuncio con gravedad, título, detalle y acción disponible sin nombrar el botón Cerrar", () => {
    const simple = textoDeAnuncio({
      gravedad: "listo",
      titulo: "Versión V2 guardada",
      detalle: "Vialidad Tramo 3",
    });
    expect(simple).toBe("Listo: Versión V2 guardada. Vialidad Tramo 3");
    expect(simple).not.toMatch(/Cerrar/i);

    const conEnlace = textoDeAnuncio({
      gravedad: "advertencia",
      titulo: "Precio vencido",
      detalle: "El aditivo venció el 31/10/2026.",
      enlace: { texto: "Ver en Precios de la empresa", ruta: "/precios/empresa" },
    });
    expect(conEnlace).toBe("Advertencia: Precio vencido. El aditivo venció el 31/10/2026. Acción disponible.");
  });
});
