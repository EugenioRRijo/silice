import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { AntesYDespues } from "./AntesYDespues";
import type { AntesYDespuesRespuesta } from "./AntesYDespues";

// Tarea 26 (MP-7): Control de obra muestra el antes y el después de cada partida cuyo APU cambió respecto de la línea
// base (`GET /v1/hoja/antes-y-despues?proyecto=`): costo directo unitario, duración, término y punto de equilibrio. Los
// montos llegan como `{texto, exacto}` con punto decimal y las cifras como texto con punto: la pantalla las formatea una
// sola vez en es-VE. Datos ficticios (la vivienda: OBRA-02 con el concreto premezclado y rendimiento 4).

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["control_de_obra", "editar_hoja"],
  modo_entrega: false,
};

const m = (texto: string, exacto = texto) => ({ texto, exacto });

const RESPUESTA: AntesYDespuesRespuesta = {
  linea_base: "001",
  version: "002",
  moneda: "Bs",
  aviso: null,
  filas: [
    {
      partida: "OBRA-02",
      descripcion: "Concreto para fundaciones",
      unidad: "m3",
      cantidad: "12",
      costo_antes: m("210.33", "210.3333333333333333333333333"),
      costo_despues: m("367.75"),
      duracion_antes: "2",
      duracion_despues: "3",
      termino_antes: 58,
      termino_despues: 59,
      equilibrio_antes: m("30779.97", "30779.9705"),
      equilibrio_despues: m("35123.40", "35123.4012"),
    },
    {
      partida: "OBRA-05",
      descripcion: "Friso liso en paredes",
      unidad: "m2",
      cantidad: "420",
      costo_antes: m("1234.50"),
      costo_despues: m("1300.00"),
      duracion_antes: "23.5",
      duracion_despues: "23.5",
      termino_antes: null,
      termino_despues: null,
      equilibrio_antes: null,
      equilibrio_despues: null,
    },
  ],
};

describe("Control de obra: antes y después de las partidas cambiadas (Tarea 26)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();
  let respuesta: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    respuesta = () => json(RESPUESTA);
    fetchFalso.mockImplementation(async (ruta) => {
      const url = new URL(String(ruta), "http://silice.local");
      if (url.pathname === "/v1/hoja/antes-y-despues") return respuesta();
      return new Response(null, { status: 404 });
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  function montar(proyecto = "Vivienda Demo 80 m2") {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto,
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <AntesYDespues proyecto={proyecto} />
      </ContextoAplicacion.Provider>,
    );
  }

  test("pide la comparación de la obra y dice contra qué línea base compara", async () => {
    montar();
    expect(await screen.findByRole("heading", { name: "Antes y después de las partidas cambiadas" })).toBeInTheDocument();
    const url = new URL(String(fetchFalso.mock.calls[0]![0]), "http://silice.local");
    expect(url.searchParams.get("proyecto")).toBe("Vivienda Demo 80 m2");
    expect(
      screen.getByText(/Compara la versión 002 con la línea base 001/),
    ).toBeInTheDocument();
  });

  test("cada partida dice su costo unitario, su duración, el término y el punto de equilibrio, antes y después, en es-VE", async () => {
    montar();
    const tabla = await screen.findByRole("table", { name: "Antes y después de las partidas cambiadas" });
    const fila = within(tabla).getByRole("row", { name: /OBRA-02/ });
    expect(fila).toHaveTextContent("OBRA-02 · Concreto para fundaciones");
    expect(fila).toHaveTextContent("210,33 Bs pasa a 367,75 Bs");
    expect(fila).toHaveTextContent("2 días pasa a 3 días");
    expect(fila).toHaveTextContent("58 días pasa a 59 días");
    expect(fila).toHaveTextContent("30.779,97 Bs pasa a 35.123,40 Bs");
    // el exacto queda en el title, sin redondear
    expect(within(fila).getByTitle("210.3333333333333333333333333")).toHaveTextContent("210,33");
  });

  test("una duración con medio día se escribe con coma, y lo que no se pudo calcular se dice", async () => {
    montar();
    const tabla = await screen.findByRole("table", { name: "Antes y después de las partidas cambiadas" });
    const fila = within(tabla).getByRole("row", { name: /OBRA-05/ });
    expect(fila).toHaveTextContent("23,5 días pasa a 23,5 días");
    expect(fila).toHaveTextContent("Sin calcular");
  });

  test("sin línea base o sin partidas cambiadas muestra el aviso del servidor y ninguna tabla", async () => {
    const aviso = "Esta obra no tiene línea base: declárela en Control de obra para comparar el antes y el después.";
    respuesta = () => json({ linea_base: null, version: "001", moneda: "Bs", filas: [], aviso });
    montar();
    expect(await screen.findByText(aviso)).toBeInTheDocument();
    expect(screen.queryByRole("table")).toBeNull();
  });

  test("un error de la API se dice con su texto y un 401 cierra la sesión", async () => {
    respuesta = () => json({ detalle: "El proyecto «X» no existe en este caso." }, 404);
    montar();
    expect(await screen.findByText(/El proyecto «X» no existe en este caso\./)).toBeInTheDocument();
    respuesta = () => json({ detalle: "Inicie sesión." }, 401);
    montar("Otra obra");
    await vi.waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("el archivo no convierte cifras (sin Number, parseFloat, toFixed ni + unario)", () => {
    const fuentes = import.meta.glob("./AntesYDespues.tsx", { query: "?raw", import: "default", eager: true }) as Record<
      string,
      string
    >;
    expect(fuentes["./AntesYDespues.tsx"]).not.toMatch(
      /\bNumber\s*\(|\bparseFloat\s*\(|\bparseInt\s*\(|\.toFixed\s*\(|(?:[=(,:?]|\breturn)\s*\+\s*[A-Za-z_$(]/,
    );
  });
});
