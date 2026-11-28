import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import {
  useModoEfectivo,
  valorParaDibujar,
  PALETA_GRAFICOS,
  coloresDeSerie,
  escalaDeColor,
  formatoNumeroEsVe,
  fusionarOpciones,
  opcionesBase,
  slotsPorGrupo,
  slotsPorRol,
} from "./paletaGraficos";

function matiz(hex: string): number | null {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255) as [number, number, number];
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  if (max - min < 0.05) return null; // gris
  const d = max - min;
  const h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return (h * 60 + 360) % 360;
}

describe("paleta de los graficos (azul, aguamarina y naranja validados; el resto, neutros)", () => {
  test("ningun color de ningun modo cae en el morado, reservado para los atipicos", () => {
    const todos = [...PALETA_GRAFICOS, ...Object.values(coloresDeSerie("claro")), ...Object.values(coloresDeSerie("oscuro"))];
    for (const hex of todos) {
      const h = matiz(hex);
      if (h !== null) expect(h < 255 || h > 330, `${hex} (matiz ${h})`).toBe(true);
    }
  });

  test("claro y oscuro dan los pasos de su modo", () => {
    expect(coloresDeSerie("claro")).toMatchObject({ serie1: "#2A78D6", serie2: "#1BAF7A", serie3: "#EB6834", neutro: "#9A9184" });
    expect(coloresDeSerie("oscuro")).toMatchObject({ serie1: "#3987E5", serie2: "#199E70", serie3: "#D95926", neutro: "#8A847A" });
  });

  test("el mismo nombre de serie da el mismo color aunque un filtro quite a las demas", () => {
    const catalogo = ["Cemento", "Acero", "Arena"];
    const completo = slotsPorGrupo(catalogo, catalogo);
    const filtrado = slotsPorGrupo(["Arena"], catalogo);
    expect(filtrado["Arena"]).toBe(completo["Arena"]);
    for (const modo of ["claro", "oscuro"] as const) {
      expect(escalaDeColor(modo, filtrado).scale["Arena"]).toBe(escalaDeColor(modo, completo).scale["Arena"]);
    }
  });

  test("sin catalogo los grupos toman los colores en orden y vuelven al inicio si son muchos", () => {
    const grupos = Array.from({ length: PALETA_GRAFICOS.length + 2 }, (_, i) => `g${i}`);
    const slots = slotsPorGrupo(grupos);
    expect(Object.keys(slots)).toEqual(grupos);
    expect(slots["g0"]).toBe("serie1");
    expect(slots[`g${PALETA_GRAFICOS.length}`]).toBe("serie1");
    expect(escalaDeColor("claro", slots).scale["g0"]).toBe(PALETA_GRAFICOS[0]);
  });

  test("por rol: lo real es la serie 1, lo gastado la 2, el pronostico la 3 y el plan es neutro, vengan las que vengan", () => {
    const todas = slotsPorRol([
      { nombre: "PV", rol: "plan" },
      { nombre: "EV", rol: "real" },
      { nombre: "AC", rol: "gastado" },
      { nombre: "EAC", rol: "pronostico" },
    ]);
    expect(todas).toEqual({ PV: "neutro", EV: "serie1", AC: "serie2", EAC: "serie3" });
    const sinGastado = slotsPorRol([
      { nombre: "PV", rol: "plan" },
      { nombre: "EV", rol: "real" },
      { nombre: "EAC", rol: "pronostico" },
    ]);
    expect(sinGastado["EAC"]).toBe("serie3");
    expect(sinGastado["EV"]).toBe("serie1");
  });

  test("una segunda serie del mismo rol no repite el color de la primera", () => {
    const slots = slotsPorRol([
      { nombre: "EV-1", rol: "real" },
      { nombre: "EV-2", rol: "real" },
    ]);
    expect(slots["EV-1"]).toBe("serie1");
    expect(slots["EV-2"]).not.toBe("serie1");
  });

  // T4 (mutante P3): la repetida va al neutro oscuro, no al neutro del plan, que otra serie puede estar usando.
  test("la segunda serie de un rol toma el neutro oscuro, distinto del neutro del plan", () => {
    const reales = slotsPorRol([
      { nombre: "EV-1", rol: "real" },
      { nombre: "EV-2", rol: "real" },
    ]);
    expect(reales["EV-2"]).toBe("neutro2");
    const planes = slotsPorRol([
      { nombre: "PV-1", rol: "plan" },
      { nombre: "PV-2", rol: "plan" },
    ]);
    expect(planes).toEqual({ "PV-1": "neutro", "PV-2": "neutro2" });
  });

  // T4 (mutante P4): un grupo que el catálogo no trae sigue a los del catálogo, no los pisa desde el principio.
  test("un grupo fuera del catálogo toma el lugar siguiente al último del catálogo", () => {
    const catalogo = ["Cemento", "Acero"];
    expect(slotsPorGrupo(["Zinc"], catalogo)).toEqual({ Zinc: "serie3" });
    expect(slotsPorGrupo(["Zinc", "Cobre"], catalogo)).toEqual({ Zinc: "serie3", Cobre: "neutro" });
  });
});

describe("useModoEfectivo", () => {
  afterEach(() => {
    delete document.documentElement.dataset.modo;
  });

  // T4 (mutante P7): un cambio de modo hecho en otro lugar de la pestaña (el selector pone `data-modo` en <html>) llega a
  // los gráficos que ya estaban montados.
  test("sigue el atributo data-modo de <html> cuando cambia con el gráfico ya montado", async () => {
    document.documentElement.dataset.modo = "claro";
    const { result } = renderHook(() => useModoEfectivo());
    expect(result.current).toBe("claro");
    act(() => {
      document.documentElement.dataset.modo = "oscuro";
    });
    await waitFor(() => expect(result.current).toBe("oscuro"));
  });
});

describe("opciones base de Carbon Charts", () => {
  test("el tema sigue al modo", () => {
    expect(opcionesBase("claro").theme).toBe("white");
    expect(opcionesBase("oscuro").theme).toBe("g100");
  });

  test("la escala de color lleva el color de cada serie en el modo pedido", () => {
    const colores = { PV: "neutro", EV: "serie1" } as const;
    expect(opcionesBase("claro", { colores }).color?.scale).toEqual({ PV: "#9A9184", EV: "#2A78D6" });
    expect(opcionesBase("oscuro", { colores }).color?.scale).toEqual({ PV: "#8A847A", EV: "#3987E5" });
  });

  test("la barra de herramientas va apagada y la cuadricula es solo la horizontal", () => {
    const o = opcionesBase("claro");
    expect(o.toolbar).toEqual({ enabled: false });
    expect(o.grid?.x?.enabled).toBe(false);
    expect(o.grid?.y?.enabled).toBe(true);
    expect(opcionesBase("claro", { ejes: false }).grid).toBeUndefined();
  });

  test("la leyenda esta presente con dos o mas series y no con una", () => {
    expect(opcionesBase("claro", { series: 1 }).legend?.enabled).toBe(false);
    expect(opcionesBase("claro", { series: 2 }).legend?.enabled).toBe(true);
    expect(opcionesBase("claro", { series: 4 }).legend?.enabled).toBe(true);
  });

  test("el globo y los ejes escriben las cifras con coma decimal y punto de miles", () => {
    expect(opcionesBase("claro").tooltip?.valueFormatter?.(95066.6, "PV")).toBe("95.066,6");
    expect(formatoNumeroEsVe(1234567)).toBe("1.234.567");
    expect(formatoNumeroEsVe("4358.20")).toBe("4.358,20");
  });
});

describe("fusionarOpciones", () => {
  test("lo propio manda, lo anidado se mezcla y la base no se toca", () => {
    const base = { toolbar: { enabled: false }, legend: { enabled: true, position: "bottom" }, theme: "white" };
    const fusion = fusionarOpciones(base, { legend: { enabled: false }, height: "320px" });
    expect(fusion).toEqual({ toolbar: { enabled: false }, legend: { enabled: false, position: "bottom" }, theme: "white", height: "320px" });
    expect(base.legend).toEqual({ enabled: true, position: "bottom" });
  });
});

describe("valorParaDibujar: la cifra del servidor pasa a geometría, nunca a texto", () => {
  test("lee el decimal con punto que manda la API y no redondea", () => {
    expect(valorParaDibujar("1234.5678")).toBe(1234.5678);
    expect(valorParaDibujar("-12.5")).toBe(-12.5);
  });
  test("un texto que no es cifra no se dibuja (NaN), no se inventa un cero", () => {
    expect(valorParaDibujar("")).toBeNaN();
    expect(valorParaDibujar("1.234,56")).toBeNaN();
  });
});
