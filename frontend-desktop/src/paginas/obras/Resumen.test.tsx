import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { pedir } from "../../api/cliente";
import type { ObraFilaRespuesta, PendienteDeObra } from "../../api/tipos";
import { EspacioDeObra } from "../../marco/EspacioDeObra";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import type { ObraAbierta } from "../../marco/obraAbierta";
import { crearVigilante } from "../../marco/otraPestana";
import { PATRON_DE_OBRA, rutaDeObra } from "../../marco/secciones";
import type { ObraDeCarpeta } from "../../marco/useObras";
import { ContextoPendientes } from "../../marco/usePendientes";
import type { PendientesDelMarco } from "../../marco/usePendientes";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { sesionDe } from "../../shell/obras/datosDePrueba";
import PaginaObras from "./index";

vi.mock("../../api/cliente", async (importarOriginal) => ({
  ...(await importarOriginal<typeof import("../../api/cliente")>()),
  pedir: vi.fn(),
}));
const pedirFalso = vi.mocked(pedir);

// Tarea 2 del plan F4: el Resumen de la obra abierta. Tres obras ficticias; los textos y las cifras son los que daría
// el servidor, escritos a mano (oráculos independientes del código). La obra 3 es «Galpón Norte».
const NORTE = "Carpeta Norte.db";
const SUR = "Carpeta Sur.db";
const FILA: ObraFilaRespuesta = {
  codigo: "3",
  nombre: "Galpón Norte",
  cliente: "Cliente Ficticio, C.A.",
  etapa: "en_aprobacion",
  etapa_texto: "En aprobación",
  version: "002",
  total: "1234567.89",
  moneda: "Bs",
  avance_real: "30.0",
  avance_plan: "37.5",
  que_pasa: "Faltan 2 precios",
  siguiente: { texto: "Abrir el presupuesto", pagina: "hoja" },
};
const OTRAS: ObraFilaRespuesta[] = [
  { ...FILA, codigo: "4", nombre: "Puente Sur", etapa: "atrasada", etapa_texto: "Atrasada" },
  { ...FILA, codigo: "5", nombre: "Depósito Este", etapa: "en_elaboracion", etapa_texto: "En elaboración" },
];

function pendiente(carpeta: string, texto: string, pagina = "mercado"): PendienteDeObra {
  return { carpeta, obra_id: 3, obra: "Galpón Norte", grupo: "precios", urgencia: "aviso", texto, accion: { texto: "Revisar precios", pagina } };
}
const sinPendientes = (pendientes: PendienteDeObra[] = []): PendientesDelMarco => ({
  estado: "listo",
  pendientes,
  carpetasOmitidas: 0,
  recargar: vi.fn(),
});

function Ubicacion() {
  return <output data-testid="ubicacion">{useLocation().pathname}</output>;
}

interface Opciones {
  ficha?: ObraAbierta["ficha"];
  sesion?: ReturnType<typeof sesionDe>;
  pendientes?: PendienteDeObra[];
  // Los módulos que la instalación apagó (plan vial, Tarea 19).
  apagados?: string[];
}

// La página sola, con la obra 3 de «Carpeta Norte.db» ya abierta (el marco la provee; aquí se arma el contexto a mano).
function montar({ ficha = { estado: "lista", obra: FILA }, sesion = sesionDe("ana"), pendientes = [], apagados }: Opciones = {}) {
  // La página no pide nada por su cuenta; si lo hiciera, recibiría una respuesta vacía y la prueba lo vería en el texto.
  pedirFalso.mockResolvedValue({ obras: [], pendientes: [], grupos: [] });
  const aplicacion: Aplicacion = { sesion, proyecto: "3", caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn(), modulosApagados: apagados };
  const abierta: ObraAbierta = { carpeta: NORTE, obraId: 3, ficha, recargarFicha: vi.fn() };
  return render(
    <MemoryRouter initialEntries={[rutaDeObra(NORTE, 3, "resumen")]}>
      <ContextoAplicacion.Provider value={aplicacion}>
        <ContextoPendientes.Provider value={sinPendientes(pendientes)}>
          <ContextoDeLaObra.Provider value={abierta}>
            <Routes>
              <Route path="*" element={<PaginaObras />} />
            </Routes>
            <Ubicacion />
          </ContextoDeLaObra.Provider>
        </ContextoPendientes.Provider>
      </ContextoAplicacion.Provider>
    </MemoryRouter>,
  );
}
const franja = () => screen.getByRole("region", { name: "Siguiente paso" });

describe("Resumen de la obra abierta", () => {
  afterEach(() => pedirFalso.mockReset());

  it("tiene un solo h1, «Resumen»", async () => {
    montar();
    expect(await screen.findAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1, name: "Resumen" })).toBeInTheDocument();
  });

  it("las cifras son las de esta obra, en es-VE y con la etapa en palabras", async () => {
    montar();
    await screen.findByRole("heading", { level: 1, name: "Resumen" });
    const cifras = screen.getByRole("group", { name: "Cifras de la obra" });
    expect(within(cifras).getByText("1.234.567,89 Bs")).toBeInTheDocument();
    expect(within(cifras).getByText("30,0 % de 37,5 %")).toBeInTheDocument();
    expect(within(cifras).getByText("002")).toBeInTheDocument();
    expect(within(cifras).getByText("En aprobación")).toBeInTheDocument();
    // Nada de otras obras ni de la mesa de toda la carpeta.
    expect(screen.queryByText("Puente Sur")).toBeNull();
    expect(screen.queryByRole("heading", { name: "Obras" })).toBeNull();
  });

  it("la cifra de versión se rotula exactamente «Versión (línea base o, sin ella, la vigente)» y no «Versión vigente»", async () => {
    montar();
    await screen.findByRole("heading", { level: 1, name: "Resumen" });
    const cifras = screen.getByRole("group", { name: "Cifras de la obra" });
    const rotulo = within(cifras).getByText("Versión (línea base o, sin ella, la vigente)", { selector: "dt" });
    expect(rotulo).toBeInTheDocument();
    expect(rotulo.nextElementSibling).toHaveTextContent("002");
    expect(within(cifras).queryByText("Versión vigente")).toBeNull();
  });

  it("lo que falta va en la franja y su único botón lleva a la sección", async () => {
    const u = userEvent.setup();
    montar();
    await screen.findByRole("heading", { level: 1, name: "Resumen" });
    expect(franja()).toHaveTextContent("Te falta: Faltan 2 precios");
    const boton = within(franja()).getByRole("button", { name: "Abrir el presupuesto" });
    await u.click(boton);
    expect(screen.getByTestId("ubicacion")).toHaveTextContent("/obra/Carpeta%20Norte.db/3/presupuesto");
  });

  it("una obra sin versiones dice «Te falta» (borrador en blanco)", async () => {
    montar({ ficha: { estado: "lista", obra: { ...FILA, version: null, total: null, que_pasa: "Sin partidas" } } });
    await screen.findByRole("heading", { level: 1, name: "Resumen" });
    expect(franja()).toHaveTextContent("Te falta: Sin partidas");
    expect(screen.getByText("Sin versión todavía")).toBeInTheDocument();
  });

  it("solo con siguiente paso, la franja dice «Siguiente paso:»", async () => {
    montar({ ficha: { estado: "lista", obra: { ...FILA, que_pasa: null } } });
    await screen.findByRole("heading", { level: 1, name: "Resumen" });
    expect(franja()).toHaveTextContent("Siguiente paso: Abrir el presupuesto");
  });

  it("sin «qué pasa» ni siguiente paso no hay franja", async () => {
    montar({ ficha: { estado: "lista", obra: { ...FILA, que_pasa: null, siguiente: null } } });
    await screen.findByRole("heading", { level: 1, name: "Resumen" });
    expect(screen.queryByRole("region", { name: "Siguiente paso" })).toBeNull();
  });

  it("muestra solo los pendientes de esta obra, no los de otra carpeta con el mismo número", async () => {
    montar({ pendientes: [pendiente(NORTE, "Precios viejos en Norte"), pendiente(SUR, "Precios viejos en Sur")] });
    const panel = await screen.findByRole("region", { name: "Pendientes de esta obra" });
    expect(within(panel).getByText("Precios viejos en Norte")).toBeInTheDocument();
    expect(within(panel).queryByText("Precios viejos en Sur")).toBeNull();
  });

  it("el botón de un pendiente navega a su destino", async () => {
    const u = userEvent.setup();
    montar({ pendientes: [pendiente(NORTE, "Precios viejos en Norte")] });
    await u.click(await screen.findByRole("button", { name: "Revisar precios" }));
    expect(screen.getByTestId("ubicacion")).toHaveTextContent("/obra/Carpeta%20Norte.db/3/mercado");
  });

  it("sin pendientes dice «Nada pendiente por ahora»", async () => {
    montar();
    expect(await screen.findByText("Nada pendiente por ahora")).toBeInTheDocument();
  });

  it("sin dato de la obra avisa y no pinta franja", async () => {
    montar({ ficha: { estado: "sin_dato" } });
    expect(await screen.findByText("No hay datos de esta obra todavía.")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Siguiente paso" })).toBeNull();
  });

  it("quien revisa ve el texto de la franja pero no el botón de una pantalla que no puede usar", async () => {
    montar({
      sesion: sesionDe("rita"),
      ficha: { estado: "lista", obra: { ...FILA, siguiente: { texto: "Registrar el avance", pagina: "control" } } },
    });
    await screen.findByRole("heading", { level: 1, name: "Resumen" });
    expect(franja()).toHaveTextContent("Te falta: Faltan 2 precios");
    expect(within(franja()).queryByRole("button")).toBeNull();
  });

  it("quien revisa sí tiene el botón hacia la Hoja: la ve en solo lectura (Tarea 2b)", async () => {
    const u = userEvent.setup();
    montar({ sesion: sesionDe("rita") });
    await u.click(await within(franja()).findByRole("button", { name: "Abrir el presupuesto" }));
    expect(screen.getByTestId("ubicacion")).toHaveTextContent("/obra/Carpeta%20Norte.db/3/presupuesto");
  });

  // F4, Tarea 11: el botón de la franja tampoco lleva a una pantalla cuyo módulo la instalación apagó (la API la cortaría).
  it("con el módulo de la pantalla apagado la franja solo informa; encendido, ofrece el botón", async () => {
    const tramos = { estado: "lista" as const, obra: { ...FILA, siguiente: { texto: "Ver los tramos", pagina: "tramos" } } };
    const { unmount } = montar({ ficha: tramos, apagados: ["vial"] });
    await screen.findByRole("heading", { level: 1, name: "Resumen" });
    expect(franja()).toHaveTextContent("Te falta: Faltan 2 precios");
    expect(within(franja()).queryByRole("button")).toBeNull();
    unmount();
    montar({ ficha: tramos, apagados: ["produccion"] });
    expect(await within(franja()).findByRole("button", { name: "Ver los tramos" })).toBeInTheDocument();
  });

  it("a lo sumo hay un botón principal", async () => {
    const { container } = montar({ pendientes: [pendiente(NORTE, "Precios viejos en Norte")] });
    await screen.findByRole("heading", { level: 1, name: "Resumen" });
    expect(container.querySelectorAll(".cds--btn--primary").length).toBeLessThanOrEqual(1);
  });

  it("ya no existen la mesa de todas las obras (bajas 1, 2, 5 y 6)", async () => {
    montar();
    await screen.findByRole("heading", { level: 1, name: "Resumen" });
    expect(screen.queryByRole("button", { name: "Nueva obra" })).toBeNull();
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.queryByText("Lo que puede hacer aquí")).toBeNull();
    expect(screen.queryByRole("button", { name: "Probar con datos de demostración" })).toBeNull();
    expect(screen.queryByText("Cree su primera obra")).toBeNull();
  });
});

// Foco de la tarea 1: la ficha se lee una vez por obra abierta y el Resumen la reutiliza (no lee `/v1/obras/resumen`
// por su cuenta). Se monta el espacio de la obra completo, con la carpeta de la empresa ya abierta.
describe("una lectura del resumen por obra abierta", () => {
  afterEach(() => pedirFalso.mockReset());

  const OBRAS: ObraDeCarpeta[] = [3, 4, 5].map((id) => ({
    carpeta: null,
    carpeta_titulo: "Carpeta de la empresa",
    obra_id: id,
    obra: ["Galpón Norte", "Puente Sur", "Depósito Este"][id - 3] ?? "",
    version_codigo: id === 3 ? "002" : null,
  }));

  it("el Resumen no vuelve a pedir `/v1/obras/resumen` y muestra solo su obra", async () => {
    const llamadas: string[] = [];
    pedirFalso.mockImplementation(async (ruta: string, opciones: { metodo?: string } = {}) => {
      const clave = `${opciones.metodo ?? "GET"} ${ruta}`;
      llamadas.push(clave);
      switch (clave) {
        case "GET /v1/obras/todas":
          return { carpeta_actual: null, obras: OBRAS };
        case "PUT /v1/sesion/proyecto":
          return undefined;
        case "GET /v1/obras/resumen":
          return { moneda: "Bs", hoy: "2026-10-31", obras: [FILA, ...OTRAS] };
      }
      throw new Error(`Ruta inesperada: ${clave}`);
    });
    const aplicacion: Aplicacion = { sesion: sesionDe("ana"), proyecto: "3", caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() };
    render(
      <MemoryRouter initialEntries={[rutaDeObra(null, 3, "resumen")]}>
        <ContextoAplicacion.Provider value={aplicacion}>
          <ContextoPendientes.Provider value={sinPendientes()}>
            <Routes>
              <Route
                path={PATRON_DE_OBRA}
                element={
                  <EspacioDeObra
                    obras={OBRAS}
                    casos={null}
                    alEntrar={() => undefined}
                    pantalla={() => <PaginaObras />}
                    vigilante={crearVigilante(null)}
                  />
                }
              />
            </Routes>
          </ContextoPendientes.Provider>
        </ContextoAplicacion.Provider>
      </MemoryRouter>,
    );
    await waitFor(() => expect(franja()).toHaveTextContent("Te falta: Faltan 2 precios"));
    expect(llamadas.filter((c) => c === "GET /v1/obras/resumen")).toHaveLength(1);
    expect(screen.queryByText("Puente Sur")).toBeNull();
    expect(screen.queryByText("Depósito Este")).toBeNull();
  });
});
