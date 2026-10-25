import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useNavigate } from "react-router";
import { afterEach, describe, expect, test } from "vitest";
import { BotonRecorrido, ColumnaRecorrido } from "./ColumnaRecorrido";
import { RECORRIDO_AUDITAR, iniciarRecorrido, recorridoEnCurso, terminarRecorrido } from "./recorrido";
import type { PaginaDef } from "./rutas";

const migrada = async () => ({ default: () => null });
const PAGINAS: PaginaDef[] = [
  { id: "inicio", titulo: "Inicio", enUnaLinea: "Pantalla de prueba", seccion: "Trabajo", accion: null, cargar: migrada },
  { id: "libros", titulo: "Libro de la empresa", enUnaLinea: "Pantalla de prueba", seccion: "Revisión", accion: "leer_proyecto", cargar: migrada },
  { id: "historial", titulo: "Historial de auditorías", enUnaLinea: "Pantalla de prueba", seccion: "Revisión", accion: "leer_proyecto", cargar: migrada },
  { id: "tablero", titulo: "Tablero del proyecto", enUnaLinea: "Pantalla de prueba", seccion: "Trabajo", accion: "leer_proyecto", cargar: migrada },
];

function Ir() {
  const navegar = useNavigate();
  return (
    <button type="button" onClick={() => navegar("/tablero")}>
      Ir al tablero
    </button>
  );
}

function montar(ruta = "/libros") {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <BotonRecorrido />
      <ColumnaRecorrido paginas={PAGINAS} acciones={["leer_proyecto"]} modoEntrega={false} />
      <Ir />
      <main id="contenido">
        <h1>Libro de la empresa</h1>
      </main>
    </MemoryRouter>,
  );
}

describe("ColumnaRecorrido", () => {
  afterEach(() => terminarRecorrido());

  test("sin recorrido no se pinta nada: ni la columna ni el boton", () => {
    montar();
    expect(screen.queryByRole("complementary", { name: "Recorrido" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Recorrido" })).not.toBeInTheDocument();
  });

  test("con un recorrido aparece la region «Recorrido» con sus pasos y sin boton en la barra", () => {
    iniciarRecorrido(RECORRIDO_AUDITAR);
    montar();
    const columna = screen.getByRole("complementary", { name: "Recorrido" });
    expect(within(columna).getByText("Lea el resumen y los hallazgos")).toBeInTheDocument();
    expect(within(columna).getByText("Suba el libro")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Recorrido" })).not.toBeInTheDocument();
  });

  test("«Ocultar» la oculta y aparece el boton; pulsarlo la muestra de nuevo", async () => {
    const usuario = userEvent.setup();
    iniciarRecorrido(RECORRIDO_AUDITAR);
    montar();
    await usuario.click(screen.getByRole("button", { name: "Ocultar" }));
    expect(screen.queryByRole("complementary", { name: "Recorrido" })).not.toBeInTheDocument();
    expect(recorridoEnCurso()).not.toBeNull();
    await usuario.click(screen.getByRole("button", { name: "Recorrido" }));
    expect(screen.getByRole("complementary", { name: "Recorrido" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Recorrido" })).not.toBeInTheDocument();
  });

  test("«Terminar recorrido» lo cierra y el foco va al h1 de la pagina", async () => {
    const usuario = userEvent.setup();
    iniciarRecorrido(RECORRIDO_AUDITAR);
    montar();
    await usuario.click(screen.getByRole("button", { name: "Terminar recorrido" }));
    expect(recorridoEnCurso()).toBeNull();
    expect(screen.queryByRole("complementary", { name: "Recorrido" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1 })).toHaveFocus();
  });

  test("navegar a otra ruta no la cierra", async () => {
    const usuario = userEvent.setup();
    iniciarRecorrido(RECORRIDO_AUDITAR);
    montar();
    await usuario.click(screen.getByRole("button", { name: "Ir al tablero" }));
    expect(screen.getByRole("complementary", { name: "Recorrido" })).toBeInTheDocument();
    expect(recorridoEnCurso()).not.toBeNull();
  });

  test("aparece cuando se inicia con la columna ya montada", () => {
    montar();
    act(() => iniciarRecorrido(RECORRIDO_AUDITAR));
    expect(screen.getByRole("complementary", { name: "Recorrido" })).toBeInTheDocument();
  });

  test("tras terminar un recorrido oculto, el siguiente empieza a la vista", async () => {
    const usuario = userEvent.setup();
    iniciarRecorrido(RECORRIDO_AUDITAR);
    montar();
    await usuario.click(screen.getByRole("button", { name: "Ocultar" }));
    act(() => terminarRecorrido());
    act(() => iniciarRecorrido(RECORRIDO_AUDITAR));
    expect(screen.getByRole("complementary", { name: "Recorrido" })).toBeInTheDocument();
  });
});
