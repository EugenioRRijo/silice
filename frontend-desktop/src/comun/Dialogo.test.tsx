import { fileURLToPath } from "node:url";
import { Button } from "@carbon/react";
import { act, render, screen, waitFor, within } from "@testing-library/react";
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
  ocultar = false,
}: {
  enviando: boolean;
  opciones: OpcionesDeMontaje;
  ocultar?: boolean;
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
      {!ocultar && (
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
      )}
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
    desmontarAbierto: () => {
      vista.rerender(<EjemploDeDialogo enviando={false} opciones={opciones} ocultar />);
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
    await waitFor(() => expect(alCerrar).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(montado.botonQueAbre()).toHaveFocus();
  });

  it("abrir, Esc, abrir, Esc: alCerrar se llama una vez por cada cierre", async () => {
    const usuario = userEvent.setup();
    const alCerrar = vi.fn();
    const montado = montarDialogoDeEjemplo({ alCerrar });

    await montado.abrir();
    await usuario.keyboard("{Escape}");
    expect(alCerrar).toHaveBeenCalledTimes(1);

    await montado.abrir();
    expect(screen.queryByRole("dialog")).not.toBeNull();
    await usuario.keyboard("{Escape}");
    expect(alCerrar).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("mientras se envía pone closedby=none y lo quita al terminar", async () => {
    const montado = montarDialogoDeEjemplo();
    await montado.abrir();
    const dialogo = screen.getByRole("dialog");
    expect(dialogo).not.toHaveAttribute("closedby");

    act(() => montado.ponerEnviando(true));
    expect(dialogo).toHaveAttribute("closedby", "none");

    act(() => montado.ponerEnviando(false));
    expect(dialogo).not.toHaveAttribute("closedby");
  });

  it("sin soporte de closedby, el segundo Esc no cancelable cierra el elemento y Dialogo lo reabre sin avisar", async () => {
    const usuario = userEvent.setup();
    const alCerrar = vi.fn();
    const montado = montarDialogoDeEjemplo({ alCerrar });
    await montado.abrir();
    const dialogo = screen.getByRole("dialog") as HTMLDialogElement;

    act(() => montado.ponerEnviando(true));
    dialogo.removeAttribute("closedby"); // navegador que ignora closedby
    await usuario.keyboard("{Escape}");
    await usuario.keyboard("{Escape}");
    await act(async () => {
      await new Promise((resolver) => setTimeout(resolver, 10));
    });

    expect(dialogo.open).toBe(true);
    expect(screen.queryByRole("dialog")).not.toBeNull();
    expect(alCerrar).not.toHaveBeenCalled();
  });

  it("un close que llega cuando el diálogo ya se reabrió se ignora", async () => {
    const alCerrar = vi.fn();
    const montado = montarDialogoDeEjemplo({ alCerrar });
    await montado.abrir();
    const dialogo = screen.getByRole("dialog") as HTMLDialogElement;

    act(() => {
      dialogo.close();
      dialogo.showModal();
    });
    await act(async () => {
      await new Promise((resolver) => setTimeout(resolver, 10));
    });

    expect(alCerrar).not.toHaveBeenCalled();
    expect(dialogo.open).toBe(true);
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

describe("Respaldo de <dialog> en pruebas: modela al navegador real", () => {
  function montarDialogoSuelto(): HTMLDialogElement {
    const dialogo = document.createElement("dialog");
    document.body.appendChild(dialogo);
    return dialogo;
  }

  it("un Esc que un control interno ya previno no cierra el diálogo", async () => {
    const usuario = userEvent.setup();
    const dialogo = montarDialogoSuelto();
    const campo = document.createElement("input");
    dialogo.appendChild(campo);
    campo.addEventListener("keydown", (evento) => {
      if (evento.key === "Escape") evento.preventDefault();
    });
    dialogo.showModal();
    campo.focus();

    await usuario.keyboard("{Escape}");

    expect(dialogo.open).toBe(true);
    dialogo.remove();
  });

  it("el Esc llega al diálogo superior aunque el foco esté en body", async () => {
    const usuario = userEvent.setup();
    const dialogo = montarDialogoSuelto();
    dialogo.showModal();
    (document.activeElement as HTMLElement | null)?.blur();
    expect(document.activeElement).toBe(document.body);

    await usuario.keyboard("{Escape}");

    expect(dialogo.open).toBe(false);
    dialogo.remove();
  });

  it("close se despacha en una tarea aparte, no dentro de close()", async () => {
    const dialogo = montarDialogoSuelto();
    const alClose = vi.fn();
    dialogo.addEventListener("close", alClose);
    dialogo.showModal();

    dialogo.close();
    expect(alClose).not.toHaveBeenCalled();
    await waitFor(() => expect(alClose).toHaveBeenCalledTimes(1));
    dialogo.remove();
  });

  it("showModal lanza InvalidStateError si no está conectado y no hace nada si ya está abierto", () => {
    const suelto = document.createElement("dialog");
    expect(() => suelto.showModal()).toThrowError(expect.objectContaining({ name: "InvalidStateError" }));

    const dialogo = montarDialogoSuelto();
    dialogo.showModal();
    expect(() => dialogo.showModal()).not.toThrow();
    expect(dialogo.open).toBe(true);
    dialogo.remove();
  });
});

describe("Dialogo: estilos", () => {
  const css = compilarScss("./Dialogo.scss");

  it("contiene el overscroll en dialog:modal y en ::backdrop", () => {
    expect(css).toMatch(/dialog\.silice-dialogo:modal\s*\{[^}]*overscroll-behavior:\s*contain/);
    expect(css).toMatch(/dialog\.silice-dialogo::backdrop\s*\{[^}]*overscroll-behavior:\s*contain/);
  });

  it("el ::backdrop es contenedor de scroll cerrado: overflow hidden junto a overscroll-behavior", () => {
    expect(css).toMatch(/dialog\.silice-dialogo::backdrop\s*\{[^}]*overflow:\s*hidden/);
  });

  it("desplaza el cuerpo largo dentro del diálogo y alinea el pie en el orden de Carbon", () => {
    expect(css).toMatch(/\.silice-dialogo\s*\{[^}]*max-block-size:\s*calc\(100dvh - 2rem\)/);
    expect(css).toMatch(/\.silice-dialogo__cuerpo\s*\{[^}]*overflow-y:\s*auto/);
    expect(css).toMatch(/\.silice-dialogo__pie\s*\{[^}]*flex-direction:\s*row/);
    expect(css).toMatch(/\.silice-dialogo__pie\s*\{[^}]*justify-content:\s*flex-end/);
  });

  it("no lleva franja lateral gruesa: el borde es de 1px en los cuatro lados, también con colores forzados", () => {
    expect(css).not.toMatch(/border-inline-start(-width|-color)?\s*:/);
    expect(css).toMatch(/\.silice-dialogo\s*\{[^}]*border:\s*1px solid var\(--cds-border-subtle\)/);
    expect(css).not.toMatch(/\.silice-dialogo--destructivo/);
  });

  // Recorrido funcional del 2026-11-27: «Nueva obra» (MarcoDeDialogo, un <div role="dialog"> con la clase `silice-dialogo`)
  // salía con `display: none` en las pantallas que cargan este archivo (la de la obra, p. ej.): `.silice-dialogo:not([open])`
  // también alcanzaba al <div>, que nunca lleva `open`. Las reglas de este archivo son solo del elemento <dialog>.
  it("sus reglas son solo del elemento <dialog>: no alcanzan a los diálogos del marco (MarcoDeDialogo)", () => {
    const selectores = [...css.matchAll(/([^{}]+)\{/g)].map((m) => (m[1] ?? "").trim()).filter((t) => !t.startsWith("@"));
    const delDialogo = selectores.flatMap((t) => t.split(",")).map((t) => t.trim()).filter((t) => t.includes(".silice-dialogo"));
    expect(delDialogo.length).toBeGreaterThan(0);
    expect(delDialogo.filter((t) => !t.startsWith("dialog.silice-dialogo"))).toEqual([]);
  });
});
