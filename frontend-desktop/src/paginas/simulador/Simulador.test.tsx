import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import { AYUDA_CIFRAS } from "../../indicadores/cifraEscrita";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { alertaConTexto } from "../../test/ayudas";
import PaginaSimulador from "./index";
import { MENSAJE_SEMILLA, MENSAJE_SIN_FILAS, MENSAJE_VARIACION } from "./logica";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja"],
  modo_entrega: false,
};

const FILAS = [
  { tipo: "material", insumo: "Arena lavada", unidad: "m3", precio: "1230.00" },
  { tipo: "mano_obra", insumo: "Peon ficticio", unidad: "jornal", precio: "12.50" },
];

describe("Simulador de listas", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    fijarCsrf("tok");
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  function montar() {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: { nombre: "clinica", ruta_relativa: "data/clinica.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter>
          <PaginaSimulador />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  function cuerpoEnviado(llamada: number): unknown {
    const init = fetchFalso.mock.calls[llamada][1] as RequestInit;
    return JSON.parse(String(init.body));
  }

  test("aclara que es una herramienta de prueba, trae los valores por omision y ayuda en cada campo", () => {
    montar();
    expect(screen.getByText(/Herramienta de prueba, no una fuente de mercado/)).toBeInTheDocument();
    expect(screen.queryByText(/UC-07/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Semilla")).toHaveValue("42");
    expect(screen.getByLabelText("Variación máxima (%)")).toHaveValue("5");
    expect(screen.getByLabelText(/^Insumos/)).toHaveValue("");
    expect(screen.getByText("Mismo número, misma lista: sirve para repetir un resultado.")).toBeInTheDocument();
    expect(screen.getByText(`Cada precio sube o baja, como máximo, este porcentaje. ${AYUDA_CIFRAS}`)).toBeInTheDocument();
    expect(screen.getByText("Escriba una palabra y elija de la lista; si no elige ninguno, se simulan todos.")).toBeInTheDocument();
  });

  test("antes de generar dice que aun no hay lista, sin tabla", () => {
    montar();
    expect(screen.getByText("Aún no hay lista simulada")).toBeInTheDocument();
    expect(screen.getByText("Ajuste los parámetros y pulse Generar lista simulada.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  test("genera la lista: manda el cuerpo por omision y muestra los precios con coma decimal", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValue(json({ filas: FILAS }));
    montar();
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    const tabla = await screen.findByRole("table", { name: "Lista simulada" });
    expect(tabla).toHaveTextContent("Arena lavada");
    expect(tabla).toHaveTextContent("1.230,00");
    expect(tabla).toHaveTextContent("12,50");
    expect(fetchFalso.mock.calls[0][0]).toBe("/v1/simulador");
    expect((fetchFalso.mock.calls[0][1] as RequestInit).method).toBe("POST");
    expect(cuerpoEnviado(0)).toEqual({ semilla: 42, variacion_max: "5", insumos: null });
    expect(screen.getByRole("button", { name: "Descargar CSV" })).toBeEnabled();
  });

  test("manda lo que se escribio", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValue(json({ filas: FILAS }));
    montar();
    await usuario.clear(screen.getByLabelText("Semilla"));
    await usuario.type(screen.getByLabelText("Semilla"), "7");
    await usuario.clear(screen.getByLabelText("Variación máxima (%)"));
    await usuario.type(screen.getByLabelText("Variación máxima (%)"), "2,5");
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    await screen.findByRole("table");
    expect(cuerpoEnviado(0)).toEqual({ semilla: 7, variacion_max: "2.5", insumos: null });
  });

  // AC3: «Insumos» es una seleccion multiple guiada. Lo que viaja es lo de siempre: UN texto con las descripciones
  // exactas separadas por coma (la API parte por la coma).
  describe("insumos elegidos de la lista", () => {
    const CATALOGO = {
      insumos: [
        {
          valor: "MAT-2",
          etiqueta: "Arena lavada (MAT-2, m3)",
          fuente: "Catálogo de la carpeta de trabajo: material",
          descripcion: "Arena lavada",
          unidad: "m3",
        },
        {
          valor: "MAT-3",
          etiqueta: "Tubo PVC, 4 pulgadas (MAT-3, m)",
          fuente: "Catálogo de la carpeta de trabajo: material",
          descripcion: "Tubo PVC, 4 pulgadas",
          unidad: "m",
        },
      ],
      salarios_cct: [
        {
          valor: "MO-1",
          etiqueta: "Peon ficticio (MO-1, jornal)",
          fuente: "Catálogo de la carpeta de trabajo: mano obra",
          descripcion: "Peon ficticio",
          unidad: "jornal",
        },
      ],
    };

    beforeEach(() => {
      fetchFalso.mockImplementation(async (entrada) => {
        const url = String(entrada);
        const tabla = /^\/v1\/consulta\/(\w+)\?/.exec(url)?.[1] as keyof typeof CATALOGO | undefined;
        if (tabla) return json({ tabla, resultados: CATALOGO[tabla], hay_mas: false });
        return json({ filas: FILAS });
      });
    });

    const consultas = () =>
      fetchFalso.mock.calls.map(([ruta]) => String(ruta)).filter((ruta) => ruta.startsWith("/v1/consulta/"));
    const posts = () => fetchFalso.mock.calls.filter(([, init]) => init?.method === "POST");
    const cuerpoDelPost = (n: number) => JSON.parse(String((posts()[n][1] as RequestInit).body));

    async function elegir(usuario: ReturnType<typeof userEvent.setup>, escrito: string, nombre: RegExp) {
      await usuario.type(screen.getByRole("combobox", { name: "Insumos" }), escrito);
      await usuario.click(await screen.findByRole("option", { name: nombre }, { timeout: 3000 }));
    }

    test("«Insumos» es un campo con busqueda en insumos y oficios, con el detalle que trae la descripcion exacta", async () => {
      const usuario = userEvent.setup();
      montar();
      await usuario.type(screen.getByRole("combobox", { name: "Insumos" }), "are");
      await screen.findByRole("option", { name: /Arena lavada/ }, { timeout: 3000 });
      expect(consultas().sort()).toEqual([
        "/v1/consulta/insumos?q=are&limite=8&detalle=true",
        "/v1/consulta/salarios_cct?q=are&limite=8&detalle=true",
      ]);
    });

    test("elegidos de la lista viajan como el texto de siempre: descripciones exactas separadas por coma", async () => {
      const usuario = userEvent.setup();
      montar();
      await elegir(usuario, "are", /Arena lavada/);
      await elegir(usuario, "peo", /Peon ficticio/);
      const lista = screen.getByRole("list", { name: "Elegidos: Insumos" });
      expect(within(lista).getByRole("button", { name: "Quitar Arena lavada" })).toBeInTheDocument();
      expect(within(lista).getByRole("button", { name: "Quitar Peon ficticio" })).toBeInTheDocument();
      await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
      await screen.findByRole("table");
      expect(cuerpoDelPost(0)).toEqual({ semilla: 42, variacion_max: "5", insumos: "Arena lavada, Peon ficticio" });
    });

    test("quitar una etiqueta la saca del envio y, tras generar, avisa que el resultado quedo viejo", async () => {
      const usuario = userEvent.setup();
      montar();
      await elegir(usuario, "are", /Arena lavada/);
      await elegir(usuario, "peo", /Peon ficticio/);
      await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
      await screen.findByRole("table");
      await usuario.click(screen.getByRole("button", { name: "Quitar Arena lavada" }));
      expect(screen.getByText(/Cambió el formulario: pulse Generar lista simulada para actualizar/)).toBeInTheDocument();
      await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
      await waitFor(() => expect(posts()).toHaveLength(2));
      expect(cuerpoDelPost(1).insumos).toBe("Peon ficticio");
    });

    test("lo escrito sin elegir no se envia y el campo lo avisa", async () => {
      const usuario = userEvent.setup();
      montar();
      await usuario.type(screen.getByRole("combobox", { name: "Insumos" }), "arena sin elegir");
      expect(screen.getByText("Falta elegir «arena sin elegir» de la lista: así no se agrega.")).toBeInTheDocument();
      await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
      await screen.findByRole("table");
      expect(cuerpoDelPost(0).insumos).toBeNull();
    });

    test("no ofrece «usar tal cual»: la API ignora en silencio lo que no existe en la lista", async () => {
      const usuario = userEvent.setup();
      montar();
      await usuario.type(screen.getByRole("combobox", { name: "Insumos" }), "are");
      await screen.findByRole("option", { name: /Arena lavada/ }, { timeout: 3000 });
      expect(screen.queryByRole("option", { name: /tal cual/ })).not.toBeInTheDocument();
    });

    test("una descripcion con coma no se agrega: la API la partiria en dos y no la encontraria", async () => {
      const usuario = userEvent.setup();
      montar();
      await usuario.type(screen.getByRole("combobox", { name: "Insumos" }), "tub");
      await usuario.click(await screen.findByRole("option", { name: /Tubo PVC/ }, { timeout: 3000 }));
      expect(screen.queryByRole("list", { name: "Elegidos: Insumos" })).not.toBeInTheDocument();
      expect(await screen.findByText(/«Tubo PVC, 4 pulgadas» lleva una coma/, {}, { timeout: 3000 })).toBeInTheDocument();
    });

    test("un 401 de la busqueda cierra la sesion", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockImplementation(async () => json({ detalle: "Sesión ausente o vencida: entre de nuevo con su cuenta." }, 401));
      montar();
      await usuario.type(screen.getByRole("combobox", { name: "Insumos" }), "are");
      await waitFor(() => expect(alExpirar).toHaveBeenCalled(), { timeout: 3000 });
    });
  });

  test("el CSV se pide con el mismo cuerpo que genero la tabla y baja con el nombre de la API", async () => {
    const usuario = userEvent.setup();
    const clics: string[] = [];
    Object.defineProperty(URL, "createObjectURL", { value: () => "blob:falso", configurable: true });
    Object.defineProperty(URL, "revokeObjectURL", { value: vi.fn(), configurable: true });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      clics.push(this.download);
    });
    fetchFalso.mockImplementation(async (entrada) =>
      String(entrada) === "/v1/simulador/csv"
        ? new Response("tipo,insumo,unidad,precio\r\n", {
            headers: { "Content-Disposition": 'attachment; filename="lista_simulada.csv"' },
          })
        : json({ filas: FILAS }),
    );
    montar();
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    await screen.findByRole("table");
    // Cambiar el campo despues de generar no cambia lo que se descarga.
    await usuario.clear(screen.getByLabelText("Semilla"));
    await usuario.type(screen.getByLabelText("Semilla"), "99");
    await usuario.click(screen.getByRole("button", { name: "Descargar CSV" }));
    await waitFor(() => expect(clics).toEqual(["lista_simulada.csv"]));
    expect(fetchFalso.mock.calls[1][0]).toBe("/v1/simulador/csv");
    expect(cuerpoEnviado(1)).toEqual({ semilla: 42, variacion_max: "5", insumos: null });
    expect(((fetchFalso.mock.calls[1][1] as RequestInit).headers as Headers).get("X-Silice-CSRF")).toBe("tok");
  });

  test("sin filas dice el mensaje de Streamlit y no ofrece la descarga", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValue(json({ filas: [] }));
    montar();
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    expect(await screen.findByText(MENSAJE_SIN_FILAS)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Lista simulada" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Descargar CSV" })).not.toBeInTheDocument();
  });

  test("el error de la API se muestra tal cual y no queda la lista anterior", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValueOnce(json({ filas: FILAS }));
    fetchFalso.mockResolvedValueOnce(
      json({ detalle: "La variacion maxima no es un numero decimal: [<class 'decimal.ConversionSyntax'>]" }, 422),
    );
    montar();
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    await screen.findByRole("table");
    await usuario.clear(screen.getByLabelText("Variación máxima (%)"));
    await usuario.type(screen.getByLabelText("Variación máxima (%)"), "7");
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    const alerta = await alertaConTexto();
    expect(alerta).toHaveTextContent("La variacion maxima no es un numero decimal");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  test("sin lista vigente (409) muestra el detalle", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValue(json({ detalle: "no hay ninguna lista de precios vigente al 2026-10-18" }, 409));
    montar();
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    expect(await alertaConTexto()).toHaveTextContent("no hay ninguna lista de precios vigente");
  });

  test("una semilla invalida avisa junto al campo y no manda nada", async () => {
    const usuario = userEvent.setup();
    montar();
    await usuario.clear(screen.getByLabelText("Semilla"));
    await usuario.type(screen.getByLabelText("Semilla"), "-3");
    expect(await screen.findByText(MENSAJE_SEMILLA)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generar lista simulada" })).toBeDisabled();
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("un 401 avisa que la sesion vencio", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValue(json({ detalle: "Sesión ausente o vencida: entre de nuevo con su cuenta." }, 401));
    montar();
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    await alertaConTexto();
    expect(alExpirar).toHaveBeenCalledOnce();
  });

  test("mientras espera muestra el esqueleto y no deja generar dos veces", async () => {
    const usuario = userEvent.setup();
    let responder: (r: Response) => void = () => {};
    fetchFalso.mockReturnValue(new Promise<Response>((res) => (responder = res)));
    montar();
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    expect(await screen.findByRole("status", { name: "Cargando lista simulada" })).toBeInTheDocument();
    expect(screen.getByText("Simulando…", { selector: "p" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Simulando…" })).toBeDisabled();
    responder(json({ filas: FILAS }));
    expect(await screen.findByRole("table", { name: "Lista simulada" })).toBeInTheDocument();
  });

  test("la variacion invalida avisa junto al campo y bloquea el boton; corregirla lo libera", async () => {
    const usuario = userEvent.setup();
    montar();
    const campo = screen.getByLabelText("Variación máxima (%)");
    for (const mala of ["-1", "abc", "2.5", "1001", "1E+999999"]) {
      await usuario.clear(campo);
      await usuario.type(campo, mala);
      expect(await screen.findByText(MENSAJE_VARIACION)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Generar lista simulada" })).toBeDisabled();
    }
    await usuario.clear(campo);
    await usuario.type(campo, "1000");
    expect(screen.queryByText(MENSAJE_VARIACION)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generar lista simulada" })).toBeEnabled();
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("solo una linea de resumen es region viva: la tabla y el error quedan fuera", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValue(json({ filas: FILAS }));
    montar();
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    const tabla = await screen.findByRole("table", { name: "Lista simulada" });
    const resumen = screen.getByText("Lista simulada: 2 filas");
    expect(resumen).toHaveAttribute("role", "status");
    expect(resumen.contains(tabla)).toBe(false);
    expect(tabla.closest("[aria-live]")).toBeNull();
  });

  test("el resumen usa singular con una fila", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValue(json({ filas: [FILAS[0]] }));
    montar();
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    expect(await screen.findByText("Lista simulada: 1 fila")).toBeInTheDocument();
  });

  test("al terminar el foco pasa al titulo del resultado, o al aviso si fallo", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValueOnce(json({ filas: FILAS }));
    fetchFalso.mockResolvedValueOnce(json({ detalle: "no hay ninguna lista de precios vigente al 2026-10-18" }, 409));
    montar();
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    const titulo = await screen.findByRole("heading", { name: "Lista simulada" });
    await waitFor(() => expect(titulo).toHaveFocus());
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    const alerta = await alertaConTexto();
    await waitFor(() => expect(alerta.parentElement).toHaveFocus());
  });

  test("rotula el resultado con los valores enviados y avisa si el formulario cambio despues", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValue(json({ filas: FILAS }));
    montar();
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    await screen.findByRole("table", { name: "Lista simulada" });
    expect(screen.getByText("Resultado con los valores enviados: semilla 42, variación 5 %, insumos: todos.")).toBeInTheDocument();
    expect(screen.queryByText(/cambió el formulario/i)).not.toBeInTheDocument();
    await usuario.clear(screen.getByLabelText("Semilla"));
    await usuario.type(screen.getByLabelText("Semilla"), "8");
    expect(screen.getByText(/cambió el formulario/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Descargar CSV" })).toBeInTheDocument();
  });

  test("Descargar CSV queda junto al titulo del resultado", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValue(json({ filas: FILAS }));
    montar();
    await usuario.click(screen.getByRole("button", { name: "Generar lista simulada" }));
    const titulo = await screen.findByRole("heading", { name: "Lista simulada" });
    expect(titulo.parentElement).toContainElement(screen.getByRole("button", { name: "Descargar CSV" }));
  });
});
