import { describe, expect, test } from "vitest";
import {
  accionesEnTexto,
  cifrasEnLista,
  conMayuscula,
  eventosDelDia,
  fechaVe,
  filtrarEventos,
  moverFoco,
  nivelesPorCuantiles,
  nombreDeCelda,
  rotulosDeMeses,
  semanas,
  sumarDias,
} from "./logica";
import type { DiaDeActividad, EventoDeActividad } from "./logica";

// Oráculos a mano. Calendario: el 1 de octubre de 2026 cae jueves y el 31, sábado (el 26 de noviembre de 2026 es jueves
// y entre uno y otro hay 56 días, ocho semanas justas).

const dias = (...cuantos: number[]): DiaDeActividad[] => cuantos.map((n, i) => ({ fecha: sumarDias("2026-10-01", i), cuantos: n }));

describe("niveles por cuantiles", () => {
  test("sin actividad es el nivel 0, y con ella los cuartiles de los días con actividad dan 1 a 4", () => {
    // 1..8: los cortes (rango más cercano) son 2, 4 y 6.
    const nivel = nivelesPorCuantiles(dias(1, 2, 3, 4, 5, 6, 7, 8, 0, 0));
    expect([0, 1, 2, 3, 4, 5, 6, 7, 8].map(nivel)).toEqual([0, 1, 1, 2, 2, 3, 3, 4, 4]);
  });

  test("los días sin actividad no cuentan para los cortes", () => {
    const con = nivelesPorCuantiles(dias(1, 2, 3, 4, 5, 6, 7, 8));
    const sin = nivelesPorCuantiles(dias(1, 2, 3, 4, 5, 6, 7, 8, 0, 0, 0, 0, 0, 0, 0, 0));
    expect([1, 3, 5, 8].map(sin)).toEqual([1, 3, 5, 8].map(con));
  });

  test("si todos los días valen lo mismo, todos quedan en el nivel 1", () => {
    const nivel = nivelesPorCuantiles(dias(3, 3, 3, 0));
    expect([0, 3].map(nivel)).toEqual([0, 1]);
  });

  test("un día solo con actividad es el nivel 1", () => {
    expect(nivelesPorCuantiles(dias(5))(5)).toBe(1);
  });

  test("un día muy por encima de los demás es el nivel 4 y los demás no", () => {
    const nivel = nivelesPorCuantiles(dias(1, 1, 1, 20));
    expect([1, 20].map(nivel)).toEqual([1, 4]);
  });

  test("sin ningún día, todo es nivel 0", () => {
    expect(nivelesPorCuantiles([])(0)).toBe(0);
  });
});

describe("semanas del calendario", () => {
  test("octubre de 2026: cinco semanas de lunes a domingo, con huecos fuera del período", () => {
    const columnas = semanas("2026-10-01", "2026-10-31");
    expect(columnas).toHaveLength(5);
    expect(columnas[0]).toEqual([null, null, null, "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04"]);
    expect(columnas[1]).toEqual(["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09", "2026-10-10", "2026-10-11"]);
    expect(columnas[4]).toEqual(["2026-10-26", "2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30", "2026-10-31", null]);
  });

  test("cada día del período sale una sola vez y en orden", () => {
    const todos = semanas("2025-11-28", "2026-11-26")
      .flat()
      .filter((d): d is string => d !== null);
    expect(todos).toHaveLength(364);
    expect(todos[0]).toBe("2025-11-28");
    expect(todos[363]).toBe("2026-11-26");
    expect(new Set(todos).size).toBe(364);
    expect([...todos].sort()).toEqual(todos);
  });

  test("cruza el fin de año sin perder ni repetir días", () => {
    const todos = semanas("2026-12-28", "2027-01-03")
      .flat()
      .filter((d): d is string => d !== null);
    expect(todos).toEqual(["2026-12-28", "2026-12-29", "2026-12-30", "2026-12-31", "2027-01-01", "2027-01-02", "2027-01-03"]);
  });

  test("un solo día es una semana con un solo lugar", () => {
    const columnas = semanas("2026-10-21", "2026-10-21");
    expect(columnas).toEqual([[null, null, "2026-10-21", null, null, null, null]]);
  });

  test("un período al revés no tiene semanas", () => {
    expect(semanas("2026-10-31", "2026-10-01")).toEqual([]);
  });
});

describe("rótulos de los meses", () => {
  test("un mes solo, un rótulo en su primera semana", () => {
    expect(rotulosDeMeses(semanas("2026-10-01", "2026-10-31"))).toEqual([{ semana: 0, mes: "oct" }]);
  });

  test("cada mes cambia en la primera semana que empieza en él", () => {
    expect(rotulosDeMeses(semanas("2026-10-01", "2026-12-06"))).toEqual([
      { semana: 0, mes: "oct" },
      { semana: 5, mes: "nov" },
    ]);
  });

  test("un mes que solo asoma en la última semana no lleva rótulo", () => {
    expect(rotulosDeMeses(semanas("2026-10-01", "2026-11-02"))).toEqual([{ semana: 0, mes: "oct" }]);
  });

  // T3 (2026-11-28): en el calendario de un año que empieza el 29/11/2025 «nov» (una sola columna) y «dic» (la siguiente)
  // se dibujaban pegadas. Cada rótulo mide unas tres columnas: si el mes siguiente empieza antes, el mes que apenas
  // asomaba cede su rótulo; y si al último no le quedan tres columnas, no se dibuja (se saldría de la caja).
  test("el mes que asoma una sola columna al principio cede su rótulo al siguiente (nov y dic no se tocan)", () => {
    expect(rotulosDeMeses(semanas("2025-11-29", "2026-01-31"))).toEqual([
      { semana: 1, mes: "dic" },
      { semana: 6, mes: "ene" },
    ]);
  });

  test("un mes que empieza con menos de tres columnas hasta el final no lleva rótulo", () => {
    // Del 1/10 al 12/11/2026: 7 columnas; «nov» empieza en la 6.ª (índice 5) y solo le quedan dos.
    expect(rotulosDeMeses(semanas("2026-10-01", "2026-11-12"))).toEqual([{ semana: 0, mes: "oct" }]);
  });

  test("en un año entero, dos rótulos nunca están a menos de tres columnas y el último cabe", () => {
    const columnas = semanas("2025-11-29", "2026-11-28");
    const rotulos = rotulosDeMeses(columnas);
    expect(columnas).toHaveLength(53);
    expect(rotulos.map((r) => r.mes)).toEqual(["dic", "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov"]);
    rotulos.forEach((r, i) => {
      if (i > 0) expect(r.semana - rotulos[i - 1]!.semana).toBeGreaterThanOrEqual(3);
    });
    expect(columnas.length - rotulos[rotulos.length - 1]!.semana).toBeGreaterThanOrEqual(3);
  });

  test("sin semanas no hay rótulos", () => {
    expect(rotulosDeMeses([])).toEqual([]);
  });
});

describe("fechas y textos", () => {
  test("sumarDias pasa de un año al otro y vuelve", () => {
    expect(sumarDias("2026-12-31", 1)).toBe("2027-01-01");
    expect(sumarDias("2027-01-01", -1)).toBe("2026-12-31");
    expect(sumarDias("2026-03-01", -1)).toBe("2026-02-28");
  });

  test("las fechas van como dd/mm/aaaa, con la hora si la traen", () => {
    expect(fechaVe("2026-10-19")).toBe("19/10/2026");
    expect(fechaVe("2026-10-19T09:05:00")).toBe("19/10/2026 09:05");
  });

  test("el nombre de una celda dice la fecha y cuántas acciones", () => {
    expect(nombreDeCelda("2026-10-19", 2)).toBe("19/10/2026: 2 acciones");
    expect(nombreDeCelda("2026-10-19", 1)).toBe("19/10/2026: 1 acción");
    expect(nombreDeCelda("2026-10-19", 0)).toBe("19/10/2026: sin actividad");
    expect(accionesEnTexto(0)).toBe("sin actividad");
  });

  test("la primera letra del texto va en mayúscula, con tilde incluida", () => {
    expect(conMayuscula("guardó la versión V2")).toBe("Guardó la versión V2");
    expect(conMayuscula("")).toBe("");
  });
});

const EVENTOS: EventoDeActividad[] = [
  { fecha: "2026-10-20T15:00:00", tipo: "auditoria", obra: "", archivo: "A.xlsx", texto: "auditó A.xlsx: 3 errores" },
  { fecha: "2026-10-19T10:00:00", tipo: "version_enviada", obra: "Obra", archivo: "", texto: "envió la versión V1 de Obra a aprobación" },
  { fecha: "2026-10-19T09:00:00", tipo: "version_guardada", obra: "Obra", archivo: "", texto: "guardó la versión V1 de Obra" },
];

describe("eventos", () => {
  test("filtrar por tipo conserva el orden; sin tipo trae todos", () => {
    expect(filtrarEventos(EVENTOS, null)).toEqual(EVENTOS);
    expect(filtrarEventos(EVENTOS, "auditoria").map((e) => e.archivo)).toEqual(["A.xlsx"]);
    expect(filtrarEventos(EVENTOS, "dictamen")).toEqual([]);
  });

  test("los eventos de un día son los de esa fecha", () => {
    expect(eventosDelDia(EVENTOS, "2026-10-19").map((e) => e.tipo)).toEqual(["version_enviada", "version_guardada"]);
    expect(eventosDelDia(EVENTOS, "2026-10-21")).toEqual([]);
  });

  test("las cifras salen en el orden de la lista de tipos, con su etiqueta", () => {
    expect(cifrasEnLista({ versiones_guardadas: 1, versiones_enviadas: 2, dictamenes: 3, auditorias: 4 })).toEqual([
      { tipo: "version_guardada", etiqueta: "Versiones guardadas", cuantos: 1 },
      { tipo: "version_enviada", etiqueta: "Versiones enviadas", cuantos: 2 },
      { tipo: "dictamen", etiqueta: "Dictámenes", cuantos: 3 },
      { tipo: "auditoria", etiqueta: "Auditorías", cuantos: 4 },
    ]);
  });
});

describe("moverse por el calendario con las flechas", () => {
  test("izquierda y derecha cambian de semana; arriba y abajo, de día", () => {
    expect(moverFoco("2026-10-14", "ArrowLeft", "2026-10-01", "2026-10-31")).toBe("2026-10-07");
    expect(moverFoco("2026-10-14", "ArrowRight", "2026-10-01", "2026-10-31")).toBe("2026-10-21");
    expect(moverFoco("2026-10-14", "ArrowUp", "2026-10-01", "2026-10-31")).toBe("2026-10-13");
    expect(moverFoco("2026-10-14", "ArrowDown", "2026-10-01", "2026-10-31")).toBe("2026-10-15");
  });

  test("no sale del período: se queda en el primero o en el último día", () => {
    expect(moverFoco("2026-10-03", "ArrowLeft", "2026-10-01", "2026-10-31")).toBe("2026-10-01");
    expect(moverFoco("2026-10-29", "ArrowRight", "2026-10-01", "2026-10-31")).toBe("2026-10-31");
  });

  test("otra tecla no mueve nada", () => {
    expect(moverFoco("2026-10-14", "Enter", "2026-10-01", "2026-10-31")).toBe("2026-10-14");
  });
});
