import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { enfocarElTitulo, nombrarLaVentana } from "./focoAlTitulo";

// Un control fuera del contenido (el enlace de la barra) que ya tiene el foco y el contenido con el h1 de la pantalla (o el
// de un esqueleto).
function montarContenido(h1: string, esqueleto = false) {
  document.body.innerHTML = `<button type="button">Control</button><main id="contenido">${esqueleto ? '<h1 data-esqueleto="">Cargando</h1>' : `<h1>${h1}</h1>`}</main>`;
  const boton = document.querySelector("button") as HTMLButtonElement;
  boton.focus();
  return boton;
}

describe("enfocarElTitulo", () => {
  let titulo: string;
  beforeEach(() => {
    titulo = document.title;
    document.title = "Antes";
  });
  afterEach(() => {
    document.body.innerHTML = "";
    document.title = titulo;
  });

  test("sin opciones no toca el foco si lo tiene otro control (la obra al reintentar)", async () => {
    const boton = montarContenido("Presupuesto");
    const parar = enfocarElTitulo();
    await new Promise((r) => setTimeout(r, 60));
    parar();
    expect(boton).toHaveFocus();
    expect(document.title).toBe("Antes");
  });

  test("con forzar el foco pasa al h1 con tabindex -1 aunque otro control lo tenga", async () => {
    montarContenido("Presupuesto");
    const parar = enfocarElTitulo({ forzar: true });
    await vi.waitFor(() => expect(document.querySelector("h1")).toHaveFocus());
    parar();
    expect(document.querySelector("h1")).toHaveAttribute("tabindex", "-1");
  });

  test("con forzar NO toca el título de la ventana: tiene una sola fuente (el marco)", async () => {
    document.title = "Resumen · Casa Demo · Sílice";
    montarContenido("Resumen de la obra");
    const parar = enfocarElTitulo({ forzar: true });
    await vi.waitFor(() => expect(document.querySelector("h1")).toHaveFocus());
    parar();
    expect(document.title).toBe("Resumen · Casa Demo · Sílice");
  });

  test("con forzar respeta el foco que la pantalla nueva ya puso en su propio contenido", async () => {
    montarContenido("Presupuesto");
    const campo = document.createElement("input");
    document.querySelector("#contenido")?.append(campo);
    campo.focus();
    const parar = enfocarElTitulo({ forzar: true });
    await new Promise((r) => setTimeout(r, 60));
    parar();
    expect(campo).toHaveFocus();
  });

  test("al enfocar avisa con el h1 (alEnfocar)", async () => {
    montarContenido("Presupuesto");
    const alEnfocar = vi.fn();
    const parar = enfocarElTitulo({ forzar: true, alEnfocar });
    await vi.waitFor(() => expect(alEnfocar).toHaveBeenCalledWith(document.querySelector("h1")));
    parar();
  });

  test("nombrarLaVentana pone «pantalla · Sílice» y deja el título que ya empieza con la pantalla", () => {
    document.title = "Antes";
    nombrarLaVentana("Mercado");
    expect(document.title).toBe("Mercado · Sílice");
    document.title = "Mercado · Galpón Sur · Sílice";
    nombrarLaVentana("Mercado");
    expect(document.title).toBe("Mercado · Galpón Sur · Sílice");
    nombrarLaVentana("");
    expect(document.title).toBe("Mercado · Galpón Sur · Sílice");
  });

  test("con forzar espera el h1 real: el de un esqueleto no cuenta y el título queda como estaba", async () => {
    const boton = montarContenido("", true);
    const parar = enfocarElTitulo({ forzar: true });
    await new Promise((r) => setTimeout(r, 60));
    expect(boton).toHaveFocus();
    expect(document.title).toBe("Antes");
    document.querySelector("h1")?.removeAttribute("data-esqueleto");
    (document.querySelector("h1") as HTMLElement).textContent = "Mercado";
    await vi.waitFor(() => expect(document.querySelector("h1")).toHaveFocus());
    parar();
    expect(document.title).toBe("Antes");
  });
});
