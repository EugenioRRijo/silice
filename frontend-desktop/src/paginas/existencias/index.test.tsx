import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import { alertaConTexto } from "../../test/ayudas";
import PaginaExistencias from "./index";
import { crearServidor, json } from "./servidorFalso";
import type { ServidorFalso } from "./servidorFalso";

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["operar_arenera"],
  modo_entrega: false,
};

const MATERIAL = "/v1/produccion/materiales";
const MOVIMIENTOS = "/v1/produccion/movimientos";
const EXISTENCIAS = "/v1/produccion/existencias";
const IMPORTAR = "/v1/produccion/bascula/importar";
const SOSPECHOSOS = "/v1/produccion/pesajes-sospechosos";

const SIN_PERMISO = "Su cuenta no tiene permiso para esta acción";
const MENSAJE_FIJO = "Ocurrió un error inesperado. Inténtelo de nuevo.";

type Usuario = ReturnType<typeof userEvent.setup>;

describe("Existencias de la arenera", () => {
  let servidor: ServidorFalso;
  let alExpirar: ReturnType<typeof vi.fn<() => void>>;
  let usuario: Usuario;

  function montar() {
    render(
      <ContextoAplicacion.Provider
        value={{ sesion: SESION, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar }}
      >
        <PaginaExistencias />
      </ContextoAplicacion.Provider>,
    );
  }

  async function irA(nombre: string) {
    await usuario.click(screen.getByRole("tab", { name: nombre }));
  }

  async function conExistencias() {
    montar();
    await screen.findByText("Arena lavada");
  }

  const filaDe = (codigo: string) => screen.getByRole("row", { name: new RegExp(codigo) });

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 9, 18, 10, 0, 0));
    servidor = crearServidor();
    vi.stubGlobal("fetch", servidor.fetchFalso);
    fijarCsrf("tok");
    alExpirar = vi.fn();
    usuario = userEvent.setup();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    fijarCsrf(null);
  });

  describe("marco de la pagina", () => {
    test("tiene su titulo y las cuatro pestanas, con Existencias abierta", async () => {
      await conExistencias();
      expect(screen.getByRole("heading", { level: 1, name: "Existencias de la arenera" })).toBeInTheDocument();
      const pestanas = screen.getAllByRole("tab").map((t) => t.textContent);
      expect(pestanas).toEqual(["Existencias", "Registrar", "Importar báscula", "Pesajes sospechosos"]);
      expect(screen.getByRole("tab", { name: "Existencias" })).toHaveAttribute("aria-selected", "true");
    });
  });

  describe("pestana Existencias", () => {
    test("mientras llegan los datos muestra un esqueleto anunciado", async () => {
      let soltar: () => void = () => {};
      servidor.responder(`GET ${EXISTENCIAS}`, () => new Promise((resolver) => (soltar = () => resolver(json([])))));
      montar();
      expect(screen.getByRole("status", { name: /Cargando/ })).toBeInTheDocument();
      soltar();
      await screen.findByText(/Todavía no hay materiales/);
    });

    test("pide la existencia de hoy y la muestra en una tabla densa de 32 px", async () => {
      await conExistencias();
      const pedidas = servidor.de("GET", EXISTENCIAS);
      expect(pedidas[0].consulta.get("a_fecha")).toBe("2026-10-18");
      const tabla = screen.getByRole("table", { name: "Existencias por material" });
      expect(tabla.closest(".cds--data-table--sm")).not.toBeNull();
      for (const encabezado of ["Código", "Material", "Unidad", "Existencia", "Mínima", "Estado"]) {
        expect(within(tabla).getByRole("columnheader", { name: new RegExp(encabezado) })).toBeInTheDocument();
      }
    });

    test("existencia y minima van a la derecha, con coma decimal y sin ceros de relleno", async () => {
      await conExistencias();
      const arena = filaDe("ARE-01");
      expect(within(arena).getByRole("cell", { name: "120,5" })).toHaveClass("silice-cifra");
      expect(within(arena).getByRole("cell", { name: "50" })).toHaveClass("silice-cifra");
      expect(within(filaDe("PIE-01")).getByRole("cell", { name: "20" })).toHaveClass("silice-cifra");
      expect(within(filaDe("GRA-01")).getByRole("cell", { name: "-4,25" })).toHaveClass("silice-cifra");
      expect(within(arena).getByRole("cell", { name: "m³" })).not.toHaveClass("silice-cifra");
      expect(screen.getByRole("columnheader", { name: /Existencia/ })).toHaveClass("silice-cifra");
    });

    test("cada estado se dice con icono y texto: Normal, Queda poco y Existencia negativa", async () => {
      await conExistencias();
      const normal = within(filaDe("ARE-01"));
      expect(normal.getByText("Normal")).toBeInTheDocument();
      expect(filaDe("ARE-01").querySelector('[data-estado="normal"] svg')).not.toBeNull();

      const poco = within(filaDe("PIE-01"));
      expect(poco.getByText("Queda poco")).toBeInTheDocument();
      expect(filaDe("PIE-01").querySelector('[data-estado="queda_poco"] svg')).not.toBeNull();

      const negativa = within(filaDe("GRA-01"));
      expect(negativa.getByText("Existencia negativa: falta registrar producción o conteo")).toBeInTheDocument();
      expect(filaDe("GRA-01").querySelector('[data-estado="negativa"] svg')).not.toBeNull();
    });

    test("la existencia negativa manda sobre queda poco: la fila negativa no dice «Queda poco»", async () => {
      await conExistencias();
      // GRA-01 llega con queda_poco y negativa a la vez.
      expect(within(filaDe("GRA-01")).queryByText("Queda poco")).not.toBeInTheDocument();
    });

    test("el resumen cuenta materiales, los que queda poco (sin las negativas) y las negativas", async () => {
      await conExistencias();
      const resumen = screen.getByRole("region", { name: "Resumen de existencias" });
      expect(within(resumen).getByText("Materiales").parentElement).toHaveTextContent("Materiales3");
      expect(within(resumen).getByText("Queda poco").parentElement).toHaveTextContent("Queda poco1");
      expect(within(resumen).getByText("Existencia negativa").parentElement).toHaveTextContent("Existencia negativa1");
    });

    test("explica la leyenda de estados y avisa que hay existencia negativa", async () => {
      await conExistencias();
      expect(screen.getByText(/Hay materiales con existencia negativa/)).toBeInTheDocument();
      expect(screen.getByText(/Registre la producción \(entrada\) o un conteo físico/)).toBeInTheDocument();
      expect(screen.getByText(/existencia menor o igual que la mínima/)).toBeInTheDocument();
    });

    test("sin materiales negativos no muestra el aviso de existencia negativa", async () => {
      servidor.estado.existencias = servidor.estado.existencias.slice(0, 2);
      await conExistencias();
      expect(screen.queryByText(/Hay materiales con existencia negativa/)).not.toBeInTheDocument();
    });

    test("cambiar la fecha vuelve a pedir la existencia a esa fecha", async () => {
      await conExistencias();
      fireEvent.change(screen.getByLabelText("Existencia al"), { target: { value: "2026-10-01" } });
      await waitFor(() => expect(servidor.de("GET", EXISTENCIAS).at(-1)?.consulta.get("a_fecha")).toBe("2026-10-01"));
    });

    test("sin materiales ensena que hacer y lleva a Registrar", async () => {
      servidor.estado.existencias = [];
      montar();
      expect(await screen.findByText("Todavía no hay materiales")).toBeInTheDocument();
      await usuario.click(screen.getByRole("button", { name: "Crear un material" }));
      expect(screen.getByRole("tab", { name: "Registrar" })).toHaveAttribute("aria-selected", "true");
    });

    test("si la API falla muestra su detalle y permite reintentar", async () => {
      servidor.responder(`GET ${EXISTENCIAS}`, () => json({ detalle: "La base de la instalación está ocupada." }, 503));
      montar();
      expect(await alertaConTexto()).toHaveTextContent("La base de la instalación está ocupada.");
      servidor.responder(`GET ${EXISTENCIAS}`, () => json(servidor.estado.existencias));
      await usuario.click(screen.getByRole("button", { name: "Reintentar" }));
      expect(await screen.findByText("Arena lavada")).toBeInTheDocument();
    });

    test("un fallo inesperado muestra un mensaje fijo, sin detalles internos", async () => {
      servidor.responder(`GET ${EXISTENCIAS}`, () => new Response("<html>no es json</html>", { status: 200 }));
      montar();
      expect(await alertaConTexto()).toHaveTextContent(MENSAJE_FIJO);
    });
  });

  describe("pestana Registrar", () => {
    async function abrirRegistrar() {
      await conExistencias();
      await irA("Registrar");
      await screen.findByLabelText("Material");
    }

    test("ofrece entrada, despacho, conteo fisico y material nuevo", async () => {
      await abrirRegistrar();
      const opciones = screen.getAllByRole("tab").map((t) => t.textContent);
      expect(opciones).toEqual(
        expect.arrayContaining(["Entrada", "Despacho", "Conteo físico", "Material nuevo"]),
      );
      expect(screen.getByText(/Un despacho nunca se bloquea/)).toBeInTheDocument();
    });

    test("la cantidad dice la unidad del material elegido", async () => {
      await abrirRegistrar();
      expect(screen.getByLabelText("Cantidad (m³)")).toBeInTheDocument();
      await usuario.selectOptions(screen.getByLabelText("Material"), "PIE-01");
      expect(screen.getByLabelText("Cantidad (t)")).toBeInTheDocument();
    });

    test("registra una entrada: coma decimal aceptada, manda punto, avisa y recarga el tablero", async () => {
      servidor.responder(`POST ${MOVIMIENTOS}`, () =>
        json({ id: 1, material_codigo: "ARE-01", fecha: "2026-10-18", tipo: "entrada", cantidad: "12.5" }, 201),
      );
      await abrirRegistrar();
      const antes = servidor.de("GET", EXISTENCIAS).length;
      await usuario.type(screen.getByLabelText("Cantidad (m³)"), "12,5");
      await usuario.type(screen.getByLabelText("Nota (opcional)"), "turno de la mañana");
      await usuario.click(screen.getByRole("button", { name: "Registrar entrada" }));

      expect(await screen.findByText("Entrada registrada: 12,5 m³ de ARE-01.")).toBeInTheDocument();
      expect(servidor.de("POST", MOVIMIENTOS)[0].cuerpo).toEqual({
        material_codigo: "ARE-01",
        tipo: "entrada",
        fecha: "2026-10-18",
        cantidad: "12.5",
        nota: "turno de la mañana",
      });
      expect(screen.getByLabelText("Cantidad (m³)")).toHaveValue("");
      expect(servidor.de("GET", EXISTENCIAS).length).toBeGreaterThan(antes);
    });

    test("la fecha parte de hoy y se puede cambiar", async () => {
      await abrirRegistrar();
      const fecha = screen.getByLabelText("Fecha");
      expect(fecha).toHaveValue("2026-10-18");
      fireEvent.change(fecha, { target: { value: "2026-10-10" } });
      await usuario.type(screen.getByLabelText("Cantidad (m³)"), "3");
      await usuario.click(screen.getByRole("button", { name: "Registrar entrada" }));
      await screen.findByText(/Entrada registrada/);
      expect(servidor.de("POST", MOVIMIENTOS)[0].cuerpo).toMatchObject({ fecha: "2026-10-10" });
    });

    test("rechaza «1.234,5» sin llamar a la API y dice como escribirlo", async () => {
      await abrirRegistrar();
      await usuario.type(screen.getByLabelText("Cantidad (m³)"), "1.234,5");
      await usuario.click(screen.getByRole("button", { name: "Registrar entrada" }));
      expect(await screen.findByText(/no debe llevar separador de miles: escriba, por ejemplo, 1234,5/)).toBeInTheDocument();
      expect(servidor.de("POST", MOVIMIENTOS)).toHaveLength(0);
    });

    test("una cantidad vacia o en cero se marca antes de llamar a la API", async () => {
      await abrirRegistrar();
      await usuario.click(screen.getByRole("button", { name: "Registrar entrada" }));
      expect(await screen.findByText("Escriba la cantidad de la entrada.")).toBeInTheDocument();
      await usuario.type(screen.getByLabelText("Cantidad (m³)"), "0");
      await usuario.click(screen.getByRole("button", { name: "Registrar entrada" }));
      expect(await screen.findByText("La cantidad de la entrada debe ser un número mayor que cero.")).toBeInTheDocument();
      expect(servidor.de("POST", MOVIMIENTOS)).toHaveLength(0);
    });

    test("registra un despacho", async () => {
      servidor.responder(`POST ${MOVIMIENTOS}`, () => json({ id: 2 }, 201));
      await abrirRegistrar();
      await irA("Despacho");
      await usuario.selectOptions(screen.getByLabelText("Material"), "PIE-01");
      await usuario.type(screen.getByLabelText("Cantidad (t)"), "8.25");
      await usuario.click(screen.getByRole("button", { name: "Registrar despacho" }));
      expect(await screen.findByText("Despacho registrado: 8,25 t de PIE-01.")).toBeInTheDocument();
      expect(servidor.de("POST", MOVIMIENTOS)[0].cuerpo).toEqual({
        material_codigo: "PIE-01",
        tipo: "despacho",
        fecha: "2026-10-18",
        cantidad: "8.25",
        nota: "",
      });
    });

    test("registra un conteo fisico: manda lo contado como ajuste", async () => {
      servidor.responder(`POST ${MOVIMIENTOS}`, () => json({ id: 3, tipo: "ajuste", cantidad: "-2.5" }, 201));
      await abrirRegistrar();
      await irA("Conteo físico");
      await usuario.type(screen.getByLabelText("Lo contado (m³)"), "118");
      await usuario.click(screen.getByRole("button", { name: "Registrar conteo" }));
      expect(await screen.findByText("Conteo registrado.")).toBeInTheDocument();
      expect(servidor.de("POST", MOVIMIENTOS)[0].cuerpo).toMatchObject({ tipo: "ajuste", cantidad: "118" });
    });

    test("un conteo igual a la existencia (la API contesta null) dice que no hizo falta ajustar", async () => {
      servidor.responder(`POST ${MOVIMIENTOS}`, () => json(null, 200));
      await abrirRegistrar();
      await irA("Conteo físico");
      await usuario.type(screen.getByLabelText("Lo contado (m³)"), "0");
      await usuario.click(screen.getByRole("button", { name: "Registrar conteo" }));
      expect(await screen.findByText("El conteo coincide con la existencia: no hizo falta ajustar.")).toBeInTheDocument();
    });

    test("crea un material nuevo con su minima y su densidad, y ya aparece en las listas", async () => {
      servidor.responder(`POST ${MATERIAL}`, () => {
        servidor.estado.materiales.push({
          id: 4,
          codigo: "ARE-02",
          nombre: "Arena fina",
          unidad_venta: "m3",
          densidad_t_m3: "1.55",
          existencia_minima: "30",
          activo: true,
        });
        return json(servidor.estado.materiales[3], 201);
      });
      await abrirRegistrar();
      await irA("Material nuevo");
      await usuario.type(screen.getByLabelText("Código"), "ARE-02");
      await usuario.type(screen.getByLabelText("Nombre"), "Arena fina");
      await usuario.selectOptions(screen.getByLabelText("Unidad de venta"), "m3");
      await usuario.type(screen.getByLabelText("Existencia mínima"), "30");
      await usuario.type(screen.getByLabelText("Densidad (t/m³, opcional)"), "1,55");
      await usuario.click(screen.getByRole("button", { name: "Crear material" }));

      expect(await screen.findByText("Material creado: ARE-02.")).toBeInTheDocument();
      expect(servidor.de("POST", MATERIAL)[0].cuerpo).toEqual({
        codigo: "ARE-02",
        nombre: "Arena fina",
        unidad_venta: "m3",
        existencia_minima: "30",
        densidad_t_m3: "1.55",
      });
      await irA("Entrada");
      expect(await screen.findByRole("option", { name: "ARE-02 · Arena fina" })).toBeInTheDocument();
    });

    test("la densidad es opcional: sin ella no viaja", async () => {
      await abrirRegistrar();
      await irA("Material nuevo");
      await usuario.type(screen.getByLabelText("Código"), "CEM-01");
      await usuario.type(screen.getByLabelText("Nombre"), "Cemento");
      await usuario.selectOptions(screen.getByLabelText("Unidad de venta"), "t");
      await usuario.type(screen.getByLabelText("Existencia mínima"), "5");
      await usuario.click(screen.getByRole("button", { name: "Crear material" }));
      await screen.findByText("Material creado: CEM-01.");
      const cuerpo = servidor.de("POST", MATERIAL)[0].cuerpo as Record<string, unknown>;
      expect(cuerpo.unidad_venta).toBe("t");
      expect(cuerpo).not.toHaveProperty("densidad_t_m3");
    });

    test("un material nuevo sin codigo, nombre o minima se marca antes de llamar a la API", async () => {
      await abrirRegistrar();
      await irA("Material nuevo");
      await usuario.click(screen.getByRole("button", { name: "Crear material" }));
      expect(await screen.findByText("Escriba el código del material.")).toBeInTheDocument();
      expect(screen.getByText("Escriba el nombre del material.")).toBeInTheDocument();
      expect(screen.getByText("Escriba la existencia mínima.")).toBeInTheDocument();
      expect(servidor.de("POST", MATERIAL)).toHaveLength(0);
    });

    test("un codigo repetido muestra el detalle de la API tal cual", async () => {
      servidor.responder(`POST ${MATERIAL}`, () => json({ detalle: "Ya existe un material con el código «ARE-01»." }, 409));
      await abrirRegistrar();
      await irA("Material nuevo");
      await usuario.type(screen.getByLabelText("Código"), "ARE-01");
      await usuario.type(screen.getByLabelText("Nombre"), "Otra arena");
      await usuario.type(screen.getByLabelText("Existencia mínima"), "1");
      await usuario.click(screen.getByRole("button", { name: "Crear material" }));
      expect(await alertaConTexto()).toHaveTextContent("Ya existe un material con el código «ARE-01».");
    });

    test("un error de la API al registrar se muestra con su detalle y no borra lo escrito", async () => {
      servidor.responder(`POST ${MOVIMIENTOS}`, () => json({ detalle: "La fecha no puede ser futura." }, 422));
      await abrirRegistrar();
      await usuario.type(screen.getByLabelText("Cantidad (m³)"), "4");
      await usuario.click(screen.getByRole("button", { name: "Registrar entrada" }));
      expect(await alertaConTexto()).toHaveTextContent("La fecha no puede ser futura.");
      expect(screen.getByLabelText("Cantidad (m³)")).toHaveValue("4");
    });

    test("un fallo inesperado al registrar da el mensaje fijo", async () => {
      servidor.responder(`POST ${MOVIMIENTOS}`, () => new Response("no es json", { status: 201 }));
      await abrirRegistrar();
      await usuario.type(screen.getByLabelText("Cantidad (m³)"), "4");
      await usuario.click(screen.getByRole("button", { name: "Registrar entrada" }));
      expect(await alertaConTexto()).toHaveTextContent(MENSAJE_FIJO);
    });

    test("sin materiales los formularios de movimiento mandan a crear uno", async () => {
      servidor.estado.materiales = [];
      servidor.estado.existencias = [];
      montar();
      await screen.findByText("Todavía no hay materiales");
      await irA("Registrar");
      expect(await screen.findByText(/Créelos en «Material nuevo»/)).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Registrar entrada" })).not.toBeInTheDocument();
    });
  });

  describe("pestana Importar báscula", () => {
    const reporte = () => new File(["a,b\n1,2"], "reporte_octubre.csv", { type: "text/csv" });

    async function abrirImportar() {
      await conExistencias();
      await irA("Importar báscula");
      await screen.findByText(/Suelte aquí el reporte/);
    }

    async function elegir(archivo: File = reporte()) {
      const entrada = document.querySelector('input[type="file"]') as HTMLInputElement;
      await usuario.upload(entrada, archivo);
    }

    test("ofrece la zona de carga, la unidad del peso y la fecha de referencia de hoy, editable", async () => {
      await abrirImportar();
      expect(screen.getByLabelText("Fecha de referencia")).toHaveValue("2026-10-18");
      expect(screen.getByRole("radio", { name: "Según el encabezado" })).toBeChecked();
      expect(screen.getByRole("radio", { name: "kg" })).toBeInTheDocument();
      expect(screen.getByRole("radio", { name: "t" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Importar" })).toBeDisabled();
    });

    test("importa el reporte: manda archivo y fecha, no manda unidad si el encabezado la trae y muestra el resultado", async () => {
      servidor.responder(`POST ${IMPORTAR}`, () => json({ registrados: 5, ya_registrados: 2, a_la_bandeja: 0, huella: "a".repeat(64) }));
      await abrirImportar();
      await elegir();
      expect(screen.getByText(/reporte_octubre\.csv/)).toBeInTheDocument();
      await usuario.click(screen.getByRole("button", { name: "Importar" }));

      const resultado = await screen.findByRole("region", { name: "Resultado de la importación" });
      expect(within(resultado).getByText("Despachos registrados").parentElement).toHaveTextContent("Despachos registrados5");
      expect(within(resultado).getByText("Ya estaban registrados").parentElement).toHaveTextContent("Ya estaban registrados2");
      expect(within(resultado).getByText("A la bandeja de sospechosos").parentElement).toHaveTextContent("A la bandeja de sospechosos0");

      const formulario = servidor.de("POST", IMPORTAR)[0].formulario!;
      expect((formulario.get("archivo") as File).name).toBe("reporte_octubre.csv");
      expect(formulario.get("fecha_referencia")).toBe("2026-10-18");
      expect(formulario.get("unidad_peso")).toBeNull();
      expect(formulario.get("mapeo")).toBeNull();
    });

    test("manda la unidad elegida y la fecha de referencia editada", async () => {
      servidor.responder(`POST ${IMPORTAR}`, () => json({ registrados: 1, ya_registrados: 0, a_la_bandeja: 0, huella: "b".repeat(64) }));
      await abrirImportar();
      await elegir();
      await usuario.click(screen.getByRole("radio", { name: "kg" }));
      fireEvent.change(screen.getByLabelText("Fecha de referencia"), { target: { value: "2026-10-16" } });
      await usuario.click(screen.getByRole("button", { name: "Importar" }));
      await screen.findByRole("region", { name: "Resultado de la importación" });
      const formulario = servidor.de("POST", IMPORTAR)[0].formulario!;
      expect(formulario.get("unidad_peso")).toBe("kg");
      expect(formulario.get("fecha_referencia")).toBe("2026-10-16");
    });

    test("solo acepta .csv y .xlsx", async () => {
      const lento = userEvent.setup({ applyAccept: false });
      await abrirImportar();
      await lento.upload(document.querySelector('input[type="file"]') as HTMLInputElement, new File(["x"], "reporte.pdf"));
      expect(await screen.findByText("Solo se aceptan archivos .csv o .xlsx.")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Importar" })).toBeDisabled();
    });

    test("pesajes que van a la bandeja: avisa y lleva a la bandeja", async () => {
      servidor.responder(`POST ${IMPORTAR}`, () => json({ registrados: 3, ya_registrados: 0, a_la_bandeja: 2, huella: "c".repeat(64) }));
      await abrirImportar();
      await elegir();
      await usuario.click(screen.getByRole("button", { name: "Importar" }));
      expect(await screen.findByText(/no entraron al inventario/)).toBeInTheDocument();
      await usuario.click(screen.getByRole("button", { name: "Ver los pesajes sospechosos" }));
      expect(screen.getByRole("tab", { name: "Pesajes sospechosos" })).toHaveAttribute("aria-selected", "true");
      expect(await screen.findByText("Material desconocido")).toBeInTheDocument();
    });

    test("recarga el tablero despues de importar", async () => {
      servidor.responder(`POST ${IMPORTAR}`, () => json({ registrados: 3, ya_registrados: 0, a_la_bandeja: 0, huella: "c".repeat(64) }));
      await abrirImportar();
      const antes = servidor.de("GET", EXISTENCIAS).length;
      await elegir();
      await usuario.click(screen.getByRole("button", { name: "Importar" }));
      await screen.findByRole("region", { name: "Resultado de la importación" });
      await irA("Existencias");
      await screen.findByText("Arena lavada");
      expect(servidor.de("GET", EXISTENCIAS).length).toBeGreaterThan(antes);
    });

    test("si la API no reconoce columnas pide el numero de columna de cada campo y vuelve a importar con el mapeo", async () => {
      let intento = 0;
      servidor.responder(`POST ${IMPORTAR}`, () => {
        intento += 1;
        if (intento === 1) {
          return json({ detalle: "No se reconocieron las columnas del reporte.", faltan: ["ticket", "neto"] }, 422);
        }
        return json({ registrados: 4, ya_registrados: 0, a_la_bandeja: 0, huella: "d".repeat(64) });
      });
      await abrirImportar();
      await elegir();
      await usuario.click(screen.getByRole("button", { name: "Importar" }));

      expect(await screen.findByText(/No se reconocieron las columnas de: ticket, peso neto/)).toBeInTheDocument();
      expect(screen.getByText(/1 = la primera columna/)).toBeInTheDocument();
      // Sin numeros no se vuelve a llamar.
      await usuario.click(screen.getByRole("button", { name: "Importar" }));
      expect(await screen.findAllByText("Escriba el número de columna.")).toHaveLength(2);
      expect(servidor.de("POST", IMPORTAR)).toHaveLength(1);

      await usuario.type(screen.getByLabelText("Columna de ticket"), "3");
      await usuario.type(screen.getByLabelText("Columna de peso neto"), "7");
      await usuario.click(screen.getByRole("button", { name: "Importar" }));

      await screen.findByRole("region", { name: "Resultado de la importación" });
      const segundo = servidor.de("POST", IMPORTAR)[1].formulario!;
      expect(JSON.parse(String(segundo.get("mapeo")))).toEqual({ ticket: 2, neto: 6 });
      expect((segundo.get("archivo") as File).name).toBe("reporte_octubre.csv");
      expect(screen.queryByLabelText("Columna de ticket")).not.toBeInTheDocument();
    });

    test("una columna fuera de rango o con decimales se marca", async () => {
      servidor.responder(`POST ${IMPORTAR}`, () => json({ detalle: "Faltan columnas.", faltan: ["fecha"] }, 422));
      await abrirImportar();
      await elegir();
      await usuario.click(screen.getByRole("button", { name: "Importar" }));
      await screen.findByLabelText("Columna de fecha");
      await usuario.type(screen.getByLabelText("Columna de fecha"), "2,5");
      await usuario.click(screen.getByRole("button", { name: "Importar" }));
      expect(await screen.findByText("Escriba un número entero de columna, desde 1.")).toBeInTheDocument();
      expect(servidor.de("POST", IMPORTAR)).toHaveLength(1);
    });

    test("un 422 sin columnas por indicar muestra el detalle de la API (por ejemplo, falta la unidad)", async () => {
      servidor.responder(`POST ${IMPORTAR}`, () =>
        json({ detalle: "Indique si los pesos están en kg o en t." }, 422),
      );
      await abrirImportar();
      await elegir();
      await usuario.click(screen.getByRole("button", { name: "Importar" }));
      expect(await alertaConTexto()).toHaveTextContent("Indique si los pesos están en kg o en t.");
      expect(screen.queryByLabelText(/Columna de/)).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Importar" })).toBeEnabled();
    });

    test("elegir otro archivo borra las columnas pedidas y el resultado anterior", async () => {
      servidor.responder(`POST ${IMPORTAR}`, () => json({ detalle: "Faltan columnas.", faltan: ["fecha"] }, 422));
      await abrirImportar();
      await elegir();
      await usuario.click(screen.getByRole("button", { name: "Importar" }));
      await screen.findByLabelText("Columna de fecha");
      await elegir(new File(["x"], "otro.xlsx"));
      expect(screen.queryByLabelText("Columna de fecha")).not.toBeInTheDocument();
      expect(screen.getByText(/otro\.xlsx/)).toBeInTheDocument();
    });
  });

  describe("pestana Pesajes sospechosos", () => {
    async function abrirBandeja() {
      await conExistencias();
      await irA("Pesajes sospechosos");
      await screen.findByText("El neto no es bruto menos tara");
    }

    test("lista los pesajes con lo que dice el archivo y su motivo", async () => {
      await abrirBandeja();
      const tabla = screen.getByRole("table", { name: "Pesajes sospechosos" });
      expect(tabla.closest(".cds--data-table--sm")).not.toBeNull();
      for (const encabezado of ["Fila", "Ticket", "Fecha", "Placa", "Material", "Bruto", "Tara", "Neto", "Motivo"]) {
        expect(within(tabla).getByRole("columnheader", { name: new RegExp(`^${encabezado}`) })).toBeInTheDocument();
      }
      const fila = within(screen.getByRole("row", { name: /T-0042/ }));
      expect(fila.getByText("A12BC3D")).toBeInTheDocument();
      expect(fila.getByText("31500")).toBeInTheDocument();
      expect(screen.getByText(/2 pesajes por resolver/)).toBeInTheDocument();
    });

    test("sin pesajes pendientes lo dice", async () => {
      servidor.estado.sospechosos = [];
      await conExistencias();
      await irA("Pesajes sospechosos");
      expect(await screen.findByText("No hay pesajes sospechosos por resolver")).toBeInTheDocument();
    });

    test("revisar un pesaje abre el formulario con el material, la fecha y el ticket del archivo", async () => {
      await abrirBandeja();
      await usuario.click(screen.getByRole("button", { name: "Revisar el pesaje de la fila 12" }));
      expect(screen.getByRole("heading", { name: "Pesaje de la fila 12" })).toBeInTheDocument();
      expect(screen.getByLabelText("Material correcto")).toHaveValue("ARE-01"); // «arena lavada» coincide con el nombre
      expect(screen.getByLabelText("Fecha")).toHaveValue("2026-10-15");
      expect(screen.getByLabelText("Ticket")).toHaveValue("T-0042");
      expect(screen.getByLabelText("Peso neto (t)")).toHaveValue("");
    });

    test("lo que no se reconoce queda sin elegir, para no registrar un despacho a ciegas", async () => {
      await abrirBandeja();
      await usuario.click(screen.getByRole("button", { name: "Revisar el pesaje de la fila 15" }));
      expect(screen.getByLabelText("Material correcto")).toHaveValue("");
      expect(screen.getByLabelText("Fecha")).toHaveValue("");
      await usuario.click(screen.getByRole("button", { name: "Resolver como despacho" }));
      expect(await screen.findByText("Elija el material correcto.")).toBeInTheDocument();
      expect(screen.getByText("Escriba la fecha del despacho.")).toBeInTheDocument();
      expect(screen.getByText("Escriba el peso neto en toneladas.")).toBeInTheDocument();
      expect(servidor.de("POST", `${SOSPECHOSOS}/8/resolver`)).toHaveLength(0);
    });

    test("resuelve el pesaje como despacho con los valores corregidos y recarga la bandeja", async () => {
      servidor.responder(`POST ${SOSPECHOSOS}/7/resolver`, () => {
        servidor.estado.sospechosos = servidor.estado.sospechosos.filter((s) => s.id !== 7);
        return json({ id: 9, material_codigo: "ARE-01", tipo: "despacho" }, 201);
      });
      await abrirBandeja();
      await usuario.click(screen.getByRole("button", { name: "Revisar el pesaje de la fila 12" }));
      await usuario.type(screen.getByLabelText("Peso neto (t)"), "19,5");
      await usuario.click(screen.getByRole("button", { name: "Resolver como despacho" }));

      expect(await screen.findByText("Pesaje resuelto: despacho de ARE-01 registrado.")).toBeInTheDocument();
      expect(servidor.de("POST", `${SOSPECHOSOS}/7/resolver`)[0].cuerpo).toEqual({
        material_codigo: "ARE-01",
        fecha: "2026-10-15",
        neto_t: "19.5",
        ticket: "T-0042",
        ahora: "2026-10-18T10:00:00",
      });
      await waitFor(() => expect(screen.queryByRole("row", { name: /T-0042/ })).not.toBeInTheDocument());
      expect(screen.queryByRole("heading", { name: "Pesaje de la fila 12" })).not.toBeInTheDocument();
      expect(screen.getByText(/1 pesaje por resolver/)).toBeInTheDocument();
    });

    test("el peso neto con separador de miles se rechaza sin llamar a la API", async () => {
      await abrirBandeja();
      await usuario.click(screen.getByRole("button", { name: "Revisar el pesaje de la fila 12" }));
      await usuario.type(screen.getByLabelText("Peso neto (t)"), "1.234,5");
      await usuario.click(screen.getByRole("button", { name: "Resolver como despacho" }));
      expect(await screen.findByText(/no debe llevar separador de miles/)).toBeInTheDocument();
      expect(servidor.de("POST", `${SOSPECHOSOS}/7/resolver`)).toHaveLength(0);
    });

    test("descarta el pesaje sin crear ningun despacho", async () => {
      servidor.responder(`POST ${SOSPECHOSOS}/8/descartar`, () => {
        servidor.estado.sospechosos = servidor.estado.sospechosos.filter((s) => s.id !== 8);
        return new Response(null, { status: 204 });
      });
      await abrirBandeja();
      await usuario.click(screen.getByRole("button", { name: "Revisar el pesaje de la fila 15" }));
      await usuario.click(screen.getByRole("button", { name: "Descartar" }));
      expect(await screen.findByText("Pesaje descartado: no se registró ningún despacho.")).toBeInTheDocument();
      expect(servidor.de("POST", `${SOSPECHOSOS}/8/descartar`)[0].cuerpo).toEqual({ ahora: "2026-10-18T10:00:00" });
      await waitFor(() => expect(screen.queryByRole("row", { name: /Material desconocido/ })).not.toBeInTheDocument());
    });

    test("un pesaje que ya se resolvio en otra sesion muestra el detalle de la API y refresca la lista", async () => {
      servidor.responder(`POST ${SOSPECHOSOS}/8/descartar`, () =>
        json({ detalle: "Ese pesaje sospechoso ya fue resuelto o descartado." }, 409),
      );
      await abrirBandeja();
      await usuario.click(screen.getByRole("button", { name: "Revisar el pesaje de la fila 15" }));
      const antes = servidor.de("GET", SOSPECHOSOS).length;
      await usuario.click(screen.getByRole("button", { name: "Descartar" }));
      expect(await alertaConTexto()).toHaveTextContent("Ese pesaje sospechoso ya fue resuelto o descartado.");
      await waitFor(() => expect(servidor.de("GET", SOSPECHOSOS).length).toBeGreaterThan(antes));
    });
  });

  describe("permisos y sesion", () => {
    test("un 403 al cargar muestra «Su cuenta no tiene permiso para esta acción» en lugar de las pestanas", async () => {
      servidor.responder(`GET ${EXISTENCIAS}`, () => json({ detalle: "Acción no permitida para su rol." }, 403));
      montar();
      expect(await screen.findByText(SIN_PERMISO)).toBeInTheDocument();
      expect(screen.queryByRole("tab")).not.toBeInTheDocument();
    });

    test("un 403 al registrar tambien lo dice", async () => {
      servidor.responder(`POST ${MOVIMIENTOS}`, () => json({ detalle: "Acción no permitida para su rol." }, 403));
      await conExistencias();
      await irA("Registrar");
      await screen.findByLabelText("Material");
      await usuario.type(screen.getByLabelText("Cantidad (m³)"), "4");
      await usuario.click(screen.getByRole("button", { name: "Registrar entrada" }));
      expect(await screen.findByText(SIN_PERMISO)).toBeInTheDocument();
      expect(screen.queryByRole("tab")).not.toBeInTheDocument();
    });

    test("un 403 en la bandeja tambien lo dice", async () => {
      servidor.responder(`GET ${SOSPECHOSOS}`, () => json({ detalle: "No." }, 403));
      await conExistencias();
      await irA("Pesajes sospechosos");
      expect(await screen.findByText(SIN_PERMISO)).toBeInTheDocument();
    });

    test("un 401 avisa a la aplicacion que la sesion vencio", async () => {
      servidor.responder(`GET ${EXISTENCIAS}`, () => json({ detalle: "Sesión vencida." }, 401));
      montar();
      await waitFor(() => expect(alExpirar).toHaveBeenCalled());
    });
  });
});
