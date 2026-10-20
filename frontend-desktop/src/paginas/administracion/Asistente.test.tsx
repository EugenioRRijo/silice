import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import Asistente from "./Asistente";
import type { AsistenteEstado } from "./logica";

// Pestaña «Asistente de IA»: textos y validaciones de `pestana_asistente` (ui/paginas/administracion.py),
// escritos a mano. Sin gasto: la API se simula y ninguna prueba llama a un proveedor de IA.

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "admin",
  nombre: "Admin Ficticio",
  roles: ["administrador"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["administrar_cuentas", "administrar_empresa"],
  modo_entrega: false,
};
const REMOTO = "Esta operación solo puede hacerse desde el propio equipo donde corre Sílice, no desde la red.";
const AVISO_DE_NUBE =
  "Con el modo en la nube activo, el pedido y el resumen del borrador viajan al proveedor (sin precios, montos ni nombres de proyecto, empresa o usuarios). Es una excepción declarada a la ejecución local; el modo local no envía nada fuera del equipo.";
const CLAVE = "sk-ant-api03-ABCD1234efgh5678";
const RESPALDO = "contrasena del respaldo larga";
const FABRICA: AsistenteEstado = {
  activo: false,
  proveedor: "claude",
  proveedores: [
    { valor: "claude", etiqueta: "Claude (en la nube, con la clave de la empresa)" },
    { valor: "ollama", etiqueta: "Ollama (local, en este equipo)" },
  ],
  modelo_claude: "claude-opus-5-5",
  modelo_local: "",
  anfitrion_ollama: "http://127.0.0.1:11434",
  tope_usd: "2.50",
  clave_registrada: null,
  clave_guardada: false,
  pide_contrasena: false,
  falta_el_componente: null,
  aviso_de_nube: AVISO_DE_NUBE,
  sensible: { permitida: true, motivo: "" },
};

describe("Asistente de IA", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    fijarCsrf("tok");
  });
  afterEach(() => {
    fijarCsrf(null);
    vi.unstubAllGlobals();
  });

  function montar() {
    const valor: Aplicacion = { sesion: SESION, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <Asistente />
      </ContextoAplicacion.Provider>,
    );
  }

  const llamada = (i: number) => fetchFalso.mock.calls[i] as [string, RequestInit | undefined];
  const cuerpo = (i: number) => JSON.parse(String(llamada(i)[1]?.body)) as Record<string, unknown>;
  const sinRastro = (texto: string) => {
    expect(document.body.innerHTML).not.toContain(texto);
    expect(Object.values(localStorage).join()).not.toContain(texto);
    expect(Object.values(sessionStorage).join()).not.toContain(texto);
  };

  test("muestra el aviso de la nube y la configuración que manda la API", async () => {
    fetchFalso.mockResolvedValueOnce(json(FABRICA));
    montar();
    expect(await screen.findByText(AVISO_DE_NUBE)).toBeInTheDocument();
    expect(llamada(0)[0]).toBe("/v1/admin/asistente");
    expect(screen.getByLabelText("Activar el asistente de IA (viene apagado)")).not.toBeChecked();
    expect(screen.getByLabelText("Proveedor por defecto")).toHaveValue("claude");
    expect(screen.getByRole("option", { name: "Ollama (local, en este equipo)" })).toBeInTheDocument();
    expect(screen.getByLabelText("Modelo de Claude")).toHaveValue("claude-opus-5-5");
    expect(screen.getByLabelText("Modelo local (Ollama)")).toHaveValue("");
    expect(screen.getByLabelText("Dirección de Ollama")).toHaveValue("http://127.0.0.1:11434");
    expect(screen.getByLabelText("Tope de costo por sesión (USD)")).toHaveValue("2,50");
    expect(screen.getByText("Mayor que cero; puede escribir coma o punto decimal.")).toBeInTheDocument();
    expect(screen.getByText(/Si la dirección de Ollama no es de este equipo/)).toBeInTheDocument();
    expect(screen.getByText("Clave registrada: ninguna")).toBeInTheDocument();
  });

  test("guarda la configuración con el tope tal como se escribió", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValueOnce(json(FABRICA));
    fetchFalso.mockResolvedValueOnce(
      json({ mensaje: "Configuración del asistente guardada.", estado: { ...FABRICA, activo: true, tope_usd: "3.75" } }),
    );
    montar();
    await usuario.click(await screen.findByLabelText("Activar el asistente de IA (viene apagado)"));
    await usuario.selectOptions(screen.getByLabelText("Proveedor por defecto"), "ollama");
    await usuario.type(screen.getByLabelText("Modelo local (Ollama)"), "llama-ficticio");
    const tope = screen.getByLabelText("Tope de costo por sesión (USD)");
    await usuario.clear(tope);
    await usuario.type(tope, "3,75");
    await usuario.click(screen.getByRole("button", { name: "Guardar la configuración" }));
    expect(await screen.findByText("Configuración del asistente guardada.")).toBeInTheDocument();
    expect(llamada(1)[0]).toBe("/v1/admin/asistente/configuracion");
    expect(cuerpo(1)).toEqual({
      activo: true,
      proveedor: "ollama",
      modelo_claude: "claude-opus-5-5",
      modelo_local: "llama-ficticio",
      anfitrion_ollama: "http://127.0.0.1:11434",
      tope_usd: "3,75",
    });
    expect(screen.getByLabelText("Tope de costo por sesión (USD)")).toHaveValue("3,75");
  });

  test("un tope rechazado muestra el mensaje de la API", async () => {
    const usuario = userEvent.setup();
    const detalle = "El tope de costo debe ser mayor que cero: escriba, por ejemplo, 2,50.";
    fetchFalso.mockResolvedValueOnce(json(FABRICA));
    fetchFalso.mockResolvedValueOnce(json({ detalle }, 400));
    montar();
    const tope = await screen.findByLabelText("Tope de costo por sesión (USD)");
    await usuario.clear(tope);
    await usuario.type(tope, "0");
    await usuario.click(screen.getByRole("button", { name: "Guardar la configuración" }));
    expect(await screen.findByText(detalle)).toBeInTheDocument();
  });

  test("registra la clave: la manda solo en el cuerpo, vacía los campos y no la deja en la página", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValueOnce(json(FABRICA));
    fetchFalso.mockResolvedValueOnce(
      json({ mensaje: "Clave de IA registrada (…5678).", estado: { ...FABRICA, clave_registrada: "…5678" } }),
    );
    montar();
    await usuario.type(await screen.findByLabelText("Clave de IA de la empresa"), CLAVE);
    await usuario.type(
      screen.getByLabelText("Contraseña del respaldo cifrado (solo si el almacén de credenciales no está)"),
      RESPALDO,
    );
    await usuario.click(screen.getByRole("button", { name: "Registrar la clave" }));
    expect(await screen.findByText("Clave de IA registrada (…5678).")).toBeInTheDocument();
    expect(screen.getByText("Clave registrada: …5678")).toBeInTheDocument();
    expect(llamada(1)[0]).toBe("/v1/admin/asistente/clave");
    expect(llamada(1)[1]?.method).toBe("POST");
    expect(new Headers(llamada(1)[1]?.headers).get("X-Silice-CSRF")).toBe("tok");
    expect(cuerpo(1)).toEqual({ clave: CLAVE, contrasena_respaldo: RESPALDO });
    expect(screen.getByLabelText("Clave de IA de la empresa")).toHaveValue("");
    sinRastro(CLAVE);
    sinRastro(RESPALDO);
  });

  test("sin contraseña de respaldo no se manda ese campo; un rechazo vacía igual la clave", async () => {
    const usuario = userEvent.setup();
    const detalle = "Escriba la clave de IA de la empresa.";
    fetchFalso.mockResolvedValueOnce(json(FABRICA));
    fetchFalso.mockResolvedValueOnce(json({ detalle }, 400));
    montar();
    await usuario.type(await screen.findByLabelText("Clave de IA de la empresa"), CLAVE);
    await usuario.click(screen.getByRole("button", { name: "Registrar la clave" }));
    expect(await screen.findByText(detalle)).toBeInTheDocument();
    expect(cuerpo(1)).toEqual({ clave: CLAVE });
    sinRastro(CLAVE);
  });

  test("desde otro equipo dice por qué y no deja escribir ni registrar la clave", async () => {
    fetchFalso.mockResolvedValueOnce(json({ ...FABRICA, sensible: { permitida: false, motivo: REMOTO } }));
    montar();
    expect(await screen.findByText(REMOTO)).toBeInTheDocument();
    expect(screen.getByLabelText("Clave de IA de la empresa")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Registrar la clave" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Olvidar la clave" })).toBeDisabled();
  });

  test("apagado con una clave guardada lo dice como la clásica", async () => {
    fetchFalso.mockResolvedValueOnce(json({ ...FABRICA, clave_guardada: true }));
    montar();
    expect(
      await screen.findByText(
        "Clave registrada: hay una guardada, pero no se carga mientras el asistente esté apagado (se carga al activarlo).",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reactivar la clave" })).toBeNull();
  });

  test("con solo el respaldo pide su contraseña, la manda y la vacía", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValueOnce(json({ ...FABRICA, activo: true, pide_contrasena: true }));
    fetchFalso.mockResolvedValueOnce(
      json({ mensaje: "Clave de IA reactivada (…5678).", estado: { ...FABRICA, activo: true, clave_registrada: "…5678" } }),
    );
    montar();
    expect(await screen.findByText(/hay una en el respaldo cifrado/)).toBeInTheDocument();
    await usuario.type(screen.getByLabelText("Contraseña del respaldo cifrado de la clave"), RESPALDO);
    await usuario.click(screen.getByRole("button", { name: "Reactivar la clave" }));
    expect(await screen.findByText("Clave de IA reactivada (…5678).")).toBeInTheDocument();
    expect(llamada(1)[0]).toBe("/v1/admin/asistente/clave/reactivar");
    expect(cuerpo(1)).toEqual({ contrasena: RESPALDO });
    expect(screen.queryByLabelText("Contraseña del respaldo cifrado de la clave")).toBeNull();
    sinRastro(RESPALDO);
  });

  test("una contraseña equivocada al reactivar muestra el mensaje y no la deja escrita", async () => {
    const usuario = userEvent.setup();
    const detalle = "La contraseña no abre el respaldo de la clave de IA.";
    fetchFalso.mockResolvedValueOnce(json({ ...FABRICA, activo: true, pide_contrasena: true }));
    fetchFalso.mockResolvedValueOnce(json({ detalle }, 400));
    montar();
    await usuario.type(await screen.findByLabelText("Contraseña del respaldo cifrado de la clave"), "otra contrasena larga");
    await usuario.click(screen.getByRole("button", { name: "Reactivar la clave" }));
    expect(await screen.findByText(detalle)).toBeInTheDocument();
    expect(screen.getByLabelText("Contraseña del respaldo cifrado de la clave")).toHaveValue("");
    sinRastro("otra contrasena larga");
  });

  test("desde otro equipo no se ofrece reactivar", async () => {
    fetchFalso.mockResolvedValueOnce(
      json({ ...FABRICA, activo: true, pide_contrasena: true, sensible: { permitida: false, motivo: REMOTO } }),
    );
    montar();
    expect(await screen.findByText(/hay una en el respaldo cifrado/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Contraseña del respaldo cifrado de la clave")).toBeNull();
  });

  test("olvidar la clave pide confirmación y luego la borra", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValueOnce(json({ ...FABRICA, activo: true, clave_registrada: "…5678" }));
    fetchFalso.mockResolvedValueOnce(
      json({ mensaje: "La clave de IA se olvidó: ya no está en este equipo.", estado: { ...FABRICA, activo: true } }),
    );
    montar();
    await usuario.click(await screen.findByRole("button", { name: "Olvidar la clave" }));
    expect(fetchFalso).toHaveBeenCalledTimes(1);
    await usuario.click(screen.getByRole("button", { name: "Sí, olvidar la clave" }));
    expect(await screen.findByText("La clave de IA se olvidó: ya no está en este equipo.")).toBeInTheDocument();
    expect(llamada(1)[0]).toBe("/v1/admin/asistente/clave/olvidar");
    expect(screen.getByText("Clave registrada: ninguna")).toBeInTheDocument();
  });

  // VB-18: el aviso es para quien administra, no para quien desarrolla: sin comandos de consola.
  test("sin el componente de IA lo dice en lenguaje llano y no ofrece la sección de la clave", async () => {
    fetchFalso.mockResolvedValueOnce(
      json({
        ...FABRICA,
        falta_el_componente:
          "Falta el componente del asistente de IA en este equipo. Instálelo con «uv sync --extra ia» y vuelva a abrir Sílice.",
      }),
    );
    montar();
    expect(await screen.findByText(/Falta un componente opcional del asistente de IA/)).toHaveTextContent(
      "Pídalo a quien instaló Sílice",
    );
    expect(document.body.textContent).not.toMatch(/uv sync|--extra/);
    expect(screen.getByLabelText("Activar el asistente de IA (viene apagado)")).toBeInTheDocument();
    expect(screen.queryByLabelText("Clave de IA de la empresa")).toBeNull();
  });

  test("la pestaña no deja regiones role=alert vacías", async () => {
    fetchFalso.mockResolvedValueOnce(json(FABRICA));
    montar();
    await screen.findByLabelText("Modelo de Claude");
    const vacias = screen.queryAllByRole("alert").filter((a) => (a.textContent ?? "").trim() === "");
    expect(vacias).toHaveLength(0);
  });

  test("una sesión vencida avisa al marco", async () => {
    fetchFalso.mockResolvedValueOnce(json({ detalle: "Su sesión terminó." }, 401));
    montar();
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });
});
