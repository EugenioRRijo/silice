import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { alertaConTexto } from "../../test/ayudas";
import PaginaRevisar from "./index";
import type { ContraLista, DictamenGuardado, ExcelExterno, Revision } from "./tipos";

// «Revisar un paquete» en la interfaz nueva (T7). Las respuestas son las de /v1/revision escritas a mano con los
// textos literales de la pantalla clasica (ui/paginas/revisar.py, paquete/verificar.py) y la memoria del ejemplo
// minimo (total 836,7975 USD). La interfaz no calcula: muestra el texto de la API con formato es-VE.

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "rita",
  nombre: "Rita",
  roles: ["revisa"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["leer_proyecto", "revisar_paquete"],
  modo_entrega: false,
};

const VERIFICADO =
  "Verificado: emitido por Contratista Demo, C.A. el 2026-11-10. No se alteró desde que se firmó.";
const RECHAZADO =
  "Rechazado: El archivo no es un paquete de Silice válido (el ZIP está dañado). Pida uno nuevo.";

const CONTRA_MI_LISTA: ContraLista = {
  lista_id: 2,
  diferencia: {
    titulo: "El paquete con los precios de mi lista",
    total_antes: "836.7975",
    total_antes_texto: "836.80",
    total_despues: "887.3975",
    total_despues_texto: "887.40",
    diferencia: "50.6000",
    diferencia_texto: "50.60",
    por_cantidad_y_precio: "Por cantidad: 0.00. Por precio: 50.60.",
    partidas: [
      {
        codigo_partida: "MIN-001",
        descripcion: "Relleno de prueba",
        estado: "cambiada",
        desvio_cantidad: "0",
        desvio_cantidad_texto: "0.00",
        desvio_precio: "50.6000",
        desvio_precio_texto: "50.60",
        desvio_total: "50.6000",
        desvio_total_texto: "50.60",
      },
    ],
  },
  no_contrastables: "No contrastables (no están en mi lista; no suman): EQU-001, MO-001",
};

const CONTRA_LA_DE_PRUEBA: ContraLista = {
  lista_id: 1,
  diferencia: {
    ...CONTRA_MI_LISTA.diferencia,
    total_despues: "836.7975",
    total_despues_texto: "836.80",
    diferencia: "0",
    diferencia_texto: "0.00",
    por_cantidad_y_precio: "Por cantidad: 0.00. Por precio: 0.00.",
    partidas: [],
  },
  no_contrastables: null,
};

const REVISION: Revision = {
  sha256: "a".repeat(64),
  estado: "verificado",
  motivo: "firma_valida",
  color: "verde",
  banner: VERIFICADO,
  legible: true,
  banner_version: "Versión 005 del 2026-11-10; es la primera que recibe de este proyecto.",
  ayuda_registro: null,
  avisos: ["Este paquete se emitió para Obra Norte."],
  retroactiva: null,
  aviso_armo: null,
  reauditoria: {
    termino: true,
    avisos: [],
    total_recalculado: "836.79750000",
    total_recalculado_texto: "836.80",
    reglas: "Reglas corridas a la fecha de emisión (2026-11-10): R1-R7, R11-R12.",
    precios_coinciden: true,
    mensaje_precios: "Los precios y totales que declara el paquete coinciden con los recalculados.",
    diferencias: [],
    hallazgos: [
      {
        titulo: "El emisor no los declaró",
        hallazgos: [{ regla: "R11", severidad: "INFO", descripcion: "3 insumos no contrastables" }],
      },
      { titulo: "Los declaró y ya no aparecen", hallazgos: [] },
      { titulo: "En común", hallazgos: [] },
    ],
  },
  entrega_anterior: null,
  sin_entrega_anterior: "Esta instalación no recibió una entrega anterior de este proyecto.",
  listas: [
    { id: 2, nombre: "Lista del revisor" },
    { id: 1, nombre: "Lista de prueba" },
  ],
  sin_listas: null,
  contra_lista: CONTRA_MI_LISTA,
  cambios_titulo: "Quién cambió qué",
  cambios: [
    {
      version: "005",
      objeto: "apu",
      clave: "MIN-001|Arena",
      campo: "cantidad",
      antes: "1.00",
      despues: "1.50",
      fuente: "memoria",
      responsable: "Ana <ana>",
      fecha: "2026-11-02T08:00:00",
      marca: "",
    },
  ],
  dictamenes: [],
  resultados: ["conforme", "con observaciones", "rechazado"],
  nota_excel: "Este Excel se regeneró aquí desde presupuesto.json; el del emisor no se ofrece.",
};

const RECHAZADA: Revision = {
  ...REVISION,
  estado: "rechazado",
  motivo: "rechazado",
  color: "rojo",
  banner: RECHAZADO,
  legible: false,
  banner_version: null,
  avisos: [],
  reauditoria: null,
  sin_entrega_anterior: null,
  listas: [],
  contra_lista: null,
  cambios: [],
};

const DICTAMEN: DictamenGuardado = {
  mensaje: "Dictamen guardado, atado al SHA-256 de este archivo.",
  dictamenes: [
    {
      resultado: "con observaciones",
      usuario: "Rita <rita>",
      fecha: "2026-11-12T10:05",
      estado_verificacion: "verificado",
      texto: "Dictamen anterior: con observaciones · Rita <rita> · 2026-11-12 10:05 · verificación entonces: verificado",
    },
  ],
};

const EXTERNO: ExcelExterno = {
  aviso: "No verificado: un Excel no trae cadena ni firma. Se audita igual.",
  total: "836.79750000",
  total_texto: "836.80",
  hallazgos: [{ regla: "R2", severidad: "ERROR", descripcion: "La curva no cierra" }],
};

describe("Revisar un paquete", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let paquete: () => Response;
  let dictamen: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    paquete = () => json(REVISION);
    dictamen = () => json(DICTAMEN);
    fetchFalso.mockImplementation(async (ruta, opciones) => {
      const url = String(ruta);
      if (url === "/v1/revision/paquete") return paquete();
      if (url === "/v1/revision/contra-lista") {
        const lista = (opciones?.body as FormData).get("lista");
        return json(lista === "1" ? CONTRA_LA_DE_PRUEBA : CONTRA_MI_LISTA);
      }
      if (url === "/v1/revision/dictamen") return dictamen();
      if (url === "/v1/revision/excel-externo") return json(EXTERNO);
      return json({ detalle: "ruta inesperada " + url }, 404);
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  function montar(alExpirar = vi.fn()) {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: { nombre: "clinica", ruta_relativa: "data/clinica.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    render(
      <ContextoAplicacion.Provider value={valor}>
        <PaginaRevisar />
      </ContextoAplicacion.Provider>,
    );
    return alExpirar;
  }

  function llamadas(url: string) {
    return fetchFalso.mock.calls.filter(([ruta]) => String(ruta) === url);
  }

  async function subir(nombre = "recibido.silice") {
    const usuario = userEvent.setup();
    const campo = document.querySelector('input[type="file"]') as HTMLInputElement;
    await usuario.upload(campo, new File(["PK"], nombre));
    return usuario;
  }

  async function subirYEsperar() {
    montar();
    const usuario = await subir();
    await screen.findByText(VERIFICADO);
    return usuario;
  }

  test("tiene un solo h1, las dos pestañas de la clasica y dice que elija el archivo", () => {
    montar();
    expect(screen.getAllByRole("heading", { level: 1 }).map((h) => h.textContent)).toEqual(["Revisar un paquete"]);
    expect(screen.getByRole("tab", { name: "Paquete .silice" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Presupuesto en Excel" })).toBeInTheDocument();
    expect(screen.getByText("Elija el archivo .silice que recibió.")).toBeInTheDocument();
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("subir un paquete lo manda a la API y muestra banner, version, total, hallazgos y cambios", async () => {
    await subirYEsperar();
    const [, opciones] = llamadas("/v1/revision/paquete")[0];
    expect(opciones?.method).toBe("POST");
    expect(((opciones?.body as FormData).get("paquete") as File).name).toBe("recibido.silice");
    expect(screen.getByText("Versión 005 del 2026-11-10; es la primera que recibe de este proyecto.")).toBeInTheDocument();
    expect(screen.getByText("Este paquete se emitió para Obra Norte.")).toBeInTheDocument();
    const recalculado = screen.getByText("Total recalculado").parentElement as HTMLElement;
    expect(within(recalculado).getByText("836,80")).toHaveAttribute("title", "Valor exacto: 836.79750000");
    expect(screen.getByText("Reglas corridas a la fecha de emisión (2026-11-10): R1-R7, R11-R12.")).toBeInTheDocument();
    expect(
      screen.getByText("Los precios y totales que declara el paquete coinciden con los recalculados."),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "El emisor no los declaró (1)" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "En común (0)" })).toBeInTheDocument();
    const nuevos = screen.getByRole("table", { name: "El emisor no los declaró" });
    expect(within(nuevos).getByText("Información")).toBeInTheDocument(); // la severidad con su nombre, no solo color
    expect(screen.getByText("Esta instalación no recibió una entrega anterior de este proyecto.")).toBeInTheDocument();
    const cambios = screen.getByRole("table", { name: "Quién cambió qué" });
    expect(within(cambios).getByText("MIN-001|Arena")).toBeInTheDocument();
    expect(screen.getByText(REVISION.nota_excel)).toBeInTheDocument();
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });

  test("el contraste usa la lista mas nueva y al elegir otra la pide a la API con el mismo archivo", async () => {
    const usuario = await subirYEsperar();
    expect(screen.getByText("No contrastables (no están en mi lista; no suman): EQU-001, MO-001")).toBeInTheDocument();
    const contraste = screen.getByRole("region", { name: "El paquete con los precios de mi lista" });
    expect(within(contraste).getByText("887,40")).toHaveAttribute("title", "Valor exacto: 887.3975");
    expect(within(contraste).getByText("Por cantidad: 0.00. Por precio: 50.60.")).toBeInTheDocument();
    await usuario.selectOptions(screen.getByLabelText("Contrastar con mi lista"), "1");
    await waitFor(() => expect(llamadas("/v1/revision/contra-lista")).toHaveLength(1));
    const cuerpo = llamadas("/v1/revision/contra-lista")[0][1]?.body as FormData;
    expect(cuerpo.get("lista")).toBe("1");
    expect((cuerpo.get("paquete") as File).name).toBe("recibido.silice");
    expect(await within(contraste).findByText("Por cantidad: 0.00. Por precio: 0.00.")).toBeInTheDocument();
    expect(screen.queryByText(/No contrastables/)).not.toBeInTheDocument();
  });

  test("un archivo rechazado muestra el mensaje de la clasica y nada que auditar", async () => {
    paquete = () => json(RECHAZADA);
    montar();
    await subir();
    expect(await alertaConTexto()).toHaveTextContent(RECHAZADO);
    expect(screen.queryByText("Total recalculado")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Guardar dictamen" })).not.toBeInTheDocument();
  });

  test("un documento con la forma equivocada muestra el detalle de la API", async () => {
    paquete = () => json({ detalle: "El documento o su anexo no tiene la forma esperada." }, 422);
    montar();
    await subir();
    expect(await alertaConTexto()).toHaveTextContent("El documento o su anexo no tiene la forma esperada.");
  });

  test("la sesion vencida avisa al marco", async () => {
    paquete = () => json({ detalle: "Sesión ausente o vencida: entre de nuevo con su cuenta." }, 401);
    const alExpirar = montar();
    await subir();
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("el dictamen manda resultado y notas, muestra el error de la API y, guardado, vacia el formulario", async () => {
    const usuario = await subirYEsperar();
    dictamen = () => json({ detalle: "Un dictamen con observaciones o de rechazo necesita notas." }, 422);
    await usuario.click(screen.getByRole("radio", { name: "con observaciones" }));
    await usuario.click(screen.getByRole("button", { name: "Guardar dictamen" }));
    expect(await screen.findByText("Un dictamen con observaciones o de rechazo necesita notas.")).toBeInTheDocument();
    dictamen = () => json(DICTAMEN);
    await usuario.type(screen.getByLabelText("Notas"), "Falta la memoria de cálculo de R4");
    await usuario.click(screen.getByRole("button", { name: "Guardar dictamen" }));
    expect(await screen.findByText(DICTAMEN.mensaje)).toBeInTheDocument();
    const cuerpo = llamadas("/v1/revision/dictamen")[1][1]?.body as FormData;
    expect([cuerpo.get("resultado"), cuerpo.get("notas")]).toEqual([
      "con observaciones",
      "Falta la memoria de cálculo de R4",
    ]);
    expect(screen.getByLabelText("Notas")).toHaveValue("");
    expect(screen.getByText(DICTAMEN.dictamenes[0].texto)).toBeInTheDocument();
  });

  test("quien revisa lo que armo ve el aviso y una empresa no registrada, la ayuda", async () => {
    paquete = () =>
      json({
        ...REVISION,
        color: "ambar",
        banner: "No verificado: dice venir de Contratista Demo, C.A., pero no se pudo comprobar.",
        ayuda_registro: "Para que sus paquetes salgan verificados, el administrador debe registrar la clave.",
        aviso_armo: "Usted armó o cambió este presupuesto: (figura en la versión 005).",
      });
    montar();
    await subir();
    expect(await screen.findByText(/^No verificado: dice venir de/)).toBeInTheDocument();
    expect(screen.getByText(/el administrador debe registrar la clave/)).toBeInTheDocument();
    expect(screen.getByText(/Usted armó o cambió este presupuesto/)).toBeInTheDocument();
  });

  test("la pestaña de Excel ofrece la plantilla y audita un presupuesto en memoria", async () => {
    montar();
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("tab", { name: "Presupuesto en Excel" }));
    expect(screen.getByRole("button", { name: "Descargar la plantilla del formato" })).toBeInTheDocument();
    const campos = document.querySelectorAll('input[type="file"]');
    await usuario.upload(campos[campos.length - 1] as HTMLInputElement, new File(["PK"], "externo.xlsx"));
    expect(await screen.findByText(EXTERNO.aviso)).toBeInTheDocument();
    const cuerpo = llamadas("/v1/revision/excel-externo")[0][1]?.body as FormData;
    expect((cuerpo.get("presupuesto") as File).name).toBe("externo.xlsx");
    expect(screen.getByText("836,80")).toHaveAttribute("title", "Valor exacto: 836.79750000");
    expect(within(screen.getByRole("table", { name: "Hallazgos del presupuesto en Excel" })).getByText("R2")).toBeInTheDocument();
  });
});
