import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Link, MemoryRouter, Route, Routes } from "react-router";
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
const AVISO_DE_TEMA = "El texto de la barra superior no se lee bien sobre el color del marco: 4,4:1, hace falta 4,5:1";
const SESION: SesionRespuesta = {
  login: "admin",
  nombre: "Admin Ficticio",
  roles: ["administrador"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["administrar_cuentas", "administrar_empresa"],
  modo_entrega: false,
};
const ADMIN: Cuenta = { id: 1, login: "admin", nombre: "Admin Ficticio", roles: ["administrador"], activa: true };
const ANA: Cuenta = { id: 2, login: "ana", nombre: "Ana", roles: ["arma"], activa: true };
const LUIS: Cuenta = { id: 3, login: "luis", nombre: "Luis", roles: ["revisa"], activa: false };
const TEMPORAL = "temporal ficticia 123";
const PIDE = { timeout: 5000 };

// F6, T6: «Administración» ya no es una pantalla con pestañas: cada sección de la Cuenta (/cuenta/:seccion) monta lo suyo.
// El marco pone el h1 y la barra de secciones; aquí se prueba el contenido. Los enlaces de prueba hacen de barra.
function EnLaCuenta({ seccion, children }: { seccion: string; children: React.ReactNode }) {
  return (
    <MemoryRouter initialEntries={[`/cuenta/${seccion}`]}>
      <nav aria-label="Ir a otra sección">
        {["cuentas", "empresa", "carpetas", "sistema"].map((s) => (
          <Link key={s} to={`/cuenta/${s}`}>{`Ir a ${s}`}</Link>
        ))}
      </nav>
      <Routes>
        <Route path="/cuenta/:seccion" element={children} />
      </Routes>
    </MemoryRouter>
  );
}
const ASISTENTE_DE_FABRICA = {
  activo: false,
  proveedor: "claude",
  proveedores: [{ valor: "claude", etiqueta: "Claude (en la nube, con la clave de la empresa)" }],
  modelo_claude: "claude-opus-5-5",
  modelo_local: "",
  anfitrion_ollama: "http://127.0.0.1:11434",
  tope_usd: "2",
  clave_registrada: null,
  clave_guardada: false,
  pide_contrasena: false,
  falta_el_componente: null,
  aviso_de_nube: "Aviso de nube ficticio.",
  sensible: { permitida: true, motivo: "" },
};

describe("Administracion: Cuentas y Accesos", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let cuentas: Cuenta[];
  let accesos: AccesosRespuesta;
  // Lo que contesta la API a un POST y si el GET de cuentas falla (para la recarga tras una accion).
  let alPost: (ruta: string, cuerpo: unknown) => Response | Promise<Response>;
  let fallaElGet: boolean;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
    cuentas = [ADMIN, ANA, LUIS];
    fallaElGet = false;
    alPost = () => json({ cuenta: ANA, mensaje: "ok", aviso: null });
    accesos = {
      maximo: 200,
      eventos: [{ id: 5, fecha_hora: "2026-11-10 09:00:00", tipo: "fallo", usuario: "ana", ip: "10.0.0.7", detalle: "" }],
    };
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      const metodo = init?.method ?? "GET";
      if (metodo === "POST") return alPost(url, JSON.parse(String(init?.body ?? "{}")));
      if (url === "/v1/cuentas") {
        return fallaElGet
          ? json({ detalle: "La base no responde." }, 503)
          : json({ cuentas, aviso_arma_y_revisa: AVISO } satisfies CuentasRespuesta);
      }
      if (url === "/v1/accesos") return json(accesos);
      if (url === "/v1/admin/empresas-registradas") return json({ registradas: [], metodos: [] });
      if (url === "/v1/admin/asistente") return json(ASISTENTE_DE_FABRICA);
      if (url === "/v1/tema") return json({ acento: null, marco: "#777777", lateral: null, tiene_logo: false, avisos: [AVISO_DE_TEMA] });
      return json({ detalle: "no esperada" }, 500);
    });
  });
  afterEach(() => {
    fijarCsrf(null);
    vi.unstubAllGlobals();
  });

  function montar(sesion = SESION, alExpirar = vi.fn(), seccion = "cuentas") {
    const valor: Aplicacion = { sesion, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar };
    const vista = render(
      <ContextoAplicacion.Provider value={valor}>
        <EnLaCuenta seccion={seccion}>
          <PaginaAdministracion />
        </EnLaCuenta>
      </ContextoAplicacion.Provider>,
    );
    return { alExpirar, ...vista };
  }

  const cargada = () => screen.findByRole("table", { name: "Cuentas de la instalación" }, PIDE);
  const posts = () => fetchFalso.mock.calls.filter(([, init]) => init?.method === "POST");
  const resultado = () => screen.getByRole("group", { name: "Resultado de la última acción" });

  async function elegir(login: string) {
    const usuario = userEvent.setup();
    await cargada();
    const id = { admin: "1", ana: "2", luis: "3" }[login]!;
    await usuario.selectOptions(screen.getByLabelText("Cuenta que va a cambiar"), id);
    return usuario;
  }

  test("«cuentas» apila Cuentas y Accesos, sin pestañas, con la tabla de cuentas y sus datos", async () => {
    montar();
    expect(screen.queryAllByRole("tab")).toHaveLength(0);
    const tabla = await cargada();
    expect(within(tabla).getByText("luis")).toBeInTheDocument();
    expect(within(tabla).getAllByText("no")).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 2, name: "Cuentas" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 2, name: "Accesos" }, PIDE)).toBeInTheDocument();
    expect(await screen.findByRole("table", { name: "Eventos de acceso" }, PIDE)).toBeInTheDocument();
    // El h1 y la barra son del marco; el contenido no pone otro.
    expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
  });

  test("«cuentas» no monta lo de las otras secciones: ni la empresa, ni el asistente", async () => {
    montar();
    await cargada();
    expect(fetchFalso.mock.calls.map(([r]) => String(r))).not.toContain("/v1/admin/empresas-registradas");
    expect(fetchFalso.mock.calls.map(([r]) => String(r))).not.toContain("/v1/admin/asistente");
  });

  test("«Especialidades», en «sistema», solo la tiene quien puede activar módulos (plan vial, Tarea 19)", async () => {
    montar(SESION, vi.fn(), "sistema");
    expect(await screen.findByLabelText("Activar el asistente de IA (viene apagado)", {}, PIDE)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 2, name: "Especialidades" })).toBeNull();
    cleanup();
    montar({ ...SESION, acciones: [...SESION.acciones, "activar_modulos"] }, vi.fn(), "sistema");
    expect(await screen.findByRole("heading", { level: 2, name: "Especialidades" })).toBeInTheDocument();
  });

  test("«sistema» trae Asistente de IA, Claves de API e Instalación, en ese orden, cada una con su título", async () => {
    montar({ ...SESION, acciones: [...SESION.acciones, "activar_modulos"] }, vi.fn(), "sistema");
    await screen.findByRole("heading", { level: 2, name: "Especialidades" });
    const titulos = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(titulos.indexOf("Especialidades")).toBeLessThan(titulos.indexOf("Claves de API"));
    expect(titulos).toContain("Claves de API");
    expect(titulos.indexOf("Configuración del asistente")).toBeLessThan(titulos.indexOf("Claves de API"));
  });

  test("ninguna sección lleva la marca «clásica»", async () => {
    for (const seccion of ["cuentas", "empresa", "carpetas", "sistema"]) {
      const vista = montar({ ...SESION, acciones: [...SESION.acciones, "cambiar_caso"] }, vi.fn(), seccion);
      await new Promise((r) => setTimeout(r, 20));
      expect(document.body.textContent, seccion).not.toMatch(/clásica/);
      vista.unmount();
    }
  });

  test("«empresa» trae Empresas registradas, que pide sus datos a la API", async () => {
    montar(SESION, vi.fn(), "empresa");
    expect(await screen.findByText("Todavía no hay empresas registradas", {}, PIDE)).toBeInTheDocument();
    expect(fetchFalso.mock.calls.map(([r]) => String(r))).toContain("/v1/admin/empresas-registradas");
    expect(screen.queryByText("En la interfaz clásica")).toBeNull();
  });

  test("los avisos de contraste del tema salen en «empresa» y no en «cuentas»", async () => {
    montar();
    await cargada();
    expect(screen.queryByText(AVISO_DE_TEMA)).toBeNull();
    cleanup();
    montar(SESION, vi.fn(), "empresa");
    expect(await screen.findByText(AVISO_DE_TEMA, {}, PIDE)).toBeInTheDocument();
  });

  test("«sistema» trae el Asistente de IA, que pide su estado a la API", async () => {
    montar(SESION, vi.fn(), "sistema");
    expect(await screen.findByLabelText("Activar el asistente de IA (viene apagado)", {}, PIDE)).toBeInTheDocument();
    expect(fetchFalso.mock.calls.map(([r]) => String(r))).toContain("/v1/admin/asistente");
    expect(screen.queryByText("En la interfaz clásica")).toBeNull();
  });

  test("sin la accion administrar_cuentas no se ofrece nada (también aquí, aunque el marco ya lo filtra)", () => {
    montar({ ...SESION, acciones: [] });
    expect(screen.queryByRole("tab")).toBeNull();
    expect(screen.getByText("Su cuenta no tiene permiso para administrar la instalación.")).toBeInTheDocument();
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("una sección que no es de administración (preferencias, ayuda o una que no existe) no monta nada", () => {
    for (const seccion of ["preferencias", "ayuda", "xyz"]) {
      const vista = montar(SESION, vi.fn(), seccion);
      expect(vista.container.querySelector(".silice-adm")?.textContent ?? "", seccion).toBe("");
      vista.unmount();
    }
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  describe("crear una cuenta", () => {
    async function llenar(usuario: ReturnType<typeof userEvent.setup>, clave = TEMPORAL) {
      await usuario.type(screen.getByLabelText("Usuario"), "rita");
      await usuario.type(screen.getByLabelText("Nombre de la persona"), "Rita");
      await usuario.type(screen.getByLabelText("Contraseña temporal"), clave);
    }

    test("el boton espera usuario, nombre y una contrasena de 10 a 128 caracteres", async () => {
      montar();
      const usuario = userEvent.setup();
      await cargada();
      const boton = screen.getByRole("button", { name: "Crear la cuenta" });
      expect(boton).toBeDisabled();
      await usuario.type(screen.getByLabelText("Usuario"), "rita");
      await usuario.type(screen.getByLabelText("Nombre de la persona"), "Rita");
      await usuario.type(screen.getByLabelText("Contraseña temporal"), "corta");
      expect(boton).toBeDisabled();
      expect(screen.getByText("La contraseña debe tener entre 10 y 128 caracteres.")).toBeInTheDocument();
      await usuario.type(screen.getByLabelText("Contraseña temporal"), "-ya-larga");
      expect(boton).toBeEnabled();
      expect(screen.queryByText("La contraseña debe tener entre 10 y 128 caracteres.")).toBeNull();
    });

    test("explica el usuario y la politica de contrasena", async () => {
      montar();
      await cargada();
      expect(screen.getByText("Minúsculas, sin espacios; de 3 a 40 caracteres.")).toBeInTheDocument();
      expect(screen.getAllByText(/De 10 a 128 caracteres\. Anótela y entréguela en persona/).length).toBeGreaterThan(0);
      expect(screen.getByLabelText("Usuario")).toBeRequired();
      expect(screen.getByLabelText("Nombre de la persona")).toBeRequired();
    });

    test("manda el cuerpo, vacia la contrasena, lleva el foco al resultado y no deja nada en la pagina", async () => {
      montar();
      const usuario = userEvent.setup();
      await cargada();
      alPost = () => {
        cuentas = [...cuentas, { id: 4, login: "rita", nombre: "Rita", roles: ["arma", "revisa"], activa: true }];
        return json(
          { cuenta: cuentas[3], mensaje: "Cuenta creada. La persona deberá cambiar la contraseña al entrar.", aviso: AVISO },
          201,
        );
      };
      await llenar(usuario);
      await usuario.click(screen.getByLabelText("arma presupuestos (arma)", { selector: "#adm-roles-arma" }));
      await usuario.click(screen.getByLabelText("revisa paquetes (revisa)", { selector: "#adm-roles-revisa" }));
      expect(screen.getAllByText(AVISO).length).toBeGreaterThan(0);
      await usuario.click(screen.getByRole("button", { name: "Crear la cuenta" }));

      await waitFor(() => expect(posts()).toHaveLength(1));
      const [ruta, init] = posts()[0];
      expect(ruta).toBe("/v1/cuentas");
      expect(JSON.parse(String(init?.body))).toEqual({
        login: "rita",
        nombre: "Rita",
        roles: ["arma", "revisa"],
        contrasena_temporal: TEMPORAL,
      });
      expect(new Headers(init?.headers).get("X-Silice-CSRF")).toBe("tok");
      expect(await screen.findByText("Cuenta creada. La persona deberá cambiar la contraseña al entrar.")).toBeInTheDocument();
      expect(screen.getByLabelText("Contraseña temporal")).toHaveValue("");
      await waitFor(() => expect(resultado()).toHaveFocus());
      expect(document.body.innerHTML).not.toContain(TEMPORAL);
    });

    test("un error de la API se muestra con su mensaje, con el foco, y la contrasena igual se vacia", async () => {
      montar();
      const usuario = userEvent.setup();
      await cargada();
      alPost = () => json({ detalle: "Ya existe una cuenta con el usuario 'rita'." }, 422);
      await llenar(usuario);
      await usuario.click(screen.getByRole("button", { name: "Crear la cuenta" }));
      expect(await screen.findByText("Ya existe una cuenta con el usuario 'rita'.")).toBeInTheDocument();
      expect(screen.getByLabelText("Contraseña temporal")).toHaveValue("");
      await waitFor(() => expect(resultado()).toHaveFocus());
    });

    test("un 401 durante el alta llama a alExpirar", async () => {
      const { alExpirar } = montar();
      const usuario = userEvent.setup();
      await cargada();
      alPost = () => json({ detalle: "Sesión ausente o vencida: entre de nuevo con su cuenta." }, 401);
      await llenar(usuario);
      await usuario.click(screen.getByRole("button", { name: "Crear la cuenta" }));
      await waitFor(() => expect(alExpirar).toHaveBeenCalled());
    });

    test("se puede mostrar y ocultar la contrasena con el control de Carbon", async () => {
      montar();
      const usuario = userEvent.setup();
      await cargada();
      const campo = screen.getByLabelText("Contraseña temporal");
      expect(campo).toHaveAttribute("type", "password");
      await usuario.click(screen.getAllByRole("button", { name: "Mostrar contraseña" })[0]);
      expect(screen.getByLabelText("Contraseña temporal")).toHaveAttribute("type", "text");
    });
  });

  describe("cambiar una cuenta", () => {
    test("no preselecciona ninguna: invita a elegir y las acciones esperan", async () => {
      montar();
      await cargada();
      expect(screen.getByRole("heading", { name: "Cambiar una cuenta" })).toBeInTheDocument();
      const selector = screen.getByLabelText("Cuenta que va a cambiar");
      expect(selector).toHaveValue("");
      expect(within(selector).getByText("Elija una cuenta", { selector: "option" })).toBeInTheDocument();
      for (const nombre of ["Guardar roles", "Desactivar", "Desbloquear", "Restablecer la contraseña"]) {
        expect(screen.getByRole("button", { name: nombre })).toBeDisabled();
      }
      expect(posts()).toHaveLength(0);
    });

    test("las acciones y la seccion nombran la cuenta elegida", async () => {
      montar();
      await elegir("ana");
      expect(screen.getByRole("heading", { name: "Cambiar la cuenta ana" })).toBeInTheDocument();
      for (const nombre of [
        "Guardar roles de ana",
        "Desactivar a ana",
        "Desbloquear a ana",
        "Restablecer la contraseña de ana",
      ]) {
        expect(screen.getByRole("button", { name: nombre })).toBeInTheDocument();
      }
      expect(screen.getByText(/permite entrar de nuevo a una cuenta bloqueada por intentos fallidos/i)).toBeInTheDocument();
    });

    test("guardar roles muestra el aviso en la edicion y manda los roles; desbloquear llama a su ruta", async () => {
      montar();
      const usuario = await elegir("ana");
      await usuario.click(screen.getByLabelText("revisa paquetes (revisa)", { selector: "#adm-roles-de-revisa" }));
      expect(screen.getByText(AVISO)).toBeInTheDocument();
      await usuario.click(screen.getByRole("button", { name: "Guardar roles de ana" }));
      await waitFor(() => expect(posts()).toHaveLength(1));
      expect(posts()[0][0]).toBe("/v1/cuentas/2/roles");
      expect(JSON.parse(String(posts()[0][1]?.body))).toEqual({ roles: ["arma", "revisa"] });
      await usuario.click(screen.getByRole("button", { name: "Desbloquear a ana" }));
      await waitFor(() => expect(posts()).toHaveLength(2));
      expect(posts()[1][0]).toBe("/v1/cuentas/2/desbloquear");
    });

    test("una cuenta desactivada ofrece Reactivar, sin confirmacion", async () => {
      montar();
      const usuario = await elegir("luis");
      await usuario.click(screen.getByRole("button", { name: "Reactivar a luis" }));
      await waitFor(() => expect(posts()[0][0]).toBe("/v1/cuentas/3/reactivar"));
      expect(screen.queryByRole("alertdialog")).toBeNull();
    });

    test("un 401 durante una accion de escritura llama a alExpirar", async () => {
      const { alExpirar } = montar();
      const usuario = await elegir("ana");
      alPost = () => json({ detalle: "Sesión ausente o vencida: entre de nuevo con su cuenta." }, 401);
      await usuario.click(screen.getByRole("button", { name: "Desbloquear a ana" }));
      await waitFor(() => expect(alExpirar).toHaveBeenCalled());
    });

    test("si la recarga falla tras una accion exitosa se avisa, se conserva la tabla y se puede reintentar", async () => {
      montar();
      const usuario = await elegir("ana");
      alPost = () => {
        fallaElGet = true;
        return json({ cuenta: ANA, mensaje: "Cuenta desbloqueada.", aviso: null });
      };
      await usuario.click(screen.getByRole("button", { name: "Desbloquear a ana" }));
      expect(await screen.findByText("Cuenta desbloqueada.")).toBeInTheDocument();
      expect(screen.getByText(/no se pudo recargar la lista de cuentas/)).toBeInTheDocument();
      expect(screen.getByRole("table", { name: "Cuentas de la instalación" })).toBeInTheDocument();
      expect(screen.getByText("La base no responde.")).toBeInTheDocument();
      fallaElGet = false;
      await usuario.click(screen.getByRole("button", { name: "Reintentar" }));
      await waitFor(() => expect(screen.queryByText("La base no responde.")).toBeNull());
    });

    test("tras la accion el foco va al resultado y se anuncia por una sola via (sin aria-live)", async () => {
      montar();
      const usuario = await elegir("ana");
      await usuario.click(screen.getByRole("button", { name: "Desbloquear a ana" }));
      await waitFor(() => expect(resultado()).toHaveFocus());
      expect(resultado().querySelector("[aria-live]")).toBeNull();
      expect(resultado().closest("[aria-live]")).toBeNull();
    });
  });

  describe("confirmacion (desactivar y restablecer)", () => {
    test("desactivar abre un dialogo con el foco, deja el resto inert y solo entonces llama a la API", async () => {
      montar();
      const usuario = await elegir("ana");
      alPost = () => json({ cuenta: { ...ANA, activa: false }, mensaje: "Cuenta desactivada; sus registros se conservan.", aviso: null });
      await usuario.click(screen.getByRole("button", { name: "Desactivar a ana" }));
      const dialogo = await screen.findByRole("alertdialog");
      expect(dialogo).toHaveFocus();
      expect(dialogo).toHaveAttribute("aria-modal", "true");
      expect(within(dialogo).getByText(/La cuenta «ana» no podrá entrar/)).toBeInTheDocument();
      expect(within(dialogo).queryByText(/Es su propia cuenta/)).toBeNull();
      expect(screen.getByLabelText("Cuenta que va a cambiar").closest("[inert]")).not.toBeNull();
      expect(screen.getByRole("table", { name: "Cuentas de la instalación" }).closest("[inert]")).not.toBeNull();
      expect(posts()).toHaveLength(0);

      await usuario.click(within(dialogo).getByRole("button", { name: "Desactivar a ana" }));
      await waitFor(() => expect(posts()).toHaveLength(1));
      expect(posts()[0][0]).toBe("/v1/cuentas/2/desactivar");
      expect(await screen.findByText("Cuenta desactivada; sus registros se conservan.")).toBeInTheDocument();
      await waitFor(() => expect(resultado()).toHaveFocus());
      expect(screen.queryByRole("alertdialog")).toBeNull();
    });

    test("Cancelar y Escape cierran sin llamar y devuelven el foco al boton que la abrio", async () => {
      montar();
      const usuario = await elegir("ana");
      const abrir = screen.getByRole("button", { name: "Desactivar a ana" });
      await usuario.click(abrir);
      await usuario.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Cancelar" }));
      expect(screen.queryByRole("alertdialog")).toBeNull();
      await waitFor(() => expect(abrir).toHaveFocus());

      await usuario.click(abrir);
      await screen.findByRole("alertdialog");
      await usuario.keyboard("{Escape}");
      expect(screen.queryByRole("alertdialog")).toBeNull();
      await waitFor(() => expect(abrir).toHaveFocus());
      expect(posts()).toHaveLength(0);
    });

    test("Tab y Mayus+Tab se quedan dentro del dialogo", async () => {
      montar();
      const usuario = await elegir("ana");
      await usuario.click(screen.getByRole("button", { name: "Desactivar a ana" }));
      const dialogo = await screen.findByRole("alertdialog");
      const confirmar = within(dialogo).getByRole("button", { name: "Desactivar a ana" });
      const cancelar = within(dialogo).getByRole("button", { name: "Cancelar" });
      confirmar.focus();
      await usuario.tab();
      expect(cancelar).toHaveFocus();
      await usuario.tab();
      expect(confirmar).toHaveFocus();
      await usuario.tab({ shift: true });
      expect(cancelar).toHaveFocus();
    });

    test("si la cuenta es la propia la confirmacion lo advierte", async () => {
      montar();
      const usuario = await elegir("admin");
      await usuario.click(screen.getByRole("button", { name: "Desactivar a admin" }));
      const dialogo = await screen.findByRole("alertdialog");
      expect(within(dialogo).getByText(/Es su propia cuenta: se cerrará su sesión y perderá el acceso/)).toBeInTheDocument();
    });

    test("restablecer confirma, manda la contrasena solo en el cuerpo y la vacia", async () => {
      montar();
      const usuario = await elegir("ana");
      alPost = () => json({ cuenta: ANA, mensaje: "Contraseña restablecida; sus sesiones se cerraron.", aviso: null });
      await usuario.type(screen.getByLabelText("Contraseña temporal nueva"), TEMPORAL);
      await usuario.click(screen.getByRole("button", { name: "Restablecer la contraseña de ana" }));
      expect(posts()).toHaveLength(0);
      const dialogo = await screen.findByRole("alertdialog");
      await usuario.click(within(dialogo).getByRole("button", { name: "Restablecer la contraseña de ana" }));
      await waitFor(() => expect(posts()).toHaveLength(1));
      const [ruta, init] = posts()[0];
      expect(ruta).toBe("/v1/cuentas/2/restablecer");
      expect(JSON.parse(String(init?.body))).toEqual({ contrasena_temporal: TEMPORAL });
      expect(await screen.findByText("Contraseña restablecida; sus sesiones se cerraron.")).toBeInTheDocument();
      expect(screen.getByLabelText("Contraseña temporal nueva")).toHaveValue("");
      expect(document.body.innerHTML).not.toContain(TEMPORAL);
    });

    test("cancelar la confirmacion de restablecer tambien vacia la contrasena", async () => {
      montar();
      const usuario = await elegir("ana");
      await usuario.type(screen.getByLabelText("Contraseña temporal nueva"), TEMPORAL);
      await usuario.click(screen.getByRole("button", { name: "Restablecer la contraseña de ana" }));
      await usuario.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Cancelar" }));
      expect(screen.getByLabelText("Contraseña temporal nueva")).toHaveValue("");
      expect(posts()).toHaveLength(0);
    });

    test("restablecer pide una contrasena de 10 a 128 caracteres antes de habilitarse", async () => {
      montar();
      const usuario = await elegir("ana");
      await usuario.type(screen.getByLabelText("Contraseña temporal nueva"), "corta");
      expect(screen.getByRole("button", { name: "Restablecer la contraseña de ana" })).toBeDisabled();
    });
  });

  describe("secretos y desmontaje", () => {
    test("la contrasena del alta y la del restablecer se vacian al irse a otra seccion y volver", async () => {
      montar();
      const usuario = await elegir("ana");
      await usuario.type(screen.getByLabelText("Contraseña temporal"), TEMPORAL);
      await usuario.type(screen.getByLabelText("Contraseña temporal nueva"), TEMPORAL);
      await usuario.click(screen.getByRole("link", { name: "Ir a sistema" }));
      await screen.findByLabelText("Activar el asistente de IA (viene apagado)", {}, PIDE);
      expect(screen.queryByLabelText("Contraseña temporal")).toBeNull();
      expect(document.body.innerHTML).not.toContain(TEMPORAL);
      await usuario.click(screen.getByRole("link", { name: "Ir a cuentas" }));
      await cargada();
      expect(screen.getByLabelText("Contraseña temporal")).toHaveValue("");
      expect(document.body.innerHTML).not.toContain(TEMPORAL);
    });

    test("desmontar antes de que responda la peticion no da errores ni cambia la pantalla", async () => {
      const errores = vi.spyOn(console, "error").mockImplementation(() => {});
      const vista = montar();
      const usuario = await elegir("ana");
      let soltar: (r: Response) => void = () => {};
      alPost = () => new Promise<Response>((resolver) => (soltar = resolver));
      await usuario.click(screen.getByRole("button", { name: "Desbloquear a ana" }));
      await waitFor(() => expect(posts()).toHaveLength(1));
      vista.unmount();
      soltar(json({ cuenta: ANA, mensaje: "Cuenta desbloqueada.", aviso: null }));
      await new Promise((r) => setTimeout(r, 50));
      expect(errores).not.toHaveBeenCalled();
      errores.mockRestore();
    });

    test("un 401 al leer la lista llama a alExpirar", async () => {
      fetchFalso.mockImplementation(async () => json({ detalle: "Sesión ausente o vencida: entre de nuevo con su cuenta." }, 401));
      const { alExpirar } = montar();
      await waitFor(() => expect(alExpirar).toHaveBeenCalled());
    });
  });

  describe("accesos", () => {
    test("muestra la nota con el tope de la API, la fecha legible y ninguna escritura", async () => {
      accesos = { ...accesos, maximo: 50 };
      montar();
      expect(
        await screen.findByText("Los 50 últimos eventos de acceso; este registro solo se agrega, no se edita."),
      ).toBeInTheDocument();
      const tabla = await screen.findByRole("table", { name: "Eventos de acceso" }, PIDE);
      expect(within(tabla).getByText("10 nov 2026, 09:00")).toBeInTheDocument();
      expect(within(tabla).getByText("10.0.0.7")).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /Crear|Guardar|Desactivar|Reactivar|Desbloquear|Restablecer/ })).toBeNull();
      expect(posts()).toHaveLength(0);
    });
  });
});

// VB-23: el campo de texto sobre la capa blanca de la pestaña lleva el token de campo de la capa (`$field-02`): el
// contenido de la pestaña va dentro de un <Layer> de Carbon, que sube un nivel de capa.
describe("Administracion: capa de los campos", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
    fetchFalso.mockImplementation(async (entrada) => {
      const ruta = String(entrada);
      if (ruta === "/v1/admin/cuentas") return json({ cuentas: [], roles: [], aviso_de_roles: null });
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    fijarCsrf(null);
    vi.unstubAllGlobals();
  });

  test("el contenido de la sección está dentro de una capa de nivel dos", async () => {
    const valor: Aplicacion = { sesion: SESION, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() };
    const { container } = render(
      <ContextoAplicacion.Provider value={valor}>
        <EnLaCuenta seccion="cuentas">
          <PaginaAdministracion />
        </EnLaCuenta>
      </ContextoAplicacion.Provider>,
    );
    const pagina = container.querySelector(".silice-adm");
    await waitFor(() => expect(pagina?.querySelector(".cds--layer-two")).not.toBeNull());
  });
});


// Plan de modulos, MOD-3b (diseno de modulos §7 y §12.2): las carpetas de trabajo se administran en la Cuenta, sección
// «Carpetas» (BCP-5; F6, T6). El administrador puede cambiar de carpeta pero no editar la hoja: sin «Demostración».
describe("Administracion: Carpetas de trabajo", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const CASOS = {
    actual: { nombre: "silice.db", ruta_relativa: "casos/silice.db" },
    casos: [
      { nombre: "silice.db", ruta_relativa: "casos/silice.db" },
      { nombre: "s1.db", ruta_relativa: "casos/s1.db" },
    ],
    empresa: { nombre: "silice.db", ruta_relativa: "casos/silice.db" },
    es_demostracion: false,
  };
  const ADMIN_CON_CARPETAS: SesionRespuesta = { ...SESION, acciones: [...SESION.acciones, "cambiar_caso"] };

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
    fetchFalso.mockImplementation(async (entrada) => {
      const ruta = String(entrada);
      if (ruta === "/v1/casos") return json(CASOS);
      if (ruta === "/v1/cuentas") return json({ cuentas: [ADMIN], aviso_arma_y_revisa: AVISO });
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    fijarCsrf(null);
    vi.unstubAllGlobals();
  });

  function montarConCarpetas(sesion: SesionRespuesta, abrirCarpeta = vi.fn(async () => true)) {
    const valor: Aplicacion = { sesion, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn(), abrirCarpeta };
    render(
      <ContextoAplicacion.Provider value={valor}>
        <EnLaCuenta seccion="carpetas">
          <PaginaAdministracion />
        </EnLaCuenta>
      </ContextoAplicacion.Provider>,
    );
    return abrirCarpeta;
  }

  test("el admin ve «Carpetas» con la lista y «Crear», sin «Demostración»", async () => {
    montarConCarpetas(ADMIN_CON_CARPETAS);
    const lista = await screen.findByRole("list", { name: "Carpetas de trabajo de la instalación" }, PIDE);
    expect(within(lista).getAllByRole("listitem").map((li) => li.querySelector(".silice-carpetas__nombre")?.textContent)).toEqual([
      "silice",
      "s1",
    ]);
    expect(screen.getByRole("tab", { name: "Crear" })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Demostración" })).not.toBeInTheDocument();
  });

  test("abrir una carpeta desde la sección pasa por la aplicación (confirmación y aviso del armazón)", async () => {
    const u = userEvent.setup();
    const abrirCarpeta = montarConCarpetas(ADMIN_CON_CARPETAS);
    await u.click(await screen.findByRole("button", { name: "Abrir s1" }, PIDE));
    expect(abrirCarpeta).toHaveBeenCalledWith("s1.db");
  });

  test("sin cambiar de carpeta la sección no ofrece nada (también aquí, aunque el marco ya lo filtra)", () => {
    montarConCarpetas(SESION);
    expect(screen.queryByRole("list", { name: "Carpetas de trabajo de la instalación" })).not.toBeInTheDocument();
    expect(screen.getByText("Su cuenta no tiene permiso para administrar la instalación.")).toBeInTheDocument();
    expect(fetchFalso).not.toHaveBeenCalled();
  });
});
