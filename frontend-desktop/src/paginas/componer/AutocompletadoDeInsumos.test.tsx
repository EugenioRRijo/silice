import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { TablaInsumos } from "./TablaInsumos";
import { agregarFila, borrarFila, completarFila, editarCelda, tablasVacias } from "./tablas";
import type { Fila, Tablas, TipoTabla } from "./tablas";

// AC1 (pedido de Eugenio, 2026-10-21): la descripción de cada fila es un campo con sugerencias del catálogo. AC1b: el precio
// que se llena es el de la lista para armar a la fecha de la composición, con su moneda, y llega en la misma respuesta de
// `GET /v1/consulta/{tabla}`; nunca el de la lista vigente de `GET /insumos`. Montos y textos ficticios; la API es un
// `fetch` falso con la forma de `api/rutas/consulta.py`.

const MODALIDADES = ["JORNAL", "DESTAJO"];
const AVISO = "Descripción propia: no viene del catálogo.";
const FECHA = "2026-08-15";

// `precio` es el de la lista para armar a FECHA; `vigente`, el de la lista vigente hoy (lo que da `GET /insumos`): son
// distintos a propósito para que la prueba sepa de dónde salió el precio.
const CATALOGO = [
  { codigo: "MAT-1", descripcion: "Cemento gris ficticio", tipo: "material", unidad: "saco", precio: "18.00", vigente: "25.50" },
  { codigo: "MAT-2", descripcion: "Cemento blanco ficticio", tipo: "material", unidad: null, precio: null, vigente: null },
  { codigo: "EQ-1", descripcion: "Mezcladora ficticia", tipo: "equipo", unidad: "h", precio: "2000", vigente: "2500" },
  { codigo: "MO-1", descripcion: "Albañil ficticio", tipo: "mano_obra", unidad: null, precio: "12.3400", vigente: "15" },
];
const TIPOS_DE: Record<string, string[]> = { insumos: ["material", "equipo"], salarios_cct: ["mano_obra"] };

let llamadas: string[];
let estadoDeConsulta: number;
// La moneda de la lista para armar (la carpeta trabaja en Bs): en USD el servidor no manda el precio y sí el aviso.
let monedaDeLaLista: "Bs" | "USD";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

function sugerencia(i: (typeof CATALOGO)[number], params: URLSearchParams) {
  const base = {
    valor: i.codigo,
    etiqueta: `${i.descripcion} (${i.codigo}${i.unidad ? `, ${i.unidad}` : ""})`,
    fuente: `Catálogo de la carpeta de trabajo: ${i.tipo.replace("_", " ")}`,
  };
  const fecha = params.get("para_armar_al");
  if (params.get("detalle") !== "true" && fecha === null) return base;
  const detalle = { ...base, descripcion: i.descripcion, ...(i.unidad ? { unidad: i.unidad } : {}) };
  if (fecha === null || i.precio === null) return detalle;
  if (monedaDeLaLista === "USD") {
    const columna = i.tipo === "mano_obra" ? "sueldo" : "precio";
    return { ...detalle, moneda: "USD", fecha_precio: "2026-07-01", aviso_precio: `El catálogo lo tiene en USD; escriba el ${columna} en Bs.` };
  }
  return { ...detalle, precio: i.precio, moneda: "Bs", fecha_precio: "2026-07-01" };
}

beforeEach(() => {
  llamadas = [];
  estadoDeConsulta = 200;
  monedaDeLaLista = "Bs";
  vi.stubGlobal(
    "fetch",
    vi.fn((ruta: string) => {
      llamadas.push(ruta);
      const consulta = /^\/v1\/consulta\/(\w+)\?(.*)$/.exec(ruta);
      if (consulta) {
        if (estadoDeConsulta !== 200) return Promise.resolve(json({ detalle: "Sin sesión." }, estadoDeConsulta));
        const params = new URLSearchParams(consulta[2]);
        const q = (params.get("q") ?? "").toLowerCase();
        const halladas = CATALOGO.filter(
          (i) => TIPOS_DE[consulta[1]]?.includes(i.tipo) && i.descripcion.toLowerCase().includes(q),
        );
        return Promise.resolve(json({ tabla: consulta[1], hay_mas: false, resultados: halladas.map((i) => sugerencia(i, params)) }));
      }
      if (ruta === "/insumos") {
        return Promise.resolve(
          json(CATALOGO.map((i) => ({ codigo: i.codigo, descripcion: i.descripcion, tipo: i.tipo, unidad: i.unidad, precio_vigente: i.vigente }))),
        );
      }
      return Promise.resolve(json({ detalle: "No hay." }, 404));
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());

interface PropsArnes {
  tipo: TipoTabla;
  filas: Fila[];
  paraArmarAl?: string;
  moneda?: string | null;
  alEscape?: () => void;
  alExpirar?: () => void;
}

function Arnes({ tipo, filas, paraArmarAl = FECHA, moneda = "Bs", alEscape, alExpirar = () => {} }: PropsArnes) {
  const [tablas, setTablas] = useState<Tablas>({ ...tablasVacias(), [tipo]: filas });
  return (
    <div onKeyDown={(e) => e.key === "Escape" && alEscape?.()}>
      <TablaInsumos
        tipo={tipo}
        filas={tablas[tipo]}
        modalidades={MODALIDADES}
        paraArmarAl={paraArmarAl}
        moneda={moneda}
        alCambiar={(i, clave, valor) => setTablas((t) => editarCelda(t, tipo, i, clave, valor))}
        alCompletar={(i, valores) => setTablas((t) => completarFila(t, tipo, i, valores))}
        alAgregar={() => setTablas((t) => agregarFila(t, tipo))}
        alBorrar={(i) => setTablas((t) => borrarFila(t, tipo, i))}
        alExpirar={alExpirar}
      />
    </div>
  );
}

const MATERIAL = { descripcion: "", unidad: "", cantidad: "3", precio: "" };
const EQUIPO = { descripcion: "", cantidad: "1", precio: "", depreciacion: "0,5" };
const OBRERO = { descripcion: "", cantidad: "2", sueldo: "", modalidad: "JORNAL" };
const descripcion = (n = 1) => screen.getByRole("combobox", { name: `Descripción, fila ${n}` });

describe("TablaInsumos: autocompletado de la descripción", () => {
  test("cada descripción y cada unidad (AC4) son un combobox con su nombre «…, fila N»; las cifras siguen siendo texto", () => {
    render(<Arnes tipo="materiales" filas={[MATERIAL, { ...MATERIAL }]} />);
    expect(descripcion(1)).toBeInTheDocument();
    expect(descripcion(2)).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Unidad, fila 1" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Unidad, fila 2" })).toBeInTheDocument();
    expect(screen.getAllByRole("combobox")).toHaveLength(4);
    expect(screen.getByRole("textbox", { name: "Consumo por unidad, fila 1" })).toBeInTheDocument();
  });

  test("materiales: pide «insumos»; al elegir llena descripción, unidad y precio (con coma) y respeta el consumo", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="materiales" filas={[MATERIAL]} />);
    await u.type(descripcion(), "cemento g");
    const opcion = await screen.findByRole("option", { name: /Cemento gris ficticio/ });
    expect(llamadas.some((l) => l.startsWith("/v1/consulta/insumos?q=cemento+g"))).toBe(true);
    await u.click(opcion);
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Unidad, fila 1" })).toHaveValue("saco"));
    expect(descripcion()).toHaveValue("Cemento gris ficticio");
    expect(screen.getByRole("textbox", { name: "Precio, fila 1" })).toHaveValue("18,00");
    expect(screen.getByRole("textbox", { name: "Consumo por unidad, fila 1" })).toHaveValue("3");
  });

  test("equipos: usa la misma tabla «insumos»; llena descripción y precio y no toca cantidad ni depreciación", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="equipos" filas={[EQUIPO]} />);
    await u.type(descripcion(), "mezcla");
    await u.click(await screen.findByRole("option", { name: /Mezcladora ficticia/ }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Precio, fila 1" })).toHaveValue("2.000"));
    expect(descripcion()).toHaveValue("Mezcladora ficticia");
    expect(screen.getByRole("textbox", { name: "Cantidad, fila 1" })).toHaveValue("1");
    expect(screen.getByRole("textbox", { name: "Depreciación, fila 1" })).toHaveValue("0,5");
    expect(llamadas.some((l) => l.startsWith("/v1/consulta/insumos?"))).toBe(true);
  });

  test("mano de obra: usa «salarios_cct», el jornal va al sueldo y la modalidad no cambia", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="mano_obra" filas={[OBRERO]} />);
    await u.type(descripcion(), "alba");
    await u.click(await screen.findByRole("option", { name: /Albañil ficticio/ }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Sueldo, fila 1" })).toHaveValue("12,3400"));
    expect(descripcion()).toHaveValue("Albañil ficticio");
    expect(screen.getByRole("combobox", { name: "Modalidad, fila 1" })).toHaveValue("JORNAL");
    expect(llamadas.some((l) => l.startsWith("/v1/consulta/salarios_cct?"))).toBe(true);
  });

  // Solo lo que la persona tecleó es suyo (ronda 2, MAYOR 1): una unidad o un precio que traía la fila de fuera se quita.
  test("un insumo sin unidad ni precio en el catálogo no borra ni inventa lo que la persona tecleó", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="materiales" filas={[{ ...MATERIAL }]} />);
    await u.type(screen.getByRole("combobox", { name: "Unidad, fila 1" }), "kg");
    await u.type(screen.getByRole("textbox", { name: "Precio, fila 1" }), "7,5");
    await u.type(descripcion(), "cemento b");
    await u.click(await screen.findByRole("option", { name: /Cemento blanco ficticio/ }));
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento blanco ficticio"));
    expect(screen.getByRole("combobox", { name: "Unidad, fila 1" })).toHaveValue("kg");
    expect(screen.getByRole("textbox", { name: "Precio, fila 1" })).toHaveValue("7,5");
  });

  test("el precio es el de la lista para armar a la fecha de la composición, en la misma respuesta: no se pide GET /insumos", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="materiales" filas={[MATERIAL]} />);
    await u.type(descripcion(), "cemento g");
    await u.click(await screen.findByRole("option", { name: /Cemento gris ficticio/ }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Precio, fila 1" })).toHaveValue("18,00"));
    expect(screen.getByRole("textbox", { name: "Precio, fila 1" })).not.toHaveValue("25,50");
    const pedida = llamadas.filter((l) => l.startsWith("/v1/consulta/insumos?")).at(-1)!;
    const params = new URLSearchParams(pedida.split("?")[1]);
    expect(params.get("para_armar_al")).toBe(FECHA);
    expect(params.get("detalle")).toBe("true");
    expect(llamadas).not.toContain("/insumos");
  });

  test("otra moneda: no se copia el precio, la celda lo dice en texto llano y la descripción y la unidad sí se copian", async () => {
    monedaDeLaLista = "USD";
    const u = userEvent.setup();
    render(<Arnes tipo="materiales" filas={[MATERIAL]} />);
    await u.type(descripcion(), "cemento g");
    await u.click(await screen.findByRole("option", { name: /Cemento gris ficticio/ }));
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento gris ficticio"));
    const precio = screen.getByRole("textbox", { name: "Precio, fila 1" });
    expect(precio).toHaveValue("");
    expect(screen.getByRole("combobox", { name: "Unidad, fila 1" })).toHaveValue("saco");
    // El aviso se ve en la celda del precio y se dice en la región viva del campo (WCAG 4.1.3).
    expect(screen.getAllByText("El catálogo lo tiene en USD; escriba el precio en Bs.")).toHaveLength(2);
    expect(precio).toHaveAccessibleDescription("El catálogo lo tiene en USD; escriba el precio en Bs.");
  });

  test("otra moneda en la mano de obra: el sueldo queda vacío y su celda lo avisa", async () => {
    monedaDeLaLista = "USD";
    const u = userEvent.setup();
    render(<Arnes tipo="mano_obra" filas={[OBRERO]} />);
    await u.type(descripcion(), "alba");
    await u.click(await screen.findByRole("option", { name: /Albañil ficticio/ }));
    await waitFor(() => expect(descripcion()).toHaveValue("Albañil ficticio"));
    expect(screen.getByRole("textbox", { name: "Sueldo, fila 1" })).toHaveValue("");
    expect(screen.getByRole("textbox", { name: "Sueldo, fila 1" })).toHaveAccessibleDescription(
      "El catálogo lo tiene en USD; escriba el sueldo en Bs.",
    );
  });

  test("un precio que llega en otra moneda que la de la carpeta no se copia aunque el servidor lo mande", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="materiales" filas={[MATERIAL]} moneda="USD" />);
    await u.type(descripcion(), "cemento g");
    await u.click(await screen.findByRole("option", { name: /Cemento gris ficticio/ }));
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento gris ficticio"));
    expect(screen.getByRole("textbox", { name: "Precio, fila 1" })).toHaveValue("");
    expect(screen.getAllByText("El catálogo lo tiene en Bs; escriba el precio en USD.")).toHaveLength(2);
  });

  test("elegir otro insumo quita el aviso de moneda de la fila", async () => {
    const u = userEvent.setup();
    monedaDeLaLista = "USD";
    render(<Arnes tipo="materiales" filas={[MATERIAL]} />);
    await u.type(descripcion(), "cemento g");
    await u.click(await screen.findByRole("option", { name: /Cemento gris ficticio/ }));
    await waitFor(() =>
      expect(screen.getByRole("textbox", { name: "Precio, fila 1" })).toHaveAccessibleDescription("El catálogo lo tiene en USD; escriba el precio en Bs."),
    );
    monedaDeLaLista = "Bs";
    await u.clear(descripcion());
    await u.type(descripcion(), "cemento b");
    await u.click(await screen.findByRole("option", { name: /Cemento blanco ficticio/ }));
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento blanco ficticio"));
    expect(screen.getByRole("textbox", { name: "Precio, fila 1" })).toHaveAccessibleDescription("");
  });

  test("sin fecha de composición no hay lista con que armar: se copian descripción y unidad, nunca el precio", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="materiales" filas={[MATERIAL]} paraArmarAl="" />);
    await u.type(descripcion(), "cemento g");
    await u.click(await screen.findByRole("option", { name: /Cemento gris ficticio/ }));
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Unidad, fila 1" })).toHaveValue("saco"));
    expect(descripcion()).toHaveValue("Cemento gris ficticio");
    expect(screen.getByRole("textbox", { name: "Precio, fila 1" })).toHaveValue("");
    const pedida = llamadas.filter((l) => l.startsWith("/v1/consulta/insumos?")).at(-1)!;
    expect(new URLSearchParams(pedida.split("?")[1]).has("para_armar_al")).toBe(false);
    expect(llamadas).not.toContain("/insumos");
  });

  test("se puede usar una descripción propia: la lista lo ofrece con su aviso y queda dicho que no viene del catálogo", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="materiales" filas={[MATERIAL]} />);
    await u.type(descripcion(), "Piedra de río ficticia");
    const propio = await screen.findByRole("option", {
      name: /Usar «Piedra de río ficticia» tal cual.*no viene del catálogo/,
    });
    await u.click(propio);
    expect(descripcion()).toHaveValue("Piedra de río ficticia");
    expect(screen.getByText(AVISO)).toBeInTheDocument();
    expect(descripcion()).toHaveAccessibleDescription(expect.stringContaining("no viene del catálogo"));
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  test("lo escrito y no elegido también queda marcado como propio; elegir del catálogo quita el aviso", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="materiales" filas={[MATERIAL]} />);
    await u.type(descripcion(), "Cemento gris");
    await u.tab();
    expect(screen.getByText(AVISO)).toBeInTheDocument();
    // La búsqueda de la pausa (300 ms) termina con el campo sin foco: así pasa siempre que la máquina va lenta entre el Tab y
    // el clic. Se espera a que haya salido, para que el orden no dependa del reloj.
    await waitFor(() => expect(llamadas.some((l) => l.startsWith("/v1/consulta/insumos?q=Cemento+gris"))).toBe(true));
    // Volver al campo no abre la lista por sí solo cuando la búsqueda ya terminó sin foco (solo la abre una respuesta que
    // llega con el campo enfocado): se abre con la flecha hacia abajo, que sirve en cualquier orden (si la búsqueda sigue en vuelo, la repite).
    await u.click(descripcion());
    await u.keyboard("{ArrowDown}");
    await u.click(await screen.findByRole("option", { name: /Cemento gris ficticio/ }));
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento gris ficticio"));
    expect(screen.queryByText(AVISO)).not.toBeInTheDocument();
  });

  test("una fila precargada o de la referencia no se marca como propia", () => {
    render(<Arnes tipo="materiales" filas={[{ ...MATERIAL, descripcion: "Arena ficticia" }]} />);
    expect(screen.queryByText(AVISO)).not.toBeInTheDocument();
  });

  test("teclado: Tab con la lista abierta la cierra, sigue a la columna siguiente y no elige; Enter elige la activa", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="materiales" filas={[MATERIAL]} />);
    await u.type(descripcion(), "cemento b");
    await screen.findByRole("option", { name: /Cemento blanco ficticio/ });
    await u.tab();
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Unidad, fila 1" })).toHaveFocus();
    expect(descripcion()).toHaveValue("cemento b");

    await u.click(descripcion());
    await u.keyboard("{Enter}"); // con la lista cerrada y sin opción activa: no elige nada
    expect(descripcion()).toHaveValue("cemento b");
    await u.keyboard("{ArrowDown}"); // abre la lista y deja activa la primera
    await screen.findByRole("option", { name: /Cemento blanco ficticio/ });
    await u.keyboard("{Enter}");
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento blanco ficticio"));
  });

  test("Esc con la lista abierta solo la cierra: el Esc no llega al panel que contiene la tabla", async () => {
    const u = userEvent.setup();
    const alEscape = vi.fn();
    render(<Arnes tipo="materiales" filas={[MATERIAL]} alEscape={alEscape} />);
    await u.type(descripcion(), "cemento g");
    await screen.findByRole("option", { name: /Cemento gris ficticio/ });
    await u.keyboard("{Escape}");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(alEscape).not.toHaveBeenCalled();
    expect(descripcion()).toHaveValue("cemento g");
  });

  test("Esc con la lista cerrada no borra la descripción ya elegida", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="materiales" filas={[MATERIAL]} />);
    await u.type(descripcion(), "cemento g");
    await u.click(await screen.findByRole("option", { name: /Cemento gris ficticio/ }));
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento gris ficticio"));
    await u.keyboard("{Escape}");
    expect(descripcion()).toHaveValue("Cemento gris ficticio");
    expect(screen.getByRole("combobox", { name: "Unidad, fila 1" })).toHaveValue("saco");
  });

  test("una sesión vencida durante la búsqueda avisa con alExpirar", async () => {
    estadoDeConsulta = 401;
    const u = userEvent.setup();
    const alExpirar = vi.fn();
    render(<Arnes tipo="materiales" filas={[MATERIAL]} alExpirar={alExpirar} />);
    await u.type(descripcion(), "cemento");
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("borrar una fila quita el aviso de propia de la que se va y no se lo pasa a la siguiente", async () => {
    const u = userEvent.setup();
    render(<Arnes tipo="materiales" filas={[MATERIAL, { ...MATERIAL, descripcion: "Arena ficticia" }]} />);
    await u.type(descripcion(1), "Piedra propia");
    await u.tab();
    expect(screen.getAllByText(AVISO)).toHaveLength(1);
    await u.click(screen.getByRole("button", { name: "Borrar fila 1 de Materiales" }));
    expect(descripcion(1)).toHaveValue("Arena ficticia");
    expect(screen.queryByText(AVISO)).not.toBeInTheDocument();
  });

  test("una descripción de más de 80 letras se puede escribir (el catálogo las tiene) y la búsqueda manda solo las primeras 80", async () => {
    const u = userEvent.setup();
    const larga = "Tubería de concreto reforzado ficticia para drenaje de aguas de lluvia, ".repeat(2).trim();
    expect(larga.length).toBeGreaterThan(80);
    render(<Arnes tipo="materiales" filas={[MATERIAL]} />);
    await u.click(descripcion());
    await u.paste(larga);
    expect(descripcion()).toHaveValue(larga);
    await waitFor(() => expect(llamadas.some((l) => l.startsWith("/v1/consulta/insumos?"))).toBe(true));
    const q = new URLSearchParams(llamadas.find((l) => l.startsWith("/v1/consulta/insumos?"))!.split("?")[1]).get("q")!;
    expect(q.length).toBeLessThanOrEqual(80);
    expect(larga.startsWith(q)).toBe(true);
  });
});
