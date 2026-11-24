import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import type { Similar } from "./cliente";
import { Similares } from "./Similares";

const UNA: Similar = {
  codigo: "FIC-001",
  descripcion: "Muro ficticio de bloque",
  puntaje: 0.8734,
  rendimiento: "12.00",
  unidad: "m2",
  tablas: {
    // Las tablas llegan como se escriben en los campos (coma decimal, `aplicacion.cifras.texto_de_cifra`).
    materiales: [{ descripcion: "Bloque ficticio", unidad: "u", cantidad: "12,5", precio: "0,80" }],
    equipos: [],
    mano_obra: [{ descripcion: "Albañil ficticio", cantidad: "1", sueldo: "20", modalidad: "JORNAL" }],
  },
  aviso: null,
};

describe("Similares", () => {
  test("sin similares no pinta nada", () => {
    const { container } = render(<Similares similares={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  test("lista cada partida con puntaje a dos decimales, código y descripción", () => {
    render(<Similares similares={[UNA]} />);
    expect(screen.getByRole("heading", { name: "Partidas similares del catálogo" })).toBeInTheDocument();
    expect(screen.getByText("FIC-001 · Muro ficticio de bloque (similitud 0,87)")).toBeInTheDocument();
  });

  test("al abrir una muestra el rendimiento y sus tablas de solo lectura", async () => {
    const usuario = userEvent.setup();
    render(<Similares similares={[UNA]} />);
    await usuario.click(screen.getByRole("button", { name: /FIC-001/ }));
    expect(screen.getByText("Rendimiento: 12,00 m²/día")).toBeInTheDocument();
    expect(screen.getByText("12,5")).toBeInTheDocument();
    // Las celdas llegan en es-VE («1.500,5»): `compararDecimales` las ordenaria mal, asi que no se ofrece ordenar
    // (arbitro, ronda 1, menor 4).
    const tabla = screen.getByRole("table", { name: "Materiales de FIC-001" });
    expect(within(tabla).queryAllByRole("button")).toHaveLength(0);
    expect(screen.getByText("Bloque ficticio")).toBeInTheDocument();
    expect(screen.getByText("Albañil ficticio")).toBeInTheDocument();
    expect(screen.queryAllByRole("textbox")).toHaveLength(0);
  });

  test("con aviso de desglose incompleto lo muestra en lugar de las tablas", async () => {
    const usuario = userEvent.setup();
    render(
      <Similares
        similares={[{ ...UNA, codigo: "FIC-002", tablas: null, rendimiento: null, unidad: null, aviso: "Desglose incompleto en la lista vigente: falta un precio." }]}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: /FIC-002/ }));
    expect(screen.getByText(/Desglose incompleto en la lista vigente: falta un precio\./)).toBeInTheDocument();
  });
});

// Decisión de Eugenio (2026-11-23): «Empezar desde esta». Quien no domina el oficio parte de una partida real parecida
// en vez de copiar tres tablas a mano. Lo pulsa la persona, todo se puede corregir y nada se guarda hasta guardar.
describe("Similares: empezar desde una partida parecida", () => {
  test("cada parecida con tablas ofrece «Empezar desde» y, sin nada escrito, la entrega de una vez", async () => {
    const usuario = userEvent.setup();
    const elegidas: string[] = [];
    render(<Similares similares={[UNA]} alEmpezarDesde={(s) => elegidas.push(s.codigo)} conAlgoEscrito={false} />);
    await usuario.click(screen.getByRole("button", { name: /^FIC-001 · / }));
    await usuario.click(screen.getByRole("button", { name: "Empezar desde FIC-001" }));
    expect(elegidas).toEqual(["FIC-001"]);
  });

  test("una parecida sin tablas (desglose incompleto) no ofrece empezar desde ella", async () => {
    const usuario = userEvent.setup();
    render(<Similares similares={[{ ...UNA, tablas: null, aviso: "Desglose incompleto." }]} alEmpezarDesde={() => undefined} conAlgoEscrito={false} />);
    await usuario.click(screen.getByRole("button", { name: /^FIC-001 · / }));
    expect(screen.queryByRole("button", { name: /^Empezar desde/ })).toBeNull();
  });

  test("con insumos ya escritos pregunta antes de reemplazarlos, con el foco en «Cancelar»", async () => {
    const usuario = userEvent.setup();
    const elegidas: string[] = [];
    render(<Similares similares={[UNA]} alEmpezarDesde={(s) => elegidas.push(s.codigo)} conAlgoEscrito />);
    await usuario.click(screen.getByRole("button", { name: /^FIC-001 · / }));
    await usuario.click(screen.getByRole("button", { name: "Empezar desde FIC-001" }));
    const aviso = screen.getByRole("alert");
    expect(aviso).toHaveTextContent("Se reemplazarán los insumos y el rendimiento que ya escribió por los de FIC-001.");
    expect(elegidas).toEqual([]);
    expect(within(aviso).getByRole("button", { name: "Cancelar" })).toHaveFocus();
    await usuario.click(within(aviso).getByRole("button", { name: "Reemplazar por los de FIC-001" }));
    expect(elegidas).toEqual(["FIC-001"]);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  test("la nota ya no dice «solo lectura»: dice cómo empezar desde una y que nada se guarda solo", () => {
    render(<Similares similares={[UNA]} alEmpezarDesde={() => undefined} conAlgoEscrito={false} />);
    expect(screen.queryByText(/solo lectura/)).toBeNull();
    expect(screen.getByText(/Puede empezar desde una de ellas/)).toBeInTheDocument();
  });
});
