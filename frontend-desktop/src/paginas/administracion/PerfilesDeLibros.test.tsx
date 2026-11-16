import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PerfilesDeLibros from "./PerfilesDeLibros";

// Libro por frentes (ola 2, línea 3, 2026-11-13): quien administra pone un perfil del libro con un APU por hoja desde la
// interfaz (`POST /v1/admin/empresa/perfiles-libros`); antes se copiaba a mano el JSON a la carpeta de datos. El servidor
// lo valida entero y no pisa uno que ya está sin «Reemplazar». Datos FICTICIOS.
const PUESTO = {
  nombre: "obra_local",
  origen: "local",
  hoja_presupuesto: "FRENTE A",
  hojas_presupuesto: ["FRENTE A", "FRENTE B"],
  motivo: null,
};

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

function montar() {
  const valor = { alExpirar: vi.fn() } as unknown as Aplicacion;
  return render(
    <ContextoAplicacion.Provider value={valor}>
      <PerfilesDeLibros />
    </ContextoAplicacion.Provider>,
  );
}

describe("Perfiles de los libros de la empresa", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let usuario: ReturnType<typeof userEvent.setup>;
  const campo = () => document.querySelector<HTMLInputElement>('input[type="file"]')!;

  beforeEach(() => {
    usuario = userEvent.setup({ applyAccept: false });
    fijarCsrf("tok");
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fetchFalso.mockResolvedValue(json(PUESTO, 201));
  });
  afterEach(() => vi.unstubAllGlobals());

  test("sube el JSON y dice qué hojas lee el perfil puesto", async () => {
    montar();
    expect(screen.getByRole("heading", { name: "Perfiles de los libros de la empresa" })).toBeInTheDocument();
    const boton = screen.getByRole("button", { name: "Poner el perfil" });
    expect(boton).toBeDisabled();
    await usuario.upload(campo(), new File(['{"nombre":"obra_local"}'], "obra_local.json", { type: "application/json" }));
    await usuario.click(boton);
    await waitFor(() => expect(fetchFalso).toHaveBeenCalledTimes(1));
    const [ruta, opciones] = fetchFalso.mock.calls[0]!;
    expect(ruta).toBe("/v1/admin/empresa/perfiles-libros");
    const cuerpo = opciones?.body as FormData;
    expect((cuerpo.get("perfil") as File).name).toBe("obra_local.json");
    expect(cuerpo.get("reemplazar")).toBe("false");
    expect(
      await screen.findByText("Perfil «obra_local» puesto en esta instalación: lee las hojas FRENTE A y FRENTE B."),
    ).toBeInTheDocument();
  });

  test("si ya hay uno con ese nombre, dice el motivo y deja reemplazarlo", async () => {
    fetchFalso.mockResolvedValueOnce(
      json({ detalle: "Ya hay un perfil «obra_local» en esta instalación: marque «Reemplazar» para cambiarlo." }, 409),
    );
    montar();
    await usuario.upload(campo(), new File(["{}"], "obra_local.json", { type: "application/json" }));
    await usuario.click(screen.getByRole("button", { name: "Poner el perfil" }));
    expect(await screen.findByText(/Ya hay un perfil «obra_local»/)).toBeInTheDocument();
    await usuario.click(screen.getByRole("checkbox", { name: "Reemplazar el que ya está con ese nombre" }));
    fetchFalso.mockResolvedValueOnce(json(PUESTO, 200));
    await usuario.click(screen.getByRole("button", { name: "Poner el perfil" }));
    await waitFor(() => expect(fetchFalso).toHaveBeenCalledTimes(2));
    expect((fetchFalso.mock.calls[1]![1]?.body as FormData).get("reemplazar")).toBe("true");
    expect(await screen.findByText(/Perfil «obra_local» puesto en esta instalación/)).toBeInTheDocument();
  });
});
