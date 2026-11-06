import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { TablaInsumos } from "./TablaInsumos";
import { agregarFila, borrarFila, completarFila, editarCelda, tablasVacias } from "./tablas";
import type { Fila, Tablas } from "./tablas";

// Dictamen de Claude (xhigh) sobre el autocompletado, 2026-11-05: los dos BLOQUEANTE de dinero y sus vecinos.
//   1. El precio salia de la lista de OTRA fecha al cambiar la «Fecha» de la composicion.
//   2. Elegir un segundo insumo mezclaba la fila (el precio del primero se quedaba) y pisaba lo escrito por la persona.
//   5. El aviso de moneda y el de «el catalogo tiene X» tambien se dicen en la region viva del campo (WCAG 4.1.3).
//   6. Las marcas por indice no seguian a la fila cuando las filas cambian desde fuera (precarga).
// Montos y textos ficticios; la API es un `fetch` falso con la forma de `api/rutas/consulta.py`.

const FECHA_VIEJA = "2026-08-15";
const FECHA_NUEVA = "2026-10-20";
const AVISO_USD = "El catálogo lo tiene en USD; escriba el precio en Bs.";

// La lista para armar vigente a cada fecha: la del 01/07/2026 rige hasta el 30/09 y la del 01/10/2026 despues.
const LISTA_VIEJA = "2026-07-01";
const LISTA_NUEVA = "2026-10-01";
const CATALOGO = [
  { codigo: "MAT-1", descripcion: "Cemento gris ficticio", unidad: "saco", antes: "18.00", despues: "25.50" },
  { codigo: "MAT-2", descripcion: "Cemento blanco ficticio", unidad: null, antes: null, despues: null },
  { codigo: "MAT-3", descripcion: "Cemento rojo ficticio", unidad: "kg", antes: "9.00", despues: "9.00" },
];

let llamadas: string[];
let monedaDeLaLista: "Bs" | "USD";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

function sugerencia(i: (typeof CATALOGO)[number], fecha: string | null) {
  const base = {
    valor: i.codigo,
    etiqueta: `${i.descripcion} (${i.codigo}${i.unidad ? `, ${i.unidad}` : ""})`,
    fuente: "Catálogo de la carpeta de trabajo: material",
    descripcion: i.descripcion,
    ...(i.unidad ? { unidad: i.unidad } : {}),
  };
  const precio = fecha !== null && fecha >= LISTA_NUEVA ? i.despues : i.antes;
  if (fecha === null || precio === null) return base;
  const fecha_precio = fecha >= LISTA_NUEVA ? LISTA_NUEVA : LISTA_VIEJA;
  if (monedaDeLaLista === "USD") return { ...base, moneda: "USD", fecha_precio, aviso_precio: AVISO_USD };
  return { ...base, precio, moneda: "Bs", fecha_precio };
}

beforeEach(() => {
  llamadas = [];
  monedaDeLaLista = "Bs";
  vi.stubGlobal(
    "fetch",
    vi.fn((ruta: string) => {
      llamadas.push(ruta);
      const consulta = /^\/v1\/consulta\/(\w+)\?(.*)$/.exec(ruta);
      if (!consulta) return Promise.resolve(json({ detalle: "No hay." }, 404));
      const params = new URLSearchParams(consulta[2]);
      const q = (params.get("q") ?? "").toLowerCase();
      const halladas = CATALOGO.filter((i) => i.descripcion.toLowerCase().includes(q));
      const fecha = params.get("para_armar_al");
      return Promise.resolve(json({ tabla: consulta[1], hay_mas: false, resultados: halladas.map((i) => sugerencia(i, fecha)) }));
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());

const MATERIAL: Fila = { descripcion: "", unidad: "", cantidad: "3", precio: "" };
const OTRA_FILA: Fila = { descripcion: "Arena ficticia", unidad: "m3", cantidad: "1", precio: "5,00" };

function Arnes({ filas, moneda = "Bs" }: { filas: Fila[]; moneda?: string }) {
  const [fecha, setFecha] = useState(FECHA_VIEJA);
  const [tablas, setTablas] = useState<Tablas>({ ...tablasVacias(), materiales: filas });
  return (
    <div>
      <button type="button" onClick={() => setFecha(FECHA_NUEVA)}>
        Cambiar fecha
      </button>
      <button type="button" onClick={() => setFecha(FECHA_VIEJA)}>
        Volver a la fecha
      </button>
      <button type="button" onClick={() => setTablas({ ...tablasVacias(), materiales: [{ ...OTRA_FILA }, { ...OTRA_FILA }] })}>
        Precargar
      </button>
      <TablaInsumos
        tipo="materiales"
        filas={tablas.materiales}
        modalidades={[]}
        paraArmarAl={fecha}
        moneda={moneda}
        alCambiar={(i, clave, valor) => setTablas((t) => editarCelda(t, "materiales", i, clave, valor))}
        alCompletar={(i, valores) => setTablas((t) => completarFila(t, "materiales", i, valores))}
        alAgregar={() => setTablas((t) => agregarFila(t, "materiales"))}
        alBorrar={(i) => setTablas((t) => borrarFila(t, "materiales", i))}
        alExpirar={() => {}}
      />
    </div>
  );
}

const descripcion = (n = 1) => screen.getByRole("combobox", { name: `Descripción, fila ${n}` });
const unidad = (n = 1) => screen.getByRole("combobox", { name: `Unidad, fila ${n}` });
const precio = (n = 1) => screen.getByRole("textbox", { name: `Precio, fila ${n}` });

async function elegir(u: ReturnType<typeof userEvent.setup>, buscado: string, nombre: RegExp, fila = 1) {
  await u.clear(descripcion(fila));
  await u.type(descripcion(fila), buscado);
  await u.click(await screen.findByRole("option", { name: nombre }));
  await waitFor(() => expect(screen.queryByRole("listbox")).not.toBeInTheDocument());
}

describe("1. el precio sale de la lista de la fecha vigente de la composición", () => {
  test("caso del dictamen: cemento con 15/08, Tab, fecha 20/10, Flecha abajo y Enter no elige el resultado viejo (18,00)", async () => {
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await u.type(descripcion(), "cemento");
    await screen.findByRole("option", { name: /Cemento gris ficticio/ });
    await u.tab(); // la lista se cierra, pero el campo guardaba sus resultados
    await u.click(screen.getByRole("button", { name: "Cambiar fecha" }));
    await u.click(descripcion());
    await u.keyboard("{ArrowDown}{Enter}");
    expect(precio()).not.toHaveValue("18,00");

    // Lo que se puede elegir ahora viene de una busqueda hecha con la fecha nueva, y el precio es el de esa lista.
    const opcion = await screen.findByRole("option", { name: /Cemento gris ficticio/ });
    await u.click(opcion);
    await waitFor(() => expect(precio()).toHaveValue("25,50"));
    const pedida = llamadas.filter((l) => l.startsWith("/v1/consulta/insumos?")).at(-1)!;
    expect(new URLSearchParams(pedida.split("?")[1]).get("para_armar_al")).toBe(FECHA_NUEVA);
  });

  test("un precio ya llenado desde el catálogo no se toca al cambiar la fecha, pero queda avisado con la lista de la que salió", async () => {
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(precio()).toHaveValue("18,00"));
    expect(precio()).toHaveAccessibleDescription("");

    await u.click(screen.getByRole("button", { name: "Cambiar fecha" }));
    expect(precio()).toHaveValue("18,00");
    const aviso = "Precio de la lista del 01/07/2026, tomado con la fecha de composición 15/08/2026; revise.";
    expect(screen.getByText(aviso)).toBeInTheDocument();
    expect(precio()).toHaveAccessibleDescription(aviso);
  });

  test("el aviso de fecha se va si el precio se vuelve a escribir, y no aparece si la fecha vuelve a ser la misma", async () => {
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(precio()).toHaveValue("18,00"));
    await u.click(screen.getByRole("button", { name: "Cambiar fecha" }));
    expect(screen.getByText(/tomado con la fecha de composición/)).toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: "Volver a la fecha" }));
    expect(screen.queryByText(/tomado con la fecha de composición/)).not.toBeInTheDocument();

    await u.click(screen.getByRole("button", { name: "Cambiar fecha" }));
    await u.clear(precio());
    await u.type(precio(), "20");
    expect(screen.queryByText(/tomado con la fecha de composición/)).not.toBeInTheDocument();
    expect(precio()).toHaveValue("20");
  });

  test("un precio que escribió la persona no se avisa al cambiar la fecha", async () => {
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL, precio: "7,5" }]} />);
    await u.click(screen.getByRole("button", { name: "Cambiar fecha" }));
    expect(precio()).toHaveValue("7,5");
    expect(precio()).toHaveAccessibleDescription("");
  });
});

describe("2. una fila nunca mezcla el catálogo de un insumo con el de otro", () => {
  test("elegir con precio y luego uno sin precio ni unidad deja precio y unidad vacíos (nunca el 18,00 del primero)", async () => {
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(precio()).toHaveValue("18,00"));
    expect(unidad()).toHaveValue("saco");

    await elegir(u, "cemento b", /Cemento blanco ficticio/);
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento blanco ficticio"));
    expect(precio()).toHaveValue("");
    expect(unidad()).toHaveValue("");
  });

  test("elegir otro insumo con precio y unidad reemplaza los del catálogo anterior", async () => {
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(precio()).toHaveValue("18,00"));
    await elegir(u, "cemento r", /Cemento rojo ficticio/);
    await waitFor(() => expect(precio()).toHaveValue("9,00"));
    expect(unidad()).toHaveValue("kg");
    expect(descripcion()).toHaveValue("Cemento rojo ficticio");
  });

  test("un precio escrito antes de elegir se conserva y la celda dice lo que el catálogo tiene", async () => {
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL, precio: "7,5" }]} />);
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento gris ficticio"));
    expect(precio()).toHaveValue("7,5");
    expect(unidad()).toHaveValue("saco"); // la unidad estaba vacía: sí se llena
    expect(precio()).toHaveAccessibleDescription(expect.stringContaining("El catálogo tiene 18,00 Bs"));
  });

  test("lo mismo con la unidad: una unidad escrita se conserva y se dice la del catálogo", async () => {
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL, unidad: "bolsa" }]} />);
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(precio()).toHaveValue("18,00"));
    expect(unidad()).toHaveValue("bolsa");
    expect(unidad()).toHaveAccessibleDescription(expect.stringContaining("El catálogo tiene la unidad «saco»"));
  });

  test("un precio que la persona corrigió después de elegir tampoco se pisa al elegir otro insumo", async () => {
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(precio()).toHaveValue("18,00"));
    await u.clear(precio());
    await u.type(precio(), "20");
    await elegir(u, "cemento r", /Cemento rojo ficticio/);
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento rojo ficticio"));
    expect(precio()).toHaveValue("20");
    expect(precio()).toHaveAccessibleDescription(expect.stringContaining("El catálogo tiene 9,00 Bs"));
  });

  test("elegir en otra moneda deja vacío el precio que había puesto el catálogo y lo dice", async () => {
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(precio()).toHaveValue("18,00"));
    monedaDeLaLista = "USD";
    await elegir(u, "cemento r", /Cemento rojo ficticio/);
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento rojo ficticio"));
    expect(precio()).toHaveValue("");
    expect(precio()).toHaveAccessibleDescription(AVISO_USD);
  });
});

describe("4. cada sugerencia dice su precio, su moneda y la fecha de su lista", () => {
  test("la lista muestra «código · unidad · precio moneda · lista del dd/mm/aaaa» o que no hay precio", async () => {
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await u.type(descripcion(), "cemento");
    const gris = await screen.findByRole("option", { name: /Cemento gris ficticio/ });
    expect(gris).toHaveTextContent("MAT-1 · saco · 18,00 Bs · lista del 01/07/2026");
    expect(screen.getByRole("option", { name: /Cemento blanco ficticio/ })).toHaveTextContent(
      "MAT-2 · sin precio en la lista para armar",
    );
  });

  test("en otra moneda la línea dice el aviso de moneda en vez de un precio", async () => {
    monedaDeLaLista = "USD";
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await u.type(descripcion(), "cemento g");
    expect(await screen.findByRole("option", { name: /Cemento gris ficticio/ })).toHaveTextContent(`MAT-1 · saco · ${AVISO_USD}`);
  });
});

describe("5. los avisos de la elección también se dicen en la región viva del campo", () => {
  const regionDeLaDescripcion = () => document.getElementById("materiales-0-descripcion-estado");

  test("el aviso de moneda se anuncia en la región viva del campo de la descripción", async () => {
    monedaDeLaLista = "USD";
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(regionDeLaDescripcion()).toHaveTextContent(AVISO_USD));
    expect(regionDeLaDescripcion()).toHaveAttribute("aria-live", "polite");
  });

  test("«el catálogo tiene X» (lo que no se pisó) también se anuncia", async () => {
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL, precio: "7,5" }]} />);
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(regionDeLaDescripcion()).toHaveTextContent(/El catálogo tiene 18,00 Bs/));
  });

  test("una elección sin nada que avisar no anuncia ningún aviso", async () => {
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(precio()).toHaveValue("18,00"));
    expect(regionDeLaDescripcion()).not.toHaveTextContent(/El catálogo/);
  });
});

describe("6. las marcas siguen a la fila, no al índice", () => {
  test("si las filas cambian desde fuera (precarga) el aviso de moneda de la fila anterior no queda pegado a la nueva", async () => {
    monedaDeLaLista = "USD";
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(precio(1)).toHaveAccessibleDescription(AVISO_USD));
    await u.click(screen.getByRole("button", { name: "Precargar" }));
    expect(descripcion(1)).toHaveValue("Arena ficticia");
    expect(precio(1)).toHaveAccessibleDescription("");
  });

  test("el aviso de moneda desaparece cuando la persona escribe un precio", async () => {
    monedaDeLaLista = "USD";
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(precio()).toHaveAccessibleDescription(AVISO_USD));
    await u.type(precio(), "4");
    expect(precio()).toHaveValue("4");
    expect(precio()).toHaveAccessibleDescription("");
  });

  test("lo que la fila 1 llenó del catálogo no se atribuye a la fila 2 al quitar la fila 1", async () => {
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL }, { ...MATERIAL, descripcion: "Arena ficticia", unidad: "m3", precio: "18,00" }]} />);
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(precio(1)).toHaveValue("18,00"));
    await u.click(screen.getByRole("button", { name: "Borrar fila 1 de Materiales" }));
    // La fila que quedó es la de «Arena»: su 18,00 es de la persona, así que elegir un insumo sin precio no lo vacía.
    await elegir(u, "cemento b", /Cemento blanco ficticio/);
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento blanco ficticio"));
    expect(precio()).toHaveValue("18,00");
  });
});
