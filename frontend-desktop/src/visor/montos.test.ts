import { describe, expect, test } from "vitest";
import { montosEnFormatoUnico } from "./montos";

describe("montosEnFormatoUnico", () => {
  test("pasa el formato local a punto decimal sin separador de miles", () => {
    expect(montosEnFormatoUnico("difiere en 4 331,43 USD del total")).toBe("difiere en 4331.43 USD del total");
    expect(montosEnFormatoUnico("1 234 567,80")).toBe("1234567.80");
    expect(montosEnFormatoUnico("1.234,56 Bs")).toBe("1234.56 Bs");
    expect(montosEnFormatoUnico("12,5")).toBe("12.5");
  });
  test("deja intactos los montos que ya vienen con punto y el texto sin montos", () => {
    expect(montosEnFormatoUnico("4203.93")).toBe("4203.93");
    expect(montosEnFormatoUnico("Celda F12 de la hoja 2")).toBe("Celda F12 de la hoja 2");
  });
  test("no toca listas de enteros separadas por coma y espacio", () => {
    expect(montosEnFormatoUnico("filas 3, 4, 5")).toBe("filas 3, 4, 5");
  });
});
