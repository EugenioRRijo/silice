import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { formulariosSucios, olvidarFormularios } from "../../shell/sucio";
import { ComponerPartida } from "./ComponerPartida";
import type { PartidaCompuesta } from "./ComponerPartida";

// Tarea 9 del plan F4: la composición de una partida, sin h1 ni navegación, para la pantalla «Componer una partida» (que
// sigue en Ctrl+K hasta F5) y para el panel de «Agregar partida». `nivelDelTitulo` es el nivel del título que la
// encabeza: sus bloques van un nivel por debajo. Al guardar avisa con la partida guardada. Datos ficticios; el servidor
// se simula con la forma de `api/rutas/composicion.py`.

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "leer_proyecto"],
  modo_entrega: false,
};

const VACIA = {
  estado: "vacio",
  aviso: "Comience por la cabecera (código y descripción) y declare al menos un insumo.",
  desglose: null,
  advertencias: [],
  requiere_justificacion: false,
  contraste: null,
};
const GUARDADO = {
  precio_unitario: "120.00",
  mensaje: "Composición guardada para la partida Z-99: precio unitario 120,00.",
  justificada: false,
  avisos: [],
};
const SIN_VARIANTES = { lista: { nombre: "Lista ficticia de Bs", moneda: "Bs", fecha: "2026-10-26" }, lista_nueva: false, variantes: [] };
const CON_LISTA = {
  moneda: "Bs",
  declarada: true,
  lista: { nombre: "Lista ficticia de Bs", moneda: "Bs", fecha: "2026-10-25", origen: "prueba" },
  aviso: null,
};

const ESPERA = { timeout: 3000 };

describe("ComponerPartida (Tarea 9)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let rutas: string[];

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
    rutas = [];
    fetchFalso.mockImplementation(async (entrada) => {
      const ruta = String(entrada);
      rutas.push(ruta);
      if (ruta === "/v1/composicion/opciones") return json({ dominios: ["civil"], modalidades: ["jornal"] });
      if (ruta === "/v1/composicion/evaluar") return json(VACIA);
      if (ruta.startsWith("/v1/composicion/partidas/")) {
        return json({ existe: false, tablas: { materiales: [], equipos: [], mano_obra: [] }, rendimiento_propuesto: null, hay_historial: false });
      }
      if (ruta.startsWith("/v1/composicion/referencia") || ruta.startsWith("/v1/composicion/similares")) return json([]);
      if (ruta === "/v1/composicion/prever") return json(SIN_VARIANTES);
      if (ruta === "/v1/composicion/guardar") return json(GUARDADO);
      if (ruta === "/v1/carpeta") return json(CON_LISTA);
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    fijarCsrf(null);
    olvidarFormularios();
  });

  function montar(nivelDelTitulo: 1 | 2, codigoInicial = "", alGuardar = vi.fn<(p: PartidaCompuesta) => void>()) {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: null,
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter>
          <ComponerPartida codigoInicial={codigoInicial} nivelDelTitulo={nivelDelTitulo} alGuardar={alGuardar} />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
    return alGuardar;
  }

  const BLOQUES = ["Cabecera de la partida", "Rendimiento", "Insumos", "Desglose en vivo", "Guardar"];

  test("bajo un título de nivel 2 (el panel) sus bloques son h3 y sus tablas h4, sin h1", async () => {
    montar(2);
    await screen.findByText("Precios en Bs", {}, ESPERA);
    expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
    for (const bloque of BLOQUES) expect(screen.getByRole("heading", { name: bloque }), bloque).toHaveProperty("tagName", "H3");
    expect(screen.getByRole("heading", { name: "Materiales" })).toHaveProperty("tagName", "H4");
  });

  test("bajo un h1 (la pantalla) sus bloques son h2 y sus tablas h3", async () => {
    montar(1);
    await screen.findByText("Precios en Bs", {}, ESPERA);
    for (const bloque of BLOQUES) expect(screen.getByRole("heading", { name: bloque }), bloque).toHaveProperty("tagName", "H2");
    expect(screen.getByRole("heading", { name: "Materiales" })).toHaveProperty("tagName", "H3");
  });

  test("llega con el código inicial, lo consulta una vez y no cuenta como cambio sin guardar", async () => {
    montar(2, "Z-99");
    expect(screen.getByLabelText("Código")).toHaveValue("Z-99");
    await waitFor(() => expect(rutas.filter((r) => r === "/v1/composicion/partidas/Z-99")).toHaveLength(1), ESPERA);
    expect(formulariosSucios()).toEqual([]);
  });

  test("el campo «Código» explica qué es y qué pasa si ya existe", () => {
    montar(1);
    expect(screen.getByLabelText("Código")).toHaveAccessibleDescription(
      "Con este código la partida queda en el catálogo de la empresa, por ejemplo «E-411» o uno propio. Si ya existe, se cargan sus tablas.",
    );
  });

  test("al guardar avisa con el código, la descripción y la unidad guardados, y no ofrece volver a la Hoja", async () => {
    const u = userEvent.setup();
    const alGuardar = montar(2, "Z-99");
    await u.type(screen.getByLabelText("Descripción"), "Zanja ficticia");
    await u.type(screen.getByLabelText("Unidad"), "m3");
    await u.type(screen.getByLabelText("Condiciones del rendimiento"), "Condiciones ficticias");
    await u.click(screen.getByRole("button", { name: "Guardar composición" }));
    await waitFor(() => expect(alGuardar).toHaveBeenCalledTimes(1), ESPERA);
    expect(alGuardar).toHaveBeenCalledWith({ codigo: "Z-99", descripcion: "Zanja ficticia", unidad: "m3" });
    expect(screen.queryByRole("button", { name: "Volver a la Hoja" })).toBeNull();
  });
});
