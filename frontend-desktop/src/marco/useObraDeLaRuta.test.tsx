import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ErrorDeApi, pedir, type OpcionesDePeticion } from "../api/cliente";
import { busDePestanas } from "../test/pestanasFalsas";
import { crearVigilante, type VigilanteDeObra } from "./otraPestana";
import { PATRON_DE_OBRA, rutaDeObra } from "./secciones";
import { useObraDeLaRuta } from "./useObraDeLaRuta";

vi.mock("../api/cliente", async (importarOriginal) => ({
  ...(await importarOriginal<typeof import("../api/cliente")>()),
  pedir: vi.fn(),
}));

const pedirFalso = vi.mocked(pedir);

// Carpetas y obras inventadas.
const NORTE = "Carpeta Norte.db";
const SUR = "Carpeta Sur.db";
const OBRAS: [string | null, number][] = [
  [null, 1],
  [NORTE, 1],
  [NORTE, 2],
  [SUR, 3],
];

interface Llamada {
  clave: string;
  cuerpo: unknown;
}

// Un servidor de mentira con la carpeta abierta de la sesion. `retener` deja una peticion colgada hasta que la prueba
// la suelta; `fallarUnaVez` hace que la proxima peticion con esa clave conteste con ese error.
function servidor(abierta: string | null) {
  const estado = { abierta };
  const llamadas: Llamada[] = [];
  const fallos = new Map<string, ErrorDeApi>();
  const retenidas = new Map<string, Promise<void>>();
  pedirFalso.mockImplementation(async (ruta: string, opciones: OpcionesDePeticion = {}) => {
    const clave = `${opciones.metodo ?? "GET"} ${ruta}`;
    const cuerpo = opciones.cuerpo as Record<string, unknown> | undefined;
    llamadas.push({ clave, cuerpo: cuerpo ?? null });
    const retenida = retenidas.get(clave);
    if (retenida) {
      retenidas.delete(clave);
      await retenida;
    }
    const fallo = fallos.get(clave);
    if (fallo) {
      fallos.delete(clave);
      throw fallo;
    }
    switch (clave) {
      case "GET /v1/obras/todas":
        return {
          carpeta_actual: estado.abierta,
          obras: OBRAS.map(([carpeta, obra_id]) => ({
            carpeta,
            carpeta_titulo: carpeta ?? "Carpeta de la empresa",
            obra_id,
            obra: `Obra ${obra_id}`,
            version_codigo: null,
          })),
        };
      case "POST /v1/casos/actual":
        estado.abierta = String(cuerpo?.nombre);
        return { nombre: estado.abierta, ruta_relativa: estado.abierta };
      case "DELETE /v1/casos/actual":
        estado.abierta = null;
        return { nombre: "empresa.db", ruta_relativa: "empresa.db" };
      case "PUT /v1/sesion/proyecto":
        return undefined;
    }
    throw new Error(`Ruta inesperada: ${clave}`);
  });
  return {
    estado,
    llamadas,
    escrituras: () =>
      llamadas.filter((l) => !l.clave.startsWith("GET ")).map((l) => `${l.clave} ${JSON.stringify(l.cuerpo)}`),
    fallarUnaVez(clave: string, error: ErrorDeApi) {
      fallos.set(clave, error);
    },
    retener(clave: string): () => void {
      let soltar!: () => void;
      retenidas.set(clave, new Promise<void>((r) => (soltar = r)));
      return () => soltar();
    },
  };
}

function montar(ruta: string, vigilante: VigilanteDeObra = crearVigilante(null)) {
  const envoltura = ({ children }: { children: ReactNode }) => (
    <MemoryRouter initialEntries={[ruta]}>
      <Routes>
        <Route path={PATRON_DE_OBRA} element={children} />
      </Routes>
    </MemoryRouter>
  );
  return renderHook(() => ({ estado: useObraDeLaRuta({ vigilante }), navegar: useNavigate() }), { wrapper: envoltura });
}

const PUT_3 = 'PUT /v1/sesion/proyecto {"proyecto":"3"}';

describe("useObraDeLaRuta", () => {
  afterEach(() => {
    pedirFalso.mockReset();
  });

  it("en la misma carpeta solo fija la obra en la sesion", async () => {
    const api = servidor(SUR);
    const { result } = montar(rutaDeObra(SUR, 3, "presupuesto"));
    expect(result.current.estado.tipo).toBe("cargando");

    await waitFor(() => expect(result.current.estado.tipo).toBe("lista"));
    expect(api.escrituras()).toEqual([PUT_3]);
    const estado = result.current.estado;
    if (estado.tipo !== "lista") throw new Error("no quedo lista");
    expect(estado.carpeta).toBe(SUR);
    expect(estado.obraId).toBe(3);
    expect(estado.seccion.id).toBe("presupuesto");
  });

  it("en otra carpeta la abre y despues fija la obra, en ese orden, y solo entonces queda lista", async () => {
    const api = servidor(NORTE);
    const soltarPut = api.retener("PUT /v1/sesion/proyecto");
    const { result } = montar(rutaDeObra(SUR, 3, "resumen"));

    await waitFor(() => expect(api.llamadas.map((l) => l.clave)).toContain("PUT /v1/sesion/proyecto"));
    expect(result.current.estado.tipo).toBe("cargando");
    soltarPut();

    await waitFor(() => expect(result.current.estado.tipo).toBe("lista"));
    expect(api.escrituras()).toEqual([`POST /v1/casos/actual {"nombre":"${SUR}"}`, PUT_3]);
  });

  it("la ruta «empresa» con otra carpeta abierta vuelve a la de la empresa", async () => {
    const api = servidor(NORTE);
    const { result } = montar("/obra/empresa/1/resumen");

    await waitFor(() => expect(result.current.estado.tipo).toBe("lista"));
    expect(api.escrituras()).toEqual(["DELETE /v1/casos/actual null", 'PUT /v1/sesion/proyecto {"proyecto":"1"}']);
    const estado = result.current.estado;
    if (estado.tipo === "lista") expect(estado.carpeta).toBeNull();
  });

  it("la ruta «empresa» con la de la empresa abierta no cambia de carpeta", async () => {
    const api = servidor(null);
    const { result } = montar("/obra/empresa/1/resumen");

    await waitFor(() => expect(result.current.estado.tipo).toBe("lista"));
    expect(api.escrituras()).toEqual(['PUT /v1/sesion/proyecto {"proyecto":"1"}']);
  });

  it("una obra que ya no existe (enlace viejo) da no_existe sin escribir nada", async () => {
    const api = servidor(SUR);
    const { result } = montar(rutaDeObra(SUR, 99, "presupuesto"));

    await waitFor(() => expect(result.current.estado.tipo).toBe("no_existe"));
    expect(api.escrituras()).toEqual([]);
  });

  it("una carpeta que ya no existe da no_existe sin escribir nada", async () => {
    const api = servidor(SUR);
    const { result } = montar(rutaDeObra("Carpeta Borrada.db", 3, "presupuesto"));

    await waitFor(() => expect(result.current.estado.tipo).toBe("no_existe"));
    expect(api.escrituras()).toEqual([]);
  });

  it.each([
    ["POST /v1/casos/actual", 404],
    ["POST /v1/casos/actual", 403],
    ["PUT /v1/sesion/proyecto", 404],
  ])("%s con %i da no_existe", async (clave, codigo) => {
    const api = servidor(NORTE);
    api.fallarUnaVez(clave, new ErrorDeApi(codigo, "No."));
    const { result } = montar(rutaDeObra(SUR, 3, "presupuesto"));

    await waitFor(() => expect(result.current.estado.tipo).toBe("no_existe"));
  });

  it("una seccion desconocida o sin pantalla, o un numero de obra roto, da no_existe sin pedir nada", async () => {
    servidor(SUR);
    for (const ruta of ["/obra/Carpeta%20Sur.db/3/tablero", "/obra/Carpeta%20Sur.db/3/archivos", "/obra/Carpeta%20Sur.db/x/resumen", "/obra/Carpeta%20Sur.db/0/resumen"]) {
      const { result, unmount } = montar(ruta);
      expect(result.current.estado.tipo, ruta).toBe("no_existe");
      unmount();
    }
    await act(async () => {});
    expect(pedirFalso).not.toHaveBeenCalled();
  });

  it("otro fallo deja un error que se puede reintentar", async () => {
    const api = servidor(NORTE);
    api.fallarUnaVez("POST /v1/casos/actual", new ErrorDeApi(500, "Se cayo."));
    const { result } = montar(rutaDeObra(SUR, 3, "presupuesto"));

    await waitFor(() => expect(result.current.estado.tipo).toBe("error"));
    expect(api.escrituras()).toEqual([`POST /v1/casos/actual {"nombre":"${SUR}"}`]);
    const estado = result.current.estado;
    if (estado.tipo !== "error") throw new Error("no hubo error");

    act(() => estado.reintentar());
    expect(result.current.estado.tipo).toBe("cargando");
    await waitFor(() => expect(result.current.estado.tipo).toBe("lista"));
    expect(api.escrituras()).toEqual([
      `POST /v1/casos/actual {"nombre":"${SUR}"}`,
      `POST /v1/casos/actual {"nombre":"${SUR}"}`,
      PUT_3,
    ]);
  });

  it("cambiar de seccion dentro de la misma obra no vuelve a pedir nada", async () => {
    const api = servidor(SUR);
    const { result } = montar(rutaDeObra(SUR, 3, "presupuesto"));
    await waitFor(() => expect(result.current.estado.tipo).toBe("lista"));
    const antes = api.llamadas.length;

    act(() => void result.current.navegar(rutaDeObra(SUR, 3, "control")));

    const estado = result.current.estado;
    if (estado.tipo !== "lista") throw new Error(`quedo ${estado.tipo}`);
    expect(estado.seccion.id).toBe("control");
    await act(async () => {});
    expect(api.llamadas.length).toBe(antes);
  });

  it("una navegacion nueva cancela la anterior: la respuesta vieja no pisa el estado ni sigue escribiendo", async () => {
    const api = servidor(SUR);
    const soltarNorte = api.retener("POST /v1/casos/actual");
    const { result } = montar(rutaDeObra(NORTE, 1, "presupuesto"));
    await waitFor(() => expect(api.llamadas.map((l) => l.clave)).toContain("POST /v1/casos/actual"));

    act(() => void result.current.navegar(rutaDeObra(SUR, 3, "presupuesto")));
    expect(result.current.estado.tipo).toBe("cargando");
    // La de Sur espera a que termine lo que la de Norte ya mando: el servidor no recibe dos cambios cruzados.
    await act(async () => {});
    expect(api.llamadas.map((l) => l.clave)).toEqual(["GET /v1/obras/todas", "POST /v1/casos/actual"]);

    soltarNorte();
    await waitFor(() => expect(result.current.estado.tipo).toBe("lista"));
    expect(api.escrituras()).toEqual([
      `POST /v1/casos/actual {"nombre":"${NORTE}"}`,
      `POST /v1/casos/actual {"nombre":"${SUR}"}`,
      PUT_3,
    ]);
    expect(api.estado.abierta).toBe(SUR);
    const estado = result.current.estado;
    if (estado.tipo === "lista") expect([estado.carpeta, estado.obraId]).toEqual([SUR, 3]);
  });

  it("si otra pestaña abre otra obra, esta pasa a en_otra_pestana y «retomar» la vuelve a tomar", async () => {
    const api = servidor(SUR);
    const bus = busDePestanas();
    const otra = crearVigilante(bus.canal());
    const avisoEnLaOtra = vi.fn();
    otra.escucharOtraPestana(avisoEnLaOtra);
    const { result } = montar(rutaDeObra(SUR, 3, "presupuesto"), crearVigilante(bus.canal()));
    await waitFor(() => expect(result.current.estado.tipo).toBe("lista"));

    // La otra pestaña toma la sesion con una obra de otra carpeta.
    api.estado.abierta = NORTE;
    act(() => {
      otra.anunciarObra(NORTE, 2);
    });
    const estado = result.current.estado;
    if (estado.tipo !== "en_otra_pestana") throw new Error(`quedo ${estado.tipo}`);
    const antes = api.escrituras().length;

    act(() => estado.retomar());
    await waitFor(() => expect(result.current.estado.tipo).toBe("lista"));
    expect(api.escrituras().slice(antes)).toEqual([`POST /v1/casos/actual {"nombre":"${SUR}"}`, PUT_3]);
    expect(avisoEnLaOtra).toHaveBeenCalledWith({ carpeta: SUR, obraId: 3 });
  });

  it("si otra pestaña anuncia la misma obra, esta sigue lista", async () => {
    servidor(SUR);
    const bus = busDePestanas();
    const otra = crearVigilante(bus.canal());
    const { result } = montar(rutaDeObra(SUR, 3, "presupuesto"), crearVigilante(bus.canal()));
    await waitFor(() => expect(result.current.estado.tipo).toBe("lista"));

    act(() => otra.anunciarObra(SUR, 3));
    expect(result.current.estado.tipo).toBe("lista");
  });
});
