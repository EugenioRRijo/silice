import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, test, vi } from "vitest";
import type { Mock } from "vitest";
import { MENSAJE_CIFRA } from "../../../indicadores/cifraEscrita";
import { FRASES_DE_RECHAZO } from "../logicaSecciones";
import { CeldaDeCantidad } from "./CeldaDeCantidad";
import type { PropiedadesDeCeldaDeCantidad } from "./CeldaDeCantidad";

// Lote B1-5 (ficha-b1 §1.10, pruebas 5 y 6): la celda de cantidad sola, dentro de una celda de grilla. La conexión con la
// grilla real, el motor de envío y el servidor se prueban en useCantidadesDeLaSuperficie.test.tsx. Datos ficticios.

interface Montaje {
  alCambiar: Mock<(texto: string) => void>;
  alRestaurar: Mock<() => void>;
  alConfirmar: Mock<() => void>;
}

const espiasNuevos = (): Montaje => ({ alCambiar: vi.fn(), alRestaurar: vi.fn(), alConfirmar: vi.fn() });

// Dos filas de una grilla mínima: la celda de EXC-01 y, debajo, la de REL-02 (para ver adónde baja el foco).
function Celdas({
  valorInicial = "3",
  extra = {},
  espias,
  alTeclearAfuera,
}: {
  valorInicial?: string;
  extra?: Partial<PropiedadesDeCeldaDeCantidad>;
  espias: Montaje;
  alTeclearAfuera?: (tecla: string) => void;
}) {
  const [valor, setValor] = useState(valorInicial);
  return (
    <div onKeyDown={(e) => alTeclearAfuera?.(e.key)}>
      <button type="button">Afuera</button>
      <table role="grid" aria-label="Partidas">
        <tbody>
          <tr>
            <th scope="row">EXC-01</th>
            <td role="gridcell" data-celda="" data-fila={0} data-columna={1} tabIndex={0}>
              <CeldaDeCantidad
                etiqueta="Cantidad, EXC-01"
                valor={valor}
                alCambiar={(texto) => {
                  setValor(texto);
                  espias.alCambiar(texto);
                }}
                alRestaurar={() => {
                  setValor("3");
                  espias.alRestaurar();
                }}
                alConfirmar={espias.alConfirmar}
                {...extra}
              />
            </td>
          </tr>
          <tr>
            <th scope="row">REL-02</th>
            <td role="gridcell" data-celda="" data-fila={1} data-columna={1} tabIndex={-1}>
              20
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function montar(
  props: { valorInicial?: string; extra?: Partial<PropiedadesDeCeldaDeCantidad>; alTeclearAfuera?: (tecla: string) => void } = {},
) {
  const espias = espiasNuevos();
  const utilidades = render(<Celdas {...props} espias={espias} />);
  return { ...espias, ...utilidades, u: userEvent.setup() };
}

// La celda de EXC-01 (la de REL-02 es la de abajo).
const celda = () => screen.getAllByRole("gridcell")[0]!;
const campo = () => screen.getByRole("textbox", { name: "Cantidad, EXC-01" });
const sinCampo = () => expect(screen.queryByRole("textbox")).toBeNull();

describe("CeldaDeCantidad: en reposo", () => {
  test("es solo el texto: ningún campo ni parada de Tab de más", () => {
    montar();
    expect(celda()).toHaveTextContent("3");
    sinCampo();
    expect(celda().querySelectorAll("input, button, a, [tabindex]")).toHaveLength(0);
  });

  test("sin permiso de edición no se abre con F2, Enter, un carácter ni doble clic", async () => {
    const { u, alCambiar } = montar({ extra: { soloLectura: true } });
    celda().focus();
    await u.keyboard("{F2}");
    await u.keyboard("{Enter}");
    await u.keyboard("7");
    await u.dblClick(screen.getByText("3"));
    sinCampo();
    expect(celda()).toHaveTextContent("3");
    expect(alCambiar).not.toHaveBeenCalled();
  });
});

describe("CeldaDeCantidad: el permiso cambia", () => {
  test("un doble clic sin permiso no deja la edición «pendiente»: si el permiso llega después, no se abre sola", async () => {
    const espias = espiasNuevos();
    const celdaCon = (soloLectura: boolean) => (
      <table role="grid" aria-label="Partidas">
        <tbody>
          <tr>
            <th scope="row">EXC-01</th>
            <td role="gridcell" data-celda="" tabIndex={0}>
              <CeldaDeCantidad etiqueta="Cantidad, EXC-01" valor="3" soloLectura={soloLectura} {...espias} />
            </td>
          </tr>
        </tbody>
      </table>
    );
    const { rerender } = render(celdaCon(true));
    await userEvent.setup().dblClick(screen.getByText("3"));
    rerender(celdaCon(false));
    sinCampo();
  });
});

describe("CeldaDeCantidad: abrir la edición", () => {
  test("F2 abre un campo con su etiqueta oculta y el foco, con inputmode decimal y el texto que tenía", async () => {
    const { u } = montar();
    celda().focus();
    await u.keyboard("{F2}");
    expect(campo()).toHaveFocus();
    expect(campo()).toHaveValue("3");
    expect(campo()).toHaveAttribute("inputmode", "decimal");
    // La etiqueta no se ve (la cabecera da la columna), pero el campo la tiene.
    expect(screen.queryByText("Cantidad, EXC-01", { selector: "label:not(.cds--visually-hidden)" })).toBeNull();
  });

  test("Enter abre con el texto que tenía", async () => {
    const { u, alCambiar } = montar();
    celda().focus();
    await u.keyboard("{Enter}");
    expect(campo()).toHaveFocus();
    expect(campo()).toHaveValue("3");
    expect(alCambiar).not.toHaveBeenCalled();
  });

  test("un carácter imprimible abre y reemplaza el texto por ese carácter", async () => {
    const { u, alCambiar } = montar();
    celda().focus();
    await u.keyboard("7");
    expect(campo()).toHaveValue("7");
    expect(campo()).toHaveFocus();
    expect(alCambiar).toHaveBeenCalledWith("7");
  });

  test("el doble clic abre", async () => {
    const { u } = montar();
    await u.dblClick(screen.getByText("3"));
    expect(campo()).toHaveFocus();
  });

  test("con Ctrl no se abre: queda para el navegador", async () => {
    const { u } = montar();
    celda().focus();
    await u.keyboard("{Control>}7{/Control}");
    sinCampo();
  });

  test("una tecla que llega desde otro control de la celda no la abre", () => {
    montar();
    fireEvent.keyDown(screen.getByText("3"), { key: "F2" });
    sinCampo();
  });
});

describe("CeldaDeCantidad: escribir, confirmar y restaurar", () => {
  test("escribir «12,5» manda cada cambio a quien la usa y deja el texto tal cual", async () => {
    const { u, alCambiar } = montar();
    celda().focus();
    await u.keyboard("{F2}{Backspace}12,5");
    expect(campo()).toHaveValue("12,5");
    expect(alCambiar.mock.calls.map(([t]) => t)).toEqual(["", "1", "12", "12,", "12,5"]);
  });

  test("las flechas, Inicio, Fin y las letras son del campo: no confirman ni restauran", async () => {
    const { u, alConfirmar, alRestaurar } = montar();
    celda().focus();
    await u.keyboard("{F2}{ArrowLeft}{Home}{End}{ArrowUp}{ArrowDown}");
    expect(campo()).toHaveFocus();
    expect(alConfirmar).not.toHaveBeenCalled();
    expect(alRestaurar).not.toHaveBeenCalled();
  });

  test("Esc restaura, cierra, devuelve el foco a la celda y no confirma", async () => {
    const { u, alRestaurar, alConfirmar } = montar();
    celda().focus();
    await u.keyboard("{F2}{Backspace}99");
    await u.keyboard("{Escape}");
    expect(alRestaurar).toHaveBeenCalledTimes(1);
    sinCampo();
    expect(celda()).toHaveTextContent("3");
    expect(celda()).toHaveFocus();
    expect(alConfirmar).not.toHaveBeenCalled();
  });

  test("Esc cancela la edición y no sube a quien cierra paneles o diálogos por encima de la celda", async () => {
    const alTeclearAfuera = vi.fn<(tecla: string) => void>();
    const { u } = montar({ alTeclearAfuera });
    celda().focus();
    await u.keyboard("{F2}");
    alTeclearAfuera.mockClear();
    await u.keyboard("{Escape}");
    expect(alTeclearAfuera).not.toHaveBeenCalledWith("Escape");
  });

  test("Enter confirma una sola vez, cierra y baja el foco a la celda de abajo", async () => {
    const { u, alConfirmar } = montar();
    celda().focus();
    await u.keyboard("{F2}{Backspace}12,5{Enter}");
    expect(alConfirmar).toHaveBeenCalledTimes(1);
    sinCampo();
    expect(screen.getByRole("gridcell", { name: "20" })).toHaveFocus();
  });

  test("Enter en la última fila confirma y deja el foco en su celda", async () => {
    const espias = espiasNuevos();
    render(
      <table role="grid" aria-label="Partidas">
        <tbody>
          <tr>
            <th scope="row">EXC-01</th>
            <td role="gridcell" data-celda="" data-fila={0} data-columna={1} tabIndex={0}>
              <CeldaDeCantidad etiqueta="Cantidad, EXC-01" valor="3" {...espias} />
            </td>
          </tr>
        </tbody>
      </table>,
    );
    const u = userEvent.setup();
    celda().focus();
    await u.keyboard("{Enter}{Enter}");
    expect(espias.alConfirmar).toHaveBeenCalledTimes(1);
    expect(celda()).toHaveFocus();
  });

  test("Tab confirma, cierra y deja el foco en la celda para que el navegador siga desde ella", () => {
    const { alConfirmar } = montar();
    celda().focus();
    fireEvent.keyDown(celda(), { key: "F2" });
    fireEvent.keyDown(campo(), { key: "Tab" });
    expect(alConfirmar).toHaveBeenCalledTimes(1);
    sinCampo();
    expect(celda()).toHaveFocus();
  });

  test("salir del campo con la edición abierta (un clic en otro lugar) confirma lo escrito, como en Excel", async () => {
    const { u, alConfirmar } = montar();
    celda().focus();
    await u.keyboard("{F2}{Backspace}8");
    expect(alConfirmar).not.toHaveBeenCalled();
    await u.click(screen.getByRole("button", { name: "Afuera" }));
    expect(alConfirmar).toHaveBeenCalledTimes(1);
    sinCampo();
    expect(celda()).toHaveTextContent("8");
  });

  test("con la edición cerrada, un foco que pasa por la celda no confirma nada", async () => {
    const { u, alConfirmar } = montar();
    celda().focus();
    await u.click(screen.getByRole("button", { name: "Afuera" }));
    expect(alConfirmar).not.toHaveBeenCalled();
  });
});

describe("CeldaDeCantidad: errores (prueba 5)", () => {
  const DETALLE =
    "presupuesto, fila 1 (EXC-01): la cantidad no puede ser negativa; escriba cero o una cantidad positiva";
  const rechazo = () => ({ mensaje: `${DETALLE}. ${FRASES_DE_RECHAZO.cantidades}` });

  test("un rechazo del servidor deja lo escrito, lo marca con texto y no solo con color", () => {
    montar({ valorInicial: "-1", extra: { rechazo: rechazo() } });
    // El campo sigue a la vista aunque la persona ya haya salido de él.
    expect(campo()).toHaveValue("-1");
    expect(campo()).toHaveAttribute("aria-invalid", "true");
    const texto = screen.getByText("La cantidad no puede ser negativa; escriba cero o una cantidad positiva.");
    expect(texto).toBeVisible();
    expect(campo().getAttribute("aria-describedby")).toBe(texto.id);
  });

  test("cambiar el texto limpia la marca, y un rechazo nuevo (aunque diga lo mismo) la vuelve a poner", () => {
    const espias = espiasNuevos();
    const primero = rechazo();
    const { rerender } = render(
      <table role="grid" aria-label="Partidas">
        <tbody>
          <tr>
            <th scope="row">EXC-01</th>
            <td role="gridcell" data-celda="" tabIndex={0}>
              <CeldaDeCantidad etiqueta="Cantidad, EXC-01" valor="-1" rechazo={primero} {...espias} />
            </td>
          </tr>
        </tbody>
      </table>,
    );
    expect(campo()).toHaveAttribute("aria-invalid", "true");
    const con = (valor: string, r: { mensaje: string }) =>
      rerender(
        <table role="grid" aria-label="Partidas">
          <tbody>
            <tr>
              <th scope="row">EXC-01</th>
              <td role="gridcell" data-celda="" tabIndex={0}>
                <CeldaDeCantidad etiqueta="Cantidad, EXC-01" valor={valor} rechazo={r} {...espias} />
              </td>
            </tr>
          </tbody>
        </table>,
      );
    // La persona corrige el texto: el mismo rechazo ya no es de este valor.
    con("2", primero);
    sinCampo();
    // Lo vuelve a escribir mal y el servidor lo rechaza otra vez con las mismas palabras.
    con("-2", rechazo());
    expect(campo()).toHaveValue("-2");
    expect(campo()).toHaveAttribute("aria-invalid", "true");
  });

  test("lo mal escrito se marca al salir, con el mensaje de las cifras, y se confirma igual para que el servidor lo diga", async () => {
    const { u, alConfirmar } = montar();
    celda().focus();
    await u.keyboard("{F2}{Backspace}2.5");
    await u.click(screen.getByRole("button", { name: "Afuera" }));
    expect(alConfirmar).toHaveBeenCalledTimes(1);
    // El campo no desaparece: lo escrito queda a la vista con su error.
    expect(campo()).toHaveValue("2.5");
    expect(campo()).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText(MENSAJE_CIFRA)).toBeVisible();
  });

  test("mientras se escribe no se marca error: «12,5x» solo se marca al salir", async () => {
    const { u } = montar();
    celda().focus();
    await u.keyboard("{F2}{Backspace}12,5x");
    expect(campo()).toHaveAttribute("aria-invalid", "false");
  });
});
