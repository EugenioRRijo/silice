import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaAdministracion from "./index";
import type { AccesosRespuesta, Cuenta, CuentasRespuesta } from "./logica";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const AVISO = "Esta cuenta podrá revisar paquetes que ella misma armó; la vista de revisión lo indicará.";
const SESION: SesionRespuesta = {
  login: "admin",
  nombre: "Admin Ficticio",
  roles: ["administrador"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["administrar_cuentas", "administrar_empresa"],
  modo_entrega: false,
  url_clasica: "http://127.0.0.1:8501",
};
const ADMIN: Cuenta = { id: 1, login: "admin", nombre: "Admin Ficticio", roles: ["administrador"], activa: true };
const ANA: Cuenta = { id: 2, login: "ana", nombre: "Ana", roles: ["arma"], activa: true };
const LUIS: Cuenta = { id: 3, login: "luis", nombre: "Luis", roles: ["revisa"], activa: false };
const TEMPORAL = "temporal ficticia 123";

describe("Administracion: Cuentas y Accesos", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let cuentas: Cuenta[];
  let accesos: AccesosRespuesta;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
    cuentas = [ADMIN, ANA, LUIS];
    accesos = {
      maximo: 200,
      eventos: [{ id: 5, fecha_hora: "2026-11-10 09:00:00", tipo: "fallo", usuario: "ana", ip: "10.0.0.7", detalle: "" }],
    };
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      if (url === "/v1/cuentas" && (init?.method ?? "GET") === "GET") {
        return json({ cuentas, aviso_arma_y_revisa: AVISO } satisfies CuentasRespuesta);
      }
      if (url === "/v1/accesos") return json(accesos);
      return json({ detalle: "no esperada" }, 500);
    });
  });
  afterEach(() => {
    fijarCsrf(null);
    vi.unstubAllGlobals();
  });

  function montar(sesion = SESION, alExpirar = vi.fn()) {
    const valor: Aplicacion = {
      sesion,
      proyecto: null,
      caso: null,
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    render(
      <ContextoAplicacion.Provider value={valor}>
        <PaginaAdministracion />
      </ContextoAplicacion.Provider>,
    );
    return alExpirar;
  }

  function cargada() {
    return screen.findByRole("table", { name: "Cuentas de la instalación" }, { timeout: 5000 });
  }

  function llamadas(metodo: string) {
    return fetchFalso.mock.calls.filter(([, init]) => init?.method === metodo);
  }

  test("muestra las siete pestanas y la tabla de cuentas con sus datos", async () => {
    montar();
    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual([
      "Cuentas",
      "Empresa y clave de firma",
      "Empresas registradas",
      "Claves de API",
      "Asistente de IA",
      "Accesos",
      "Instalación",
    ]);
    const tabla = await cargada();
    expect(within(tabla).getByText("luis")).toBeInTheDocument();
    expect(within(tabla).getAllByText("no")).toHaveLength(1);
  });

  test("las pestanas aun no migradas dicen «En la interfaz clásica» y enlazan a ella", async () => {
    montar();
    await userEvent.setup().click(screen.getByRole("tab", { name: "Claves de API" }));
    expect(await screen.findByText("En la interfaz clásica")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir la interfaz clásica" })).toHaveAttribute(
      "href",
      "http://127.0.0.1:8501/administracion",
    );
  });

  test("sin la accion administrar_cuentas no se ofrece nada", () => {
    montar({ ...SESION, acciones: [] });
    expect(screen.queryByRole("tab")).toBeNull();
    expect(screen.getByText("Su cuenta no tiene permiso para administrar la instalación.")).toBeInTheDocument();
  });

  test("crear una cuenta manda el cuerpo, vacia la contrasena y no la deja en la pagina", async () => {
    montar();
    const usuario = userEvent.setup();
    await cargada();
    fetchFalso.mockImplementation(async (_ruta, init) => {
      if (init?.method === "POST") {
        cuentas = [...cuentas, { id: 4, login: "rita", nombre: "Rita", roles: ["arma", "revisa"], activa: true }];
        return json(
          { cuenta: cuentas[3], mensaje: "Cuenta creada. La persona deberá cambiar la contraseña al entrar.", aviso: AVISO },
          201,
        );
      }
      return json({ cuentas, aviso_arma_y_revisa: AVISO });
    });
    await usuario.type(screen.getByLabelText("Usuario (minúsculas, sin espacios)"), "rita");
    await usuario.type(screen.getByLabelText("Nombre de la persona"), "Rita");
    await usuario.click(screen.getByLabelText("arma presupuestos (arma)", { selector: "#adm-roles-arma" }));
    await usuario.click(screen.getByLabelText("revisa paquetes (revisa)", { selector: "#adm-roles-revisa" }));
    expect(screen.getAllByText(AVISO).length).toBeGreaterThan(0);
    await usuario.type(screen.getByLabelText(/Contraseña temporal \(10 a 128/), TEMPORAL);
    await usuario.click(screen.getByRole("button", { name: "Crear la cuenta" }));

    await waitFor(() => expect(llamadas("POST")).toHaveLength(1));
    const [ruta, init] = llamadas("POST")[0];
    expect(ruta).toBe("/v1/cuentas");
    expect(JSON.parse(String(init?.body))).toEqual({
      login: "rita",
      nombre: "Rita",
      roles: ["arma", "revisa"],
      contrasena_temporal: TEMPORAL,
    });
    expect(new Headers(init?.headers).get("X-Silice-CSRF")).toBe("tok");
    expect(await screen.findByText("Cuenta creada. La persona deberá cambiar la contraseña al entrar.")).toBeInTheDocument();
    expect(screen.getByLabelText(/Contraseña temporal \(10 a 128/)).toHaveValue("");
    expect(document.body.innerHTML).not.toContain(TEMPORAL);
  });

  test("un error de la API se muestra con su mensaje y la contrasena igual se vacia", async () => {
    montar();
    const usuario = userEvent.setup();
    await cargada();
    fetchFalso.mockImplementation(async (_r, init) =>
      init?.method === "POST"
        ? json({ detalle: "La contraseña debe tener al menos 10 caracteres." }, 422)
        : json({ cuentas, aviso_arma_y_revisa: AVISO }),
    );
    await usuario.type(screen.getByLabelText(/Contraseña temporal \(10 a 128/), "corta");
    await usuario.click(screen.getByRole("button", { name: "Crear la cuenta" }));
    expect(await screen.findByText("La contraseña debe tener al menos 10 caracteres.")).toBeInTheDocument();
    expect(screen.getByLabelText(/Contraseña temporal \(10 a 128/)).toHaveValue("");
  });

  test("desactivar pide confirmacion y solo entonces llama a la API", async () => {
    montar();
    const usuario = userEvent.setup();
    await cargada();
    await usuario.selectOptions(screen.getByLabelText("Cuenta"), "2");
    fetchFalso.mockImplementation(async (_r, init) =>
      init?.method === "POST"
        ? json({ cuenta: { ...ANA, activa: false }, mensaje: "Cuenta desactivada; sus registros se conservan.", aviso: null })
        : json({ cuentas, aviso_arma_y_revisa: AVISO }),
    );
    await usuario.click(screen.getByRole("button", { name: "Desactivar" }));
    expect(llamadas("POST")).toHaveLength(0);
    expect(await screen.findByText(/La cuenta «ana» no podrá entrar/)).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(llamadas("POST")).toHaveLength(0);

    await usuario.click(screen.getByRole("button", { name: "Desactivar" }));
    const dialogo = await screen.findByRole("alertdialog");
    await usuario.click(within(dialogo).getByRole("button", { name: "Desactivar" }));
    await waitFor(() => expect(llamadas("POST")).toHaveLength(1));
    expect(llamadas("POST")[0][0]).toBe("/v1/cuentas/2/desactivar");
    expect(await screen.findByText("Cuenta desactivada; sus registros se conservan.")).toBeInTheDocument();
  });

  test("una cuenta desactivada ofrece Reactivar, sin confirmacion", async () => {
    montar();
    const usuario = userEvent.setup();
    await cargada();
    await usuario.selectOptions(screen.getByLabelText("Cuenta"), "3");
    fetchFalso.mockImplementation(async (_r, init) =>
      init?.method === "POST"
        ? json({ cuenta: { ...LUIS, activa: true }, mensaje: "Cuenta reactivada.", aviso: null })
        : json({ cuentas, aviso_arma_y_revisa: AVISO }),
    );
    await usuario.click(screen.getByRole("button", { name: "Reactivar" }));
    await waitFor(() => expect(llamadas("POST")[0][0]).toBe("/v1/cuentas/3/reactivar"));
  });

  test("restablecer confirma, manda la contrasena solo en el cuerpo y la vacia", async () => {
    montar();
    const usuario = userEvent.setup();
    await cargada();
    await usuario.selectOptions(screen.getByLabelText("Cuenta"), "2");
    fetchFalso.mockImplementation(async (_r, init) =>
      init?.method === "POST"
        ? json({ cuenta: ANA, mensaje: "Contraseña restablecida; sus sesiones se cerraron.", aviso: null })
        : json({ cuentas, aviso_arma_y_revisa: AVISO }),
    );
    await usuario.type(screen.getByLabelText("Contraseña temporal nueva"), TEMPORAL);
    await usuario.click(screen.getByRole("button", { name: "Restablecer la contraseña" }));
    expect(llamadas("POST")).toHaveLength(0);
    const dialogo = await screen.findByRole("alertdialog");
    await usuario.click(within(dialogo).getByRole("button", { name: "Restablecer" }));
    await waitFor(() => expect(llamadas("POST")).toHaveLength(1));
    const [ruta, init] = llamadas("POST")[0];
    expect(ruta).toBe("/v1/cuentas/2/restablecer");
    expect(JSON.parse(String(init?.body))).toEqual({ contrasena_temporal: TEMPORAL });
    expect(await screen.findByText("Contraseña restablecida; sus sesiones se cerraron.")).toBeInTheDocument();
    expect(screen.getByLabelText("Contraseña temporal nueva")).toHaveValue("");
    expect(document.body.innerHTML).not.toContain(TEMPORAL);
  });

  test("guardar roles y desbloquear llaman a su ruta", async () => {
    montar();
    const usuario = userEvent.setup();
    await cargada();
    await usuario.selectOptions(screen.getByLabelText("Cuenta"), "2");
    fetchFalso.mockImplementation(async (_r, init) =>
      init?.method === "POST"
        ? json({ cuenta: ANA, mensaje: "ok", aviso: null })
        : json({ cuentas, aviso_arma_y_revisa: AVISO }),
    );
    await usuario.click(screen.getByLabelText("revisa paquetes (revisa)", { selector: "#adm-roles-de-revisa" }));
    await usuario.click(screen.getByRole("button", { name: "Guardar roles" }));
    await waitFor(() => expect(llamadas("POST")).toHaveLength(1));
    expect(llamadas("POST")[0][0]).toBe("/v1/cuentas/2/roles");
    expect(JSON.parse(String(llamadas("POST")[0][1]?.body))).toEqual({ roles: ["arma", "revisa"] });
    await usuario.click(screen.getByRole("button", { name: "Desbloquear" }));
    await waitFor(() => expect(llamadas("POST")).toHaveLength(2));
    expect(llamadas("POST")[1][0]).toBe("/v1/cuentas/2/desbloquear");
  });

  test("un 401 llama a alExpirar", async () => {
    fetchFalso.mockImplementation(async () => json({ detalle: "Sesión ausente o vencida: entre de nuevo con su cuenta." }, 401));
    const alExpirar = montar();
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("Accesos muestra la nota, los eventos y no ofrece ninguna escritura", async () => {
    montar();
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("tab", { name: "Accesos" }));
    expect(
      await screen.findByText("Los 200 últimos eventos de acceso; este registro solo se agrega, no se edita."),
    ).toBeInTheDocument();
    const tabla = await screen.findByRole("table", { name: "Eventos de acceso" }, { timeout: 5000 });
    expect(within(tabla).getByText("2026-11-10 09:00:00")).toBeInTheDocument();
    expect(within(tabla).getByText("10.0.0.7")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Crear|Guardar|Desactivar|Reactivar|Desbloquear|Restablecer/ })).toBeNull();
    expect(llamadas("POST")).toHaveLength(0);
  });
});
