import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoDeLaHoja } from "../hoja/ProveedorDeLaHoja";
import type { HojaDeLaObra } from "../hoja/ProveedorDeLaHoja";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { olvidarFormularios } from "../../shell/sucio";
import { ComponerPartida } from "./ComponerPartida";

// RF-200 (ola 2, 2026-11-13; bitácora `2026-11-13-ola2-front.md` §6): Componer calculaba siempre con los parámetros de
// omisión y su precio unitario no era el de la obra. Ahora propone los de «Ajustes de costo» de la obra abierta (o los de
// omisión sin obra), los deja cambiar para este cálculo y los manda al servidor, que calcula. No se guardan con la partida.
// Datos ficticios; el servidor se simula con la forma de `api/rutas/composicion.py` y de la vista `parametros` de la Hoja.

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
const CON_LISTA = {
  moneda: "Bs",
  declarada: true,
  lista: { nombre: "Lista ficticia de Bs", moneda: "Bs", fecha: "2026-10-25", origen: "prueba" },
  aviso: null,
};
const ROTULOS = {
  fcas: "FCAS (fracción: 6.00 = prestaciones del 600 %)",
  bono_alimentacion: "Bono de alimentación (por obrero y día)",
  administracion: "Administración (fracción del costo directo)",
  utilidad: "Utilidad (fracción, en cascada sobre la administración)",
};
const campos = (valores: Record<keyof typeof ROTULOS, string>) =>
  (Object.keys(ROTULOS) as (keyof typeof ROTULOS)[]).map((clave) => ({ clave, rotulo: ROTULOS[clave], valor: valores[clave] }));
const DE_OMISION = { campos: campos({ fcas: "6,00", bono_alimentacion: "1,00", administracion: "0,15", utilidad: "0,10" }) };
const DE_LA_OBRA = {
  campos: campos({ fcas: "5,5", bono_alimentacion: "2", administracion: "0,12", utilidad: "0,15" }),
  moneda_proyecto: "Bs",
  total: { texto: "100.00", exacto: "100" },
  puede_convertir: false,
};
const VALIDA = {
  estado: "valido",
  aviso: null,
  desglose: {
    materiales: "7.19",
    equipos: "0.03",
    mano_obra: "0.81",
    costo_directo: "8.03",
    con_administracion: "8.99",
    precio_unitario: "10.34",
  },
  advertencias: [],
  requiere_justificacion: false,
  contraste: null,
};
const ESPERA = { timeout: 3000 };

describe("Componer: parámetros del precio unitario (RF-200)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let evaluaciones: { parametros?: Record<string, string> }[];
  let respuestaEvaluar: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
    evaluaciones = [];
    respuestaEvaluar = () => json(VALIDA);
    fetchFalso.mockImplementation(async (entrada, init) => {
      const ruta = String(entrada);
      if (ruta === "/v1/composicion/opciones") return json({ dominios: ["civil"], modalidades: ["jornal"] });
      if (ruta === "/v1/composicion/parametros") return json(DE_OMISION);
      if (ruta === "/v1/hoja/borradores/b-1/vistas/parametros") return json(DE_LA_OBRA);
      if (ruta === "/v1/composicion/evaluar") {
        evaluaciones.push(JSON.parse(String(init?.body)) as { parametros?: Record<string, string> });
        return respuestaEvaluar();
      }
      if (ruta.startsWith("/v1/composicion/partidas/")) {
        return json({ existe: false, tablas: { materiales: [], equipos: [], mano_obra: [] }, rendimiento_propuesto: null, hay_historial: false });
      }
      if (ruta.startsWith("/v1/composicion/referencia") || ruta.startsWith("/v1/composicion/similares")) return json([]);
      if (ruta === "/v1/carpeta") return json(CON_LISTA);
      if (ruta === "/v1/consulta/unidades") return json({ unidades: [] });
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    fijarCsrf(null);
    olvidarFormularios();
  });

  function montar(conObra: boolean) {
    const valor: Aplicacion = { sesion: SESION, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() };
    const componer = <ComponerPartida codigoInicial="" nivelDelTitulo={1} alGuardar={vi.fn()} />;
    render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter>
          {conObra ? (
            <ContextoDeLaHoja.Provider value={{ id: "b-1" } as HojaDeLaObra}>{componer}</ContextoDeLaHoja.Provider>
          ) : (
            componer
          )}
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }
  const bloque = () => screen.getByRole("region", { name: "Parámetros del precio unitario" });
  const campo = (nombre: RegExp) => within(bloque()).getByRole("textbox", { name: nombre });
  const ultima = () => evaluaciones.at(-1)?.parametros;

  test("sin obra abierta propone los de omisión, lo dice y los manda al evaluar", async () => {
    montar(false);
    await waitFor(() => expect(campo(/^FCAS/)).toHaveValue("6,00"), ESPERA);
    expect(campo(/^Bono de alimentación/)).toHaveValue("1,00");
    expect(campo(/^Administración/)).toHaveValue("0,15");
    expect(campo(/^Utilidad/)).toHaveValue("0,10");
    // El rótulo del servidor trae «6.00»: se lee con coma.
    expect(campo(/^FCAS/)).toHaveAccessibleName("FCAS (fracción: 6,00 = prestaciones del 600 %)");
    expect(within(bloque()).getByText(/Son los de omisión de Sílice: no hay una obra abierta\./)).toBeInTheDocument();
    await waitFor(
      () => expect(ultima()).toEqual({ fcas: "6,00", bono_alimentacion: "1,00", administracion: "0,15", utilidad: "0,10" }),
      ESPERA,
    );
  });

  test("con una obra abierta propone los de su «Ajustes de costo» y el desglose es el que calcula el servidor con ellos", async () => {
    montar(true);
    await waitFor(() => expect(campo(/^FCAS/)).toHaveValue("5,5"), ESPERA);
    expect(campo(/^Utilidad/)).toHaveValue("0,15");
    expect(
      within(bloque()).getByText(
        "Son los de «Ajustes de costo» de esta obra. Cambiarlos aquí solo cambia este cálculo: el presupuesto sigue con los de la obra y la partida no los guarda.",
      ),
    ).toBeInTheDocument();
    await waitFor(
      () => expect(ultima()).toEqual({ fcas: "5,5", bono_alimentacion: "2", administracion: "0,12", utilidad: "0,15" }),
      ESPERA,
    );
    const desglose = screen.getByRole("table", { name: "Desglose del precio unitario" });
    expect(await within(desglose).findByText("10,34 Bs", {}, ESPERA)).toBeInTheDocument();
  });

  test("cambiar uno lo manda al evaluar tal como se escribió, y «Volver a los de la obra» lo devuelve", async () => {
    const u = userEvent.setup();
    montar(true);
    await waitFor(() => expect(campo(/^Utilidad/)).toHaveValue("0,15"), ESPERA);
    await u.clear(campo(/^Utilidad/));
    await u.type(campo(/^Utilidad/), "0,18");
    await waitFor(() => expect(ultima()?.utilidad).toBe("0,18"), ESPERA);
    await u.click(within(bloque()).getByRole("button", { name: "Volver a los de la obra" }));
    expect(campo(/^Utilidad/)).toHaveValue("0,15");
    await waitFor(() => expect(ultima()?.utilidad).toBe("0,15"), ESPERA);
    expect(within(bloque()).queryByRole("button", { name: "Volver a los de la obra" })).not.toBeInTheDocument();
  });

  test("un parámetro mal escrito queda marcado con el mensaje del servidor", async () => {
    const u = userEvent.setup();
    montar(false);
    await waitFor(() => expect(campo(/^Utilidad/)).toHaveValue("0,10"), ESPERA);
    respuestaEvaluar = () =>
      json({
        ...VALIDA,
        estado: "incompleto",
        desglose: null,
        aviso: "Parámetros del precio unitario. Utilidad: Use la coma para los decimales: por ejemplo 2,5. El punto separa los miles: 1.234,56.",
      });
    await u.clear(campo(/^Utilidad/));
    await u.type(campo(/^Utilidad/), "0.2");
    await waitFor(() => expect(campo(/^Utilidad/)).toHaveAttribute("aria-invalid", "true"), ESPERA);
    expect(campo(/^Utilidad/)).toHaveAccessibleDescription(expect.stringContaining("Use la coma para los decimales"));
    expect(campo(/^FCAS/)).not.toHaveAttribute("aria-invalid", "true");
  });

  test("si no se pueden leer, lo dice y el servidor calcula con los de omisión (no se manda nada)", async () => {
    const base = fetchFalso.getMockImplementation()!;
    fetchFalso.mockImplementation(async (entrada, init) =>
      String(entrada) === "/v1/composicion/parametros" ? json({ detalle: "Error." }, 500) : base(entrada, init),
    );
    montar(false);
    expect(
      await within(bloque()).findByText("No se pudieron leer los parámetros: el desglose usa los de omisión de Sílice.", {}, ESPERA),
    ).toBeInTheDocument();
    await waitFor(() => expect(evaluaciones.length).toBeGreaterThan(0), ESPERA);
    expect(ultima()).toBeUndefined();
  });
});
