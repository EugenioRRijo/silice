import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { CalculadoraFCAS } from "./CalculadoraFCAS";

// Datos ficticios con la forma de `/v1/fcas`. El servidor manda cada cifra como texto con punto decimal y ya redondeada;
// la pantalla no calcula nada: solo la escribe con coma y punto de miles. Oráculo a mano (Dodi y Salas, 2019): 365 días,
// 23,13 de bonificación y 217,28 trabajados dan 78,63 % y × 1,7863.
function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const POR_DEFECTO = {
  dias_calendario: "365",
  fcas_version: "6.00",
  componentes: [
    { id: "utilidades", nombre: "Utilidades", base: "dias", valor: "100", fuente: "CCT 2023, cláusula 48", a_cotejar: false },
    { id: "paro_forzoso", nombre: "Paro forzoso", base: "porcentaje", valor: "2", fuente: "Ley del Régimen Prestacional de Empleo, art. 46 — a cotejar con el texto de la ley", a_cotejar: true },
    { id: "ivss", nombre: "Seguro social (IVSS)", base: "porcentaje", valor: "11", fuente: "Reglamento, art. 109 — a cotejar", a_cotejar: true },
    { id: "pensiones", nombre: "Contribución especial para pensiones", base: "porcentaje", valor: "9", fuente: "Ley de 2024 — a cotejar", a_cotejar: true },
  ],
};

const DODI = {
  fcas: "0.7863",
  fcas_por_dias: "0.7863",
  dias_pagados: "388.13",
  porcentaje: "78.63",
  multiplicador: "1.7863",
  desglose: [
    { id: "dias_no_trabajados", nombre: "Días pagados sin trabajar (descansos, feriados, permisos)", aporte: "0.6799" },
    { id: "utilidades", nombre: "Utilidades", aporte: "0.1064" },
  ],
  a_cotejar: [] as { id: string; nombre: string }[],
  version: { fcas: "6.00", porcentaje: "600.00", multiplicador: "7.00" },
};

describe("Calculadora del FCAS por componentes", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let calculo: (cuerpo: Record<string, unknown>) => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    calculo = () => json(DODI);
    fetchFalso.mockImplementation(async (ruta, opciones) => {
      const url = String(ruta);
      const metodo = opciones?.method ?? "GET";
      if (url === "/v1/fcas/componentes" && metodo === "GET") return json(POR_DEFECTO);
      if (url === "/v1/fcas/calcular" && metodo === "POST") return calculo(JSON.parse(String(opciones?.body)));
      return json({ detalle: "ruta inesperada " + url }, 404);
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  async function montar() {
    const usuario = userEvent.setup();
    const alExpirar = vi.fn();
    render(<CalculadoraFCAS alExpirar={alExpirar} />);
    await screen.findByRole("checkbox", { name: /Utilidades/ });
    return { usuario, alExpirar };
  }

  function llamadasA(ruta: string, metodo: string) {
    return fetchFalso.mock.calls.filter(([r, o]) => String(r) === ruta && (o?.method ?? "GET") === metodo);
  }

  async function escribir(usuario: ReturnType<typeof userEvent.setup>, etiqueta: string | RegExp, texto: string) {
    const campo = screen.getByLabelText(etiqueta);
    await usuario.clear(campo);
    await usuario.type(campo, texto);
  }

  test("trae los componentes por defecto, con su fuente y el aviso de los que están por cotejar", async () => {
    await montar();
    expect(screen.getAllByRole("checkbox")).toHaveLength(4);
    expect(screen.getAllByRole("checkbox").every((c) => (c as HTMLInputElement).checked)).toBe(true);
    expect(screen.getByLabelText("Días calendario del período")).toHaveValue("365");
    expect(screen.getByLabelText("FCAS de la versión")).toHaveValue("6,00");
    expect(screen.getByText(/CCT 2023, cláusula 48/)).toBeInTheDocument();
    expect(screen.getAllByText("a cotejar")).toHaveLength(3);
    // el valor por defecto, como se escribe en es-VE
    expect(screen.getByLabelText(/Contribución especial para pensiones/, { selector: 'input[type="text"]' })).toHaveValue("9");
  });

  test("calcula el oráculo y lo muestra como 78,63 % y × 1,7863 al lado del de la versión", async () => {
    const { usuario } = await montar();
    await escribir(usuario, "Días trabajados", "217,28");
    await usuario.click(screen.getByRole("button", { name: "Calcular el FCAS" }));
    const calculado = await screen.findByRole("region", { name: "FCAS calculado" });
    expect(within(calculado).getByText("78,63 %")).toBeInTheDocument();
    expect(within(calculado).getByText("× 1,7863")).toBeInTheDocument();
    expect(within(calculado).getByText(/388,13/)).toBeInTheDocument();
    const deLaVersion = screen.getByRole("region", { name: "FCAS de la versión" });
    expect(within(deLaVersion).getByText("600,00 %")).toBeInTheDocument();
    expect(within(deLaVersion).getByText("× 7,00")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Desglose del FCAS" })).toBeInTheDocument();
  });

  test("manda decimales con punto y solo los componentes activos", async () => {
    const { usuario } = await montar();
    await escribir(usuario, "Días trabajados", "1.217,28");
    await usuario.click(screen.getByRole("checkbox", { name: /Contribución especial para pensiones/ }));
    await usuario.click(screen.getByRole("button", { name: "Calcular el FCAS" }));
    await screen.findByRole("region", { name: "FCAS calculado" });
    const cuerpo = JSON.parse(String(llamadasA("/v1/fcas/calcular", "POST")[0]![1]!.body));
    expect(cuerpo.dias_calendario).toBe("365");
    expect(cuerpo.dias_trabajados).toBe("1217.28");
    expect(cuerpo.fcas_version).toBe("6.00");
    expect(cuerpo.componentes.map((c: { id: string }) => c.id)).toEqual(["utilidades", "paro_forzoso", "ivss"]);
    expect(cuerpo.componentes[0]).toMatchObject({ base: "dias", valor: "100" });
  });

  test("lo que está por cotejar se avisa con el foco en el aviso", async () => {
    calculo = () => json({ ...DODI, a_cotejar: [{ id: "ivss", nombre: "Seguro social (IVSS)" }] });
    const { usuario } = await montar();
    await escribir(usuario, "Días trabajados", "217,28");
    await usuario.click(screen.getByRole("button", { name: "Calcular el FCAS" }));
    const aviso = await screen.findByText(/Seguro social \(IVSS\)/, { selector: "[role=status] *" });
    expect(aviso).toBeInTheDocument();
    await waitFor(() => expect(document.activeElement?.closest("[tabindex='-1']")).toContainElement(aviso));
  });

  test("no se aplica sola: dice dónde se aplica y no llama a ninguna ruta de parámetros", async () => {
    const { usuario } = await montar();
    await escribir(usuario, "Días trabajados", "217,28");
    await usuario.click(screen.getByRole("button", { name: "Calcular el FCAS" }));
    await screen.findByRole("region", { name: "FCAS calculado" });
    expect(screen.getByText(/pestaña Parámetros de la Hoja del proyecto/)).toBeInTheDocument();
    expect(screen.getByText(/0,7863/, { selector: "strong" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /aplicar/i })).not.toBeInTheDocument();
    expect(fetchFalso.mock.calls.every(([r]) => String(r).startsWith("/v1/fcas/"))).toBe(true);
  });

  test("una cifra mal escrita se explica y no se envía", async () => {
    const { usuario } = await montar();
    await escribir(usuario, "Días trabajados", "217.28");
    await usuario.click(screen.getByRole("button", { name: "Calcular el FCAS" }));
    expect(await screen.findByText(/Use la coma para los decimales/)).toBeInTheDocument();
    expect(llamadasA("/v1/fcas/calcular", "POST")).toHaveLength(0);
  });

  test("el error de la API se muestra con su detalle y avisa si la sesión expiró", async () => {
    calculo = () => json({ detalle: "los días trabajados no pueden pasar de los días calendario." }, 422);
    const { usuario, alExpirar } = await montar();
    await escribir(usuario, "Días trabajados", "400");
    await usuario.click(screen.getByRole("button", { name: "Calcular el FCAS" }));
    expect(await screen.findByText(/no pueden pasar de los días calendario/)).toBeInTheDocument();
    expect(alExpirar).toHaveBeenCalled();
    expect(screen.queryByRole("region", { name: "FCAS calculado" })).not.toBeInTheDocument();
  });
});
