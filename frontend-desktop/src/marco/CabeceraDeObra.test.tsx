import { act, render, renderHook, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ErrorDeApi, pedir, type OpcionesDePeticion } from "../api/cliente";
import { ContextoAplicacion } from "../shell/contexto";
import type { Aplicacion } from "../shell/contexto";
import { CabeceraDeObra } from "./CabeceraDeObra";
import { EspacioDeObra } from "./EspacioDeObra";
import { useObraAbierta } from "./obraAbierta";
import { crearVigilante } from "./otraPestana";
import { PATRON_DE_OBRA, rutaDeObra } from "./secciones";
import type { FichaDeLaObra } from "./useFichaDeLaObra";
import type { ObraDeCarpeta } from "./useObras";

vi.mock("../api/cliente", async (importarOriginal) => ({
  ...(await importarOriginal<typeof import("../api/cliente")>()),
  pedir: vi.fn(),
}));
const pedirFalso = vi.mocked(pedir);

// Tarea 1 del plan F4: la cabecera de la obra abierta dice su estado en palabras (con su ícono) y la ficha se pide una
// vez por obra. Tres obras ficticias; los textos de la etapa son los que daría el servidor, escritos a mano.
const NOMBRES = ["Galpón Norte", "Puente Sur", "Depósito Este"];
const OBRAS: ObraDeCarpeta[] = [3, 4, 5].map((id) => ({
  carpeta: null,
  carpeta_titulo: "Carpeta de la empresa",
  obra_id: id,
  obra: NOMBRES[id - 3] ?? "",
  version_codigo: id === 3 ? "002" : null,
}));
const RESUMEN = {
  moneda: "Bs",
  hoy: "2026-10-31",
  obras: [
    { codigo: "3", nombre: "Galpón Norte", etapa: "en_aprobacion", etapa_texto: "En aprobación" },
    { codigo: "4", nombre: "Puente Sur", etapa: "atrasada", etapa_texto: "Atrasada" },
    { codigo: "5", nombre: "Depósito Este", etapa: "en_elaboracion", etapa_texto: "En elaboración" },
  ],
};

// Un servidor de mentira: la carpeta de la empresa ya está abierta, así que entrar en una obra solo la fija en la sesión.
// `resumen` es lo que contesta `GET /v1/obras/resumen` (puede lanzar un error de la API).
function servidor(resumen: () => unknown = () => RESUMEN) {
  const llamadas: string[] = [];
  pedirFalso.mockImplementation(async (ruta: string, opciones: OpcionesDePeticion = {}) => {
    const clave = `${opciones.metodo ?? "GET"} ${ruta}`;
    llamadas.push(clave);
    switch (clave) {
      case "GET /v1/obras/todas":
        return { carpeta_actual: null, obras: OBRAS };
      case "PUT /v1/sesion/proyecto":
        return undefined;
      case "GET /v1/obras/resumen":
        return resumen();
    }
    throw new Error(`Ruta inesperada: ${clave}`);
  });
  return { resumenes: () => llamadas.filter((c) => c === "GET /v1/obras/resumen").length };
}

// La sección de prueba: un h1, botones para cambiar de sección o de obra y uno que pide recargar la ficha.
function SeccionDePrueba({ pagina }: { pagina: string }) {
  const navegar = useNavigate();
  const { recargarFicha } = useObraAbierta();
  return (
    <div>
      <h1>{`Sección ${pagina}`}</h1>
      <button type="button" onClick={() => navegar(rutaDeObra(null, 3, "mercado"))}>
        Ir a Mercado
      </button>
      <button type="button" onClick={() => navegar(rutaDeObra(null, 4, "resumen"))}>
        Ir a la obra 4
      </button>
      <button type="button" onClick={recargarFicha}>
        Recargar ficha
      </button>
    </div>
  );
}

function montar(ruta: string) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <Routes>
        <Route
          path={PATRON_DE_OBRA}
          element={
            <EspacioDeObra
              obras={OBRAS}
              casos={null}
              alEntrar={() => undefined}
              pantalla={(pagina) => <SeccionDePrueba pagina={pagina} />}
              vigilante={crearVigilante(null)}
            />
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}
const cabecera = () => screen.getByRole("region", { name: "Obra abierta" });

describe("CabeceraDeObra: el estado de la obra", () => {
  afterEach(() => pedirFalso.mockReset());

  it("muestra el estado de la obra en palabras", async () => {
    servidor();
    montar(rutaDeObra(null, 3, "resumen"));
    await screen.findByRole("heading", { level: 1 });
    await waitFor(() => expect(cabecera()).toHaveTextContent("Estado: En aprobación"));
    expect(cabecera()).toHaveTextContent("Versión: 002");
  });

  it("obra atrasada lleva el ícono de advertencia junto a la palabra", async () => {
    servidor();
    montar(rutaDeObra(null, 4, "resumen"));
    const palabra = await within(await screen.findByRole("region", { name: "Obra abierta" })).findByText("Atrasada");
    // El ícono es decorativo (aria-hidden) y va dentro de la misma etiqueta que la palabra: el color no va solo.
    expect(palabra.querySelector('svg[aria-hidden="true"]')).not.toBeNull();
  });

  it("las demás etapas llevan también su ícono y su palabra, pero no el color de atrasada", async () => {
    servidor();
    montar(rutaDeObra(null, 5, "resumen"));
    const palabra = await within(await screen.findByRole("region", { name: "Obra abierta" })).findByText("En elaboración");
    expect(palabra.querySelector('svg[aria-hidden="true"]')).not.toBeNull();
    expect(palabra.className).not.toContain("atrasada");
  });

  it("sin permiso no dice el estado y la sección se monta igual", async () => {
    const api = servidor(() => {
      throw new ErrorDeApi(403, "No puede");
    });
    montar(rutaDeObra(null, 3, "resumen"));
    expect(await screen.findByRole("heading", { level: 1, name: "Sección obras" })).toBeInTheDocument();
    await waitFor(() => expect(api.resumenes()).toBe(1));
    await act(async () => undefined);
    expect(cabecera()).not.toHaveTextContent("Estado:");
    expect(cabecera()).toHaveTextContent("Galpón Norte");
  });

  it("sin la fila de la obra no dice el estado y la sección se monta igual", async () => {
    const api = servidor(() => ({ ...RESUMEN, obras: RESUMEN.obras.filter((o) => o.codigo !== "3") }));
    montar(rutaDeObra(null, 3, "resumen"));
    expect(await screen.findByRole("heading", { level: 1, name: "Sección obras" })).toBeInTheDocument();
    await waitFor(() => expect(api.resumenes()).toBe(1));
    await act(async () => undefined);
    expect(cabecera()).not.toHaveTextContent("Estado:");
  });

  it("la ficha se pide una vez por obra", async () => {
    const u = userEvent.setup();
    const api = servidor();
    montar(rutaDeObra(null, 3, "resumen"));
    await waitFor(() => expect(cabecera()).toHaveTextContent("Estado: En aprobación"));
    expect(api.resumenes()).toBe(1);

    // Otra sección de la misma obra: no repite.
    await u.click(screen.getByRole("button", { name: "Ir a Mercado" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Sección mercado" })).toBeInTheDocument();
    expect(cabecera()).toHaveTextContent("Estado: En aprobación");
    expect(api.resumenes()).toBe(1);

    // Otra obra: sí.
    await u.click(screen.getByRole("button", { name: "Ir a la obra 4" }));
    await waitFor(() => expect(cabecera()).toHaveTextContent("Estado: Atrasada"));
    expect(api.resumenes()).toBe(2);
  });

  it("recargarFicha vuelve a pedir el resumen", async () => {
    const u = userEvent.setup();
    const api = servidor();
    montar(rutaDeObra(null, 3, "resumen"));
    await waitFor(() => expect(cabecera()).toHaveTextContent("Estado: En aprobación"));
    await u.click(screen.getByRole("button", { name: "Recargar ficha" }));
    await waitFor(() => expect(api.resumenes()).toBe(2));
  });
});

// La carpeta no declara moneda: la línea de la lista dice la de la obra, que la cabecera toma de su ficha y le pasa.
describe("CabeceraDeObra: la moneda de la obra llega a la lista de la carpeta", () => {
  afterEach(() => pedirFalso.mockReset());
  const aplicacion = { alExpirar: vi.fn() } as unknown as Aplicacion;
  const FILA = { ...RESUMEN.obras[0]!, cliente: "Cliente Demo", version: "002", total: null, moneda: "USD", avance_real: null, avance_plan: null, que_pasa: null, siguiente: null, version_de_linea_base: false };

  function montarCabecera(ficha: FichaDeLaObra) {
    pedirFalso.mockImplementation(async (ruta: string) => {
      if (ruta === "/v1/carpeta") return { moneda: null, declarada: false, lista: null, aviso: "Sin lista para armar" };
      throw new Error(`Ruta inesperada: ${ruta}`);
    });
    render(
      <ContextoAplicacion.Provider value={aplicacion}>
        <CabeceraDeObra carpeta={null} obraId={3} nombre="Galpón Norte" version="002" ficha={ficha} />
      </ContextoAplicacion.Provider>,
    );
  }

  it("con la ficha lista dice la moneda de la obra y el aviso de la carpeta", async () => {
    montarCabecera({ estado: "lista", obra: { ...FILA, etapa: "en_aprobacion" } });
    expect(await within(cabecera()).findByText("Moneda: USD · Sin lista para armar")).toBeInTheDocument();
  });

  it("sin dato de la ficha la carpeta sigue sin moneda declarada", async () => {
    montarCabecera({ estado: "sin_dato" });
    expect(await within(cabecera()).findByText("Carpeta sin moneda declarada")).toBeInTheDocument();
  });

  it("mientras la ficha carga dice que lee la moneda", async () => {
    montarCabecera({ estado: "cargando" });
    expect(await within(cabecera()).findByText("Leyendo la moneda de la carpeta…")).toBeInTheDocument();
  });
});

describe("useObraAbierta", () => {
  it("fuera de una obra lanza un error con mensaje claro", () => {
    const aviso = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() => renderHook(() => useObraAbierta())).toThrow(/fuera de una obra abierta/);
    aviso.mockRestore();
  });
});
