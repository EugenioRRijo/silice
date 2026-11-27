import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ProveedorDeAnuncios } from "../../comun/Anunciador";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { RECORRIDO_AUDITAR, recorridoEnCurso, terminarRecorrido } from "../../shell/recorrido";
import { crearAlmacen } from "../../visor/almacen";
import type { AlmacenDelVisor } from "../../visor/almacen";
import { tomarArchivoPendiente } from "../inicio/archivoPendiente";
import { AuditarUnLibro } from "./AuditarUnLibro";
import { auditoriaDePrueba, auditoriaSinHallazgos, catalogoDePrueba } from "./datosDePrueba";

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

const REPLICA = { nombre: "Presupuesto cliente A.xlsx", sha256: "a".repeat(64), hojas: [], estilos: [] };

describe("Auditar un libro, en una sola página", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let auditoria: () => Response;
  let catalogo: () => Response;
  let almacen: AlmacenDelVisor;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    auditoria = () => json(auditoriaDePrueba());
    catalogo = () => json(catalogoDePrueba());
    almacen = crearAlmacen();
    fetchFalso.mockImplementation(async (entrada) => {
      const ruta = String(entrada);
      if (ruta === "/v1/libros/auditoria") return auditoria();
      if (ruta === "/v1/libros/que-hacer") return catalogo();
      if (ruta === "/v1/libros/replica") return json(REPLICA);
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    tomarArchivoPendiente();
    terminarRecorrido();
  });

  function montar(aplicacion: Partial<Aplicacion> = {}) {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: { nombre: "clinica", ruta_relativa: "data/clinica.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
      almacenDelLibro: almacen,
      ...aplicacion,
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <ProveedorDeAnuncios>
          <MemoryRouter initialEntries={["/auditoria"]}>
            <Routes>
              <Route path="/auditoria" element={<AuditarUnLibro />} />
              <Route path="/auditoria/libros" element={<h1>Pantalla del libro</h1>} />
              <Route path="/auditoria/historial" element={<h1>Pantalla del historial</h1>} />
            </Routes>
          </MemoryRouter>
        </ProveedorDeAnuncios>
      </ContextoAplicacion.Provider>,
    );
  }

  // La línea «Archivo elegido: …» (el anunciador también es un `status`, pero oculto).
  const estadoDelArchivo = () =>
    screen.getAllByRole("status").find((r) => !r.classList.contains("cds--visually-hidden")) as HTMLElement;
  const campoArchivo = () => document.querySelector('input[type="file"]') as HTMLInputElement;
  const llamadas = (ruta: string) => fetchFalso.mock.calls.filter((c) => String(c[0]) === ruta);

  async function subirYAuditar(nombre = "Presupuesto cliente A.xlsx") {
    const usuario = userEvent.setup();
    const vista = montar();
    await usuario.upload(campoArchivo(), new File(["x"], nombre));
    await usuario.click(screen.getByRole("button", { name: "Auditar el libro" }));
    await screen.findByRole("heading", { level: 2, name: /hallazgos? en el libro|no tiene hallazgos/ });
    return { usuario, vista };
  }

  // Los controles de decisión a la vista: lo que está dentro de un pliegue cerrado no cuenta, salvo su resumen.
  function controlesAlaVista(): HTMLElement[] {
    const todos = [
      ...document.querySelectorAll<HTMLElement>(
        "button, a[href], input:not([type='hidden']):not([aria-hidden='true']), select, textarea, summary",
      ),
    ];
    return todos.filter((c) => {
      const pliegue = c.closest("details");
      return !pliegue || pliegue.open || c.tagName === "SUMMARY";
    });
  }

  describe("antes de auditar", () => {
    test("la zona, el principal y un pliegue: tres decisiones a la vista", () => {
      montar();
      const seccion = screen.getByRole("region", { name: "Suba el libro" });
      const dentro = controlesAlaVista().filter((c) => seccion.contains(c));
      expect(dentro.map((c) => c.textContent?.slice(0, 20))).toHaveLength(3);
      expect(screen.getByRole("button", { name: /Suelte aquí el libro \.xlsx/ })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Auditar el libro" })).toBeInTheDocument();
      expect(screen.getByText("Más opciones")).toBeInTheDocument();
    });

    test("hay un solo principal y, sin archivo, está inactivo y dice por qué al pulsarlo", async () => {
      const usuario = userEvent.setup();
      montar();
      const principales = screen.getAllByRole("button").filter((b) => b.classList.contains("cds--btn--primary"));
      expect(principales.map((b) => b.textContent)).toEqual(["Auditar el libro"]);
      const principal = principales[0];
      expect(principal).toHaveAttribute("aria-disabled", "true");
      await usuario.click(principal);
      expect(await screen.findByText("Elija primero el libro .xlsx.")).toBeInTheDocument();
      expect(llamadas("/v1/libros/auditoria")).toHaveLength(0);
    });

    test("dice que el original no se modifica ni se guarda", () => {
      montar();
      expect(screen.getByText(/El archivo original no se modifica ni se guarda/)).toBeInTheDocument();
    });

    test("«Más opciones» trae la fecha de hoy y el recorrido guiado, con su valor por omisión dicho", () => {
      montar();
      const pliegue = screen.getByText("Más opciones").closest("details") as HTMLElement;
      expect(pliegue).not.toHaveAttribute("open");
      expect(within(pliegue).getByLabelText("Fecha de la revisión")).toHaveValue(
        new Date().toLocaleDateString("sv-SE"),
      );
      expect(within(pliegue).getByText(/Se revisa con la fecha de hoy/)).toBeInTheDocument();
      expect(within(pliegue).getByRole("button", { name: "Auditar con recorrido guiado" })).toBeDisabled();
    });

    test("con un archivo el principal se activa y se dice qué archivo es", async () => {
      const usuario = userEvent.setup();
      montar();
      await usuario.upload(campoArchivo(), new File(["x"], "obra-norte.xlsx"));
      expect(estadoDelArchivo()).toHaveTextContent("Archivo elegido: obra-norte.xlsx");
      expect(screen.getByRole("button", { name: "Auditar el libro" })).not.toHaveAttribute("aria-disabled");
    });
  });

  describe("al auditar", () => {
    test("manda una sola auditoría, con la fecha de la revisión, y ninguna réplica", async () => {
      await subirYAuditar();
      expect(llamadas("/v1/libros/auditoria")).toHaveLength(1);
      expect(llamadas("/v1/libros/replica")).toHaveLength(0);
      const cuerpo = llamadas("/v1/libros/auditoria")[0][1]?.body as FormData;
      expect((cuerpo.get("libro") as File).name).toBe("Presupuesto cliente A.xlsx");
      expect(cuerpo.get("fecha_devolucion")).toBe(new Date().toLocaleDateString("sv-SE"));
    });

    test("mientras espera, el esqueleto no trae cifras ni regiones vivas con texto", async () => {
      let soltar: (r: Response) => void = () => {};
      auditoria = () => new Response(null);
      fetchFalso.mockImplementation(async (entrada) => {
        const ruta = String(entrada);
        if (ruta === "/v1/libros/auditoria") return new Promise<Response>((res) => (soltar = res));
        return json({ detalle: "No encontrado." }, 404);
      });
      const usuario = userEvent.setup();
      montar();
      await usuario.upload(campoArchivo(), new File(["x"], "obra.xlsx"));
      await usuario.click(screen.getByRole("button", { name: "Auditar el libro" }));
      const espera = await screen.findByText("Auditando el libro…");
      const contenedor = espera.closest("[aria-busy='true']") as HTMLElement;
      expect(contenedor).not.toBeNull();
      expect(contenedor.querySelector("[aria-live], [role='status'], [role='alert']")).toBeNull();
      expect(contenedor.textContent).not.toMatch(/\d/);
      expect(screen.getByRole("button", { name: "Auditando…" })).toBeDisabled();
      soltar(json(auditoriaDePrueba()));
      await screen.findByRole("heading", { level: 2, name: "8 hallazgos en el libro" });
    });

    test("la frase de respuesta es el titular, recibe el foco y se anuncia una vez", async () => {
      await subirYAuditar();
      const titular = screen.getByRole("heading", { level: 2, name: "8 hallazgos en el libro" });
      await waitFor(() => expect(titular).toHaveFocus());
      expect(titular).toHaveAttribute("tabindex", "-1");
      expect(screen.getByText("8 errores")).toBeInTheDocument();
      const anuncios = screen.getAllByRole("status").filter((r) => r.classList.contains("cds--visually-hidden"));
      expect(anuncios).toHaveLength(1);
      await waitFor(() => expect(anuncios[0]).toHaveTextContent("Auditoría lista: 8 errores."));
    });

    test("los tres pasos están numerados y en orden, y la página tiene un solo h1 si se monta dentro de la suya", async () => {
      await subirYAuditar();
      const h2 = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
      expect(h2).toEqual(["1Suba el libro", "28 hallazgos en el libro", "3Conclusión y entrega"]);
    });

    test("el libro auditado queda dicho, con la fecha de la revisión, y se puede auditar otro", async () => {
      const { usuario } = await subirYAuditar();
      const paso1 = screen.getByRole("region", { name: "Suba el libro" });
      expect(within(paso1).getByText(/Presupuesto cliente A\.xlsx/)).toBeInTheDocument();
      expect(document.querySelector('input[type="file"]')).toBeNull();
      await usuario.click(within(paso1).getByRole("button", { name: "Auditar otro libro" }));
      expect(screen.getByRole("button", { name: /Suelte aquí el libro \.xlsx/ })).toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: "8 hallazgos en el libro" })).not.toBeInTheDocument();
    });
  });

  describe("las seis alertas de la prueba de comprensión, en la pantalla", () => {
    test("A1 a A3 salen en «Alertas de precio» y A4 a A6 en «Qué se encontró»", async () => {
      await subirYAuditar();
      const alertas = await screen.findByRole("list", { name: "Alertas de precio" });
      const [a1, a2, a3] = within(alertas).getAllByRole("listitem");
      expect(a1).toHaveTextContent("Sin fuente · MT-04");
      expect(a1).toHaveTextContent("la FUENTE de MT-04 dice «POR COTIZAR»");
      expect(a2).toHaveTextContent("Base de la empresa · MT-08");
      expect(a2).toHaveTextContent("+20,00 %, pasa del umbral de 5,00 %");
      expect(a3).toHaveTextContent("USD-Bs · MT-08");
      expect(a3).toHaveTextContent("+10,00 %, pasa del umbral de 5,00 %");
      expect(within(alertas).getAllByRole("listitem")).toHaveLength(3);

      const sueltos = screen.getByRole("list", { name: "Hallazgos uno por uno" });
      const [a4, a5] = within(sueltos).getAllByRole("listitem");
      expect(a4).toHaveTextContent("APU-02!G36 · Error · Componente fuera del total (L4)");
      expect(a4).toHaveTextContent("1.265,00");
      expect(a5).toHaveTextContent("RESUMEN!B4 · Error · Referencia rota o externa (L5)");
      const causa = within(screen.getByRole("list", { name: "Causas raíz" })).getByRole("listitem");
      expect(causa).toHaveTextContent("Error · 6 casos · Referencia desalineada (L1)");
      expect(causa).toHaveTextContent("Encontrado 0 · esperado 120");
    });

    test("cada alerta y cada hallazgo tiene su «Qué hacer», cerrado y sin title", async () => {
      await subirYAuditar();
      const botones = await screen.findAllByRole("button", { name: /^Qué hacer con/ });
      expect(botones).toHaveLength(6);
      for (const b of botones) {
        expect(b).toHaveAttribute("aria-expanded", "false");
        expect(b).not.toHaveAttribute("title");
      }
      expect(document.querySelector("[title]")).toBeNull();
    });

    test("pedir el «Qué hacer» al abrir un hallazgo muestra la guía del servidor", async () => {
      const { usuario } = await subirYAuditar();
      const sueltos = screen.getByRole("list", { name: "Hallazgos uno por uno" });
      const [a4] = within(sueltos).getAllByRole("listitem");
      await usuario.click(await within(a4).findByRole("button", { name: /Qué hacer/ }));
      expect(within(a4).getByText("Corrija el rango de la suma.")).toBeInTheDocument();
      expect(llamadas("/v1/libros/que-hacer")).toHaveLength(1);
    });

    test("la alerta USD-Bs dentro del umbral no se muestra", async () => {
      await subirYAuditar();
      const alertas = await screen.findByRole("list", { name: "Alertas de precio" });
      expect(alertas).not.toHaveTextContent("dentro del umbral");
      expect(alertas).not.toHaveTextContent("MT-01");
    });

    test("si no se pudo leer el catálogo, el libro se ve igual sin los «Qué hacer»", async () => {
      catalogo = () => json({ detalle: "Error interno." }, 500);
      await subirYAuditar();
      expect(screen.getByRole("list", { name: "Hallazgos uno por uno" })).toBeInTheDocument();
      await waitFor(() => expect(llamadas("/v1/libros/que-hacer")).toHaveLength(1));
      expect(screen.queryByRole("button", { name: /Qué hacer/ })).not.toBeInTheDocument();
    });

    test("la severidad se dice con palabra y las alertas no llevan color de gravedad", async () => {
      await subirYAuditar();
      const alertas = await screen.findByRole("list", { name: "Alertas de precio" });
      expect(alertas.querySelector("[style*='--halo-color']")).toBeNull();
      const sueltos = screen.getByRole("list", { name: "Hallazgos uno por uno" });
      expect(within(sueltos).getAllByText("Error").length).toBe(2);
    });
  });

  describe("conclusión y entrega", () => {
    test("con hallazgos el principal es el informe y el libro «no cumple»", async () => {
      await subirYAuditar();
      const seccion = screen.getByRole("region", { name: "Conclusión y entrega" });
      expect(within(seccion).getByText("El libro no cumple")).toBeInTheDocument();
      const principales = screen.getAllByRole("button").filter((b) => b.classList.contains("cds--btn--primary"));
      expect(principales.map((b) => b.textContent)).toEqual(["Descargar el informe en PDF"]);
    });

    test("«Ver la hoja marcada» pide la réplica una vez, deja el resultado en el almacén y no audita otra vez", async () => {
      const { usuario } = await subirYAuditar();
      expect(almacen.leer()).toBeNull();
      await usuario.click(screen.getByRole("button", { name: "Ver la hoja marcada" }));
      expect(await screen.findByRole("heading", { name: "Pantalla del libro" })).toBeInTheDocument();
      expect(llamadas("/v1/libros/replica")).toHaveLength(1);
      expect(llamadas("/v1/libros/auditoria")).toHaveLength(1);
      const guardado = almacen.leer();
      expect(guardado?.auditoria.libro.nombre).toBe("Presupuesto cliente A.xlsx");
      expect(guardado?.replica.nombre).toBe("Presupuesto cliente A.xlsx");
      expect(guardado?.archivo?.name).toBe("Presupuesto cliente A.xlsx");
      expect(tomarArchivoPendiente()).toBeNull();
    });

    test("un error al preparar la hoja se dice y el resultado sigue a la vista", async () => {
      fetchFalso.mockImplementation(async (entrada) => {
        const ruta = String(entrada);
        if (ruta === "/v1/libros/auditoria") return json(auditoriaDePrueba());
        if (ruta === "/v1/libros/que-hacer") return json(catalogoDePrueba());
        return json({ detalle: "El libro no se pudo interpretar." }, 422);
      });
      const { usuario } = await subirYAuditar();
      await usuario.click(screen.getByRole("button", { name: "Ver la hoja marcada" }));
      expect(await screen.findByRole("alert")).toHaveTextContent("El libro no se pudo interpretar.");
      expect(screen.getByRole("heading", { name: "8 hallazgos en el libro" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Ver la hoja marcada" })).toBeEnabled();
    });

    test("sin almacén del libro, la hoja se abre con el archivo pendiente y el Visor audita por su cuenta", async () => {
      const usuario = userEvent.setup();
      montar({ almacenDelLibro: undefined });
      const archivo = new File(["x"], "obra.xlsx");
      await usuario.upload(campoArchivo(), archivo);
      await usuario.click(screen.getByRole("button", { name: "Auditar el libro" }));
      await screen.findByRole("heading", { level: 2, name: "8 hallazgos en el libro" });
      await usuario.click(screen.getByRole("button", { name: "Ver la hoja marcada" }));
      await screen.findByRole("heading", { name: "Pantalla del libro" });
      const pendiente = tomarArchivoPendiente();
      expect(pendiente?.archivo).toBe(archivo);
      expect(pendiente?.modo).toBe("propio");
    });

    test("lleva al historial", async () => {
      const { usuario } = await subirYAuditar();
      await usuario.click(screen.getByRole("link", { name: "Ver el historial" }));
      expect(await screen.findByRole("heading", { name: "Pantalla del historial" })).toBeInTheDocument();
    });

    test("el aviso de que no quedó en el historial es del servidor y la auditoría vale", async () => {
      auditoria = () =>
        json(auditoriaDePrueba({ aviso_historial: "No se pudo guardar la auditoría en el historial." }));
      await subirYAuditar();
      expect(screen.getByText("No se pudo guardar la auditoría en el historial.")).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "8 hallazgos en el libro" })).toBeInTheDocument();
    });
  });

  describe("sin hallazgos", () => {
    test("lo dice, el libro cumple y el principal es auditar otro libro", async () => {
      auditoria = () => json(auditoriaSinHallazgos());
      const { usuario } = await subirYAuditar();
      expect(screen.getByRole("heading", { level: 2, name: "El libro no tiene hallazgos" })).toBeInTheDocument();
      expect(screen.getByText("El libro cumple")).toBeInTheDocument();
      const principales = screen.getAllByRole("button").filter((b) => b.classList.contains("cds--btn--primary"));
      expect(principales.map((b) => b.textContent)).toEqual(["Auditar otro libro"]);
      expect(screen.queryByRole("button", { name: "Descargar el informe en PDF" })).not.toBeInTheDocument();
      await usuario.click(principales[0]);
      expect(screen.getByRole("button", { name: /Suelte aquí el libro \.xlsx/ })).toBeInTheDocument();
    });
  });

  describe("cuando algo falla", () => {
    test("un error al auditar muestra el detalle del servidor, conserva el archivo y deja reintentar", async () => {
      let intento = 0;
      auditoria = () => (++intento === 1 ? json({ detalle: "El libro no se pudo interpretar." }, 422) : json(auditoriaDePrueba()));
      const usuario = userEvent.setup();
      montar();
      await usuario.upload(campoArchivo(), new File(["x"], "roto.xlsx"));
      await usuario.click(screen.getByRole("button", { name: "Auditar el libro" }));
      expect(await screen.findByRole("alert")).toHaveTextContent("El libro no se pudo interpretar.");
      expect(estadoDelArchivo()).toHaveTextContent("Archivo elegido: roto.xlsx");
      const principales = screen.getAllByRole("button").filter((b) => b.classList.contains("cds--btn--primary"));
      expect(principales.map((b) => b.textContent)).toEqual(["Reintentar"]);
      await usuario.click(principales[0]);
      await screen.findByRole("heading", { level: 2, name: "8 hallazgos en el libro" });
      expect(llamadas("/v1/libros/auditoria")).toHaveLength(2);
    });

    test("una respuesta 401 avisa que la sesión venció", async () => {
      const alExpirar = vi.fn();
      auditoria = () => json({ detalle: "Sesión vencida." }, 401);
      const usuario = userEvent.setup();
      montar({ alExpirar });
      await usuario.upload(campoArchivo(), new File(["x"], "obra.xlsx"));
      await usuario.click(screen.getByRole("button", { name: "Auditar el libro" }));
      await waitFor(() => expect(alExpirar).toHaveBeenCalled());
    });

    test("un archivo que no es .xlsx no habilita nada", async () => {
      const usuario = userEvent.setup({ applyAccept: false });
      montar();
      await usuario.upload(campoArchivo(), new File(["x"], "foto.png"));
      expect(screen.getByRole("alert")).toHaveTextContent("Solo se aceptan archivos .xlsx.");
      expect(screen.getByRole("button", { name: "Auditar el libro" })).toHaveAttribute("aria-disabled", "true");
    });

    test("una fecha de revisión incompleta no deja auditar y dice dónde corregirla", async () => {
      const usuario = userEvent.setup();
      montar();
      await usuario.upload(campoArchivo(), new File(["x"], "obra.xlsx"));
      const fecha = screen.getByLabelText("Fecha de la revisión");
      await usuario.clear(fecha);
      const principal = screen.getByRole("button", { name: "Auditar el libro" });
      expect(principal).toHaveAttribute("aria-disabled", "true");
      await usuario.click(principal);
      expect(await screen.findByText("Escriba la fecha de la revisión en «Más opciones».")).toBeInTheDocument();
      expect(llamadas("/v1/libros/auditoria")).toHaveLength(0);
    });
  });

  describe("el recorrido guiado de siempre", () => {
    test("«Auditar con recorrido guiado» deja el archivo en modo guiado, pone en curso el recorrido y lleva al libro", async () => {
      const usuario = userEvent.setup();
      montar();
      const archivo = new File(["x"], "obra-norte.xlsx");
      expect(recorridoEnCurso()).toBeNull();
      await usuario.upload(campoArchivo(), archivo);
      await usuario.click(screen.getByRole("button", { name: "Auditar con recorrido guiado" }));
      expect(await screen.findByRole("heading", { name: "Pantalla del libro" })).toBeInTheDocument();
      const pendiente = tomarArchivoPendiente();
      expect(pendiente?.archivo).toBe(archivo);
      expect(pendiente?.modo).toBe("guiado");
      expect(recorridoEnCurso()).toBe(RECORRIDO_AUDITAR);
      expect(llamadas("/v1/libros/auditoria")).toHaveLength(0);
    });
  });
});
