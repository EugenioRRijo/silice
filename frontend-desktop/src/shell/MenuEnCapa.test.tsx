import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, test, vi } from "vitest";
import { MenuEnCapa } from "./MenuEnCapa";
import { navegacion, type EntradaNav } from "./navegacion";
import { PAGINAS } from "./rutas";

const TODAS = [...new Set(PAGINAS.flatMap((p) => (p.accion ? [p.accion] : [])))];

function idsDe(entradas: readonly EntradaNav[]): string[] {
  return entradas.flatMap((e) => (e.tipo === "enlace" ? [e.pagina.id] : e.grupos.flatMap((g) => g.paginas.map((p) => p.id))));
}

function pintar(props: Partial<React.ComponentProps<typeof MenuEnCapa>> = {}) {
  const alCerrar = vi.fn();
  const entradas = navegacion("obras", TODAS, false);
  render(
    <MemoryRouter initialEntries={["/"]}>
      <MenuEnCapa entradas={entradas} abierto alCerrar={alCerrar} {...props} />
    </MemoryRouter>,
  );
  return { alCerrar, entradas };
}

describe("MenuEnCapa", () => {
  test("abierto muestra todas las paginas de la navegacion, cada una una sola vez", () => {
    const { entradas } = pintar();
    const nav = screen.getByRole("navigation", { name: "Menú principal (capa)", hidden: true });
    const enlaces = within(nav).getAllByRole("link", { hidden: true });
    const esperados = idsDe(entradas);
    expect(enlaces).toHaveLength(esperados.length);
    const titulos = esperados.map((id) => PAGINAS.find((p) => p.id === id)!.titulo);
    expect(enlaces.map((a) => a.querySelector(".silice-capa__nombre")?.textContent)).toEqual(titulos);
  });

  test("cada area lleva su rotulo de texto", () => {
    pintar();
    for (const t of ["Obras", "Partidas", "Mercado", "Control"]) expect(screen.getAllByText(t, { selector: ".silice-capa__rotulo" }).length).toBeGreaterThan(0);
  });

  // Diseno §1 y §5.1: un area de una sola pantalla es un enlace directo; repetir su nombre como rotulo y como enlace
  // («Inicio / Inicio») reproduce el doble que la barra quiso quitar.
  test("un area de una sola pantalla no repite su nombre: sin rotulo, solo el enlace con su ayuda", () => {
    const { entradas } = pintar();
    const nav = screen.getByRole("navigation", { name: "Menú principal (capa)", hidden: true });
    const enlaces = entradas.filter((e) => e.tipo === "enlace");
    expect(enlaces.map((e) => e.area)).toEqual(["inicio"]);
    for (const e of enlaces) {
      if (e.tipo !== "enlace") continue;
      expect(within(nav).queryAllByText(e.titulo, { selector: ".silice-capa__rotulo" })).toHaveLength(0);
      expect(within(nav).getAllByText(e.pagina.titulo)).toHaveLength(1);
      const enlace = within(nav).getByRole("link", { name: new RegExp(`^${e.pagina.titulo}`), hidden: true });
      const idAyuda = enlace.getAttribute("aria-describedby") ?? "";
      expect(document.getElementById(idAyuda)?.textContent).toBe(e.pagina.enUnaLinea);
    }
    // Las areas con panel conservan su rotulo.
    expect(within(nav).queryAllByText("Inicio", { selector: ".silice-capa__rotulo" })).toHaveLength(0);
    expect(within(nav).getAllByText("Obras", { selector: ".silice-capa__rotulo" })).toHaveLength(1);
  });

  test("cada enlace describe su pagina con su linea de ayuda", () => {
    const { entradas } = pintar();
    for (const id of idsDe(entradas)) {
      const p = PAGINAS.find((x) => x.id === id)!;
      const enlace = screen.getByRole("link", { name: new RegExp(`^${p.titulo}`), hidden: true });
      const ids = (enlace.getAttribute("aria-describedby") ?? "").split(" ");
      expect(ids.length).toBeGreaterThan(0);
      expect(document.getElementById(ids[0])?.textContent).toBe(p.enUnaLinea);
    }
  });

  test("elegir un enlace llama alCerrar", async () => {
    const { alCerrar } = pintar();
    await userEvent.click(screen.getAllByRole("link", { hidden: true })[0]);
    expect(alCerrar).toHaveBeenCalledTimes(1);
  });

  test("Esc llama alCerrar", async () => {
    const { alCerrar } = pintar();
    screen.getAllByRole("link", { hidden: true })[0].focus();
    await userEvent.keyboard("{Escape}");
    expect(alCerrar).toHaveBeenCalledTimes(1);
  });

  test("con nombre muestra la sesion al pie; sin nombre no", () => {
    pintar({ nombre: "Ana" });
    expect(screen.getByText("Sesión de Ana")).toBeTruthy();
  });

  test("sin nombre no hay pie de sesion", () => {
    pintar();
    expect(screen.queryByText(/Sesión de/)).toBeNull();
  });
});
