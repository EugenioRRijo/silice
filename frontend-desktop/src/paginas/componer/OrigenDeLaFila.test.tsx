import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { olvidarFormularios } from "../../shell/sucio";
import { ComponerPartida } from "./ComponerPartida";

// Ronda 2 del dictamen del autocompletado (2026-11-05), MAYOR 1 y MENOR 2, por la pantalla de verdad: una fila que trajo la
// precarga de una partida guardada o «Usar esta fila» de MaPreX no la tecleó nadie. Al elegir otro insumo del catálogo se
// reemplaza (o se vacía) y se dice; nunca queda mezclada (diseño del autocompletado, §1.6, punto 6). Montos y textos ficticios.

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
const CON_LISTA = {
  moneda: "Bs",
  declarada: true,
  lista: { nombre: "Lista ficticia de Bs", moneda: "Bs", fecha: "2026-10-25", origen: "prueba" },
  aviso: null,
};

// La lista del 01/07/2026 rige hasta el 30/09; la del 01/10/2026, desde entonces.
const CATALOGO = [
  { codigo: "MAT-1", descripcion: "Cemento gris ficticio", unidad: "saco", precio: "18.00" },
  { codigo: "MAT-2", descripcion: "Cemento blanco ficticio", unidad: null, precio: null },
  { codigo: "MAT-3", descripcion: "Cemento rojo ficticio", unidad: "kg", precio: "9.00" },
];
const ARENA = { descripcion: "Arena ficticia", unidad: "m3", cantidad: "1", precio: "5,00" };
const FECHA_VIEJA = "2026-08-15";
const FECHA_NUEVA = "2026-10-20";

describe("Componer: el origen de cada dato de la fila", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let partidaGuardada: Record<string, unknown>[];
  let deMaPreX: { etiqueta: string; ref_maprex: string; fila: Record<string, string> }[];

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
    partidaGuardada = [{ ...ARENA }, { ...ARENA }];
    deMaPreX = [{ etiqueta: "Arena de MaPreX", ref_maprex: "MP-1", fila: { ...ARENA, descripcion: "Arena de MaPreX" } }];
    fetchFalso.mockImplementation(async (entrada) => {
      const ruta = String(entrada);
      const url = new URL(ruta, "http://x");
      if (ruta === "/v1/composicion/opciones") return json({ dominios: ["civil"], modalidades: ["jornal"] });
      if (ruta === "/v1/composicion/evaluar") return json(VACIA);
      if (ruta.startsWith("/v1/composicion/partidas/")) {
        return json({
          existe: true,
          tablas: { materiales: partidaGuardada, equipos: [], mano_obra: [] },
          rendimiento_propuesto: null,
          hay_historial: false,
        });
      }
      if (url.pathname === "/v1/composicion/referencia") return json(deMaPreX);
      if (url.pathname === "/v1/composicion/similares") return json([]);
      if (ruta === "/v1/carpeta") return json(CON_LISTA);
      if (ruta === "/v1/consulta/unidades") return json({ unidades: [] });
      if (url.pathname === "/v1/consulta/insumos") {
        const q = (url.searchParams.get("q") ?? "").toLowerCase();
        const fecha = url.searchParams.get("para_armar_al");
        const resultados = CATALOGO.filter((i) => i.descripcion.toLowerCase().includes(q) || i.codigo.toLowerCase().includes(q)).map((i) => {
          const base = {
            valor: i.codigo,
            etiqueta: `${i.descripcion} (${i.codigo})`,
            fuente: "Catálogo de la carpeta de trabajo: material",
            descripcion: i.descripcion,
            ...(i.unidad ? { unidad: i.unidad } : {}),
          };
          if (fecha === null || i.precio === null) return base;
          const nueva = fecha >= "2026-10-01";
          return { ...base, precio: nueva ? "25.50" : i.precio, moneda: "Bs", fecha_precio: nueva ? "2026-10-01" : "2026-07-01" };
        });
        return json({ tabla: "insumos", hay_mas: false, resultados });
      }
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    fijarCsrf(null);
    olvidarFormularios();
  });

  function montar(codigoInicial = "") {
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
          <ComponerPartida codigoInicial={codigoInicial} nivelDelTitulo={2} alGuardar={vi.fn()} />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  const ESPERA = { timeout: 3000 };
  const descripcion = (n = 1) => screen.getByRole("combobox", { name: `Descripción, fila ${n}` });
  const unidad = (n = 1) => screen.getByRole("combobox", { name: `Unidad, fila ${n}` });
  const precio = (n = 1) => screen.getByRole("textbox", { name: `Precio, fila ${n}` });
  const fijarFecha = (valor: string) => fireEvent.change(screen.getByLabelText("Fecha"), { target: { value: valor } });
  const regionDeLaFecha = () => document.getElementById("componer-fecha-estado");

  async function elegir(u: ReturnType<typeof userEvent.setup>, buscado: string, nombre: RegExp, fila = 1) {
    await u.clear(descripcion(fila));
    await u.type(descripcion(fila), buscado);
    await u.click(await screen.findByRole("option", { name: nombre }));
    await waitFor(() => expect(screen.queryByRole("listbox")).not.toBeInTheDocument());
  }

  async function conPartidaPrecargada() {
    montar("FIC-01");
    await screen.findByText("Precios en Bs", {}, ESPERA);
    fijarFecha(FECHA_VIEJA);
    await waitFor(() => expect(descripcion(1)).toHaveValue("Arena ficticia"), ESPERA);
  }

  async function conFilaDeMaPreX(u: ReturnType<typeof userEvent.setup>) {
    montar();
    await screen.findByText("Precios en Bs", {}, ESPERA);
    fijarFecha(FECHA_VIEJA);
    await u.type(screen.getByRole("textbox", { name: "Buscar en la referencia MaPreX (materiales)" }), "arena");
    await u.click(await screen.findByRole("button", { name: "Usar esta fila" }, ESPERA));
    expect(descripcion(1)).toHaveValue("Arena de MaPreX");
  }

  describe("una partida guardada que se precarga", () => {
    test("elegir un insumo con precio reemplaza la unidad y el precio de la precarga y lo dice", async () => {
      const u = userEvent.setup();
      await conPartidaPrecargada();
      await elegir(u, "cemento g", /Cemento gris ficticio/);
      await waitFor(() => expect(precio()).toHaveValue("18,00"));
      expect(unidad()).toHaveValue("saco");
      expect(precio()).toHaveAccessibleDescription(expect.stringContaining("Se cambió el precio 5,00 por el del catálogo, 18,00 Bs."));
      expect(precio()).not.toHaveAccessibleDescription(expect.stringContaining("se conserva"));
      expect(unidad()).toHaveAccessibleDescription(expect.stringContaining("Se cambió la unidad m3 por la del catálogo, saco."));
      // La segunda fila precargada sigue igual.
      expect(precio(2)).toHaveValue("5,00");
    });

    test("elegir un insumo sin precio ni unidad quita los de la precarga y lo dice: la fila no queda mezclada", async () => {
      const u = userEvent.setup();
      await conPartidaPrecargada();
      await elegir(u, "cemento b", /Cemento blanco ficticio/);
      await waitFor(() => expect(descripcion()).toHaveValue("Cemento blanco ficticio"));
      expect(precio()).toHaveValue("");
      expect(unidad()).toHaveValue("");
      expect(precio()).toHaveAccessibleDescription(expect.stringContaining("Se quitó el precio 5,00: este insumo no tiene precio en la lista."));
      expect(unidad()).toHaveAccessibleDescription(expect.stringContaining("Se quitó la unidad m3: este insumo no tiene unidad en el catálogo."));
    });
  });

  describe("«Usar esta fila» de MaPreX", () => {
    test("elegir después un insumo con precio reemplaza lo de MaPreX y lo dice", async () => {
      const u = userEvent.setup();
      await conFilaDeMaPreX(u);
      await elegir(u, "cemento g", /Cemento gris ficticio/);
      await waitFor(() => expect(precio()).toHaveValue("18,00"));
      expect(unidad()).toHaveValue("saco");
      expect(precio()).toHaveAccessibleDescription(expect.stringContaining("Se cambió el precio 5,00 por el del catálogo, 18,00 Bs."));
      expect(precio()).not.toHaveAccessibleDescription(expect.stringContaining("se conserva"));
    });

    test("elegir después un insumo sin precio quita el de MaPreX y lo dice", async () => {
      const u = userEvent.setup();
      await conFilaDeMaPreX(u);
      await elegir(u, "cemento b", /Cemento blanco ficticio/);
      await waitFor(() => expect(descripcion()).toHaveValue("Cemento blanco ficticio"));
      expect(precio()).toHaveValue("");
      expect(unidad()).toHaveValue("");
      expect(precio()).toHaveAccessibleDescription(expect.stringContaining("Se quitó el precio 5,00: este insumo no tiene precio en la lista."));
    });
  });

  // Ronda 3, MENOR 2: lo tecleado se recuerda por indice de fila; una precarga que reemplaza las tablas trae filas nuevas y
  // nada de lo tecleado antes es suyo, aunque coincida el indice y el texto («m3»).
  describe("una precarga que reemplaza las tablas", () => {
    test("con el foco en una celda de la tabla, una precarga conserva el foco en ella (WCAG 2.4.3)", async () => {
      const u = userEvent.setup();
      montar();
      await screen.findByText("Precios en Bs", {}, ESPERA);
      fijarFecha(FECHA_VIEJA);
      await u.click(screen.getByRole("button", { name: "Agregar fila a Materiales" }));
      const celda = precio(1);
      await u.click(celda);
      expect(celda).toHaveFocus();

      fireEvent.change(screen.getByRole("combobox", { name: "Código" }), { target: { value: "FIC-01" } });
      await waitFor(() => expect(descripcion(1)).toHaveValue("Arena ficticia"), ESPERA);

      expect(precio(1)).toBe(celda);
      expect(celda).toHaveFocus();
    });

    test("la unidad «m3» tecleada antes en esa fila no hace «de la persona» la «m3» que trae la precarga", async () => {
      const u = userEvent.setup();
      montar();
      await screen.findByText("Precios en Bs", {}, ESPERA);
      fijarFecha(FECHA_VIEJA);
      await u.click(screen.getByRole("button", { name: "Agregar fila a Materiales" }));
      await u.type(unidad(1), "m3");
      expect(unidad(1)).toHaveValue("m3");

      await u.type(screen.getByRole("combobox", { name: "Código" }), "FIC-01");
      await waitFor(() => expect(descripcion(1)).toHaveValue("Arena ficticia"), ESPERA);
      expect(unidad(1)).toHaveValue("m3");

      await elegir(u, "cemento b", /Cemento blanco ficticio/);
      await waitFor(() => expect(descripcion()).toHaveValue("Cemento blanco ficticio"));
      expect(unidad()).toHaveValue("");
      expect(precio()).toHaveValue("");
      expect(unidad()).toHaveAccessibleDescription(expect.stringContaining("Se quitó la unidad m3: este insumo no tiene unidad en el catálogo."));
      expect(precio()).toHaveAccessibleDescription(expect.stringContaining("Se quitó el precio 5,00: este insumo no tiene precio en la lista."));
    });
  });

  describe("el aviso junto a la «Fecha»", () => {
    test("anuncia una vez, en una región viva, cuántos precios quedaron con otra lista", async () => {
      const u = userEvent.setup();
      await conPartidaPrecargada();
      await elegir(u, "cemento g", /Cemento gris ficticio/, 1);
      await elegir(u, "cemento r", /Cemento rojo ficticio/, 2);
      await waitFor(() => expect(precio(2)).toHaveValue("9,00"));
      expect(regionDeLaFecha()).toHaveAttribute("aria-live", "polite");
      expect(regionDeLaFecha()).toBeEmptyDOMElement();

      fijarFecha(FECHA_NUEVA);
      await waitFor(() => expect(regionDeLaFecha()).toHaveTextContent("2 precios son de otra lista; revíselos."), ESPERA);

      // Un precio que la persona escribe ya no es del catálogo: queda uno.
      await u.clear(precio(2));
      await u.type(precio(2), "10");
      await waitFor(() => expect(regionDeLaFecha()).toHaveTextContent("1 precio es de otra lista; revíselo."));

      fijarFecha(FECHA_VIEJA);
      await waitFor(() => expect(regionDeLaFecha()).toBeEmptyDOMElement());
    });

    test("con la «Fecha» vacía no anuncia nada", async () => {
      const u = userEvent.setup();
      await conPartidaPrecargada();
      await elegir(u, "cemento g", /Cemento gris ficticio/);
      await waitFor(() => expect(precio()).toHaveValue("18,00"));
      fijarFecha("");
      await new Promise((r) => setTimeout(r, 100));
      expect(regionDeLaFecha()).toBeEmptyDOMElement();
    });
  });
});
