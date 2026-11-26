import { fileURLToPath } from "node:url";
import { Button } from "@carbon/react";
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import * as sass from "sass";
import { describe, expect, it, vi } from "vitest";
import { CampoTexto } from "./CampoTexto";
import { Dialogo } from "./Dialogo";
import { probarContratoDeDialogo } from "./contratoDeDialogo";
import type { DialogoMontado } from "./contratoDeDialogo";

interface OpcionesDeMontaje {
  destructivo?: boolean;
  invertirPie?: boolean;
  id?: string;
  alCerrar?: () => void;
}

function EjemploDeDialogo({
  enviando,
  opciones,
}: {
  enviando: boolean;
  opciones: OpcionesDeMontaje;
}) {
  const [abierto, setAbierto] = useState(false);

  const cerrar = () => {
    opciones.alCerrar?.();
    setAbierto(false);
  };

  const botonCancelar = (
    <Button key="cancelar" kind="secondary" size="md" disabled={enviando} onClick={cerrar}>
      Cancelar
    </Button>
  );
  const botonPrincipal = (
    <Button
      key="principal"
      kind={opciones.destructivo ? "danger" : "primary"}
      size="md"
      disabled={enviando}
      onClick={cerrar}
    >
      {opciones.destructivo ? "Eliminar versión" : "Guardar versión"}
    </Button>
  );

  return (
    <div>
      <Button kind="primary" onClick={() => setAbierto(true)}>
        Abrir
      </Button>
      <Dialogo
        id={opciones.id}
        abierto={abierto}
        titulo="Guardar versión de obra"
        alCerrar={cerrar}
        enviando={enviando}
        destructivo={opciones.destructivo}
        pie={opciones.invertirPie ? [botonPrincipal, botonCancelar] : [botonCancelar, botonPrincipal]}
      >
        <CampoTexto id="campo-motivo" labelText="Motivo del cambio" />
      </Dialogo>
    </div>
  );
}

function FormularioConDosCampos({ marcarSegundo }: { marcarSegundo: boolean }) {
  const [abierto, setAbierto] = useState(false);
  return (
    <div>
      <Button kind="primary" onClick={() => setAbierto(true)}>
        Abrir formulario
      </Button>
      <Dialogo abierto={abierto} titulo="Registrar partida" alCerrar={() => setAbierto(false)}>
        <Button kind="ghost" size="sm">
          Ver ayuda
        </Button>
        <CampoTexto id="campo-codigo" labelText="Código" />
        <CampoTexto
          id="campo-descripcion"
          labelText="Descripción"
          {...(marcarSegundo ? { "data-autofocus": true } : {})}
        />
      </Dialogo>
    </div>
  );
}

function montarDialogoDeEjemplo(opciones: OpcionesDeMontaje = {}): DialogoMontado {
  const usuario = userEvent.setup();
  const vista = render(<EjemploDeDialogo enviando={false} opciones={opciones} />);

  return {
    abrir: async () => {
      await usuario.click(screen.getByRole("button", { name: "Abrir" }));
    },
    botonQueAbre: () => screen.getByRole("button", { name: "Abrir" }),
    enfocadoAlAbrir: () => screen.getByLabelText("Motivo del cambio"),
    ponerEnviando: (enviando: boolean) => {
      vista.rerender(<EjemploDeDialogo enviando={enviando} opciones={opciones} />);
    },
  };
}

probarContratoDeDialogo("Dialogo", () => montarDialogoDeEjemplo());

describe("Dialogo: comportamiento y accesibilidad propios", () => {
  it("aria-labelledby apunta al h2 del título y conserva el id opcional", async () => {
    const montado = montarDialogoDeEjemplo({ id: "dialogo-version" });
    await montado.abrir();

    const dialogo = screen.getByRole("dialog", { name: "Guardar versión de obra" });
    const titulo = screen.getByRole("heading", { level: 2, name: "Guardar versión de obra" });

    expect(titulo.id).not.toBe("");
    expect(dialogo).toHaveAttribute("aria-labelledby", titulo.id);
    expect(dialogo).toHaveAttribute("id", "dialogo-version");
    expect(titulo).toHaveClass("cds--type-heading-compact-02");
  });

  it("el elemento es un <dialog> nativo sin role='dialog' ni aria-modal", async () => {
    const montado = montarDialogoDeEjemplo();
    await montado.abrir();

    const dialogo = screen.getByRole("dialog");
    expect(dialogo.tagName).toBe("DIALOG");
    expect(dialogo).not.toHaveAttribute("role");
    expect(dialogo).not.toHaveAttribute("aria-modal");
    expect(dialogo).not.toHaveAttribute("tabindex");
  });

  it("el pie respeta el orden de Carbon: secundario a la izquierda y principal a la derecha", async () => {
    const montado = montarDialogoDeEjemplo();
    await montado.abrir();

    const dialogo = screen.getByRole("dialog");
    const pie = dialogo.querySelector<HTMLElement>(".silice-dialogo__pie");
    expect(pie).not.toBeNull();

    const botones = within(pie!).getAllByRole("button");
    expect(botones).toHaveLength(2);
    expect(botones[0]).toHaveTextContent("Cancelar");
    expect(botones[0]).toHaveClass("cds--btn--secondary");
    expect(botones[1]).toHaveTextContent("Guardar versión");
    expect(botones[1]).toHaveClass("cds--btn--primary");
  });

  it("el pie mantiene el orden de Carbon aunque los botones se entreguen invertidos", async () => {
    const montado = montarDialogoDeEjemplo({ destructivo: true, invertirPie: true });
    await montado.abrir();

    const dialogo = screen.getByRole("dialog");
    const pie = dialogo.querySelector<HTMLElement>(".silice-dialogo__pie");
    expect(pie).not.toBeNull();

    const botones = within(pie!).getAllByRole("button");
    expect(botones).toHaveLength(2);
    expect(botones[0]).toHaveTextContent("Cancelar");
    expect(botones[0]).toHaveClass("cds--btn--secondary");
    expect(botones[1]).toHaveTextContent("Eliminar versión");
    expect(botones[1]).toHaveClass("cds--btn--danger");
  });

  it("con destructivo, el foco inicial queda en «Cancelar» aunque haya campos antes", async () => {
    const montado = montarDialogoDeEjemplo({ destructivo: true });
    await montado.abrir();

    expect(screen.getByRole("button", { name: "Cancelar" })).toHaveFocus();
    expect(screen.getByRole("dialog")).toHaveClass("silice-dialogo--destructivo");
  });

  it("enfoca el primer campo aunque antes haya un botón auxiliar, y respeta data-autofocus", async () => {
    const usuario = userEvent.setup();
    const vista = render(<FormularioConDosCampos marcarSegundo={false} />);
    await usuario.click(screen.getByRole("button", { name: "Abrir formulario" }));
    expect(screen.getByLabelText("Código")).toHaveFocus();

    await usuario.keyboard("{Escape}");
    vista.rerender(<FormularioConDosCampos marcarSegundo={true} />);
    await usuario.click(screen.getByRole("button", { name: "Abrir formulario" }));
    expect(screen.getByLabelText("Descripción")).toHaveFocus();
  });

  it("alCerrar se llama una sola vez al cerrar con Esc", async () => {
    const usuario = userEvent.setup();
    const alCerrar = vi.fn();
    const montado = montarDialogoDeEjemplo({ alCerrar });

    await montado.abrir();
    await usuario.keyboard("{Escape}");

    expect(alCerrar).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("alCerrar se llama una sola vez cuando el diálogo se cierra por el evento nativo close", async () => {
    const alCerrar = vi.fn();
    const montado = montarDialogoDeEjemplo({ alCerrar });

    await montado.abrir();
    const dialogo = screen.getByRole("dialog") as HTMLDialogElement;
    act(() => {
      dialogo.close();
    });

    expect(alCerrar).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(montado.botonQueAbre()).toHaveFocus();
  });

  it("al cerrar pulsando «Cancelar», alCerrar se llama una sola vez y el foco vuelve al botón que abrió", async () => {
    const usuario = userEvent.setup();
    const alCerrar = vi.fn();
    const montado = montarDialogoDeEjemplo({ alCerrar });

    await montado.abrir();
    await usuario.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(alCerrar).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(montado.botonQueAbre()).toHaveFocus();
  });
});

const compilarScss = (ruta: string) => sass.compile(fileURLToPath(new URL(ruta, import.meta.url))).css;

describe("Dialogo: estilos", () => {
  const css = compilarScss("./Dialogo.scss");

  it("contiene el overscroll en dialog:modal y en ::backdrop", () => {
    expect(css).toMatch(/dialog\.silice-dialogo:modal\s*\{[^}]*overscroll-behavior:\s*contain/);
    expect(css).toMatch(/dialog\.silice-dialogo::backdrop\s*\{[^}]*overscroll-behavior:\s*contain/);
  });

  it("desplaza el cuerpo largo dentro del diálogo y alinea el pie en el orden de Carbon", () => {
    expect(css).toMatch(/\.silice-dialogo\s*\{[^}]*max-block-size:\s*calc\(100dvh - 2rem\)/);
    expect(css).toMatch(/\.silice-dialogo__cuerpo\s*\{[^}]*overflow-y:\s*auto/);
    expect(css).toMatch(/\.silice-dialogo__pie\s*\{[^}]*flex-direction:\s*row/);
    expect(css).toMatch(/\.silice-dialogo__pie\s*\{[^}]*justify-content:\s*flex-end/);
  });
});
