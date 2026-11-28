import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ProveedorDeAnuncios } from "../../comun/Anunciador";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import Cuentas from "./Cuentas";
import type { Cuenta, CuentasRespuesta } from "./logica";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { "Content-Type": "application/json" },
  });
}

interface SolicitudDePrueba {
  id: number;
  nombre: string;
  login: string;
  correo: string;
  creada: string;
  estado: "pendiente" | "aprobada" | "rechazada" | "usada" | "vencida";
  papel: string | null;
  vence: string | null;
}

const SESION: SesionRespuesta = {
  login: "admin",
  nombre: "Admin Ficticio",
  roles: ["administrador"],
  csrf: "tok-csrf",
  debe_cambiar_clave: false,
  acciones: ["administrar_cuentas"],
  modo_entrega: false,
};

const ADMIN: Cuenta = {
  id: 1,
  login: "admin",
  nombre: "Admin Ficticio",
  roles: ["administrador"],
  activa: true,
};

const CODIGO_UNICO = "BCDE-FGHJ-KLMN-PQRS-TUVW";
const MAILTO_SERVIDOR =
  "mailto:maria@empresa.com?subject=Su%20c%C3%B3digo%20para%20entrar%20en%20S%C3%ADlice&body=Hola%2C%20Mar%C3%ADa";

function crearSolicitudesBase(): SolicitudDePrueba[] {
  return [
    {
      id: 10,
      nombre: "María Rivas",
      login: "mrivas",
      correo: "maria@empresa.com",
      creada: "2026-11-26T09:15:00",
      estado: "pendiente",
      papel: null,
      vence: null,
    },
    {
      id: 11,
      nombre: "Carlos Méndez",
      login: "cmendez",
      correo: "carlos@empresa.com",
      creada: "2026-11-18T11:00:00",
      estado: "vencida",
      papel: "revisa",
      vence: "2026-11-25T11:00:00",
    },
    {
      id: 12,
      nombre: "Elena Soto",
      login: "esoto",
      correo: "elena@empresa.com",
      creada: "2026-11-24T15:00:00",
      estado: "aprobada",
      papel: "arma",
      vence: "2026-12-01T15:00:00",
    },
    {
      id: 13,
      nombre: "Pedro Lara",
      login: "plara",
      correo: "pedro@empresa.com",
      creada: "2026-11-20T08:30:00",
      estado: "rechazada",
      papel: null,
      vence: null,
    },
    {
      id: 14,
      nombre: "Lucía Vega",
      login: "lvega",
      correo: "lucia@empresa.com",
      creada: "2026-11-15T10:45:00",
      estado: "usada",
      papel: "revisa",
      vence: "2026-11-22T10:45:00",
    },
  ];
}

describe("Cuentas: sección Solicitudes (C9)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let solicitudes: SolicitudDePrueba[];
  let cuentas: Cuenta[];

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok-csrf");
    solicitudes = crearSolicitudesBase();
    cuentas = [ADMIN];
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = String(entrada);
      const metodo = init?.method ?? "GET";
      if (url === "/v1/cuentas" && metodo === "GET") {
        return json({ cuentas, aviso_arma_y_revisa: "Aviso de roles." } satisfies CuentasRespuesta);
      }
      if (url === "/v1/solicitudes" && metodo === "GET") {
        return json({ solicitudes });
      }
      if (url === "/v1/solicitudes/10/aprobar" && metodo === "POST") {
        const cuerpo = JSON.parse(String(init?.body ?? "{}")) as { papel: string };
        solicitudes = solicitudes.map((s) =>
          s.id === 10 ? { ...s, estado: "aprobada", papel: cuerpo.papel, vence: "2026-12-03T14:30:00" } : s,
        );
        return json({ codigo: CODIGO_UNICO, vence: "2026-12-03T14:30:00", mailto: MAILTO_SERVIDOR });
      }
      if (url === "/v1/solicitudes/11/aprobar" && metodo === "POST") {
        const cuerpo = JSON.parse(String(init?.body ?? "{}")) as { papel: string };
        solicitudes = solicitudes.map((s) =>
          s.id === 11 ? { ...s, estado: "aprobada", papel: cuerpo.papel, vence: "2026-12-03T16:00:00" } : s,
        );
        return json({ codigo: CODIGO_UNICO, vence: "2026-12-03T16:00:00", mailto: MAILTO_SERVIDOR });
      }
      if (url === "/v1/solicitudes/12/aprobar" && metodo === "POST") {
        const cuerpo = JSON.parse(String(init?.body ?? "{}")) as { papel: string };
        solicitudes = solicitudes.map((s) => (s.id === 12 ? { ...s, papel: cuerpo.papel, vence: "2026-12-05T09:00:00" } : s));
        return json({ codigo: CODIGO_UNICO, vence: "2026-12-05T09:00:00", mailto: MAILTO_SERVIDOR });
      }
      if (url === "/v1/solicitudes/10/rechazar" && metodo === "POST") {
        solicitudes = solicitudes.map((s) => (s.id === 10 ? { ...s, estado: "rechazada" } : s));
        return json({ mensaje: "Solicitud rechazada." });
      }
      return json({ detalle: "Ruta no esperada." }, 500);
    });
  });

  afterEach(() => {
    fijarCsrf(null);
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  function montar() {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: null,
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    return render(
      <MemoryRouter>
        <ProveedorDeAnuncios>
          <ContextoAplicacion.Provider value={valor}>
            <Cuentas />
          </ContextoAplicacion.Provider>
        </ProveedorDeAnuncios>
      </MemoryRouter>,
    );
  }

  test("sin solicitudes no muestra la sección «Solicitudes»", async () => {
    solicitudes = [];
    montar();
    await screen.findByRole("table", { name: "Cuentas de la instalación" });
    expect(screen.queryByRole("heading", { level: 2, name: "Solicitudes" })).toBeNull();
    expect(screen.queryByRole("table", { name: "Solicitudes de cuenta" })).toBeNull();
  });

  test("muestra «Solicitudes» arriba de «Cuentas», fechas dd/mm/aaaa, los 5 estados en palabras y acciones solo en pendiente o vencida", async () => {
    montar();
    const tablaSolicitudes = await screen.findByRole("table", { name: "Solicitudes de cuenta" });
    const h2Solicitudes = screen.getByRole("heading", { level: 2, name: "Solicitudes" });
    const h2Cuentas = screen.getByRole("heading", { level: 2, name: "Cuentas" });
    expect(h2Solicitudes.compareDocumentPosition(h2Cuentas) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    for (const cabecera of ["Nombre", "Usuario", "Correo", "Fecha", "Estado"]) {
      expect(within(tablaSolicitudes).getByRole("columnheader", { name: new RegExp(cabecera) })).toBeInTheDocument();
    }

    expect(within(tablaSolicitudes).getByText("26/11/2026")).toBeInTheDocument();
    expect(within(tablaSolicitudes).getByText("18/11/2026")).toBeInTheDocument();
    for (const estadoEnPalabras of ["Pendiente", "Vencida", "Aprobada", "Rechazada", "Usada"]) {
      expect(within(tablaSolicitudes).getByText(estadoEnPalabras)).toBeInTheDocument();
    }

    const filas = within(tablaSolicitudes).getAllByRole("row").slice(1);
    expect(filas).toHaveLength(5);

    // Filas pendiente (mrivas), vencida (cmendez) y aprobada (esoto): tienen selector de papel, aprobar y rechazar.
    // La aprobada se puede volver a aprobar (código nuevo, el anterior deja de valer) o rechazar: el servidor lo admite
    // (`RESOLUBLES` en seguridad/solicitudes.py) y sin esto, quien cerró el diálogo sin copiar el código no tenía salida.
    for (const login of ["mrivas", "cmendez", "esoto"]) {
      const fila = filas.find((f) => within(f).queryByText(login) !== null)!;
      const selector = within(fila).getByRole("combobox", { name: "Papel" });
      expect(within(selector).getByRole("option", { name: "Arma presupuestos" })).toBeInTheDocument();
      expect(within(selector).getByRole("option", { name: "Revisa" })).toBeInTheDocument();
      expect(within(fila).getByRole("button", { name: "Aprobar y generar el código" })).toBeInTheDocument();
      expect(within(fila).getByRole("button", { name: "Rechazar" })).toBeInTheDocument();
    }

    // Filas rechazada y usada: no ofrecen aprobar ni rechazar (el servidor responde 409).
    for (const login of ["plara", "lvega"]) {
      const fila = filas.find((f) => within(f).queryByText(login) !== null)!;
      expect(within(fila).queryByRole("button", { name: "Aprobar y generar el código" })).toBeNull();
      expect(within(fila).queryByRole("button", { name: "Rechazar" })).toBeNull();
      expect(within(fila).queryByRole("combobox")).toBeNull();
    }
  });

  test("aprobar envía el papel elegido, muestra el código una vez con vencimiento y mailto exacto, copia y al cerrar borra el código del DOM", async () => {
    const usuario = userEvent.setup();
    montar();
    const tabla = await screen.findByRole("table", { name: "Solicitudes de cuenta" });
    const filaMaria = within(tabla)
      .getAllByRole("row")
      .find((f) => within(f).queryByText("mrivas") !== null)!;

    await usuario.selectOptions(within(filaMaria).getByRole("combobox", { name: "Papel" }), "revisa");
    await usuario.click(within(filaMaria).getByRole("button", { name: "Aprobar y generar el código" }));

    const dialogo = await screen.findByRole("dialog", { name: /Código/ });
    const botonCopiar = within(dialogo).getByRole("button", { name: "Copiar el código" });
    expect(botonCopiar).toHaveFocus();

    const llamada = fetchFalso.mock.calls.find(([r]) => String(r) === "/v1/solicitudes/10/aprobar");
    expect(llamada).toBeDefined();
    expect(JSON.parse(String(llamada?.[1]?.body))).toEqual({ papel: "revisa" });
    expect(new Headers(llamada?.[1]?.headers).get("X-Silice-CSRF")).toBe("tok-csrf");

    expect(within(dialogo).getByText(CODIGO_UNICO)).toBeInTheDocument();
    expect(within(dialogo).getByText(/03\/12\/2026/)).toBeInTheDocument();
    expect(within(dialogo).getByText(/Este código no se vuelve a mostrar/)).toBeInTheDocument();

    const enlaceCorreo = within(dialogo).getByRole("link", { name: "Enviarlo por correo" });
    expect(enlaceCorreo).toHaveAttribute("href", MAILTO_SERVIDOR);

    await usuario.click(botonCopiar);
    expect(await navigator.clipboard.readText()).toBe(CODIGO_UNICO);

    await usuario.click(within(dialogo).getByRole("button", { name: "Cerrar" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(document.body.textContent).not.toContain(CODIGO_UNICO);
    expect(document.body.innerHTML).not.toContain(CODIGO_UNICO);
    expect(document.body.innerHTML).not.toContain(MAILTO_SERVIDOR);
  });

  test("una solicitud ya aprobada se vuelve a aprobar: código nuevo con el papel de la fila, sin cambiar de estado", async () => {
    const usuario = userEvent.setup();
    montar();
    const tabla = await screen.findByRole("table", { name: "Solicitudes de cuenta" });
    const fila = within(tabla)
      .getAllByRole("row")
      .find((f) => within(f).queryByText("esoto") !== null)!;
    // El papel que ya tenía la aprobación viene elegido en la lista.
    expect(within(fila).getByRole("combobox", { name: "Papel" })).toHaveValue("arma");

    await usuario.click(within(fila).getByRole("button", { name: "Aprobar y generar el código" }));

    const dialogo = await screen.findByRole("dialog", { name: /Código/ });
    const llamada = fetchFalso.mock.calls.find(([r]) => String(r) === "/v1/solicitudes/12/aprobar");
    expect(JSON.parse(String(llamada?.[1]?.body))).toEqual({ papel: "arma" });
    expect(within(dialogo).getByText(CODIGO_UNICO)).toBeInTheDocument();
    expect(within(dialogo).getByText(/05\/12\/2026/)).toBeInTheDocument();
  });

  test("«Rechazar» en una solicitud aprobada abre el mismo diálogo y rechaza (el código sin usar deja de valer)", async () => {
    const usuario = userEvent.setup();
    montar();
    const tabla = await screen.findByRole("table", { name: "Solicitudes de cuenta" });
    const fila = within(tabla)
      .getAllByRole("row")
      .find((f) => within(f).queryByText("esoto") !== null)!;
    await usuario.click(within(fila).getByRole("button", { name: "Rechazar" }));
    const dialogo = await screen.findByRole("dialog", { name: "Rechazar la solicitud" });
    expect(dialogo).toHaveTextContent("esoto");
    expect(dialogo).toHaveTextContent("dejará de valer");
  });

  test("si falla navigator.clipboard muestra un aviso con su palabra, y Escape cierra el diálogo borrando el código del DOM", async () => {
    const usuario = userEvent.setup();
    montar();
    const tabla = await screen.findByRole("table", { name: "Solicitudes de cuenta" });
    const filaVencida = within(tabla)
      .getAllByRole("row")
      .find((f) => within(f).queryByText("cmendez") !== null)!;

    await usuario.click(within(filaVencida).getByRole("button", { name: "Aprobar y generar el código" }));

    const dialogo = await screen.findByRole("dialog", { name: /Código/ });
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValueOnce(new Error("Permiso denegado"));
    await usuario.click(within(dialogo).getByRole("button", { name: "Copiar el código" }));
    expect(await within(dialogo).findByRole("alert")).toHaveTextContent(/Advertencia.*no se pudo copiar el código/i);

    await usuario.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(document.body.innerHTML).not.toContain(CODIGO_UNICO);
  });

  test("«Rechazar» abre un Dialogo destructivo con foco en «Cancelar», Esc devuelve el foco al botón, y confirmar rechaza", async () => {
    const usuario = userEvent.setup();
    montar();
    const tabla = await screen.findByRole("table", { name: "Solicitudes de cuenta" });
    const filaMaria = within(tabla)
      .getAllByRole("row")
      .find((f) => within(f).queryByText("mrivas") !== null)!;
    const botonRechazar = within(filaMaria).getByRole("button", { name: "Rechazar" });

    await usuario.click(botonRechazar);
    const dialogo = await screen.findByRole("dialog", { name: "Rechazar la solicitud" });
    expect(dialogo).toHaveClass("silice-dialogo--destructivo");
    expect(within(dialogo).getByRole("button", { name: "Cancelar" })).toHaveFocus();
    expect(fetchFalso.mock.calls.some(([r]) => String(r).endsWith("/rechazar"))).toBe(false);

    await usuario.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(botonRechazar).toHaveFocus();
    expect(fetchFalso.mock.calls.some(([r]) => String(r).endsWith("/rechazar"))).toBe(false);

    await usuario.click(botonRechazar);
    const dialogoReabierto = await screen.findByRole("dialog", { name: "Rechazar la solicitud" });
    await usuario.click(within(dialogoReabierto).getByRole("button", { name: "Rechazar la solicitud" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    const llamada = fetchFalso.mock.calls.find(([r]) => String(r) === "/v1/solicitudes/10/rechazar");
    expect(llamada).toBeDefined();
    expect(await screen.findByText("Solicitud rechazada.")).toBeInTheDocument();
    // La lista se recargó bien: no hay nota de que no se pudo recargar.
    expect(screen.queryByText(/no se pudo recargar la lista de solicitudes/)).toBeNull();
  });

  // T4 (mutante CU4): si el rechazo se hizo pero la lista no se pudo volver a leer, la nota lo dice.
  test("si tras rechazar no se puede recargar la lista de solicitudes, lo dice junto al mensaje", async () => {
    const usuario = userEvent.setup();
    montar();
    const tabla = await screen.findByRole("table", { name: "Solicitudes de cuenta" });
    const filaMaria = within(tabla)
      .getAllByRole("row")
      .find((f) => within(f).queryByText("mrivas") !== null)!;
    const sinRecarga = fetchFalso.getMockImplementation()!;
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = String(entrada);
      if (url === "/v1/solicitudes" && (init?.method ?? "GET") === "GET") return json({ detalle: "Sin red." }, 500);
      return sinRecarga(entrada, init);
    });

    await usuario.click(within(filaMaria).getByRole("button", { name: "Rechazar" }));
    const dialogo = await screen.findByRole("dialog", { name: "Rechazar la solicitud" });
    await usuario.click(within(dialogo).getByRole("button", { name: "Rechazar la solicitud" }));

    expect(await screen.findByText("Solicitud rechazada.")).toBeInTheDocument();
    expect(screen.getByText("La solicitud se rechazó, pero no se pudo recargar la lista de solicitudes.")).toBeInTheDocument();
  });
});
