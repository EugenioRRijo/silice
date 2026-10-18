import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import type { HallazgoLibroRespuesta } from "../api/tipos";
import { ListaHallazgos } from "./ListaHallazgos";

const hallazgos: HallazgoLibroRespuesta[] = [
  {
    codigo: "L3",
    severidad: "CRITICO",
    descripcion: "El total no coincide con la suma de las partidas",
    celda: "PRESUPUESTO!F12",
    impacto: "238.407",
    accion: "Corregir la suma",
  },
  {
    codigo: "L5",
    severidad: "ERROR",
    descripcion: "Precio unitario distinto al de INSUMOS",
    celda: "APU-01!G48",
    impacto: "12.50",
    accion: "Igualar el precio",
  },
  {
    codigo: "L7",
    severidad: "ADVERTENCIA",
    descripcion: "El libro no declara la fecha de la portada",
    celda: "",
    impacto: null,
    accion: "Completar la portada",
  },
  {
    codigo: "L9",
    severidad: "INFO",
    descripcion: "Rendimiento fuera de rango",
    celda: "APU-01!Rendimiento",
    impacto: null,
    accion: "Revisar",
  },
];

function montar(extra: Partial<React.ComponentProps<typeof ListaHallazgos>> = {}) {
  const irACelda = vi.fn();
  const onElegir = vi.fn();
  render(
    <ListaHallazgos
      hallazgos={hallazgos}
      seleccionado={null}
      irACelda={irACelda}
      onElegir={onElegir}
      {...extra}
    />,
  );
  return { irACelda, onElegir };
}

function fila(descripcion: string): HTMLElement {
  const celda = screen.getByText(descripcion);
  const f = celda.closest("tr");
  if (!f) throw new Error("sin fila");
  return f;
}

describe("ListaHallazgos", () => {
  test("lista todos los hallazgos con el nombre de su severidad en texto", () => {
    montar();
    expect(within(fila("El total no coincide con la suma de las partidas")).getByText("Crítico")).toBeInTheDocument();
    expect(within(fila("Precio unitario distinto al de INSUMOS")).getByText("Error")).toBeInTheDocument();
    expect(within(fila("El libro no declara la fecha de la portada")).getByText("Advertencia")).toBeInTheDocument();
    expect(within(fila("Rendimiento fuera de rango")).getByText("Información")).toBeInTheDocument();
  });

  test("la celda va en Plex Mono y el impacto se muestra exacto, alineado a la derecha", () => {
    montar();
    const f = fila("El total no coincide con la suma de las partidas");
    const celda = within(f).getByText("PRESUPUESTO!F12");
    expect(celda).toHaveClass("silice-codigo");
    const impacto = within(f).getByText("238.407");
    expect(impacto).toHaveClass("silice-cifra");
  });

  test("filtrar por Critico deja solo los criticos", async () => {
    const usuario = userEvent.setup();
    montar();
    await usuario.click(screen.getByRole("button", { name: /^Crítico/ }));
    expect(screen.getByText("El total no coincide con la suma de las partidas")).toBeInTheDocument();
    expect(screen.queryByText("Precio unitario distinto al de INSUMOS")).not.toBeInTheDocument();
    expect(screen.queryByText("Rendimiento fuera de rango")).not.toBeInTheDocument();
  });

  test("quitar el filtro devuelve todos", async () => {
    const usuario = userEvent.setup();
    montar();
    const boton = screen.getByRole("button", { name: /^Crítico/ });
    await usuario.click(boton);
    await usuario.click(boton);
    expect(screen.getByText("Precio unitario distinto al de INSUMOS")).toBeInTheDocument();
  });

  test("los botones del filtro dicen cuantos hay de cada severidad", () => {
    montar();
    expect(screen.getByRole("button", { name: "Crítico 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Advertencia 1" })).toBeInTheDocument();
  });

  test("los hallazgos sin celda ubicable van en el grupo Sin celda en el libro", () => {
    montar();
    const grupo = screen.getByRole("region", { name: /Sin celda en el libro/ });
    expect(within(grupo).getByText("El libro no declara la fecha de la portada")).toBeInTheDocument();
    expect(within(grupo).getByText("Rendimiento fuera de rango")).toBeInTheDocument();
    expect(within(grupo).queryByText("Precio unitario distinto al de INSUMOS")).not.toBeInTheDocument();
    // La referencia que no es A1 se muestra tal cual, para que el auditor sepa donde buscar.
    expect(within(grupo).getByText("APU-01!Rendimiento")).toBeInTheDocument();
  });

  test("sin hallazgos sin celda no aparece el grupo", () => {
    montar({ hallazgos: hallazgos.slice(0, 2) });
    expect(screen.queryByRole("region", { name: /Sin celda en el libro/ })).not.toBeInTheDocument();
  });

  test("clic en un hallazgo llama a irACelda con la hoja y la celda en base 0", async () => {
    const usuario = userEvent.setup();
    const { irACelda, onElegir } = montar();
    await usuario.click(fila("El total no coincide con la suma de las partidas"));
    expect(onElegir).toHaveBeenCalledWith(0);
    expect(irACelda).toHaveBeenCalledWith({ hoja: "PRESUPUESTO", fila0: 11, columna0: 5 }, 0);
  });

  test("clic en un hallazgo sin celda lo elige pero no mueve la hoja", async () => {
    const usuario = userEvent.setup();
    const { irACelda, onElegir } = montar();
    await usuario.click(fila("El libro no declara la fecha de la portada"));
    expect(onElegir).toHaveBeenCalledWith(2);
    expect(irACelda).not.toHaveBeenCalled();
  });

  test("con el teclado, Enter sobre una fila hace lo mismo que el clic", async () => {
    const usuario = userEvent.setup();
    const { irACelda } = montar();
    fila("Precio unitario distinto al de INSUMOS").focus();
    await usuario.keyboard("{Enter}");
    expect(irACelda).toHaveBeenCalledWith({ hoja: "APU-01", fila0: 47, columna0: 6 }, 1);
  });

  test("la fila elegida se marca con aria-current", () => {
    montar({ seleccionado: 1 });
    expect(fila("Precio unitario distinto al de INSUMOS")).toHaveAttribute("aria-current", "true");
    expect(fila("El total no coincide con la suma de las partidas")).not.toHaveAttribute("aria-current");
  });

  test("enfocar mueve el foco del teclado a la fila pedida", () => {
    montar({ seleccionado: 1, enfocar: { indice: 1, n: 1 } });
    expect(fila("Precio unitario distinto al de INSUMOS")).toHaveFocus();
  });

  test("sin hallazgos dice que el libro no tiene ninguno", () => {
    montar({ hallazgos: [] });
    expect(screen.getByText(/no tiene hallazgos/i)).toBeInTheDocument();
  });
});
