import { describe, expect, test } from "vitest";
import { MENSAJE_CIFRA, MENSAJE_CIFRA_VACIA } from "../../../indicadores/cifraEscrita";
import { vistaPresupuesto } from "../datosDePrueba";
import type { Resumen } from "../logica";
import {
  AYUDA_CANTIDAD,
  CANTIDAD_DEL_CALCULO,
  ELEGIR_DE_LA_LISTA,
  RECARGADO,
  SIN_ERRORES,
  anuncioDePartidaAgregada,
  ayudaDeCantidad,
  descripcionParaParecidas,
  estadoInicialDeAlta,
  etiquetaDeCantidad,
  leerPartidaAgregada,
  resumenDeCalculoYNota,
  rotuloCrearPartida,
  siguiente,
  solicitudDeCreacion,
  textoDePartidaElegida,
} from "./altaDePartida";
import type { EstadoDeAlta, EventoDeAlta, PartidaElegida } from "./altaDePartida";

// Oráculos escritos a mano según la ficha de B1 (§1.6, §1.8, §1.10 puntos 4 y 5, lote B1-8) y `AgregarPartida.test.tsx`.

const PARED: PartidaElegida = {
  codigo: "OBRA-04",
  descripcion: "Pared de bloques de arcilla de 15 cm",
  unidad: "m2",
};

function resumenFicticio(extra: Partial<Resumen> = {}): Resumen {
  const base = vistaPresupuesto();
  return {
    rev: 1,
    moneda: base.moneda,
    total: base.total,
    cambios: 1,
    pendientes_catalogo: 0,
    hallazgos: [],
    hay_plan: false,
    version_mas_nueva: null,
    guardado_como: null,
    espacio_vacio: true,
    ...extra,
  };
}

describe("estadoInicialDeAlta y contrato de la unión discriminada", () => {
  test("arranca en editando, vacío, con el pliegue cerrado y sin partida inicial", () => {
    expect(estadoInicialDeAlta()).toEqual({
      fase: "editando",
      texto: "",
      elegida: null,
      cantidad: "",
      calculo: "",
      nota: "",
      calculoVisto: false,
      pliegueAbierto: false,
      reinicios: 0,
    });
  });

  test("con partidaInicial arranca con la partida elegida y su texto en formato código · descripción", () => {
    expect(
      estadoInicialDeAlta({ codigo: "Z-99", descripcion: "Zanja ficticia", unidad: "m3" }),
    ).toEqual({
      fase: "editando",
      texto: "Z-99 · Zanja ficticia",
      elegida: { codigo: "Z-99", descripcion: "Zanja ficticia", unidad: "m3" },
      cantidad: "",
      calculo: "",
      nota: "",
      calculoVisto: false,
      pliegueAbierto: false,
      reinicios: 0,
    });

    expect(
      estadoInicialDeAlta({ codigo: "Z-01", descripcion: "", unidad: "" }).elegida,
    ).toEqual({ codigo: "Z-01", descripcion: "", unidad: null });
  });

  test("un estado ilegal no compila en TypeScript", () => {
    const base = {
      texto: "",
      elegida: null,
      cantidad: "",
      calculo: "",
      nota: "",
      calculoVisto: false,
      pliegueAbierto: false,
      reinicios: 0,
    };
    const editandoConErrores: EstadoDeAlta = {
      ...base,
      fase: "editando",
      // @ts-expect-error: la fase editando no admite errores
      errores: SIN_ERRORES,
    };
    // @ts-expect-error: la fase error exige errores
    const errorSinErrores: EstadoDeAlta = {
      ...base,
      fase: "error",
    };
    const enviandoConErrores: EstadoDeAlta = {
      ...base,
      fase: "enviando",
      // @ts-expect-error: la fase enviando no admite errores
      errores: SIN_ERRORES,
    };

    expect([editandoConErrores, errorSinErrores, enviandoConErrores]).toHaveLength(3);
  });
});

describe("funciones puras auxiliares de la fila de alta", () => {
  test("formatea texto elegido, etiqueta de cantidad con unidad escrita y ayuda de cálculo", () => {
    expect(textoDePartidaElegida(PARED)).toBe("OBRA-04 · Pared de bloques de arcilla de 15 cm");
    expect(textoDePartidaElegida({ codigo: "Z-99", descripcion: "   " })).toBe("Z-99");

    expect(etiquetaDeCantidad(null)).toBe("Cantidad");
    expect(etiquetaDeCantidad({ codigo: "A", descripcion: "B", unidad: null })).toBe("Cantidad");
    expect(etiquetaDeCantidad(PARED)).toBe("Cantidad (m²)");
    expect(etiquetaDeCantidad({ codigo: "Z-99", descripcion: "Zanja", unidad: "m3" })).toBe("Cantidad (m³)");

    expect(ayudaDeCantidad(false, "6*35", "")).toBe(AYUDA_CANTIDAD);
    expect(ayudaDeCantidad(true, "", "")).toBe(AYUDA_CANTIDAD);
    expect(ayudaDeCantidad(true, "6*35", "10")).toBe(AYUDA_CANTIDAD);
    expect(ayudaDeCantidad(true, "6*35", "")).toBe(`${CANTIDAD_DEL_CALCULO} ${AYUDA_CANTIDAD}`);
  });

  test("resumen del pliegue «Cálculo y nota» refleja el estado por omisión y lo escrito", () => {
    expect(resumenDeCalculoYNota("", "")).toBe("Cálculo y nota (opcional): Sin cálculo ni nota. Cambiar");
    expect(resumenDeCalculoYNota("  ", "  ")).toBe("Cálculo y nota (opcional): Sin cálculo ni nota. Cambiar");
    expect(resumenDeCalculoYNota("6*3-2", "")).toBe("Cálculo y nota (opcional): 6*3-2. Cambiar");
    expect(resumenDeCalculoYNota("", "Muro norte")).toBe("Cálculo y nota (opcional): con nota de medición. Cambiar");
    expect(resumenDeCalculoYNota("6*3-2", "Muro norte")).toBe(
      "Cálculo y nota (opcional): 6*3-2 y nota de medición. Cambiar",
    );
  });

  test("distingue código y descripción para crear partida (D4) y elige la descripción para parecidas", () => {
    expect(rotuloCrearPartida("friso de pared")).toBe("Crear la partida «friso de pared»");
    expect(solicitudDeCreacion("friso de pared")).toEqual({ codigo: "", descripcion: "friso de pared" });
    expect(solicitudDeCreacion("Z-99")).toEqual({ codigo: "Z-99", descripcion: "" });

    expect(descripcionParaParecidas(PARED, "OBRA-04 · Pared de bloques de arcilla de 15 cm")).toBe(
      "Pared de bloques de arcilla de 15 cm",
    );
    expect(descripcionParaParecidas({ codigo: "X-1", descripcion: "", unidad: null }, "texto")).toBe("texto");
    expect(descripcionParaParecidas(null, "excavación de zanja")).toBe("excavación de zanja");
  });

  test("anuncioDePartidaAgregada formatea el total del servidor en es-VE y agrega el aviso si existe", () => {
    const r = resumenFicticio({ total: { texto: "2703.86", exacto: "2703.86023" }, moneda: "USD" });
    expect(anuncioDePartidaAgregada("FRI-01", r, null)).toBe(
      "Se agregó FRI-01 al presupuesto. Total: 2.703,86 USD.",
    );
    expect(anuncioDePartidaAgregada("FRI-01", { ...r, moneda: "" }, null)).toBe(
      "Se agregó FRI-01 al presupuesto. Total: 2.703,86.",
    );
    expect(anuncioDePartidaAgregada("OBRA-04", r, "Queda pendiente sin precio.")).toBe(
      "Se agregó OBRA-04 al presupuesto. Total: 2.703,86 USD. Queda pendiente sin precio.",
    );
  });

  test("leerPartidaAgregada valida la respuesta del servidor y rechaza datos mal formados", () => {
    const r = resumenFicticio();
    expect(leerPartidaAgregada({ rev: 2, resumen: r, clave: "FRI-01|a-mano:1" })).toEqual({
      rev: 2,
      resumen: r,
      clave: "FRI-01|a-mano:1",
      aviso: null,
    });
    expect(leerPartidaAgregada({ rev: 2, resumen: r, clave: "FRI-01|a-mano:1", aviso: "Pendiente" })).toEqual({
      rev: 2,
      resumen: r,
      clave: "FRI-01|a-mano:1",
      aviso: "Pendiente",
    });
    expect(() => leerPartidaAgregada({ rev: 2, resumen: r, clave: "" })).toThrow();
    expect(() => leerPartidaAgregada(null)).toThrow();
  });
});

describe("máquina siguiente: validación local, envío, doble clic y limpieza tras éxito", () => {
  test("sin partida elegida no manda nada, marca error en Partida, enfoca errores y conserva lo escrito", () => {
    let estado = estadoInicialDeAlta();
    estado = siguiente(estado, { tipo: "cambiarTextoPartida", texto: "bloq" }).estado;
    estado = siguiente(estado, { tipo: "cambiarCantidad", valor: "210" }).estado;
    estado = siguiente(estado, { tipo: "cambiarCalculo", valor: "6*35" }).estado;
    estado = siguiente(estado, { tipo: "cambiarNota", valor: "muro" }).estado;

    const transicion = siguiente(estado, { tipo: "enviar" });
    expect(transicion.efecto).toEqual({ tipo: "enfocarErrores" });
    expect(transicion.estado.fase).toBe("error");
    if (transicion.estado.fase === "error") {
      expect(transicion.estado.errores).toEqual({ ...SIN_ERRORES, partida: ELEGIR_DE_LA_LISTA });
    }
    expect(transicion.estado.texto).toBe("bloq");
    expect(transicion.estado.cantidad).toBe("210");
    expect(transicion.estado.calculo).toBe("6*35");
    expect(transicion.estado.nota).toBe("muro");
  });

  test("con partida elegida, sin cantidad ni cálculo, marca Cantidad sin enviar", () => {
    let estado = estadoInicialDeAlta();
    estado = siguiente(estado, { tipo: "elegirPartida", partida: PARED }).estado;
    // Espacios no válidos (incluyendo NBSP) siguen contando como vacíos, igual que el servidor.
    estado = siguiente(estado, { tipo: "cambiarCantidad", valor: " \u00a0 " }).estado;

    const transicion = siguiente(estado, { tipo: "enviar" });
    expect(transicion.efecto).toEqual({ tipo: "enfocarErrores" });
    expect(transicion.estado.fase).toBe("error");
    if (transicion.estado.fase === "error") {
      expect(transicion.estado.errores).toEqual({ ...SIN_ERRORES, cantidad: MENSAJE_CIFRA_VACIA });
    }
  });

  test("con partida y cálculo sin cantidad, permite enviar el POST tal cual", () => {
    let estado = estadoInicialDeAlta();
    estado = siguiente(estado, { tipo: "elegirPartida", partida: PARED }).estado;
    estado = siguiente(estado, { tipo: "cambiarCalculo", valor: "2,5*84" }).estado;
    estado = siguiente(estado, { tipo: "cambiarNota", valor: "6 m × 35 m" }).estado;

    const transicion = siguiente(estado, { tipo: "enviar" });
    expect(transicion.estado.fase).toBe("enviando");
    expect(transicion.efecto).toEqual({
      tipo: "postPartida",
      partida: { codigo: "OBRA-04", cantidad: "", calculo: "2,5*84", nota: "6 m × 35 m" },
    });
  });

  test("un segundo clic (evento enviar mientras está enviando) no manda un segundo POST", () => {
    let estado = estadoInicialDeAlta();
    estado = siguiente(estado, { tipo: "elegirPartida", partida: PARED }).estado;
    estado = siguiente(estado, { tipo: "cambiarCantidad", valor: "50" }).estado;

    const primero = siguiente(estado, { tipo: "enviar" });
    expect(primero.estado.fase).toBe("enviando");
    expect(primero.efecto?.tipo).toBe("postPartida");

    const segundo = siguiente(primero.estado, { tipo: "enviar" });
    expect(segundo.estado).toBe(primero.estado);
    expect(segundo.efecto).toBeNull();

    // Tampoco se alteran los campos mientras la petición está en vuelo.
    const eventosIgnorados: EventoDeAlta[] = [
      { tipo: "cambiarTextoPartida", texto: "otra" },
      { tipo: "cambiarCantidad", valor: "99" },
      { tipo: "cambiarCalculo", valor: "1+1" },
      { tipo: "cambiarNota", valor: "nota" },
      { tipo: "elegirPartida", partida: PARED },
    ];
    for (const ev of eventosIgnorados) {
      expect(siguiente(primero.estado, ev)).toEqual({ estado: primero.estado, efecto: null });
    }
  });

  test("al recibir éxito, limpia los campos, cierra el pliegue e incrementa reinicios", () => {
    let estado = estadoInicialDeAlta();
    estado = siguiente(estado, { tipo: "elegirPartida", partida: PARED }).estado;
    estado = siguiente(estado, { tipo: "cambiarCantidad", valor: "50" }).estado;
    estado = siguiente(estado, { tipo: "alternarPliegue", abierto: true }).estado;
    estado = siguiente(estado, { tipo: "cambiarCalculo", valor: "10*5" }).estado;
    estado = siguiente(estado, { tipo: "verCalculo" }).estado;
    estado = siguiente(estado, { tipo: "cambiarNota", valor: "nota" }).estado;
    estado = siguiente(estado, { tipo: "enviar" }).estado;

    const fin = siguiente(estado, { tipo: "exito" });
    expect(fin).toEqual({
      estado: {
        fase: "editando",
        texto: "",
        elegida: null,
        cantidad: "",
        calculo: "",
        nota: "",
        calculoVisto: false,
        pliegueAbierto: false,
        reinicios: 1,
      },
      efecto: null,
    });
  });
});

describe("máquina siguiente: manejo de 422, 404, 409 y limpieza de errores al corregir", () => {
  function enviandoCon(cantidad: string, calculo = "", nota = ""): EstadoDeAlta {
    let estado = estadoInicialDeAlta();
    estado = siguiente(estado, { tipo: "elegirPartida", partida: PARED }).estado;
    estado = siguiente(estado, { tipo: "cambiarCantidad", valor: cantidad }).estado;
    if (calculo !== "") estado = siguiente(estado, { tipo: "cambiarCalculo", valor: calculo }).estado;
    if (nota !== "") estado = siguiente(estado, { tipo: "cambiarNota", valor: nota }).estado;
    return siguiente(estado, { tipo: "enviar" }).estado;
  }

  test("422 de cálculo abre el pliegue, conserva todo escrito y enfoca el error", () => {
    const enviando = enviandoCon("15", "6*3-2", "muro");
    const transicion = siguiente(enviando, {
      tipo: "rechazo422",
      detalle: "El cálculo da 16 y la cantidad es 15: corrija uno de los dos.",
    });

    expect(transicion.efecto).toEqual({ tipo: "enfocarErrores" });
    expect(transicion.estado.fase).toBe("error");
    expect(transicion.estado.pliegueAbierto).toBe(true);
    expect(transicion.estado.cantidad).toBe("15");
    expect(transicion.estado.calculo).toBe("6*3-2");
    expect(transicion.estado.nota).toBe("muro");
    expect(transicion.estado.elegida).toEqual(PARED);
    if (transicion.estado.fase === "error") {
      expect(transicion.estado.errores).toEqual({
        ...SIN_ERRORES,
        calculo: "El cálculo da 16 y la cantidad es 15: corrija uno de los dos.",
      });
    }
  });

  test("422 de cantidad marca Cantidad sin borrar lo escrito", () => {
    const enviando = enviandoCon("2.5");
    const transicion = siguiente(enviando, { tipo: "rechazo422", detalle: MENSAJE_CIFRA });

    expect(transicion.efecto).toEqual({ tipo: "enfocarErrores" });
    expect(transicion.estado.fase).toBe("error");
    expect(transicion.estado.cantidad).toBe("2.5");
    expect(transicion.estado.pliegueAbierto).toBe(false);
    if (transicion.estado.fase === "error") {
      expect(transicion.estado.errores).toEqual({ ...SIN_ERRORES, cantidad: MENSAJE_CIFRA });
    }
  });

  test("422 general sin campo específico va a errores.general sin borrar", () => {
    const enviando = enviandoCon("10");
    const transicion = siguiente(enviando, { tipo: "rechazo422", detalle: "No se pudo validar la fila." });

    expect(transicion.efecto).toEqual({ tipo: "enfocarErrores" });
    expect(transicion.estado.fase).toBe("error");
    expect(transicion.estado.cantidad).toBe("10");
    if (transicion.estado.fase === "error") {
      expect(transicion.estado.errores).toEqual({ ...SIN_ERRORES, general: "No se pudo validar la fila." });
    }
  });

  test("404 de partida fuera del catálogo marca Partida y conserva lo escrito", () => {
    const enviando = enviandoCon("210");
    const detalle = "La partida «OBRA-04» no está en el catálogo: compóngala primero en Componer.";
    const transicion = siguiente(enviando, { tipo: "fueraDeCatalogo", detalle });

    expect(transicion.efecto).toEqual({ tipo: "enfocarErrores" });
    expect(transicion.estado.fase).toBe("error");
    expect(transicion.estado.cantidad).toBe("210");
    if (transicion.estado.fase === "error") {
      expect(transicion.estado.errores).toEqual({ ...SIN_ERRORES, partida: detalle });
    }
  });

  test("409 de rev viejo añade el texto de recarga en general y conserva lo escrito", () => {
    const enviando = enviandoCon("210", "6*35", "norte");
    const detalle = "El borrador cambió en otra ventana: vuelva a cargarlo.";
    const transicion = siguiente(enviando, { tipo: "conflictoRev", detalle });

    expect(transicion.efecto).toEqual({ tipo: "enfocarErrores" });
    expect(transicion.estado.fase).toBe("error");
    expect(transicion.estado.cantidad).toBe("210");
    expect(transicion.estado.calculo).toBe("6*35");
    expect(transicion.estado.nota).toBe("norte");
    if (transicion.estado.fase === "error") {
      expect(transicion.estado.errores).toEqual({ ...SIN_ERRORES, general: `${detalle} ${RECARGADO}` });
    }
  });

  test("corregir el campo con error limpia su error y vuelve a editando si no quedan otros", () => {
    const enviando = enviandoCon("2.5");
    const conError = siguiente(enviando, { tipo: "rechazo422", detalle: MENSAJE_CIFRA }).estado;
    const corregido = siguiente(conError, { tipo: "cambiarCantidad", valor: "2,5" });

    expect(corregido.estado.fase).toBe("editando");
    expect(corregido.estado.cantidad).toBe("2,5");
  });

  test("elegir una partida desde Parecidas o desde partidaInicial pide enfocar Cantidad", () => {
    const estado = estadoInicialDeAlta();
    const desdeParecidas = siguiente(estado, { tipo: "elegirPartida", partida: PARED, enfocarCantidad: true });
    expect(desdeParecidas.efecto).toEqual({ tipo: "enfocarCantidad" });
    expect(desdeParecidas.estado.elegida).toEqual(PARED);

    const desdeComponer = siguiente(estado, {
      tipo: "fijarPartidaInicial",
      partida: { codigo: "FRI-01", descripcion: "Friso de pared", unidad: "m2" },
    });
    expect(desdeComponer.efecto).toEqual({ tipo: "enfocarCantidad" });
    expect(desdeComponer.estado.texto).toBe("FRI-01 · Friso de pared");
  });
});
