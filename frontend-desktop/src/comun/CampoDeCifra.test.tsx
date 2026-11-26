import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createRef, useState } from "react";
import { describe, expect, test, vi } from "vitest";
import { MENSAJE_CIFRA, MENSAJE_CIFRA_VACIA, AYUDA_CIFRAS } from "../indicadores/cifraEscrita";
import { CampoDeCifra } from "./CampoDeCifra";
import type { CampoDeCifraProps } from "./CampoDeCifra";

function CampoControlado({
  valorInicial = "",
  onChange,
  ...resto
}: Omit<CampoDeCifraProps, "value" | "onChange"> & {
  valorInicial?: string;
  onChange?: (texto: string) => void;
}) {
  const [valor, setValor] = useState(valorInicial);
  return (
    <div>
      <CampoDeCifra
        {...resto}
        value={valor}
        onChange={(nuevo) => {
          setValor(nuevo);
          onChange?.(nuevo);
        }}
      />
      <button type="button">Siguiente</button>
    </div>
  );
}

describe("CampoDeCifra", () => {
  test("lleva inputmode decimal, aria-invalid en false en reposo y no deja regiones vivas vacías", () => {
    const { container } = render(
      <CampoDeCifra id="cifra-1" labelText="Cantidad" value="" onChange={() => {}} />,
    );
    const campo = screen.getByLabelText("Cantidad");
    expect(campo).toHaveAttribute("inputmode", "decimal");
    expect(campo).toHaveAttribute("aria-invalid", "false");
    expect(container.querySelectorAll('[role="alert"]')).toHaveLength(0);
    expect(container.querySelectorAll("[aria-live]")).toHaveLength(0);
  });

  test("no marca error mientras la persona escribe «12,5x»", async () => {
    const u = userEvent.setup();
    render(<CampoControlado id="cifra-2" labelText="Precio unitario" />);
    const campo = screen.getByLabelText("Precio unitario");

    await u.type(campo, "12,5x");

    expect(campo).toHaveValue("12,5x");
    expect(campo).toHaveAttribute("aria-invalid", "false");
    expect(screen.queryByText(MENSAJE_CIFRA)).not.toBeInTheDocument();
  });

  test("marca error al salir del campo después de escribir, con aria-invalid en true y cómo corregir", async () => {
    const u = userEvent.setup();
    render(<CampoControlado id="cifra-3" labelText="Precio unitario" />);
    const campo = screen.getByLabelText("Precio unitario");

    await u.type(campo, "12,5x");
    await u.tab();

    expect(campo).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText(MENSAJE_CIFRA)).toBeInTheDocument();
    const idError = campo.getAttribute("aria-errormessage");
    expect(idError).toBeTruthy();
    expect(document.getElementById(idError!)).toHaveTextContent(MENSAJE_CIFRA);
  });

  test("pasar por el campo con Tab sin haber escrito no marca error hasta que se intente enviar", async () => {
    const u = userEvent.setup();
    render(<CampoControlado id="cifra-tab" labelText="Cantidad" obligatorio />);
    const campo = screen.getByLabelText("Cantidad");

    await u.click(campo);
    await u.tab();

    expect(campo).toHaveAttribute("aria-invalid", "false");
    expect(screen.queryByText(MENSAJE_CIFRA_VACIA)).not.toBeInTheDocument();
  });

  test("con mostrarError el error se ve sin haber tocado el campo", () => {
    render(
      <CampoDeCifra
        id="cifra-4"
        labelText="Rendimiento"
        value="2.5"
        mostrarError
        onChange={() => {}}
      />,
    );
    const campo = screen.getByLabelText("Rendimiento");

    expect(campo).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText(MENSAJE_CIFRA)).toBeInTheDocument();
  });

  test("«1.234,56» entrega «1234.56» en onValor y un texto inválido entrega null", async () => {
    const u = userEvent.setup();
    const onValor = vi.fn<(decimal: string | null) => void>();
    render(<CampoControlado id="cifra-5" labelText="Monto" onValor={onValor} />);
    const campo = screen.getByLabelText("Monto");

    await u.type(campo, "1.234,56");
    expect(onValor).toHaveBeenLastCalledWith("1234.56");

    await u.type(campo, "x");
    expect(onValor).toHaveBeenLastCalledWith(null);
  });

  test("obligatorio y vacío da el mensaje de vacío; opcional y vacío no marca error", () => {
    const { rerender } = render(
      <CampoDeCifra
        id="cifra-6"
        labelText="Cantidad"
        value=""
        obligatorio
        mostrarError
        onChange={() => {}}
      />,
    );
    const campo = screen.getByLabelText("Cantidad");
    expect(campo).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText(MENSAJE_CIFRA_VACIA)).toBeInTheDocument();

    rerender(
      <CampoDeCifra
        id="cifra-6"
        labelText="Cantidad"
        value=""
        obligatorio={false}
        mostrarError
        onChange={() => {}}
      />,
    );
    expect(campo).toHaveAttribute("aria-invalid", "false");
    expect(screen.queryByText(MENSAJE_CIFRA_VACIA)).not.toBeInTheDocument();
  });

  test("aplica la regla de validar sobre el decimal con punto", async () => {
    const u = userEvent.setup();
    const onValor = vi.fn<(decimal: string | null) => void>();
    const mayorQueCero = (decimal: string) =>
      decimal === "0" || decimal.startsWith("-") ? "Escriba una cantidad mayor que cero." : null;

    render(
      <CampoControlado
        id="cifra-7"
        labelText="Cantidad"
        validar={mayorQueCero}
        onValor={onValor}
      />,
    );
    const campo = screen.getByLabelText("Cantidad");

    await u.type(campo, "0");
    expect(campo).toHaveAttribute("aria-invalid", "false");
    expect(onValor).toHaveBeenLastCalledWith(null);

    await u.tab();
    expect(campo).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Escriba una cantidad mayor que cero.")).toBeInTheDocument();

    await u.clear(campo);
    await u.type(campo, "2,5");
    expect(onValor).toHaveBeenLastCalledWith("2.5");
    expect(campo).toHaveAttribute("aria-invalid", "false");
    expect(screen.queryByText("Escriba una cantidad mayor que cero.")).not.toBeInTheDocument();
  });

  test("expone ref al input para poder enfocarlo", () => {
    const ref = createRef<HTMLInputElement>();
    render(<CampoDeCifra id="cifra-8" ref={ref} labelText="Cantidad" value="" onChange={() => {}} />);
    const campo = screen.getByLabelText("Cantidad");

    expect(ref.current).toBe(campo);
    ref.current?.focus();
    expect(campo).toHaveFocus();
  });

  test("en reposo con helperText la descripción es la ayuda y con error pasa al mensaje en aria-describedby", async () => {
    const u = userEvent.setup();
    const { rerender } = render(
      <CampoDeCifra id="cifra-h1-sin" labelText="Sin ayuda" value="" onChange={() => {}} />,
    );
    expect(screen.getByLabelText("Sin ayuda")).not.toHaveAttribute("aria-describedby");

    rerender(<CampoControlado id="cifra-h1" labelText="Precio unitario" helperText={AYUDA_CIFRAS} />);
    const campo = screen.getByLabelText("Precio unitario");
    expect(campo).toHaveAccessibleDescription(AYUDA_CIFRAS);
    expect(campo).toHaveAttribute("aria-describedby", "cifra-h1-helper-text");

    await u.type(campo, "12,5x");
    await u.tab();

    expect(campo).toHaveAttribute("aria-describedby", "cifra-h1-error-msg");
    expect(campo).toHaveAccessibleDescription(MENSAJE_CIFRA);
  });

  test("si ya salió con «12,5x», el error sigue al teclear «y» y se va al corregir a «12,5»", async () => {
    const u = userEvent.setup();
    render(<CampoControlado id="cifra-h3" labelText="Precio unitario" />);
    const campo = screen.getByLabelText("Precio unitario");

    await u.type(campo, "12,5x");
    await u.tab();
    expect(campo).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText(MENSAJE_CIFRA)).toBeInTheDocument();

    await u.click(campo);
    await u.type(campo, "y");
    expect(campo).toHaveValue("12,5xy");
    expect(campo).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText(MENSAJE_CIFRA)).toBeInTheDocument();

    await u.clear(campo);
    await u.type(campo, "12,5");
    expect(campo).toHaveValue("12,5");
    expect(campo).toHaveAttribute("aria-invalid", "false");
    expect(screen.queryByText(MENSAJE_CIFRA)).not.toBeInTheDocument();
  });

  test("con disabled, mostrarError y un valor inválido queda aria-invalid en false y sin mensaje", () => {
    render(
      <CampoDeCifra
        id="cifra-disabled"
        labelText="Precio unitario"
        value="12,5x"
        disabled
        mostrarError
        onChange={() => {}}
      />,
    );
    const campo = screen.getByLabelText("Precio unitario");
    expect(campo).toHaveAttribute("aria-invalid", "false");
    expect(screen.queryByText(MENSAJE_CIFRA)).not.toBeInTheDocument();
  });

  test("con readOnly, mostrarError y un valor inválido queda aria-invalid en false y sin mensaje", () => {
    render(
      <CampoDeCifra
        id="cifra-readonly"
        labelText="Precio unitario"
        value="12,5x"
        readOnly
        mostrarError
        onChange={() => {}}
      />,
    );
    const campo = screen.getByLabelText("Precio unitario");
    expect(campo).toHaveAttribute("aria-invalid", "false");
    expect(screen.queryByText(MENSAJE_CIFRA)).not.toBeInTheDocument();
  });

  test("si el padre reemplaza el valor después de salir con error, el error se va", async () => {
    const u = userEvent.setup();
    function ConReemplazo() {
      const [valor, setValor] = useState("");
      return (
        <div>
          <CampoDeCifra id="cifra-reemplazo" labelText="Cantidad" value={valor} obligatorio onChange={setValor} />
          <button type="button">Siguiente</button>
          <button type="button" onClick={() => setValor("")}>
            Limpiar
          </button>
        </div>
      );
    }

    render(<ConReemplazo />);
    const campo = screen.getByLabelText("Cantidad");

    await u.type(campo, "12,5x");
    await u.tab();
    expect(campo).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText(MENSAJE_CIFRA)).toBeInTheDocument();

    await u.click(screen.getByRole("button", { name: "Limpiar" }));
    expect(campo).toHaveValue("");
    expect(campo).toHaveAttribute("aria-invalid", "false");
    expect(screen.queryByText(MENSAJE_CIFRA)).not.toBeInTheDocument();
    expect(screen.queryByText(MENSAJE_CIFRA_VACIA)).not.toBeInTheDocument();
  });
});
