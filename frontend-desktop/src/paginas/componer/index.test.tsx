import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { AYUDA_CIFRAS } from "../../indicadores/cifraEscrita";
import type { Evaluacion } from "./cliente";
import PaginaComponer from "./index";

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

const VACIA: Evaluacion = {
  estado: "vacio",
  aviso: "Comience por la cabecera (código y descripción) y declare al menos un insumo.",
  desglose: null,
  advertencias: [],
  requiere_justificacion: false,
  contraste: null,
};

function valida(pu: string, parcial: Partial<Evaluacion> = {}): Evaluacion {
  return {
    estado: "valido",
    aviso: null,
    desglose: {
      materiales: "20.00",
      equipos: "1.50",
      mano_obra: "3.25",
      costo_directo: "24.75",
      con_administracion: "26.10",
      precio_unitario: pu,
    },
    advertencias: [],
    requiere_justificacion: false,
    contraste: null,
    ...parcial,
  };
}

const TABLAS_FICTICIAS = {
  // La precarga llega como se escribe en los campos: coma decimal (aplicacion.cifras.texto_de_cifra).
  materiales: [{ descripcion: "Arena ficticia", unidad: "m3", cantidad: "0,5", precio: "1.040,00" }],
  equipos: [],
  mano_obra: [{ descripcion: "Peón ficticio", cantidad: "2", sueldo: "15,00", modalidad: "JORNAL" }],
};

// `GET /v1/carpeta` (api/rutas/carpeta.py, Tarea 2 del plan de montar): la moneda de trabajo y la lista para armar.
function estadoDeCarpeta(lista: string | null) {
  return {
    moneda: "Bs",
    declarada: true,
    lista: lista === null ? null : { nombre: lista, moneda: "Bs", fecha: "2026-10-25", origen: "prueba" },
    aviso:
      lista === null
        ? "Esta carpeta de trabajo no tiene lista de precios para armar. Créela a partir de MaPreX o convirtiendo la que tiene."
        : null,
  };
}

interface Llamada {
  ruta: string;
  metodo: string;
  cuerpo: Record<string, unknown> | null;
}

describe("Componer una partida", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let llamadas: Llamada[];
  let evaluacion: (cuerpo: Record<string, unknown>) => Promise<Response> | Response;
  let partida: () => Response;
  let guardado: () => Response;
  let carpeta: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    llamadas = [];
    evaluacion = () => json(VACIA);
    partida = () => json({ existe: false, tablas: { materiales: [], equipos: [], mano_obra: [] }, rendimiento_propuesto: null, hay_historial: false });
    carpeta = () => json(estadoDeCarpeta("Lista ficticia 2026-01"));
    guardado = () => json({ precio_unitario: "29.70", mensaje: "Composición guardada para la partida FIC-1: precio unitario 29.70.", justificada: false, avisos: [] });
    fetchFalso.mockImplementation(async (entrada, init) => {
      const ruta = String(entrada);
      const metodo = init?.method ?? "GET";
      const cuerpo = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : null;
      llamadas.push({ ruta, metodo, cuerpo });
      if (ruta === "/v1/composicion/opciones") return json({ dominios: ["civil", "telecom"], modalidades: ["JORNAL", "DESTAJO"] });
      if (ruta === "/v1/composicion/evaluar") return evaluacion(cuerpo ?? {});
      if (ruta.startsWith("/v1/composicion/partidas/")) return partida();
      if (ruta.startsWith("/v1/composicion/referencia")) {
        return json([{ etiqueta: "Cemento ficticio", ref_maprex: "REF-FICT-001", fila: { descripcion: "Cemento ficticio", unidad: "saco", cantidad: "", precio: "9.90" } }]);
      }
      if (ruta.startsWith("/v1/composicion/similares")) {
        return json([{ codigo: "FIC-009", descripcion: "Muro ficticio", puntaje: 0.91, rendimiento: "8.00", unidad: "m2", tablas: null, aviso: null }]);
      }
      // Guardar pregunta antes a `prever` (Tarea 3 del plan de montar); sin variantes, guarda de una vez.
      if (ruta === "/v1/composicion/prever") {
        return json({ lista: { nombre: "Lista ficticia 2026-01", moneda: "Bs", fecha: "2026-10-25" }, lista_nueva: false, variantes: [] });
      }
      if (ruta === "/v1/composicion/guardar") return guardado();
      if (ruta === "/v1/carpeta") return carpeta();
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  function de(ruta: string): Llamada[] {
    return llamadas.filter((l) => l.ruta === ruta || l.ruta.startsWith(ruta));
  }

  function montar(aplicacion: Partial<Aplicacion> = {}) {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: null,
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
      ...aplicacion,
    };
    render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter>
          <PaginaComponer />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
    return valor;
  }

  const ESPERA = { timeout: 3000 };

  test("trae las etiquetas de la página clásica y el aviso de formulario vacío", async () => {
    montar();
    expect(screen.getByRole("heading", { name: "Componer una partida" })).toBeInTheDocument();
    expect(screen.getByLabelText("Rendimiento: unidades por día")).toBeInTheDocument();
    expect(screen.getByLabelText("Condiciones del rendimiento")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Consumo por unidad" })).toBeInTheDocument();
    expect(await screen.findByText(/Comience por la cabecera/, {}, ESPERA)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText("Dominio")).toHaveValue("civil"));
    expect(within(screen.getByLabelText("Dominio")).getAllByRole("option").map((o) => o.textContent)).toEqual(["civil", "telecom"]);
  });

  test("con lista para armar no hay aviso de lista", async () => {
    montar();
    await waitFor(() => expect(de("/v1/carpeta")).toHaveLength(1), ESPERA);
    await screen.findByText(/Comience por la cabecera/, {}, ESPERA);
    expect(screen.queryByText(/no tiene lista de precios/)).not.toBeInTheDocument();
  });

  test("sin aviso de lista cuando la API no da la carpeta", async () => {
    carpeta = () => json({ detalle: "El proceso no usa un archivo SQLite." }, 503);
    montar();
    await waitFor(() => expect(de("/v1/carpeta")).toHaveLength(1), ESPERA);
    await screen.findByText(/Comience por la cabecera/, {}, ESPERA);
    expect(screen.queryByText(/no tiene lista de precios/)).not.toBeInTheDocument();
    expect(screen.queryByText("El proceso no usa un archivo SQLite.")).not.toBeInTheDocument();
    // Sin saber la moneda no se inventa: no hay «Precios en …».
    expect(screen.queryByText(/^Precios en /)).not.toBeInTheDocument();
  });

  test("guardar está deshabilitado sin condiciones y se habilita al declararlas", async () => {
    const usuario = userEvent.setup();
    montar();
    expect(screen.getByRole("button", { name: "Guardar composición" })).toBeDisabled();
    await usuario.type(screen.getByLabelText("Condiciones del rendimiento"), "Terreno plano, ficticio");
    expect(screen.getByRole("button", { name: "Guardar composición" })).toBeEnabled();
  });

  test("el desglose se pide una sola vez, 300 ms después de la última edición, con las tablas como texto", async () => {
    // Temporizadores falsos: el retardo de 300 ms se avanza a mano, sin esperas reales ni tiempos holgados.
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    // Testing Library solo reconoce temporizadores falsos si existe un `jest` global (si no, su espera interna
    // con setTimeout queda colgada); se le da el avance de Vitest. afterEach deshace el stub.
    vi.stubGlobal("jest", { advanceTimersByTime: vi.advanceTimersByTime.bind(vi) });
    try {
      const usuario = userEvent.setup({ delay: null, advanceTimers: vi.advanceTimersByTime.bind(vi) });
      evaluacion = () => json(valida("29.70"));
      montar();
      await usuario.type(screen.getByLabelText("Código"), "FIC-1");
      await usuario.type(screen.getByLabelText("Rendimiento: unidades por día"), "10");
      await usuario.click(screen.getByRole("button", { name: "Agregar fila a Materiales" }));
      await usuario.type(screen.getByLabelText("Precio, fila 1"), "1.040,00");
      // Cada edición reinició el temporizador: a 299 ms de la última no se ha pedido ningún desglose.
      await vi.advanceTimersByTimeAsync(299);
      expect(de("/v1/composicion/evaluar")).toHaveLength(0);
      // Al cumplirse los 300 ms se pide exactamente una vez (12 pulsaciones, una sola petición).
      await vi.advanceTimersByTimeAsync(1);
      const evaluaciones = de("/v1/composicion/evaluar");
      expect(evaluaciones).toHaveLength(1);
      expect(evaluaciones[0].metodo).toBe("POST");
      expect(evaluaciones[0].cuerpo).toMatchObject({
        codigo: "FIC-1",
        dominio: "civil",
        rendimiento: "10",
        // Lo tecleado viaja tal cual: lo lee el servidor con la regla unica (aplicacion/cifras.py).
        materiales: [{ descripcion: "", unidad: "", cantidad: "", precio: "1.040,00" }],
        equipos: [],
        mano_obra: [],
      });
      await vi.advanceTimersByTimeAsync(0);
      expect(screen.getAllByText("29,70 Bs").length).toBeGreaterThan(0);
      // Sin más ediciones no se vuelve a pedir.
      await vi.advanceTimersByTimeAsync(1000);
      expect(de("/v1/composicion/evaluar")).toHaveLength(1);
    } finally {
      vi.useRealTimers();
    }
  });

  test("descarta la respuesta de una petición vieja", async () => {
    const usuario = userEvent.setup();
    const pendientes: ((r: Response) => void)[] = [];
    evaluacion = () => new Promise<Response>((resolver) => pendientes.push(resolver));
    montar();
    await usuario.type(screen.getByLabelText("Código"), "A");
    await waitFor(() => expect(pendientes).toHaveLength(1), ESPERA);
    await usuario.type(screen.getByLabelText("Código"), "B");
    await waitFor(() => expect(pendientes).toHaveLength(2), ESPERA);
    pendientes[1](json(valida("2.00")));
    expect(await screen.findAllByText("2,00 Bs", { selector: "td" }, ESPERA)).not.toHaveLength(0);
    pendientes[0](json(valida("1.00")));
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.queryByText("1,00 Bs", { selector: "td" })).not.toBeInTheDocument();
    expect(screen.getAllByText("2,00 Bs", { selector: "td" }).length).toBeGreaterThan(0);
  });

  test("al teclear un código que existe precarga tablas y rendimiento una sola vez, sin pisar lo editado", async () => {
    const usuario = userEvent.setup();
    partida = () => json({ existe: true, tablas: TABLAS_FICTICIAS, rendimiento_propuesto: "10,50", hay_historial: true });
    montar();
    await usuario.type(screen.getByLabelText("Código"), "FIC-1");
    await waitFor(() => expect(screen.getAllByLabelText("Descripción, fila 1")[0]).toHaveValue("Arena ficticia"), ESPERA);
    expect(screen.getByLabelText("Rendimiento: unidades por día")).toHaveValue("10,50");
    expect(screen.getAllByLabelText(/^Descripción, fila 1$/)).toHaveLength(2); // materiales y mano de obra
    expect(de("/v1/composicion/partidas/")).toHaveLength(1);

    await usuario.clear(screen.getByLabelText("Rendimiento: unidades por día"));
    await usuario.type(screen.getByLabelText("Rendimiento: unidades por día"), "12");
    await usuario.type(screen.getAllByLabelText("Descripción, fila 1")[0], " nueva");
    await new Promise((r) => setTimeout(r, 450));
    expect(de("/v1/composicion/partidas/")).toHaveLength(1);
    expect(screen.getByLabelText("Rendimiento: unidades por día")).toHaveValue("12");
    expect(screen.getAllByLabelText("Descripción, fila 1")[0]).toHaveValue("Arena ficticia nueva");
  });

  test("un código nuevo sin historial lo dice y no pisa las tablas", async () => {
    const usuario = userEvent.setup();
    montar();
    await usuario.click(screen.getByRole("button", { name: "Agregar fila a Equipos" }));
    await usuario.type(screen.getByLabelText("Código"), "NUEVA-1");
    expect(await screen.findByText(/Todavía no hay historial de rendimientos/, {}, ESPERA)).toBeInTheDocument();
    expect(screen.getByLabelText("Cantidad, fila 1")).toBeInTheDocument();
    // Prueba en vivo 2026-10-25: «es el comportamiento correcto, no un error» confundia a quien la leia.
    expect(screen.queryByText(/comportamiento correcto|no un error/)).not.toBeInTheDocument();
  });

  test("la justificación solo aparece cuando la API pide justificar", async () => {
    const usuario = userEvent.setup();
    evaluacion = () =>
      json(valida("29.70", { requiere_justificacion: true, advertencias: [{ tipo: "rendimiento", texto: "El rendimiento se aparta del histórico." }] }));
    montar();
    expect(screen.queryByLabelText(/Justificación de la advertencia/)).not.toBeInTheDocument();
    await usuario.type(screen.getByLabelText("Código"), "FIC-1");
    expect(await screen.findByText("El rendimiento se aparta del histórico.", {}, ESPERA)).toBeInTheDocument();
    expect(screen.getByLabelText(/Justificación de la advertencia/)).toBeInTheDocument();
  });

  test("guarda con condiciones, fecha y justificación, y muestra el resultado", async () => {
    const usuario = userEvent.setup();
    evaluacion = () => json(valida("29.70", { requiere_justificacion: true, advertencias: [{ tipo: "rendimiento", texto: "Aviso de rendimiento." }] }));
    montar();
    await usuario.type(screen.getByLabelText("Código"), "FIC-1");
    await usuario.type(screen.getByLabelText("Condiciones del rendimiento"), "Condiciones ficticias");
    await screen.findByLabelText(/Justificación de la advertencia/, {}, ESPERA);
    await usuario.type(screen.getByLabelText(/Justificación de la advertencia/), "Cuadrilla reforzada");
    await usuario.click(screen.getByRole("button", { name: "Guardar composición" }));
    expect(await screen.findByText(/Composición guardada para la partida FIC-1/, {}, ESPERA)).toBeInTheDocument();
    const envio = de("/v1/composicion/guardar")[0];
    expect(envio.metodo).toBe("POST");
    expect(envio.cuerpo).toMatchObject({
      codigo: "FIC-1",
      condiciones: "Condiciones ficticias",
      justificacion: "Cuadrilla reforzada",
    });
    expect(String(envio.cuerpo?.fecha)).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  test("sin advertencia de rendimiento la justificación viaja nula", async () => {
    const usuario = userEvent.setup();
    montar();
    await usuario.type(screen.getByLabelText("Condiciones del rendimiento"), "Condiciones ficticias");
    await usuario.click(screen.getByRole("button", { name: "Guardar composición" }));
    await screen.findByText(/Composición guardada/, {}, ESPERA);
    expect(de("/v1/composicion/guardar")[0].cuerpo?.justificacion).toBeNull();
  });

  test("un 422 de guardado se muestra con su detalle y no borra lo tecleado", async () => {
    const usuario = userEvent.setup();
    guardado = () => json({ detail: "La composición no es válida: falta un precio." }, 422);
    montar();
    await usuario.type(screen.getByLabelText("Código"), "FIC-1");
    await usuario.type(screen.getByLabelText("Condiciones del rendimiento"), "Condiciones ficticias");
    await usuario.click(screen.getByRole("button", { name: "Guardar composición" }));
    expect(await screen.findByText("La composición no es válida: falta un precio.", {}, ESPERA)).toBeInTheDocument();
    expect(screen.getByLabelText("Código")).toHaveValue("FIC-1");
  });

  test("la ayuda de las cifras dice la regla: coma decimal, punto de miles (Eugenio, 2026-10-25)", () => {
    montar();
    expect(screen.getByText(AYUDA_CIFRAS)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/con coma o con punto|sin separador de miles/);
  });

  test("un dato mal escrito no borra el último desglose: lo conserva, marcado, junto al aviso", async () => {
    // Prueba en vivo 2026-10-25: un número ilegible dejaba la pantalla sin desglose y solo con el mensaje.
    const usuario = userEvent.setup();
    const AVISO = "En Equipos, fila 1 («Mezcladora»), la depreciación «0,0,5» no es un número: escriba solo cifras.";
    evaluacion = () => json(valida("29.70"));
    montar();
    await usuario.type(screen.getByLabelText("Código"), "FIC-1");
    expect(await screen.findAllByText("29,70 Bs", { selector: "td" }, ESPERA)).not.toHaveLength(0);

    evaluacion = () => json({ ...VACIA, estado: "incompleto", aviso: AVISO });
    // Pulido F5, Tarea 1: el «Código» es un campo con búsqueda y, con sus sugerencias abiertas, su lista también se llama
    // «Código»: se nombra el campo por su papel. Cambia el selector, no lo que se comprueba.
    await usuario.type(screen.getByRole("combobox", { name: "Código" }), "X");
    expect(await screen.findByText(AVISO, {}, ESPERA)).toBeInTheDocument();
    expect(screen.getAllByText("29,70 Bs", { selector: "td" }).length).toBeGreaterThan(0);
    expect(screen.getByText(/último desglose calculado/i)).toBeInTheDocument();

    // Con el formulario vacío otra vez no queda nada viejo a la vista.
    evaluacion = () => json(VACIA);
    await usuario.clear(screen.getByRole("combobox", { name: "Código" }));
    expect(await screen.findByText(/Comience por la cabecera/, {}, ESPERA)).toBeInTheDocument();
    expect(screen.queryByText("29,70 Bs", { selector: "td" })).not.toBeInTheDocument();
  });

  test("un 401 en el desglose llama a alExpirar", async () => {
    const usuario = userEvent.setup();
    evaluacion = () => json({ detalle: "Sesión vencida." }, 401);
    const app = montar();
    await usuario.type(screen.getByLabelText("Código"), "F");
    await waitFor(() => expect(app.alExpirar).toHaveBeenCalled(), ESPERA);
  });

  test("un error del desglose se muestra y la página sigue usable", async () => {
    const usuario = userEvent.setup();
    evaluacion = () => json({ detalle: "El cálculo falló." }, 500);
    montar();
    await usuario.type(screen.getByLabelText("Código"), "F");
    expect(await screen.findByText("El cálculo falló.", {}, ESPERA)).toBeInTheDocument();
    expect(screen.getByLabelText("Código")).toBeEnabled();
  });

  test("el buscador de referencia agrega la fila completada a su tabla", async () => {
    const usuario = userEvent.setup();
    montar();
    await usuario.type(screen.getByLabelText("Buscar en la referencia MaPreX (materiales)"), "cem");
    expect(await screen.findByText("Referencia MaPreX: REF-FICT-001", {}, ESPERA)).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Usar esta fila" }));
    expect(screen.getAllByLabelText("Descripción, fila 1")[0]).toHaveValue("Cemento ficticio");
    expect(screen.getByLabelText("Precio, fila 1")).toHaveValue("9.90");
  });

  test("al teclear la descripción pide las partidas similares del dominio y las lista", async () => {
    const usuario = userEvent.setup();
    montar();
    await usuario.type(screen.getByLabelText("Descripción"), "muro");
    expect(await screen.findByText("0,91 · FIC-009 · Muro ficticio", {}, ESPERA)).toBeInTheDocument();
    expect(de("/v1/composicion/similares")[0].ruta).toBe("/v1/composicion/similares?dominio=civil&descripcion=muro");
  });

  test("el texto visible no usa jerga interna (UC-10, UC-11, RF-33) ni rayas", async () => {
    montar();
    await screen.findByRole("heading", { name: "Componer una partida" });
    const texto = document.body.textContent ?? "";
    expect(texto).not.toMatch(/UC-\d|RF-\d/);
    expect(texto).not.toContain("—");
  });
});
