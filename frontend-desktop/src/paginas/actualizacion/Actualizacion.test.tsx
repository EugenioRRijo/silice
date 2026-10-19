import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { InformeAuditoriaRespuesta, SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaActualizacion from "./index";
import type { Revaloracion, VistaPrevia } from "./logica";
import { hoyIso, nombreDeLista } from "./logica";

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

const PRESUPUESTOS = [
  { codigo: "001", total: "1000.00", proyecto: "Obra ficticia A" },
  { codigo: "007", total: "500.00", proyecto: "Obra ficticia B" },
];

const INFORME: InformeAuditoriaRespuesta = {
  codigo_presupuesto: "002",
  cumple: true,
  veredicto: "Cumple",
  total_hallazgos: 0,
  por_severidad: [],
  reglas_evaluadas: [],
  hallazgos: [],
  sin_hallazgos: "Se verificaron las reglas y no hubo hallazgos.",
};

const VISTA: VistaPrevia = {
  desconocidos: [
    { descripcion: "Tornillo ficticio", tipo: "material", unidad: "u", precio: "1.50", etiqueta: "Tornillo ficticio (material, u)" },
    { descripcion: "Arandela ficticia", tipo: "material", unidad: "u", precio: "0.25", etiqueta: "Arandela ficticia (material, u)" },
  ],
  motivo: null,
};

const REVALORACION: Revaloracion = {
  proyecto: "Obra ficticia A",
  codigo_base: "001",
  codigo_nuevo: "002",
  moneda: "USD",
  resumen: "1000.00 -> 1100.00 USD  (variacion 100.00 USD, 10.00 %)",
  filas: [
    {
      codigo_partida: "FIC-01",
      descripcion: "Vaciado ficticio",
      cantidad: "10.00",
      pu_anterior: "100.00",
      pu_nuevo: "110.00",
      variacion_pct: "10.00",
      total_anterior: "1000.00",
      total_nuevo: "1100.00",
      incidencia_pct: "100.00",
    },
  ],
  dados_de_alta: ["Tornillo ficticio"],
  ignorados: ["Arandela ficticia"],
  rechazados: ["Clavo ficticio (material, kg)"],
  version_guardada: "002",
  avisos: [
    { nivel: "advertencia", texto: "Aviso de advertencia ficticio." },
    { nivel: "info", texto: "Aviso informativo ficticio." },
  ],
  informe: INFORME,
};

describe("Actualizar precios", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let presupuestos: () => Response;
  let vista: () => Response;
  let revalorar: () => Response;
  let descartar: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    presupuestos = () => json(PRESUPUESTOS);
    vista = () => json(VISTA);
    revalorar = () => json(REVALORACION);
    descartar = () => json({ codigo: "002", descartada: true, fecha: "2026-10-18" });
    fetchFalso.mockImplementation(async (ruta, opciones) => {
      const url = String(ruta);
      const metodo = opciones?.method ?? "GET";
      if (url === "/presupuestos" && metodo === "GET") return presupuestos();
      if (url === "/listas-precios/vista-previa") return vista();
      if (url === "/presupuestos/revalorar") return revalorar();
      if (url.includes("/descartar")) return descartar();
      if (url.includes("/excel")) return new Response(new Blob(["x"]), { status: 200 });
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
        <PaginaActualizacion />
      </ContextoAplicacion.Provider>,
    );
    return alExpirar;
  }

  function campoArchivo(): HTMLInputElement {
    return document.querySelector('input[type="file"]') as HTMLInputElement;
  }

  async function subir(nombre = "lista.csv") {
    const usuario = userEvent.setup();
    const archivo = new File(["tipo,insumo,unidad,precio"], nombre);
    await screen.findByRole("option", { name: "Obra ficticia A / 001" });
    await usuario.upload(campoArchivo(), archivo);
    return { usuario, archivo };
  }

  function llamada(fragmento: string) {
    return fetchFalso.mock.calls.find(([ruta]) => String(ruta).includes(fragmento));
  }

  test("lista los presupuestos como «proyecto / codigo» y muestra la ayuda y los valores por defecto", async () => {
    montar();
    expect(await screen.findByRole("option", { name: "Obra ficticia A / 001" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Obra ficticia B / 007" })).toBeInTheDocument();
    expect(screen.getByText(/Carga una lista de precios nueva \(CSV o XLSX/)).toBeInTheDocument();
    expect(screen.getByLabelText("Código de la versión nueva")).toHaveValue("002");
    expect(screen.getByLabelText("Moneda")).toHaveValue("USD");
    expect(screen.getByLabelText("Fecha de vigencia")).toHaveValue(hoyIso());
    expect(screen.getByLabelText("Nombre de la lista")).toHaveValue(nombreDeLista(hoyIso()));
    expect(screen.getByRole("button", { name: "Revalorar presupuesto" })).toBeDisabled();
  });

  test("el nombre de la lista sigue a la vigencia mientras no se edite", async () => {
    montar();
    await screen.findByRole("option", { name: "Obra ficticia A / 001" });
    const usuario = userEvent.setup();
    const fecha = screen.getByLabelText("Fecha de vigencia");
    await usuario.clear(fecha);
    await usuario.type(fecha, "2026-03-05");
    expect(screen.getByLabelText("Nombre de la lista")).toHaveValue("Lista 05/03/2026");
    const nombre = screen.getByLabelText("Nombre de la lista");
    await usuario.clear(nombre);
    await usuario.type(nombre, "Mi lista");
    await usuario.clear(fecha);
    await usuario.type(fecha, "2026-04-06");
    expect(nombre).toHaveValue("Mi lista");
  });

  test("sin presupuestos guardados muestra el estado vacio", async () => {
    presupuestos = () => json([]);
    montar();
    expect(await screen.findByText("No hay presupuestos guardados todavia")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Revalorar presupuesto" })).toBeNull();
  });

  test("al subir el archivo pide la vista previa y lista los desconocidos sin marcar", async () => {
    montar();
    await subir();
    expect(
      await screen.findByText(
        /El archivo trae 2 insumo\(s\) que no estan en el catalogo \(UC-02, flujo 2a\): Tornillo ficticio \(material, u\), Arandela ficticia \(material, u\)\. Elija en "Dar de alta"/,
      ),
    ).toBeInTheDocument();
    const [ruta, opciones] = llamada("vista-previa")!;
    expect(ruta).toBe("/listas-precios/vista-previa");
    expect(opciones?.method).toBe("POST");
    expect((opciones?.body as FormData).get("archivo")).toBeInstanceOf(File);
    const uno = screen.getByRole("checkbox", { name: "1. Tornillo ficticio (material, u), precio 1.50" });
    const dos = screen.getByRole("checkbox", { name: "2. Arandela ficticia (material, u), precio 0.25" });
    expect(uno).not.toBeChecked();
    expect(dos).not.toBeChecked();
    expect(screen.getByRole("button", { name: "Revalorar presupuesto" })).toBeEnabled();
  });

  test("el motivo de la vista previa se muestra como aviso informativo", async () => {
    vista = () => json({ desconocidos: [], motivo: "No se pudo leer el archivo ficticio." });
    montar();
    await subir();
    expect(await screen.findByText("No se pudo leer el archivo ficticio.")).toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).toBeNull();
  });

  test("cambiar el archivo limpia la vista previa y las casillas", async () => {
    montar();
    const { usuario } = await subir();
    await usuario.click(await screen.findByRole("checkbox", { name: /1\. Tornillo/ }));
    vista = () => json({ desconocidos: [], motivo: null });
    await usuario.upload(campoArchivo(), new File(["x"], "otra.csv"));
    await waitFor(() => expect(screen.queryByRole("checkbox")).toBeNull());
    expect(screen.queryByText(/El archivo trae/)).toBeNull();
  });

  test("una vista previa vieja se descarta si ya se eligio otro archivo", async () => {
    const pendientes: ((r: Response) => void)[] = [];
    fetchFalso.mockImplementation(async (ruta) => {
      const url = String(ruta);
      if (url === "/presupuestos") return json(PRESUPUESTOS);
      return new Promise<Response>((r) => pendientes.push(r));
    });
    montar();
    const usuario = userEvent.setup();
    await screen.findByRole("option", { name: "Obra ficticia A / 001" });
    await usuario.upload(campoArchivo(), new File(["x"], "uno.csv"));
    await usuario.upload(campoArchivo(), new File(["x"], "dos.csv"));
    expect(pendientes).toHaveLength(2);
    pendientes[1](json({ desconocidos: [], motivo: "Motivo de la segunda." }));
    expect(await screen.findByText("Motivo de la segunda.")).toBeInTheDocument();
    pendientes[0](json({ desconocidos: [], motivo: "Motivo de la primera." }));
    await new Promise((r) => setTimeout(r, 20));
    expect(screen.queryByText("Motivo de la primera.")).toBeNull();
  });

  test("envia el multipart con dar_de_alta solo de lo marcado", async () => {
    montar();
    const { usuario, archivo } = await subir();
    await usuario.click(await screen.findByRole("checkbox", { name: /2\. Arandela/ }));
    await usuario.selectOptions(screen.getByLabelText("Presupuesto base"), "Obra ficticia B / 007");
    await usuario.click(screen.getByRole("button", { name: "Revalorar presupuesto" }));
    await screen.findByText("Comparativo por partida");
    const [ruta, opciones] = llamada("/revalorar")!;
    expect(ruta).toBe("/presupuestos/revalorar");
    expect(opciones?.method).toBe("POST");
    const f = opciones?.body as FormData;
    expect((f.get("archivo") as File).name).toBe(archivo.name);
    expect(f.get("proyecto")).toBe("Obra ficticia B");
    expect(f.get("codigo")).toBe("007");
    expect(f.get("codigo_nuevo")).toBe("002");
    expect(f.get("moneda")).toBe("USD");
    expect(f.get("fecha_vigencia")).toBe(hoyIso());
    expect(f.get("nombre")).toBe(nombreDeLista(hoyIso()));
    expect(f.getAll("dar_de_alta")).toEqual(["Arandela ficticia"]);
  });

  test("mientras revalora dice «Revalorando...»", async () => {
    montar();
    const { usuario } = await subir();
    let soltar: (r: Response) => void = () => undefined;
    fetchFalso.mockImplementation(async (ruta) => {
      const url = String(ruta);
      if (url === "/presupuestos/revalorar") return new Promise<Response>((r) => (soltar = r));
      return json(VISTA);
    });
    await usuario.click(screen.getByRole("button", { name: "Revalorar presupuesto" }));
    expect(await screen.findByText("Revalorando...")).toBeInTheDocument();
    soltar(json(REVALORACION));
    expect(await screen.findByText("Comparativo por partida")).toBeInTheDocument();
  });

  test("muestra avisos, metrica, tabla de 9 columnas, altas, ignorados, rechazados e informe", async () => {
    montar();
    const { usuario } = await subir();
    await usuario.click(screen.getByRole("button", { name: "Revalorar presupuesto" }));
    expect(await screen.findByText("Comparativo por partida")).toBeInTheDocument();
    expect(screen.getByText("Aviso de advertencia ficticio.")).toBeInTheDocument();
    expect(screen.getByText("Aviso informativo ficticio.")).toBeInTheDocument();
    expect(screen.getByText("Total del presupuesto")).toBeInTheDocument();
    expect(screen.getByText(REVALORACION.resumen.replace(/\s+/g, " "))).toBeInTheDocument();
    const tabla = screen.getByRole("table", { name: /Comparativo/ });
    expect(within(tabla).getAllByRole("columnheader")).toHaveLength(9);
    expect(within(tabla).getByText("1100.00")).toBeInTheDocument();
    expect(
      screen.getByText("Se dieron de alta en el catalogo, con precio solo en la lista nueva (UC-02, flujo 2a): Tornillo ficticio"),
    ).toBeInTheDocument();
    expect(screen.getByText(/Se ignoraron los insumos del archivo.*: Arandela ficticia/)).toBeInTheDocument();
    expect(
      screen.getByText(/Se rechazaron las filas cuyo insumo esta en el catalogo con otra unidad \(UC-02, flujo 2b.*: Clavo ficticio \(material, kg\)/),
    ).toBeInTheDocument();
    expect(screen.getByText("Informe de auditoria de la version nueva")).toBeInTheDocument();
    expect(screen.getByText("Se verificaron las reglas y no hubo hallazgos.")).toBeInTheDocument();
  });

  test("con version guardada ofrece Excel de esa version", async () => {
    montar();
    const { usuario } = await subir();
    await usuario.click(screen.getByRole("button", { name: "Revalorar presupuesto" }));
    await screen.findByText("Comparativo por partida");
    URL.createObjectURL = vi.fn(() => "blob:x");
    URL.revokeObjectURL = vi.fn();
    await usuario.click(screen.getByRole("button", { name: "Exportar a Excel" }));
    await waitFor(() => expect(llamada("/excel")).toBeDefined());
    expect(llamada("/excel")![0]).toBe("/presupuestos/002/excel?proyecto=Obra%20ficticia%20A");
  });

  test("sin version guardada no hay Excel ni Descartar", async () => {
    revalorar = () => json({ ...REVALORACION, version_guardada: null });
    montar();
    const { usuario } = await subir();
    await usuario.click(screen.getByRole("button", { name: "Revalorar presupuesto" }));
    await screen.findByText("Comparativo por partida");
    expect(screen.queryByRole("button", { name: "Exportar a Excel" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Descartar version" })).toBeNull();
  });

  test("descartar reemplaza el boton por el aviso", async () => {
    montar();
    const { usuario } = await subir();
    await usuario.click(screen.getByRole("button", { name: "Revalorar presupuesto" }));
    await usuario.click(await screen.findByRole("button", { name: "Descartar version" }));
    expect(
      await screen.findByText("Version 002 descartada: sigue guardada como documento y su historial de cambios se conserva (UC-02, flujo 7a)."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Descartar version" })).toBeNull();
    const [ruta, opciones] = llamada("/descartar")!;
    expect(ruta).toBe("/presupuestos/002/descartar?proyecto=Obra%20ficticia%20A");
    expect(opciones?.method).toBe("POST");
  });

  test("un error al descartar se muestra y el boton sigue", async () => {
    descartar = () => json({ detalle: "La version ya no existe." }, 404);
    montar();
    const { usuario } = await subir();
    await usuario.click(screen.getByRole("button", { name: "Revalorar presupuesto" }));
    await usuario.click(await screen.findByRole("button", { name: "Descartar version" }));
    expect(await screen.findByText("La version ya no existe.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Descartar version" })).toBeInTheDocument();
  });

  test("una revaloracion nueva olvida el descarte anterior", async () => {
    montar();
    const { usuario } = await subir();
    await usuario.click(screen.getByRole("button", { name: "Revalorar presupuesto" }));
    await usuario.click(await screen.findByRole("button", { name: "Descartar version" }));
    await screen.findByText(/descartada/);
    await usuario.click(screen.getByRole("button", { name: "Revalorar presupuesto" }));
    expect(await screen.findByRole("button", { name: "Descartar version" })).toBeInTheDocument();
    expect(screen.queryByText(/descartada/)).toBeNull();
  });

  test("un 422 muestra el detalle y no hay resultado", async () => {
    revalorar = () => json({ detalle: "Falta el precio de Arena ficticia." }, 422);
    montar();
    const { usuario } = await subir();
    await usuario.click(screen.getByRole("button", { name: "Revalorar presupuesto" }));
    expect(await screen.findByText("Falta el precio de Arena ficticia.")).toBeInTheDocument();
    expect(screen.queryByText("Comparativo por partida")).toBeNull();
    expect(screen.getByRole("button", { name: "Revalorar presupuesto" })).toBeEnabled();
  });

  test("un 401 avisa a alExpirar", async () => {
    revalorar = () => json({ detalle: "Sesión ausente o vencida." }, 401);
    const alExpirar = montar();
    const { usuario } = await subir();
    await usuario.click(screen.getByRole("button", { name: "Revalorar presupuesto" }));
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("un 401 al listar presupuestos avisa a alExpirar", async () => {
    presupuestos = () => json({ detalle: "Sesión ausente o vencida." }, 401);
    const alExpirar = montar();
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });
});
