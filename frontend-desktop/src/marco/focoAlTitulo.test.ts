import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { enfocarElTitulo } from "./focoAlTitulo";

// Un contenido con un control que ya tiene el foco y el h1 de la pantalla (o el de un esqueleto).
function montarContenido(h1: string, esqueleto = false) {
  document.body.innerHTML = `<main id="contenido">${esqueleto ? '<h1 data-esqueleto="">Cargando</h1>' : `<h1>${h1}</h1>`}<button type="button">Control</button></main>`;
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

  test("con forzar el título de la ventana dice la pantalla y Sílice", async () => {
    montarContenido("Presupuesto");
    const parar = enfocarElTitulo({ forzar: true });
    await vi.waitFor(() => expect(document.title).toBe("Presupuesto · Sílice"));
    parar();
  });

  test("con forzar no pisa un título que ya empieza con la pantalla", async () => {
    document.title = "Presupuesto · Galpón Sur · Sílice";
    montarContenido("Presupuesto");
    const parar = enfocarElTitulo({ forzar: true });
    await vi.waitFor(() => expect(document.querySelector("h1")).toHaveFocus());
    parar();
    expect(document.title).toBe("Presupuesto · Galpón Sur · Sílice");
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
    expect(document.title).toBe("Mercado · Sílice");
  });
});
