import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRef, useState } from "react";
import { describe, expect, test, vi } from "vitest";
import { useFocoEnPrimerError } from "./useFocoEnPrimerError";

interface Errores {
  primero?: string | null;
  segundo?: string | null;
  tercero?: string | null;
}

function FormularioDePrueba({
  errores,
  alResultado,
}: {
  errores: Errores;
  alResultado: (huboError: boolean) => void;
}) {
  const enfocarPrimerError = useFocoEnPrimerError();
  const refPrimero = useRef<HTMLInputElement>(null);
  const refSegundo = useRef<HTMLInputElement>(null);
  const refTercero = useRef<HTMLInputElement>(null);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const huboError = enfocarPrimerError([
          { error: errores.primero, ref: refPrimero },
          { error: errores.segundo, ref: refSegundo },
          { error: errores.tercero, ref: refTercero },
        ]);
        alResultado(huboError);
      }}
    >
      <label htmlFor="c-1">Primero</label>
      <input id="c-1" ref={refPrimero} />
      <label htmlFor="c-2">Segundo</label>
      <input id="c-2" ref={refSegundo} />
      <label htmlFor="c-3">Tercero</label>
      <input id="c-3" ref={refTercero} />
      <button type="submit">Guardar</button>
    </form>
  );
}

describe("useFocoEnPrimerError", () => {
  test("enfoca el primero con error en el orden dado aunque haya otros después, y devuelve true", async () => {
    const u = userEvent.setup();
    const alResultado = vi.fn<(huboError: boolean) => void>();
    render(
      <FormularioDePrueba
        errores={{
          primero: null,
          segundo: "Escriba la fuente de la serie.",
          tercero: "Escriba la fecha de descarga.",
        }}
        alResultado={alResultado}
      />,
    );

    const boton = screen.getByRole("button", { name: "Guardar" });
    await u.click(boton);

    expect(alResultado).toHaveBeenLastCalledWith(true);
    expect(screen.getByLabelText("Segundo")).toHaveFocus();

    // Un segundo intento con el mismo error vuelve a llevar el foco al primer campo inválido.
    boton.focus();
    expect(boton).toHaveFocus();
    await u.click(boton);
    expect(alResultado).toHaveBeenCalledTimes(2);
    expect(screen.getByLabelText("Segundo")).toHaveFocus();
  });

  test("devuelve false y no mueve el foco a ningún campo cuando no hay errores", async () => {
    const u = userEvent.setup();
    const alResultado = vi.fn<(huboError: boolean) => void>();
    render(
      <FormularioDePrueba
        errores={{ primero: null, segundo: undefined, tercero: "" }}
        alResultado={alResultado}
      />,
    );

    const boton = screen.getByRole("button", { name: "Guardar" });
    await u.click(boton);

    expect(alResultado).toHaveBeenLastCalledWith(false);
    expect(screen.getByLabelText("Primero")).not.toHaveFocus();
    expect(screen.getByLabelText("Segundo")).not.toHaveFocus();
    expect(screen.getByLabelText("Tercero")).not.toHaveFocus();
  });

  test("enfoca un elemento que recién se monta al pintarse el error", async () => {
    const u = userEvent.setup();
    function ConAvisoCondicional() {
      const enfocarPrimerError = useFocoEnPrimerError();
      const [mostrarError, setMostrarError] = useState(false);
      const refAviso = useRef<HTMLDivElement>(null);
      return (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setMostrarError(true);
            enfocarPrimerError([{ error: "Elija el archivo CSV de la serie.", ref: refAviso }]);
          }}
        >
          {mostrarError && (
            <div ref={refAviso} tabIndex={-1}>
              Elija el archivo CSV de la serie.
            </div>
          )}
          <button type="submit">Importar</button>
        </form>
      );
    }

    render(<ConAvisoCondicional />);
    await u.click(screen.getByRole("button", { name: "Importar" }));

    expect(screen.getByText("Elija el archivo CSV de la serie.")).toHaveFocus();
  });
});
