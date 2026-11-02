import { describe, expect, test } from "vitest";
import {
  PESTANAS,
  SIN_VERSIONES,
  campoDelErrorDePartida,
  comoSeMidio,
  cuerpoDeAgregarPartida,
  esBorradorAusente,
  pestanaInicial,
  rotuloDeVersion,
  rutaDeAgregarPartida,
  rutaDeQuitarPartida,
  rutaDeVersiones,
  textoDeCambios,
  versionesOfrecidas,
} from "./logica";
import type { VersionFila } from "./logica";
import { ErrorDeApi } from "../../api/cliente";

function version(codigo: string, extra: Partial<VersionFila> = {}): VersionFila {
  return {
    codigo,
    fecha: "2026-10-05",
    motivo: "",
    origen: "",
    vigente: false,
    descartada: false,
    cambios: 0,
    ...extra,
  };
}

describe("lógica de la hoja del proyecto", () => {
  test("las nueve pestañas van en el orden de la página clásica", () => {
    expect(PESTANAS).toEqual([
      "Espacio y metrajes",
      "APU",
      "Presupuesto",
      "Plan y curva",
      "Punto de equilibrio",
      "Precios",
      "Parámetros",
      "Auditoría",
      "Trazabilidad",
    ]);
  });

  test("el proyecto va codificado en la ruta de versiones", () => {
    expect(rutaDeVersiones("OF-001: oficina & baño")).toBe(
      "/v1/hoja/versiones?proyecto=OF-001%3A%20oficina%20%26%20ba%C3%B1o",
    );
  });

  test("se ofrecen las versiones no descartadas; si todas lo están, todas", () => {
    const a = version("001");
    const b = version("002", { vigente: true });
    const c = version("003", { descartada: true });
    expect(versionesOfrecidas([a, b, c]).map((v) => v.codigo)).toEqual(["001", "002"]);
    expect(versionesOfrecidas([{ ...a, descartada: true }, c]).map((v) => v.codigo)).toEqual(["001", "003"]);
    expect(versionesOfrecidas([])).toEqual([]);
  });

  test("la vigente se rotula con ' (vigente)' y las demás con su código", () => {
    expect(rotuloDeVersion(version("002", { vigente: true }))).toBe("002 (vigente)");
    expect(rotuloDeVersion(version("001"))).toBe("001");
  });

  test("los cambios sin guardar se dicen en singular y plural", () => {
    expect(textoDeCambios(0)).toBe("Sin cambios sin guardar");
    expect(textoDeCambios(1)).toBe("1 cambio sin guardar");
    expect(textoDeCambios(3)).toBe("3 cambios sin guardar");
  });

  test("el aviso de la obra sin versiones dice «obra» y lleva tilde", () => {
    expect(SIN_VERSIONES).toBe("Esta obra aún no tiene versiones");
  });

  test("solo el 404 de 'ya no está en el servidor' es un borrador ausente", () => {
    const ausente = new ErrorDeApi(404, "Ese borrador ya no está en el servidor (se reinició Sílice).");
    expect(esBorradorAusente(ausente)).toBe(true);
    expect(esBorradorAusente(new ErrorDeApi(404, "El proyecto «Z» no existe en este caso."))).toBe(false);
    expect(esBorradorAusente(new ErrorDeApi(500, "Ese borrador ya no está"))).toBe(false);
    expect(esBorradorAusente("otra cosa")).toBe(false);
  });

  // --- Tarea 11: agregar y quitar partidas ---

  test("una obra sin espacio abre en «Presupuesto» (2); con espacio, en «Espacio y metrajes» (0)", () => {
    expect(pestanaInicial({ espacio_vacio: true })).toBe(2);
    expect(PESTANAS[pestanaInicial({ espacio_vacio: true })]).toBe("Presupuesto");
    expect(pestanaInicial({ espacio_vacio: false })).toBe(0);
  });

  test("las rutas de agregar y quitar son las de la Tarea 9", () => {
    expect(rutaDeAgregarPartida("id-1")).toBe("/v1/hoja/borradores/id-1/partidas");
    expect(rutaDeQuitarPartida("id-1")).toBe("/v1/hoja/borradores/id-1/partidas/quitar");
  });

  test("el cuerpo de agregar lleva lo escrito tal cual, sin recortar ni convertir", () => {
    expect(cuerpoDeAgregarPartida(3, { codigo: "OBRA-04", cantidad: " 1.234,5 ", calculo: "2,5 × 4", nota: "muro norte" })).toEqual({
      rev: 3,
      codigo: "OBRA-04",
      cantidad: " 1.234,5 ",
      calculo: "2,5 × 4",
      nota: "muro norte",
    });
  });

  test("el error de un 422 va al campo que lo causó", () => {
    const cifra = "Use la coma para los decimales: por ejemplo 2,5. El punto separa los miles: 1.234,56.";
    const sinCalculo = { cantidad: "2.5", calculo: "" };
    expect(campoDelErrorDePartida("El cálculo da 16 y la cantidad es 15: corrija uno de los dos.", { cantidad: "15", calculo: "6*3-2" })).toBe(
      "calculo",
    );
    expect(campoDelErrorDePartida("El cálculo divide entre cero.", { cantidad: "", calculo: "1/0" })).toBe("calculo");
    expect(campoDelErrorDePartida("Escriba el cálculo, por ejemplo 6*3-2.", { cantidad: "", calculo: " " })).toBe("calculo");
    expect(
      campoDelErrorDePartida(
        "Con cuatro decimales, el resultado del cálculo pierde precisión: escriba también la cantidad, con los decimales que necesite.",
        { cantidad: "", calculo: "0,00005*1" },
      ),
    ).toBe("calculo");
    expect(campoDelErrorDePartida("La cantidad no puede ser negativa.", { cantidad: "-1", calculo: "" })).toBe("cantidad");
    expect(campoDelErrorDePartida(`Escriba un número. ${cifra}`, { cantidad: "", calculo: "" })).toBe("cantidad");
    // La regla de las cifras vale para los dos campos: es de la cantidad si no hay cálculo o si la cantidad está mal escrita.
    expect(campoDelErrorDePartida(cifra, sinCalculo)).toBe("cantidad");
    expect(campoDelErrorDePartida(cifra, { cantidad: "2.5", calculo: "6*3" })).toBe("cantidad");
    expect(campoDelErrorDePartida(cifra, { cantidad: "", calculo: "2.5*4" })).toBe("calculo");
    expect(campoDelErrorDePartida(cifra, { cantidad: "10", calculo: "2.5*4" })).toBe("calculo");
    // El servidor lee primero el cálculo: con los dos mal escritos, el error es del cálculo.
    expect(campoDelErrorDePartida(cifra, { cantidad: "2.5", calculo: "(1.5 + 2) × 4" })).toBe("calculo");
    expect(campoDelErrorDePartida("Otra cosa que no es de un campo.", sinCalculo)).toBeNull();
  });

  test("«Cómo se midió»: el cálculo y la nota del renglón; si no, de dónde sale la cantidad", () => {
    const base = { quitable: true, calculo: null, nota: null };
    expect(comoSeMidio({ ...base, calculo: "6*35", nota: "6 m × 35 m de muro" })).toEqual({ calculo: "6*35", nota: "6 m × 35 m de muro", texto: null });
    expect(comoSeMidio({ ...base, nota: "Medido en el plano A-2" })).toEqual({ calculo: null, nota: "Medido en el plano A-2", texto: null });
    expect(comoSeMidio(base)).toEqual({ calculo: null, nota: null, texto: "Sin cálculo" });
    expect(comoSeMidio({ ...base, quitable: false })).toEqual({ calculo: null, nota: null, texto: "Sale del espacio" });
  });
});
