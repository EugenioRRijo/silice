import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { alertaConTexto } from "../../test/ayudas";
import PaginaEntregar from "./index";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { "Content-Type": "application/json" },
  });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["entregar_paquete", "leer_proyecto"],
  modo_entrega: false,
};

const PROYECTOS = [
  {
    codigo: "1",
    nombre: "Clínica",
    version_vigente: 2,
    version_codigo: "002",
    actualizado: null,
  },
  {
    codigo: "2",
    nombre: "Oficina",
    version_vigente: 5,
    version_codigo: "001",
    actualizado: null,
  },
];

function resumen(parcial: Record<string, unknown> = {}) {
  return {
    proyecto: "Clínica",
    version: "002",
    moneda: "USD",
    total: "836.79750000",
    total_texto: "836.8",
    hallazgos_total: 3,
    hallazgos_por_severidad: { ADVERTENCIA: 2, ERROR: 1 },
    cadena_integra: true,
    mensaje_de_cadena: "",
    entregable: true,
    empresa: "Contratista Demo, C.A.",
    firma_disponible: false,
    viaja_con: ["presupuesto", "informe", "cadena"],
    ...parcial,
  };
}

const SHA = "a".repeat(64);

describe("Entregar paquete", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();
  let proyectos: () => Response;
  let versiones: (proyecto: string) => Response;
  let resumenDe: (proyecto: string, version: string) => Response;
  let entrega: () => Response;
  const guardado = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    guardado.mockReset();
    URL.createObjectURL = vi.fn(() => "blob:falso");
    URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      guardado(this.download);
    });
    proyectos = () => json(PROYECTOS);
    versiones = () =>
      json([
        { codigo: "002", moneda: "USD" },
        { codigo: "001", moneda: "USD" },
      ]);
    resumenDe = () => json(resumen());
    entrega = () =>
      new Response("zip", {
        status: 200,
        headers: {
          "Content-Type": "application/zip",
          "Content-Disposition": 'attachment; filename="Clinica-002.silice"',
          "X-Silice-SHA256": SHA,
          "X-Silice-Firmado": "0",
        },
      });
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://x");
      if (url.pathname === "/v1/proyectos") return proyectos();
      if (url.pathname === "/v1/entregas/versiones")
        return versiones(url.searchParams.get("proyecto") ?? "");
      if (url.pathname === "/v1/entregas/resumen") {
        return resumenDe(
          url.searchParams.get("proyecto") ?? "",
          url.searchParams.get("version") ?? "",
        );
      }
      if (url.pathname === "/v1/entregas" && init?.method === "POST")
        return entrega();
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  function montar(proyecto: string | null = null) {
    const aplicacion: Aplicacion = {
      sesion: SESION,
      proyecto,
      caso: null,
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    return render(
      <ContextoAplicacion.Provider value={aplicacion}>
        <PaginaEntregar />
      </ContextoAplicacion.Provider>,
    );
  }

  function llamadasPost() {
    return fetchFalso.mock.calls.filter(([, init]) => init?.method === "POST");
  }

  test("sin proyectos dice que el caso está vacío", async () => {
    proyectos = () => json([]);
    montar();
    expect(
      await screen.findByText("Este caso todavía no tiene proyectos."),
    ).toBeInTheDocument();
  });

  test("elige el proyecto de la cabecera y la versión más nueva, y muestra lo que viajará", async () => {
    montar("2");
    expect(await screen.findByText("836,80 USD")).toBeInTheDocument();
    expect(screen.getByLabelText("Proyecto")).toHaveValue("Oficina");
    expect(screen.getByLabelText("Versión")).toHaveValue("002");
    expect(screen.getByText("3")).toBeInTheDocument(); // hallazgos
    expect(screen.getByText("2 advertencias, 1 error")).toBeInTheDocument(); // VB-16
    expect(screen.getByText("Íntegra")).toBeInTheDocument();
    expect(
      screen.getByText("Viaja con: presupuesto, informe, cadena."),
    ).toBeInTheDocument();
    expect(screen.getByText(/el paquete saldrá SIN FIRMA/)).toBeInTheDocument();
    expect(
      screen.getByLabelText("Contraseña de la clave de firma"),
    ).toBeDisabled();
  });

  test("sin empresa avisa que el paquete no dirá quién lo emite", async () => {
    resumenDe = () => json(resumen({ empresa: null }));
    montar();
    expect(
      await screen.findByText(/no dirá quién lo emite/),
    ).toBeInTheDocument();
  });

  test("una cadena rota se dice con su mensaje y no deja generar el paquete", async () => {
    resumenDe = () =>
      json(
        resumen({
          cadena_integra: false,
          mensaje_de_cadena: "Cadena rota en la versión 001.",
        }),
      );
    montar();
    expect(
      await screen.findByText("Cadena rota en la versión 001."),
    ).toBeInTheDocument();
    expect(screen.getByText("Rota")).toBeInTheDocument(); // VB-16: mayúscula inicial, no «ROTA»
    expect(
      screen.getByRole("button", { name: "Generar paquete" }),
    ).toBeDisabled();
  });

  const AVISO_LEGADO =
    "La versión 001 se selló antes de la corrección de cifras y no puede entregarse tal cual; confirme una versión nueva (quedará sellada con la cifra corregida) y entregue esa.";

  test("una versión sellada antes de VB-1 muestra el aviso y no deja generar el paquete", async () => {
    resumenDe = () =>
      json(resumen({ entregable: false, mensaje_de_cadena: AVISO_LEGADO }));
    montar();
    await screen.findByText(AVISO_LEGADO);
    const aviso = screen
      .getAllByRole("status")
      .find((a) => (a.textContent ?? "").includes(AVISO_LEGADO));
    expect(aviso).toBeDefined();
    expect(screen.getByText("Íntegra")).toBeInTheDocument();
    const boton = screen.getByRole("button", { name: "Generar paquete" });
    expect(boton).toBeDisabled();
    const motivo = document.getElementById(
      boton.getAttribute("aria-describedby") ?? "",
    );
    expect(motivo?.textContent).toContain(AVISO_LEGADO);
    expect(screen.queryByText("Cadena rota")).not.toBeInTheDocument();
    expect(llamadasPost()).toHaveLength(0);
  });

  test("una versión entregable no muestra aviso de sellado y deja generar el paquete", async () => {
    resumenDe = () =>
      json(resumen({ entregable: true, mensaje_de_cadena: "" }));
    montar();
    await screen.findByText("836,80 USD");
    const boton = screen.getByRole("button", { name: "Generar paquete" });
    expect(boton).toBeEnabled();
    expect(boton).not.toHaveAttribute("aria-describedby");
    expect(
      screen.queryByText(/sellada con la cifra corregida/),
    ).not.toBeInTheDocument();
  });

  test("una cadena rota sigue siendo error y no deja generar, con entregable verdadero", async () => {
    resumenDe = () =>
      json(
        resumen({
          cadena_integra: false,
          entregable: true,
          mensaje_de_cadena: "Cadena rota en la versión 001.",
        }),
      );
    montar();
    expect((await alertaConTexto()).textContent).toContain(
      "Cadena rota en la versión 001.",
    );
    expect(
      screen.getByRole("button", { name: "Generar paquete" }),
    ).toBeDisabled();
    expect(
      screen
        .getAllByRole("status")
        .some((a) => (a.textContent ?? "").includes("Cadena rota en")),
    ).toBe(false);
  });

  test("si el servidor responde 409 al entregar se muestra el detalle tal cual", async () => {
    resumenDe = () => json(resumen());
    entrega = () => json({ detalle: AVISO_LEGADO }, 409);
    const u = userEvent.setup();
    montar();
    await screen.findByText("836,80 USD");
    await u.click(screen.getByRole("button", { name: "Generar paquete" }));
    expect((await alertaConTexto()).textContent).toContain(AVISO_LEGADO);
    expect(screen.queryByText(/Paquete listo/)).not.toBeInTheDocument();
  });

  test("genera el paquete sin firma, muestra su SHA-256 y lo descarga con el nombre de la API", async () => {
    const u = userEvent.setup();
    montar();
    expect(await screen.findByText("836,80 USD")).toHaveAttribute(
      "title",
      "Valor exacto: 836.79750000 USD",
    );
    expect(
      screen.getByText(/Valor exacto: 836\.79750000 USD/, { selector: "span" }),
    ).toBeInTheDocument();
    await u.type(
      screen.getByLabelText("Para quién es (opcional)"),
      "Cliente S.A.",
    );
    await u.click(screen.getByRole("button", { name: "Generar paquete" }));
    expect(
      await screen.findByText("Paquete listo (sin firma)."),
    ).toBeInTheDocument();
    expect(screen.getByText(`SHA-256: ${SHA}`)).toBeInTheDocument();
    const [ruta, init] = llamadasPost()[0];
    expect(ruta).toBe("/v1/entregas");
    expect(JSON.parse(String(init?.body))).toEqual({
      proyecto: "Clínica",
      version: "002",
      destinatario: "Cliente S.A.",
    });
    await u.click(screen.getByRole("button", { name: "Descargar el paquete" }));
    expect(guardado).toHaveBeenCalledWith("Clinica-002.silice");
  });

  test("con clave de firma pide la contraseña, la manda y vacía el campo al enviar", async () => {
    resumenDe = () => json(resumen({ firma_disponible: true }));
    entrega = () =>
      new Response("zip", {
        status: 200,
        headers: {
          "Content-Disposition": 'attachment; filename="Clinica-002.silice"',
          "X-Silice-SHA256": SHA,
          "X-Silice-Firmado": "1",
        },
      });
    const u = userEvent.setup();
    montar();
    await screen.findByText("836,80 USD");
    const campo = screen.getByLabelText("Contraseña de la clave de firma");
    expect(campo).toBeEnabled();
    expect(campo).toHaveAttribute("autocomplete", "off");
    await u.type(campo, "frase de firma");
    await u.click(screen.getByRole("button", { name: "Generar paquete" }));
    expect(
      await screen.findByText("Paquete listo y firmado."),
    ).toBeInTheDocument();
    expect(
      JSON.parse(String(llamadasPost()[0][1]?.body)).contrasena_clave,
    ).toBe("frase de firma");
    expect(
      screen.getByLabelText("Contraseña de la clave de firma"),
    ).toHaveValue("");
    expect(document.body.textContent).not.toContain("frase de firma");
  });

  test("una contraseña incorrecta muestra el detalle de la API y no deja un paquete a la vista", async () => {
    resumenDe = () => json(resumen({ firma_disponible: true }));
    entrega = () =>
      json({ detalle: "La contraseña de la clave no es correcta." }, 400);
    const u = userEvent.setup();
    montar();
    await screen.findByText("836,80 USD");
    await u.type(
      screen.getByLabelText("Contraseña de la clave de firma"),
      "mala",
    );
    await u.click(screen.getByRole("button", { name: "Generar paquete" }));
    expect((await alertaConTexto()).textContent).toContain(
      "La contraseña de la clave no es correcta.",
    );
    expect(screen.queryByText(/Paquete listo/)).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("Contraseña de la clave de firma"),
    ).toHaveValue("");
  });

  test("firmar desde otra máquina muestra el motivo de la API", async () => {
    resumenDe = () => json(resumen({ firma_disponible: true }));
    entrega = () =>
      json(
        {
          detalle: "Esta operación solo puede hacerse desde el propio equipo.",
        },
        403,
      );
    const u = userEvent.setup();
    montar();
    await screen.findByText("836,80 USD");
    await u.type(screen.getByLabelText("Contraseña de la clave de firma"), "x");
    await u.click(screen.getByRole("button", { name: "Generar paquete" }));
    expect((await alertaConTexto()).textContent).toContain(
      "solo puede hacerse desde el propio equipo",
    );
  });

  test("al cambiar de versión desaparece el paquete anterior y se pide el resumen de la nueva", async () => {
    const u = userEvent.setup();
    montar();
    await screen.findByText("836,80 USD");
    await u.click(screen.getByRole("button", { name: "Generar paquete" }));
    await screen.findByText("Paquete listo (sin firma).");
    resumenDe = (_p, version) =>
      json(resumen({ version, total: "4131.1", total_texto: "10.5" }));
    await u.selectOptions(screen.getByLabelText("Versión"), "001");
    expect(await screen.findByText("4.131,10 USD")).toBeInTheDocument();
    expect(
      screen.queryByText("Paquete listo (sin firma)."),
    ).not.toBeInTheDocument();
  });

  test("un 401 avisa que la sesión venció", async () => {
    proyectos = () => json({ detalle: "Sesión ausente o vencida." }, 401);
    montar();
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });
});
