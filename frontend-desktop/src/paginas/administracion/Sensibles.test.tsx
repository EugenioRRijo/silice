import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import ClavesApi from "./ClavesApi";
import Empresa from "./Empresa";
import Instalacion from "./Instalacion";
import type { EmpresaEstado, InstalacionEstado } from "./sensibles";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "admin",
  nombre: "Admin de Prueba",
  roles: ["administrador"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["administrar_cuentas", "administrar_empresa", "administrar_red_y_api"],
  modo_entrega: false,
};
const LOCAL = { permitida: true, motivo: "" };
const REMOTO = { permitida: false, motivo: "Esta operación solo puede hacerse desde el propio equipo donde corre Sílice, no desde la red." };
const FRASE = "frase de firma larga y propia";

describe("pestañas sensibles de Administración", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    fijarCsrf("tok");
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  function montar(pestana: React.ReactElement) {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: null,
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter>{pestana}</MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  function cuerpo(llamada: number): Record<string, unknown> {
    return JSON.parse(String((fetchFalso.mock.calls[llamada][1] as RequestInit).body)) as Record<string, unknown>;
  }

  describe("Empresa y clave de firma", () => {
    const SIN_CLAVE: EmpresaEstado = {
      empresa: { nombre: "Contratista Demo, C.A.", rif: "J-00000000-0", ciudad: "" },
      clave: null,
      sensible: LOCAL,
    };
    const CON_CLAVE: EmpresaEstado = { ...SIN_CLAVE, clave: { estado: "activa", huella: "AB12 CD34" } };

    test("sin empresa pide primero el nombre y el RIF", async () => {
      fetchFalso.mockResolvedValue(json({ empresa: null, clave: null, sensible: LOCAL }));
      montar(<Empresa />);
      expect(await screen.findByText(/Primero guarde el nombre y el RIF/)).toBeInTheDocument();
      expect(screen.queryByLabelText(/Contraseña de la clave/)).not.toBeInTheDocument();
    });

    test("guarda la empresa", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockResolvedValueOnce(json({ empresa: null, clave: null, sensible: LOCAL }));
      fetchFalso.mockResolvedValueOnce(json(SIN_CLAVE));
      montar(<Empresa />);
      await usuario.type(await screen.findByLabelText("Nombre de la empresa"), "Contratista Demo, C.A.");
      await usuario.type(screen.getByLabelText("RIF"), "J-00000000-0");
      await usuario.click(screen.getByRole("button", { name: "Guardar la empresa" }));
      await screen.findByText("Empresa guardada.");
      expect(fetchFalso.mock.calls[1][0]).toBe("/v1/admin/empresa");
      expect(cuerpo(1)).toEqual({ nombre: "Contratista Demo, C.A.", rif: "J-00000000-0", ciudad: "" });
    });

    test("dos contraseñas distintas no llegan a la API", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockResolvedValue(json(SIN_CLAVE));
      montar(<Empresa />);
      await usuario.type(await screen.findByLabelText(/Contraseña de la clave \(12/), FRASE);
      await usuario.type(screen.getByLabelText("Repítala"), "otra frase distinta");
      await usuario.click(screen.getByRole("button", { name: "Generar la clave" }));
      expect(await screen.findByText("Las dos contraseñas no coinciden.")).toBeInTheDocument();
      expect(fetchFalso).toHaveBeenCalledTimes(1);
    });

    test("genera la clave: manda la contraseña y la borra de la pantalla", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockResolvedValueOnce(json(SIN_CLAVE));
      fetchFalso.mockResolvedValueOnce(json(CON_CLAVE));
      montar(<Empresa />);
      await usuario.type(await screen.findByLabelText(/Contraseña de la clave \(12/), FRASE);
      await usuario.type(screen.getByLabelText("Repítala"), FRASE);
      await usuario.click(screen.getByRole("button", { name: "Generar la clave" }));
      await screen.findByText("AB12 CD34");
      expect(fetchFalso.mock.calls[1][0]).toBe("/v1/admin/empresa/clave");
      expect((fetchFalso.mock.calls[1][1] as RequestInit).method).toBe("POST");
      expect(cuerpo(1)).toEqual({ contrasena: FRASE });
      expect(document.body.textContent).not.toContain(FRASE);
      expect(Object.values(localStorage).join()).not.toContain(FRASE);
      expect(Object.values(sessionStorage).join()).not.toContain(FRASE);
    });

    test("un rechazo del servidor al generar se muestra sin repetir la contraseña", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockResolvedValueOnce(json(SIN_CLAVE));
      fetchFalso.mockResolvedValueOnce(json({ detalle: "La contraseña de la clave debe tener al menos 12 caracteres." }, 400));
      montar(<Empresa />);
      await usuario.type(await screen.findByLabelText(/Contraseña de la clave \(12/), "corta-123");
      await usuario.type(screen.getByLabelText("Repítala"), "corta-123");
      await usuario.click(screen.getByRole("button", { name: "Generar la clave" }));
      expect(await screen.findByText(/al menos 12 caracteres/)).toBeInTheDocument();
      expect(document.body.textContent).not.toContain("corta-123");
    });

    test("revocar con contraseña: la manda, descarga el aviso y vacía el campo", async () => {
      const usuario = userEvent.setup();
      const crear = vi.fn(() => "blob:aviso");
      vi.stubGlobal("URL", { createObjectURL: crear, revokeObjectURL: vi.fn() });
      fetchFalso.mockResolvedValueOnce(json(CON_CLAVE));
      fetchFalso.mockResolvedValueOnce(json({ aviso: "AAECAw==" }));
      fetchFalso.mockResolvedValueOnce(json({ ...CON_CLAVE, clave: null }));
      montar(<Empresa />);
      await screen.findByText("AB12 CD34");
      await usuario.type(screen.getByLabelText("Motivo"), "expuesta");
      await usuario.type(screen.getByLabelText(/Contraseña de la clave \(para firmar/), FRASE);
      await usuario.click(screen.getByRole("button", { name: "Revocar" }));
      await usuario.click(screen.getByRole("button", { name: "Sí, revocar" }));
      await waitFor(() => expect(fetchFalso.mock.calls[1][0]).toBe("/v1/admin/empresa/clave/revocar"));
      expect(cuerpo(1)).toEqual({ motivo: "expuesta", contrasena: FRASE });
      await waitFor(() => expect(crear).toHaveBeenCalledTimes(1));
      expect(await screen.findByText("Clave revocada: los paquetes firmados con ella dejan de verificar.")).toBeInTheDocument();
      expect(document.body.textContent).not.toContain(FRASE);
    });

    test("desde otro equipo no deja generar y dice por qué", async () => {
      fetchFalso.mockResolvedValue(json({ ...SIN_CLAVE, sensible: REMOTO }));
      montar(<Empresa />);
      expect(await screen.findByText(REMOTO.motivo)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Generar la clave" })).toBeDisabled();
    });

    test("con clave muestra la huella y las descargas; revocar pide confirmación", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockResolvedValueOnce(json(CON_CLAVE));
      fetchFalso.mockResolvedValueOnce(json({ aviso: null }));
      fetchFalso.mockResolvedValueOnce(json({ ...CON_CLAVE, clave: null }));
      montar(<Empresa />);
      expect(await screen.findByText("AB12 CD34")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Descargar la clave pública" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Descargar el respaldo cifrado de la clave" })).toBeInTheDocument();
      await usuario.type(screen.getByLabelText("Motivo"), "perdida");
      await usuario.click(screen.getByRole("button", { name: "Revocar" }));
      expect(fetchFalso).toHaveBeenCalledTimes(1); // nada hasta confirmar
      await usuario.click(screen.getByRole("button", { name: "Sí, revocar" }));
      await waitFor(() => expect(fetchFalso.mock.calls[1][0]).toBe("/v1/admin/empresa/clave/revocar"));
      expect(cuerpo(1)).toEqual({ motivo: "perdida" });
      expect(await screen.findByText(/Sin la contraseña no hay aviso firmado/)).toBeInTheDocument();
    });

    test("desde otro equipo oculta el respaldo de la clave", async () => {
      fetchFalso.mockResolvedValue(json({ ...CON_CLAVE, sensible: REMOTO }));
      montar(<Empresa />);
      await screen.findByText("AB12 CD34");
      expect(screen.queryByRole("button", { name: "Descargar el respaldo cifrado de la clave" })).not.toBeInTheDocument();
      expect(screen.getByText(`Respaldo de la clave: ${REMOTO.motivo}`)).toBeInTheDocument();
    });
  });

  describe("Claves de API", () => {
    const CLAVES = [
      { id: 1, etiqueta: "api:ABCD1234", nombre: "plugin ficticio", estado: "vigente", ultimo_uso: null },
      { id: 2, etiqueta: "api:ZZZZ9999", nombre: "vieja", estado: "revocada", ultimo_uso: "2026-10-01 09:00:00" },
    ];

    test("lista las claves sin secreto", async () => {
      fetchFalso.mockResolvedValue(json(CLAVES));
      montar(<ClavesApi />);
      const tabla = await screen.findByRole("table", { name: "Claves de API" });
      expect(tabla).toHaveTextContent("api:ABCD1234");
      expect(tabla).toHaveTextContent("nunca");
      expect(tabla).toHaveTextContent("revocada");
    });

    test("la clave nueva se muestra una vez y se puede cerrar", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockResolvedValueOnce(json([]));
      fetchFalso.mockResolvedValueOnce(json({ id: 3, etiqueta: "api:NUEVA123", secreto: "NUEVA123.secreto-de-prueba" }));
      fetchFalso.mockResolvedValueOnce(json([{ ...CLAVES[0], id: 3, etiqueta: "api:NUEVA123" }]));
      montar(<ClavesApi />);
      await usuario.type(await screen.findByLabelText(/Para qué es esta clave/), "plugin ficticio");
      await usuario.click(screen.getByRole("button", { name: "Crear la clave de API" }));
      expect(await screen.findByTestId("secreto-de-api")).toHaveTextContent("NUEVA123.secreto-de-prueba");
      expect(fetchFalso.mock.calls[1][0]).toBe("/v1/admin/claves-api");
      expect(cuerpo(1)).toEqual({ nombre: "plugin ficticio" });
      expect(screen.getByRole("table", { name: "Claves de API" })).not.toHaveTextContent("secreto-de-prueba");
      await usuario.click(screen.getByRole("button", { name: /close|cerrar/i }));
      expect(screen.queryByTestId("secreto-de-api")).not.toBeInTheDocument();
      expect(document.body.textContent).not.toContain("secreto-de-prueba");
      expect(Object.values(localStorage).join()).not.toContain("secreto-de-prueba");
    });

    test("un rechazo del servidor (otro equipo) se muestra tal cual", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockResolvedValueOnce(json([]));
      fetchFalso.mockResolvedValueOnce(json({ detalle: REMOTO.motivo }, 403));
      montar(<ClavesApi />);
      await usuario.type(await screen.findByLabelText(/Para qué es esta clave/), "x");
      await usuario.click(screen.getByRole("button", { name: "Crear la clave de API" }));
      expect(await screen.findByText(REMOTO.motivo)).toBeInTheDocument();
      expect(screen.queryByTestId("secreto-de-api")).not.toBeInTheDocument();
    });

    test("revocar pide confirmación y ofrece solo las vigentes", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockResolvedValueOnce(json(CLAVES));
      fetchFalso.mockResolvedValueOnce(json({ ...CLAVES[0], estado: "revocada" }));
      fetchFalso.mockResolvedValueOnce(json(CLAVES.map((c) => ({ ...c, estado: "revocada" }))));
      montar(<ClavesApi />);
      const elegir = await screen.findByLabelText("Clave a revocar");
      expect(screen.queryByRole("option", { name: /api:ZZZZ9999/ })).not.toBeInTheDocument();
      await usuario.selectOptions(elegir, "1");
      await usuario.click(screen.getByRole("button", { name: "Revocar la clave" }));
      expect(fetchFalso).toHaveBeenCalledTimes(1);
      await usuario.click(screen.getByRole("button", { name: "Cancelar" }));
      expect(fetchFalso).toHaveBeenCalledTimes(1);
      await usuario.click(screen.getByRole("button", { name: "Revocar la clave" }));
      await usuario.click(screen.getByRole("button", { name: "Sí, revocar" }));
      await waitFor(() => expect(fetchFalso.mock.calls[1][0]).toBe("/v1/admin/claves-api/1/revocar"));
      expect((fetchFalso.mock.calls[1][1] as RequestInit).method).toBe("POST");
      await waitFor(() => expect(fetchFalso).toHaveBeenCalledTimes(3)); // recarga el listado
    });
  });

  describe("Instalación", () => {
    const BASE: InstalacionEstado = {
      red_local: false,
      direccion: "",
      puerto: 8501,
      avisos: [],
      respaldos: [{ nombre: "20261110-090000", motivo: "manual", bases: 2 }],
      pendientes: [],
      sensible: LOCAL,
    };

    test("muestra la red, la API y los respaldos con su descarga", async () => {
      fetchFalso.mockResolvedValue(json(BASE));
      montar(<Instalacion />);
      expect(await screen.findByText("Red local: apagada (solo http://127.0.0.1:8501)")).toBeInTheDocument();
      expect(screen.queryByText(/^API:/)).toBeNull();
      expect(screen.queryByText(/silice\.toml/)).toBeNull();
      expect(screen.getByText("20261110-090000 (manual, 2 bases)")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Descargar 20261110-090000 (.zip)" })).toBeInTheDocument();
    });

    test("desde otro equipo no ofrece la descarga y dice por qué", async () => {
      fetchFalso.mockResolvedValue(json({ ...BASE, sensible: REMOTO }));
      montar(<Instalacion />);
      expect(await screen.findByText(REMOTO.motivo)).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /Descargar/ })).not.toBeInTheDocument();
    });

    test("sin respaldos lo dice", async () => {
      fetchFalso.mockResolvedValue(json({ ...BASE, respaldos: [] }));
      montar(<Instalacion />);
      expect(await screen.findByText("Todavía no hay respaldos.")).toBeInTheDocument();
    });

    test("crea un respaldo y recarga", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockResolvedValueOnce(json({ ...BASE, respaldos: [] }));
      fetchFalso.mockResolvedValueOnce(json({ nombre: "20261110-100000" }));
      fetchFalso.mockResolvedValueOnce(json(BASE));
      montar(<Instalacion />);
      await usuario.click(await screen.findByRole("button", { name: "Crear respaldo ahora" }));
      expect(await screen.findByText("Respaldo creado: 20261110-100000")).toBeInTheDocument();
      expect(fetchFalso.mock.calls[1][0]).toBe("/v1/admin/instalacion/respaldos");
    });

    test("los eventos perdidos exigen marcar «Ya revisé esto» antes de revisar", async () => {
      const usuario = userEvent.setup();
      const pendiente = { nombre: "eventos_perdidos_20261110.json", diferencias: ["revocada: clave_api plugin"], eventos: 2 };
      fetchFalso.mockResolvedValueOnce(json({ ...BASE, pendientes: [pendiente] }));
      fetchFalso.mockResolvedValueOnce(json([]));
      fetchFalso.mockResolvedValueOnce(json(BASE));
      montar(<Instalacion />);
      expect(await screen.findByText("revocada: clave_api plugin")).toBeInTheDocument();
      const boton = screen.getByRole("button", { name: "Marcar como revisado" });
      expect(boton).toBeDisabled();
      await usuario.click(screen.getByLabelText("Ya revisé esto"));
      await usuario.click(boton);
      await waitFor(() =>
        expect(fetchFalso.mock.calls[1][0]).toBe("/v1/admin/instalacion/eventos/eventos_perdidos_20261110.json/revisar"),
      );
      await waitFor(() => expect(screen.queryByText("revocada: clave_api plugin")).not.toBeInTheDocument());
    });
  });
});
