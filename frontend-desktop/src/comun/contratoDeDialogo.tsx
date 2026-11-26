import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

export interface DialogoMontado {
  abrir: () => Promise<void>; // pulsa el botón que abre el diálogo
  botonQueAbre: () => HTMLElement;
  enfocadoAlAbrir: () => HTMLElement; // dónde debe quedar el foco inicial
  ponerEnviando: (enviando: boolean) => void;
}

export function probarContratoDeDialogo(nombre: string, montar: () => DialogoMontado): void {
  describe(`${nombre}: contrato del diálogo`, () => {
    it("al abrir, el foco queda en el elemento inicial", async () => {
      const montado = montar();
      await montado.abrir();
      expect(montado.enfocadoAlAbrir()).toHaveFocus();
    });

    it("Esc cierra el diálogo", async () => {
      const usuario = userEvent.setup();
      const montado = montar();
      await montado.abrir();
      expect(screen.queryByRole("dialog")).not.toBeNull();
      await usuario.keyboard("{Escape}");
      expect(screen.queryByRole("dialog")).toBeNull();
    });

    it("mientras se envía, Esc no cierra el diálogo", async () => {
      const usuario = userEvent.setup();
      const montado = montar();
      await montado.abrir();
      act(() => {
        montado.ponerEnviando(true);
      });
      await usuario.keyboard("{Escape}");
      expect(screen.queryByRole("dialog")).not.toBeNull();
    });

    it("al cerrar, el foco vuelve al botón que lo abrió", async () => {
      const usuario = userEvent.setup();
      const montado = montar();
      await montado.abrir();
      await usuario.keyboard("{Escape}");
      expect(screen.queryByRole("dialog")).toBeNull();
      expect(montado.botonQueAbre()).toHaveFocus();
    });
  });
}
