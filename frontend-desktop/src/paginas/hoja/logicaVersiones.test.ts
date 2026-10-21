import { describe, expect, test } from "vitest";
import { ErrorDeApi } from "../../api/cliente";
import {
  RUTA_DE_CONVERTIR,
  RUTA_DE_COTIZAR,
  RUTA_DE_RESTAURAR,
  RUTA_DE_RETIRAR,
  TITULO_DE_ERROR,
  avisoDeCambiosPendientes,
  clasificarErrorDeOperacion,
  cotizadasDePrecios,
  cuerpoDeConvertir,
  cuerpoDeCotizar,
  cuerpoDeRestaurar,
  cuerpoDeRetirar,
  fechaDeHoy,
  insumosDePrecios,
  monedasDestino,
  motivoParaNoConvertir,
  motivoParaNoCotizar,
  motivoParaNoRestaurar,
  motivoParaNoRetirar,
  rotuloDeCotizada,
  rotuloDeInsumo,
  rutaDeCadena,
  textoDeVersionCreada,
} from "./logicaVersiones";

// Rebanada 3d-2 (front): S2 a S6 del contrato `2026-10-20-hoja-3d2-contrato-rutas.md`. Todos los valores esperados están escritos a
// mano desde ese contrato y desde la clásica (ui/paginas/hoja.py:1946, 1985, 2081, 2151, 2201).

describe("rutas y cuerpos de S2 a S6", () => {
  test("las rutas son las del contrato", () => {
    expect(RUTA_DE_RESTAURAR).toBe("/v1/hoja/versiones/restaurar");
    expect(RUTA_DE_COTIZAR).toBe("/v1/hoja/versiones/cotizar");
    expect(RUTA_DE_RETIRAR).toBe("/v1/hoja/versiones/retirar-cotizacion");
    expect(RUTA_DE_CONVERTIR).toBe("/v1/hoja/versiones/convertir");
    expect(rutaDeCadena("OF-001")).toBe("/v1/hoja/cadena?proyecto=OF-001");
    expect(rutaDeCadena("Obra A&B")).toBe("/v1/hoja/cadena?proyecto=Obra%20A%26B");
  });

  test("restaurar manda proyecto, versión y fuente: nunca un responsable", () => {
    expect(cuerpoDeRestaurar("OF-001", "001", "Se pidió volver a la 001")).toEqual({
      proyecto: "OF-001",
      version: "001",
      fuente: "Se pidió volver a la 001",
    });
  });

  test("cotizar manda el precio como el texto que se escribió, y la evidencia vacía como null", () => {
    expect(
      cuerpoDeCotizar("OF-001", "002", {
        insumo: "MAT-001",
        precio: "3.50",
        proveedor: "Ferretería Demo, C.A.",
        numero: "COT-17",
        fecha: "2026-10-20",
        evidencia: "",
      }),
    ).toEqual({
      proyecto: "OF-001",
      version: "002",
      insumo: "MAT-001",
      precio: "3.50",
      proveedor: "Ferretería Demo, C.A.",
      numero: "COT-17",
      fecha: "2026-10-20",
      evidencia: null,
    });
    expect(
      cuerpoDeCotizar("OF-001", "002", { insumo: "MAT-001", precio: "3.5", proveedor: "P", numero: "1", fecha: "2026-10-20", evidencia: "correo del 18" })
        .evidencia,
    ).toBe("correo del 18");
    // El precio nunca es un número: un valor con ceros y más decimales viaja tal cual.
    expect(
      typeof cuerpoDeCotizar("OF-001", "002", { insumo: "M", precio: "0003.500000", proveedor: "P", numero: "1", fecha: "2026-10-20", evidencia: "" }).precio,
    ).toBe("string");
  });

  test("retirar manda insumo y motivo; convertir manda moneda, lado y fuente", () => {
    expect(cuerpoDeRetirar("OF-001", "003", "MAT-001", "La cotización venció")).toEqual({
      proyecto: "OF-001",
      version: "003",
      insumo: "MAT-001",
      motivo: "La cotización venció",
    });
    expect(cuerpoDeConvertir("OF-001", "003", "Bs", "venta", "Pedido de la gerencia")).toEqual({
      proyecto: "OF-001",
      version: "003",
      moneda: "Bs",
      lado: "venta",
      fuente: "Pedido de la gerencia",
    });
  });
});

describe("textos con cambios pendientes (P:1946, 2081, 2201, con tildes)", () => {
  test("cotizar y convertir dicen cuántos cambios hay", () => {
    expect(avisoDeCambiosPendientes("cotizar", 3)).toBe(
      "Cotizar crea una versión nueva desde la guardada: guarde o descarte primero los 3 cambios pendientes.",
    );
    expect(avisoDeCambiosPendientes("convertir", 2)).toBe(
      "Cambiar la moneda crea una versión nueva desde la guardada: guarde o descarte primero los 2 cambios pendientes.",
    );
  });

  test("con un solo cambio va en singular", () => {
    expect(avisoDeCambiosPendientes("cotizar", 1)).toBe(
      "Cotizar crea una versión nueva desde la guardada: guarde o descarte primero el cambio pendiente.",
    );
  });

  test("restaurar no dice cuántos", () => {
    expect(avisoDeCambiosPendientes("restaurar", 5)).toBe("Guarde o descarte los cambios pendientes antes de restaurar otra versión.");
  });
});

describe("motivos para no enviar (la clásica pedía estos campos)", () => {
  const completo = { precio: "3.5", proveedor: "Ferretería Demo", numero: "COT-1", fecha: "2026-10-20" };

  test("cotizar: el primer campo que falta, en el orden del formulario", () => {
    expect(motivoParaNoCotizar({ ...completo, precio: "  " })).toBe("Escriba el precio cotizado.");
    expect(motivoParaNoCotizar({ ...completo, proveedor: "" })).toBe("Escriba el proveedor de la cotización.");
    expect(motivoParaNoCotizar({ ...completo, numero: " " })).toBe("Escriba el número de la cotización.");
    expect(motivoParaNoCotizar({ ...completo, fecha: "" })).toBe("Elija la fecha de la cotización.");
    expect(motivoParaNoCotizar(completo)).toBeNull();
  });

  test("el precio mal escrito NO lo juzga la interfaz: lo juzga el servidor", () => {
    expect(motivoParaNoCotizar({ ...completo, precio: "tres con cinco" })).toBeNull();
    expect(motivoParaNoCotizar({ ...completo, precio: "3,5" })).toBeNull();
  });

  test("retirar, restaurar y convertir piden su fuente", () => {
    expect(motivoParaNoRetirar("")).toBe("Escriba por qué se retira la cotización.");
    expect(motivoParaNoRetirar("venció")).toBeNull();
    expect(motivoParaNoRestaurar("   ")).toBe("Escriba la fuente: por qué se restaura la versión.");
    expect(motivoParaNoRestaurar("Se pidió")).toBeNull();
    expect(motivoParaNoConvertir("")).toBe("Escriba por qué se cambia la moneda (la fuente).");
    expect(motivoParaNoConvertir("Gerencia")).toBeNull();
  });
});

describe("mensaje de éxito", () => {
  test("se usa el texto del servidor (ya lleva tildes)", () => {
    expect(
      textoDeVersionCreada({ codigo: "003", proyecto: "OF-001", mensaje: "La versión 001 se restauró como la versión 003 (la vigente)." }, "x"),
    ).toBe("La versión 001 se restauró como la versión 003 (la vigente).");
  });

  test("sin texto del servidor se usa el de repuesto", () => {
    expect(textoDeVersionCreada({ codigo: "003", proyecto: "OF-001", mensaje: "" }, "Se guardó la versión 003 sin la cotización.")).toBe(
      "Se guardó la versión 003 sin la cotización.",
    );
  });
});

describe("errores de S2 a S5", () => {
  const e = (estado: number, detalle: string) => new ErrorDeApi(estado, detalle);

  test("el detalle del servidor va tal cual y se clasifica por estado", () => {
    expect(clasificarErrorDeOperacion(e(422, "precio: 'x' no es un numero decimal valido"))).toEqual({
      clase: "rechazo",
      mensaje: "precio: 'x' no es un numero decimal valido",
    });
    expect(clasificarErrorDeOperacion(e(404, "El proyecto «OF-009» no existe en este caso."))).toEqual({
      clase: "ausente",
      mensaje: "El proyecto «OF-009» no existe en este caso.",
    });
    expect(clasificarErrorDeOperacion(e(409, "No se guardó nada: falta una composición")).clase).toBe("conflicto");
    expect(clasificarErrorDeOperacion(e(403, "Su cuenta no tiene permiso para esta acción.")).clase).toBe("permiso");
    expect(clasificarErrorDeOperacion(e(503, "No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro programa.")).clase).toBe("base");
    expect(clasificarErrorDeOperacion(e(500, "Internal Server Error")).clase).toBe("otro");
    expect(clasificarErrorDeOperacion(new Error("sqlite3.OperationalError en C:/data")).mensaje).toBe(
      "Ocurrió un error inesperado. Inténtelo de nuevo.",
    );
  });

  test("un 503 sin texto usa el fijo del cliente", () => {
    expect(clasificarErrorDeOperacion(e(503, "")).mensaje).toBe(
      "No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro programa.",
    );
  });

  test("el título de cada operación dice qué no pasó", () => {
    expect(TITULO_DE_ERROR).toEqual({
      restaurar: "No se restauró nada",
      cotizar: "No se guardó nada",
      retirar: "No se guardó nada",
      convertir: "No se convirtió nada",
    });
  });
});

describe("lo que ofrece la tabla de precios", () => {
  const filas = [
    { insumo: "Tubo PVC 1/2", codigo: "MAT-001", cotizacion: "" },
    { insumo: "Llave de paso", codigo: "MAT-002", cotizacion: "COT-17 · Ferretería Demo" },
    { insumo: "Cemento", codigo: { texto: "x", exacto: "x" }, cotizacion: null },
  ];

  test("insumos ofrecidos: los que traen código en texto", () => {
    expect(insumosDePrecios(filas).map(rotuloDeInsumo)).toEqual(["MAT-001 · Tubo PVC 1/2", "MAT-002 · Llave de paso"]);
  });

  test("cotizadas: solo las que traen su cotización", () => {
    const c = cotizadasDePrecios(filas);
    expect(c.map((i) => i.codigo)).toEqual(["MAT-002"]);
    expect(rotuloDeCotizada(c[0]!)).toBe("MAT-002 · Llave de paso (COT-17 · Ferretería Demo)");
  });
});

describe("fecha y monedas", () => {
  test("la fecha de hoy es AAAA-MM-DD con los componentes locales", () => {
    expect(fechaDeHoy(new Date(2026, 9, 5))).toBe("2026-10-05");
    expect(fechaDeHoy(new Date(2026, 0, 31))).toBe("2026-01-31");
  });

  test("la moneda destino excluye la actual (MONEDAS = Bs y USD)", () => {
    expect(monedasDestino("USD")).toEqual(["Bs"]);
    expect(monedasDestino("Bs")).toEqual(["USD"]);
    expect(monedasDestino(null)).toEqual(["Bs", "USD"]);
  });
});
