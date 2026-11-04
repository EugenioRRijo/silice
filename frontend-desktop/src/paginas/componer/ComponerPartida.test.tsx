import { render, screen, waitFor, within } from "@testing-library/react";
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

// Pulido F5, Tarea 1: el «Código» busca en el catálogo (`GET /v1/buscar/partidas`) y en las partidas viales de Sílice
// (`GET /v1/consulta/partidas_viales`). Datos ficticios con la forma de `api/rutas/busqueda.py` y `api/rutas/consulta.py`.
const DEL_CATALOGO = {
  rotulo: "Partidas del catálogo",
  resultados: [
    {
      clave: "partida:FIC-02",
      codigo: "FIC-02",
      descripcion: "Relleno compactado ficticio",
      unidad: "m3",
      dominio: "civil",
      tiene_composicion: true,
    },
  ],
  hay_mas: false,
};
const VIALES = {
  tabla: "partidas_viales",
  resultados: [{ valor: "C-000.000.002", etiqueta: "Base granular compactada (C-000.000.002, m3)", fuente: "Partidas viales de Sílice" }],
  hay_mas: false,
};
const CODIGO_MAL_FORMADO =
  "Un código lleva letras sin tilde, cifras, punto, guion o guion bajo, sin espacios y hasta 64 caracteres, por ejemplo «E-411». Si escribió una descripción, póngala en «Descripción» y busque aquí el código por sus palabras.";
const AYUDA_DEL_CODIGO =
  "Escriba una palabra de la descripción o el código y elija de la lista, por ejemplo «zanja» o «E-411»; también puede escribir uno propio. Con este código la partida queda en el catálogo de la empresa; si ya existe, se cargan sus tablas.";

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
      if (ruta.startsWith("/v1/buscar/partidas?")) return json(DEL_CATALOGO);
      if (ruta.startsWith("/v1/consulta/partidas_viales?")) return json(VIALES);
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

  // Pulido F5, Tarea 1: la ayuda dice además cómo se busca (antes solo decía qué es y qué pasa si ya existe).
  test("el campo «Código» explica cómo se busca, qué es y qué pasa si ya existe", () => {
    montar(1);
    expect(screen.getByLabelText("Código")).toHaveAccessibleDescription(AYUDA_DEL_CODIGO);
  });

  test("el «Código» se busca por la descripción en el catálogo y en las partidas viales; elegir del catálogo llena lo vacío", async () => {
    const u = userEvent.setup();
    montar(2);
    const codigo = screen.getByRole("combobox", { name: "Código" });
    await u.type(codigo, "compact");
    const lista = await screen.findByRole("listbox", { name: "Código" }, ESPERA);
    expect(within(lista).getByRole("group", { name: "Partidas del catálogo" })).toBeInTheDocument();
    expect(within(lista).getByRole("group", { name: "Partidas viales" })).toBeInTheDocument();
    expect(rutas.some((r) => r.startsWith("/v1/buscar/partidas?"))).toBe(true);
    expect(rutas.some((r) => r.startsWith("/v1/consulta/partidas_viales?"))).toBe(true);
    await u.click(within(lista).getByRole("option", { name: /FIC-02/ }));
    expect(codigo).toHaveValue("FIC-02");
    expect(screen.getByLabelText("Descripción")).toHaveValue("Relleno compactado ficticio");
    expect(screen.getByLabelText("Unidad")).toHaveValue("m3");
  });

  test("elegir una partida vial deja su código y no pisa la descripción escrita", async () => {
    const u = userEvent.setup();
    montar(2);
    await u.type(screen.getByLabelText("Descripción"), "Base ficticia");
    const codigo = screen.getByRole("combobox", { name: "Código" });
    await u.type(codigo, "granular");
    await u.click(await screen.findByRole("option", { name: /C-000\.000\.002/ }, ESPERA));
    expect(codigo).toHaveValue("C-000.000.002");
    expect(screen.getByLabelText("Descripción")).toHaveValue("Base ficticia");
    expect(screen.getByLabelText("Unidad")).toHaveValue("");
  });

  test("un código mal formado se dice al salir del campo, no se ofrece tal cual y no deja guardar; uno bien formado sí", async () => {
    const u = userEvent.setup();
    montar(2);
    await u.type(screen.getByLabelText("Condiciones del rendimiento"), "Condiciones ficticias");
    const codigo = screen.getByRole("combobox", { name: "Código" });
    await u.type(codigo, "excavación de zanja");
    await screen.findByRole("listbox", { name: "Código" }, ESPERA);
    expect(screen.queryByRole("option", { name: /como código/ })).toBeNull();
    // Mientras se escribe es una búsqueda: el error sale al dejar el campo.
    expect(screen.queryByText(CODIGO_MAL_FORMADO)).toBeNull();
    await u.click(screen.getByLabelText("Unidad"));
    expect(await screen.findByText(CODIGO_MAL_FORMADO)).toBeInTheDocument();
    expect(codigo).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("button", { name: "Guardar composición" })).toBeDisabled();

    await u.clear(codigo);
    await u.type(codigo, "Z-100");
    await u.click(await screen.findByRole("option", { name: "Usar «Z-100» como código" }, ESPERA));
    expect(codigo).toHaveValue("Z-100");
    expect(screen.queryByText(CODIGO_MAL_FORMADO)).toBeNull();
    expect(screen.getByRole("button", { name: "Guardar composición" })).toBeEnabled();
  });

  test("llega con la descripción inicial (componer desde «Agregar partida») y el código vacío, sin contar como cambio", async () => {
    const valor: Aplicacion = { sesion: SESION, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() };
    render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter>
          <ComponerPartida codigoInicial="" descripcionInicial="excavación de zanja" nivelDelTitulo={2} alGuardar={vi.fn()} />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
    expect(screen.getByLabelText("Descripción")).toHaveValue("excavación de zanja");
    expect(screen.getByLabelText("Código")).toHaveValue("");
    expect(formulariosSucios()).toEqual([]);
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
