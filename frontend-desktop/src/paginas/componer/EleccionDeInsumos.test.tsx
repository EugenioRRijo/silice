import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
// Ronda 2 (2026-11-05):
//   7. Solo es «de la persona» lo que se tecleo en esa celda: una fila precargada o de MaPreX se reemplaza (o se vacia) al
//      elegir otro insumo y se dice (MAYOR 1).
//   8. El aviso de fecha solo sale si la lista que rige para la «Fecha» nueva es otra (MENOR 2).
// Ronda 3 (2026-11-05):
//   9. Si la consulta del aviso de lista falla, el fallo no se guarda para siempre: se vuelve a preguntar (MENOR 3); y se
//      pregunta por el codigo del insumo, que el rango de la API pone primero, no por su descripcion con tope de 20.
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
let consultaCaida: boolean;

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
  consultaCaida = false;
  vi.stubGlobal(
    "fetch",
    vi.fn((ruta: string) => {
      llamadas.push(ruta);
      const consulta = /^\/v1\/consulta\/(\w+)\?(.*)$/.exec(ruta);
      if (!consulta) return Promise.resolve(json({ detalle: "No hay." }, 404));
      if (consultaCaida) return Promise.resolve(json({ detalle: "No se pudo consultar." }, 503));
      const params = new URLSearchParams(consulta[2]);
      const q = (params.get("q") ?? "").toLowerCase();
      const halladas = CATALOGO.filter((i) => i.descripcion.toLowerCase().includes(q) || i.codigo.toLowerCase().includes(q));
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
      <input type="date" aria-label="Fecha de prueba" value={fecha} onChange={(e) => setFecha(e.target.value)} />
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

const fijarFecha = (valor: string) => fireEvent.change(screen.getByLabelText("Fecha de prueba"), { target: { value: valor } });
const regionDeLaDescripcion = (n = 0) => document.getElementById(`materiales-${n}-descripcion-estado`);

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
    const aviso = "Precio de la lista del 01/07/2026; con la fecha 20/10/2026 rige la del 01/10/2026; revise.";
    expect(await screen.findByText(aviso)).toBeInTheDocument();
    expect(precio()).toHaveAccessibleDescription(aviso);
  });

  test("el aviso de fecha se va si el precio se vuelve a escribir, y no aparece si la fecha vuelve a ser la misma", async () => {
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(precio()).toHaveValue("18,00"));
    await u.click(screen.getByRole("button", { name: "Cambiar fecha" }));
    expect(await screen.findByText(/con la fecha 20\/10\/2026 rige la del 01\/10\/2026/)).toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: "Volver a la fecha" }));
    expect(screen.queryByText(/; revise\./)).not.toBeInTheDocument();

    await u.click(screen.getByRole("button", { name: "Cambiar fecha" }));
    expect(await screen.findByText(/; revise\./)).toBeInTheDocument();
    await u.clear(precio());
    await u.type(precio(), "20");
    expect(screen.queryByText(/; revise\./)).not.toBeInTheDocument();
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
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await u.type(precio(), "7,5");
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento gris ficticio"));
    expect(precio()).toHaveValue("7,5");
    expect(unidad()).toHaveValue("saco"); // la unidad estaba vacía: sí se llena
    expect(precio()).toHaveAccessibleDescription(expect.stringContaining("El catálogo tiene 18,00 Bs"));
  });

  test("lo mismo con la unidad: una unidad escrita se conserva y se dice la del catálogo", async () => {
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await u.type(unidad(), "bolsa");
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
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await u.type(precio(), "7,5");
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
    // La fila que quedó es la de «Arena» y su 18,00 no lo tecleó nadie (vino de fuera, como una precarga): no es del catálogo
    // de la fila 1 (no se vacía en silencio) ni de la persona (no se conserva): se quita y se dice.
    await elegir(u, "cemento b", /Cemento blanco ficticio/);
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento blanco ficticio"));
    expect(precio()).toHaveValue("");
    expect(precio()).toHaveAccessibleDescription(expect.stringContaining("Se quitó el precio 18,00: este insumo no tiene precio en la lista."));
  });
});

describe("7. solo es de la persona lo que se tecleó en esa celda (una fila precargada o de MaPreX no lo es)", () => {
  const cambioPrecio = "Se cambió el precio 5,00 por el del catálogo, 18,00 Bs.";
  const cambioUnidad = "Se cambió la unidad m3 por la del catálogo, saco.";
  const quitaPrecio = "Se quitó el precio 5,00: este insumo no tiene precio en la lista.";
  const quitaUnidad = "Se quitó la unidad m3: este insumo no tiene unidad en el catálogo.";

  async function precargar(u: ReturnType<typeof userEvent.setup>) {
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await u.click(screen.getByRole("button", { name: "Precargar" }));
    expect(descripcion(1)).toHaveValue("Arena ficticia");
  }

  test("fila precargada y un insumo con precio: la fila queda toda del insumo nuevo y se dice lo que se cambió", async () => {
    const u = userEvent.setup();
    await precargar(u);
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(precio()).toHaveValue("18,00"));
    expect(unidad()).toHaveValue("saco");
    expect(precio()).toHaveAccessibleDescription(expect.stringContaining(cambioPrecio));
    expect(precio()).not.toHaveAccessibleDescription(expect.stringContaining("se conserva"));
    expect(unidad()).toHaveAccessibleDescription(expect.stringContaining(cambioUnidad));
    await waitFor(() => expect(regionDeLaDescripcion()).toHaveTextContent(cambioPrecio));
    expect(regionDeLaDescripcion()).toHaveTextContent(cambioUnidad);
    // La otra fila precargada no se toca.
    expect(descripcion(2)).toHaveValue("Arena ficticia");
    expect(precio(2)).toHaveValue("5,00");
  });

  test("fila precargada y un insumo sin precio ni unidad: se quitan los de antes y se dice (nunca queda mezclada)", async () => {
    const u = userEvent.setup();
    await precargar(u);
    await elegir(u, "cemento b", /Cemento blanco ficticio/);
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento blanco ficticio"));
    expect(precio()).toHaveValue("");
    expect(unidad()).toHaveValue("");
    expect(precio()).toHaveAccessibleDescription(expect.stringContaining(quitaPrecio));
    expect(unidad()).toHaveAccessibleDescription(expect.stringContaining(quitaUnidad));
    await waitFor(() => expect(regionDeLaDescripcion()).toHaveTextContent(quitaPrecio));
    expect(regionDeLaDescripcion()).toHaveTextContent(quitaUnidad);
  });

  test("en otra moneda se quita el precio de antes y se dicen los dos: lo quitado y por qué no se llenó", async () => {
    monedaDeLaLista = "USD";
    const u = userEvent.setup();
    await precargar(u);
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento gris ficticio"));
    expect(precio()).toHaveValue("");
    expect(precio()).toHaveAccessibleDescription(expect.stringContaining("Se quitó el precio 5,00."));
    expect(precio()).toHaveAccessibleDescription(expect.stringContaining(AVISO_USD));
  });

  test("lo tecleado sobre la fila precargada sí es de la persona: se conserva y se dice lo que tiene el catálogo", async () => {
    const u = userEvent.setup();
    await precargar(u);
    await u.clear(precio());
    await u.type(precio(), "6");
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento gris ficticio"));
    expect(precio()).toHaveValue("6");
    expect(precio()).toHaveAccessibleDescription(expect.stringContaining("El catálogo tiene 18,00 Bs; se conserva el precio que escribió."));
    // La unidad no se tecleó: se reemplaza y se dice.
    expect(unidad()).toHaveValue("saco");
    expect(unidad()).toHaveAccessibleDescription(expect.stringContaining(cambioUnidad));
  });

  test("si lo de fuera ya es igual a lo del catálogo no hay nada que decir", async () => {
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL, descripcion: "Arena ficticia", unidad: "saco", precio: "18,00" }]} />);
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(descripcion()).toHaveValue("Cemento gris ficticio"));
    expect(precio()).toHaveValue("18,00");
    expect(precio()).toHaveAccessibleDescription("");
    expect(unidad()).toHaveAccessibleDescription("");
  });

  test("lo que puso el catálogo y se reemplaza por otro del catálogo no se anuncia como cambio (es el comportamiento de siempre)", async () => {
    const u = userEvent.setup();
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(precio()).toHaveValue("18,00"));
    await elegir(u, "cemento r", /Cemento rojo ficticio/);
    await waitFor(() => expect(precio()).toHaveValue("9,00"));
    expect(precio()).toHaveAccessibleDescription("");
    expect(unidad()).toHaveAccessibleDescription("");
  });

  test("lo escrito en la unidad de una fila precargada también es de la persona", async () => {
    const u = userEvent.setup();
    await precargar(u);
    await u.clear(unidad());
    await u.type(unidad(), "bolsa");
    await elegir(u, "cemento g", /Cemento gris ficticio/);
    await waitFor(() => expect(precio()).toHaveValue("18,00"));
    expect(unidad()).toHaveValue("bolsa");
    expect(unidad()).toHaveAccessibleDescription(expect.stringContaining("El catálogo tiene la unidad «saco»; se conserva la que escribió."));
    expect(precio()).toHaveAccessibleDescription(expect.stringContaining(cambioPrecio));
  });
});

describe("8. el aviso de fecha solo sale si la lista que rige para la «Fecha» nueva es otra", () => {
  const AVISO_OTRA = /; revise\./;

  async function conGris(u: ReturnType<typeof userEvent.setup>) {
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await elegir(u, "cemento g", /Cemento gris ficticio/); // con la «Fecha» del 15/08: lista del 01/07
    await waitFor(() => expect(precio()).toHaveValue("18,00"));
  }

  test("una fecha anterior dentro de la misma lista (20/07) no avisa", async () => {
    const u = userEvent.setup();
    await conGris(u);
    fijarFecha("2026-07-20");
    await new Promise((r) => setTimeout(r, 100));
    expect(screen.queryByText(AVISO_OTRA)).not.toBeInTheDocument();
    expect(precio()).toHaveAccessibleDescription("");
  });

  test("una fecha posterior que sigue en la misma lista (30/09) se comprueba con la API y no avisa", async () => {
    const u = userEvent.setup();
    await conGris(u);
    fijarFecha("2026-09-30");
    await waitFor(() =>
      expect(llamadas.some((l) => new URLSearchParams(l.split("?")[1]).get("para_armar_al") === "2026-09-30")).toBe(true),
    );
    await new Promise((r) => setTimeout(r, 100));
    expect(screen.queryByText(AVISO_OTRA)).not.toBeInTheDocument();
    expect(precio()).toHaveValue("18,00");
  });

  test("una fecha cuya lista es otra (20/10) avisa con las dos fechas de lista", async () => {
    const u = userEvent.setup();
    await conGris(u);
    fijarFecha(FECHA_NUEVA);
    expect(
      await screen.findByText("Precio de la lista del 01/07/2026; con la fecha 20/10/2026 rige la del 01/10/2026; revise."),
    ).toBeInTheDocument();
  });

  test("con la «Fecha» vacía no avisa", async () => {
    const u = userEvent.setup();
    await conGris(u);
    fijarFecha("");
    await new Promise((r) => setTimeout(r, 100));
    expect(screen.queryByText(AVISO_OTRA)).not.toBeInTheDocument();
    expect(precio()).toHaveValue("18,00");
  });

  test("si no se puede comprobar la lista de la fecha nueva, lo dice con prudencia en vez de callar", async () => {
    const u = userEvent.setup();
    await conGris(u);
    consultaCaida = true;
    fijarFecha(FECHA_NUEVA);
    expect(
      await screen.findByText("Precio de la lista del 01/07/2026; con la fecha 20/10/2026 puede regir otra lista; revise."),
    ).toBeInTheDocument();
  });

  test("el insumo que no tiene precio en la lista de la fecha nueva también avisa", async () => {
    const u = userEvent.setup();
    await conGris(u);
    CATALOGO[0]!.despues = null;
    try {
      fijarFecha(FECHA_NUEVA);
      expect(
        await screen.findByText("Precio de la lista del 01/07/2026; con la fecha 20/10/2026 este insumo no tiene precio en la lista; revise."),
      ).toBeInTheDocument();
    } finally {
      CATALOGO[0]!.despues = "25.50";
    }
  });
});

describe("9. la consulta del aviso de lista no guarda su fallo para siempre", () => {
  async function conGris(u: ReturnType<typeof userEvent.setup>) {
    render(<Arnes filas={[{ ...MATERIAL }]} />);
    await elegir(u, "cemento g", /Cemento gris ficticio/); // con la «Fecha» del 15/08: lista del 01/07
    await waitFor(() => expect(precio()).toHaveValue("18,00"));
  }
  const DICHO_NOSE = "Precio de la lista del 01/07/2026; con la fecha 20/10/2026 puede regir otra lista; revise.";
  const DICHO_OTRA = "Precio de la lista del 01/07/2026; con la fecha 20/10/2026 rige la del 01/10/2026; revise.";
  const pedidasAl = (fecha: string) =>
    llamadas.filter((l) => new URLSearchParams(l.split("?")[1]).get("para_armar_al") === fecha);

  test("la API falla con la «Fecha» del 20/10 y, al volver a pedir esa fecha con la API arriba, el aviso pasa a lo correcto", async () => {
    const u = userEvent.setup();
    await conGris(u);
    consultaCaida = true;
    fijarFecha(FECHA_NUEVA);
    expect(await screen.findByText(DICHO_NOSE)).toBeInTheDocument();

    consultaCaida = false;
    await u.click(screen.getByRole("button", { name: "Volver a la fecha" }));
    await waitFor(() => expect(screen.queryByText(DICHO_NOSE)).not.toBeInTheDocument());
    await u.click(screen.getByRole("button", { name: "Cambiar fecha" }));
    expect(await screen.findByText(DICHO_OTRA)).toBeInTheDocument();
    expect(screen.queryByText(DICHO_NOSE)).not.toBeInTheDocument();
  });

  test("mientras la API sigue caída no se insiste en cada tecla: una sola pregunta por fecha", async () => {
    const u = userEvent.setup();
    await conGris(u);
    consultaCaida = true;
    fijarFecha(FECHA_NUEVA);
    expect(await screen.findByText(DICHO_NOSE)).toBeInTheDocument();
    const antes = pedidasAl(FECHA_NUEVA).length;
    await u.type(precio(), "1");
    await new Promise((r) => setTimeout(r, 100));
    expect(pedidasAl(FECHA_NUEVA).length).toBe(antes);
  });

  test("la comprobación pregunta por el código del insumo y no por su descripción", async () => {
    const u = userEvent.setup();
    await conGris(u);
    fijarFecha("2026-09-30");
    await waitFor(() => expect(pedidasAl("2026-09-30").length).toBeGreaterThan(0));
    expect(pedidasAl("2026-09-30").map((l) => new URLSearchParams(l.split("?")[1]).get("q"))).toEqual(["MAT-1"]);
  });
});
