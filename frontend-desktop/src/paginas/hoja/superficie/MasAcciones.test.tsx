import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterAll, beforeAll, describe, expect, test, vi } from "vitest";
import { MasAcciones } from "./MasAcciones";

// B1-3 (ficha-b1 §4): el menú «Más acciones del presupuesto». Sale de la vista lo ocasional (Excel, PDF, descartar) para que
// la cabecera no pase del tope de decisiones. Menú con `popover` nativo (guía `dialog`, Regla 3); «Descartar» es destructivo
// y pide confirmar con el foco en «Cancelar» (D7, guía `dialog`: «autofocus on the safe action»).
const NOMBRE = "Más acciones del presupuesto";

// Respaldo solo para estas pruebas, como el de `showModal` en `test/setup.ts`: jsdom oculta todo `[popover]` y no trae
// `showPopover`/`hidePopover`; el navegador real sí. Aquí mostrar es quitar el `display: none` que jsdom le pone.
beforeAll(() => {
  const proto = HTMLElement.prototype as HTMLElement & { showPopover?: () => void; hidePopover?: () => void };
  proto.showPopover = function showPopover(this: HTMLElement) {
    this.style.display = "block";
  };
  proto.hidePopover = function hidePopover(this: HTMLElement) {
    this.style.display = "";
  };
});
afterAll(() => {
  const proto = HTMLElement.prototype as HTMLElement & { showPopover?: () => void; hidePopover?: () => void };
  Reflect.deleteProperty(proto, "showPopover");
  Reflect.deleteProperty(proto, "hidePopover");
});

function montar(
  props: {
    alDescartar?: () => void;
    cambios?: number;
    alVerFrentes?: () => void;
    rutaArchivos?: string;
    rutaPestanas?: string;
  } = {},
) {
  const alDescartar = props.alDescartar ?? vi.fn();
  render(
    <MemoryRouter>
      <MasAcciones
        alDescartar={alDescartar}
        cambios={props.cambios ?? 0}
        alVerFrentes={props.alVerFrentes}
        rutaArchivos={props.rutaArchivos}
        rutaPestanas={props.rutaPestanas}
      >
        <button type="button">Descargar Excel</button>
      </MasAcciones>
    </MemoryRouter>,
  );
  return { alDescartar, boton: screen.getByRole("button", { name: NOMBRE }) };
}

describe("MasAcciones: el menú", () => {
  test("cerrado no muestra opciones; pulsar el botón las abre y lo dice con aria-expanded", async () => {
    const { boton } = montar();
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("button", { name: "Descargar Excel" })).toBeNull();
    await userEvent.click(boton);
    expect(boton).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("button", { name: "Descargar Excel" })).toBeInTheDocument();
  });

  test("Esc cierra el menú y el foco vuelve al botón que lo abrió", async () => {
    const { boton } = montar();
    await userEvent.click(boton);
    screen.getByRole("button", { name: "Descargar Excel" }).focus();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("button", { name: "Descargar Excel" })).toBeNull();
    expect(boton).toHaveFocus();
    expect(boton).toHaveAttribute("aria-expanded", "false");
  });

  test("un clic fuera del menú lo cierra; un clic dentro no", async () => {
    const { boton } = montar();
    await userEvent.click(boton);
    await userEvent.click(screen.getByRole("button", { name: "Descargar Excel" }));
    expect(boton).toHaveAttribute("aria-expanded", "true");
    await userEvent.click(document.body);
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("button", { name: "Descargar Excel" })).toBeNull();
  });

  test("las opciones siguen montadas con el menú cerrado (una descarga que falla no pierde su aviso)", () => {
    montar();
    expect(screen.getByRole("button", { name: "Descargar Excel", hidden: true })).toBeInTheDocument();
  });

  test("el botón del menú no es principal", () => {
    const { boton } = montar();
    expect(boton).not.toHaveClass("cds--btn--primary");
  });
});

describe("MasAcciones: «Descartar los cambios»", () => {
  test("sin cambios (o sin alDescartar) no se ofrece", async () => {
    const { boton } = montar({ cambios: 0 });
    await userEvent.click(boton);
    expect(screen.queryByRole("button", { name: "Descartar cambios" })).toBeNull();
  });

  test("sin alDescartar no se ofrece aunque haya cambios", async () => {
    render(<MasAcciones cambios={2} />);
    await userEvent.click(screen.getByRole("button", { name: NOMBRE }));
    expect(screen.queryByRole("button", { name: "Descartar cambios" })).toBeNull();
  });

  test("con cambios pide confirmar, con el foco inicial en «Cancelar», y no descarta hasta confirmar", async () => {
    const { alDescartar, boton } = montar({ cambios: 2 });
    await userEvent.click(boton);
    await userEvent.click(screen.getByRole("button", { name: "Descartar cambios" }));
    const dialogo = await screen.findByRole("dialog", { name: "Descartar cambios" });
    expect(within(dialogo).getByText(/¿Descartar los 2 cambios sin guardar\? No se pueden recuperar\./)).toBeInTheDocument();
    expect(within(dialogo).getByRole("button", { name: "Cancelar" })).toHaveFocus();
    // El foco en «Cancelar» lo garantiza `Dialogo destructivo` (su propia prueba cubre el caso con campos antes); aquí se fija
    // que se pidió así.
    expect(dialogo).toHaveClass("silice-dialogo--destructivo");
    expect(alDescartar).not.toHaveBeenCalled();
  });

  test("con un solo cambio el texto va en singular", async () => {
    const { boton } = montar({ cambios: 1 });
    await userEvent.click(boton);
    await userEvent.click(screen.getByRole("button", { name: "Descartar cambios" }));
    expect(await screen.findByText("¿Descartar el cambio sin guardar? No se puede recuperar.")).toBeInTheDocument();
  });

  test("«Cancelar» cierra el diálogo, no descarta y devuelve el foco al botón del menú", async () => {
    const { alDescartar, boton } = montar({ cambios: 2 });
    await userEvent.click(boton);
    await userEvent.click(screen.getByRole("button", { name: "Descartar cambios" }));
    const dialogo = await screen.findByRole("dialog", { name: "Descartar cambios" });
    await userEvent.click(within(dialogo).getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("dialog", { name: "Descartar cambios" })).toBeNull();
    expect(alDescartar).not.toHaveBeenCalled();
    expect(boton).toHaveFocus();
  });

  test("«Descartar y abrir de nuevo» llama a alDescartar una sola vez", async () => {
    const { alDescartar, boton } = montar({ cambios: 2 });
    await userEvent.click(boton);
    await userEvent.click(screen.getByRole("button", { name: "Descartar cambios" }));
    const dialogo = await screen.findByRole("dialog", { name: "Descartar cambios" });
    await userEvent.click(within(dialogo).getByRole("button", { name: "Descartar y abrir de nuevo" }));
    expect(alDescartar).toHaveBeenCalledTimes(1);
  });
});

describe("MasAcciones: opciones de la ficha §1.6", () => {
  test("«Subtotales por frente» cierra el menú y llama a alVerFrentes una sola vez", async () => {
    const alVerFrentes = vi.fn();
    const { boton } = montar({ alVerFrentes });
    await userEvent.click(boton);
    await userEvent.click(screen.getByRole("button", { name: "Subtotales por frente" }));
    expect(alVerFrentes).toHaveBeenCalledTimes(1);
    expect(boton).toHaveAttribute("aria-expanded", "false");
  });

  test("ofrece enlaces a «Traer un plano o cómputo» y «Espacio, plan y ajustes» con sus rutas", async () => {
    const { boton } = montar({
      rutaArchivos: "/obra/empresa/1/archivos",
      rutaPestanas: "/obra/empresa/1/presupuesto/pestanas",
    });
    await userEvent.click(boton);
    expect(screen.getByRole("link", { name: "Traer un plano o cómputo" })).toHaveAttribute("href", "/obra/empresa/1/archivos");
    expect(screen.getByRole("link", { name: "Espacio, plan y ajustes" })).toHaveAttribute(
      "href",
      "/obra/empresa/1/presupuesto/pestanas",
    );
  });
});
