import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import EmpresasRegistradas from "./EmpresasRegistradas";
import type { Registrada, RegistradasRespuesta } from "./logica";

// Pestaña «Empresas registradas»: textos y validaciones de `_pestana_registradas` y `_cambiar_registrada`
// (ui/paginas/administracion.py), escritos a mano.

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
const METODOS = [
  { valor: "telefono", etiqueta: "teléfono" },
  { valor: "en persona", etiqueta: "en persona" },
  { valor: "qr", etiqueta: "código QR" },
];
const AJENA: Registrada = {
  id: 4,
  empresa: "Contratista Ajena Demo, C.A.",
  huella: "K7QF-M9XR-A2PT-W4HN-C8DV",
  estado: "activa",
  comprobada_con: "Pedro Pérez",
  metodo: "telefono",
};
const VACIA: RegistradasRespuesta = { registradas: [], metodos: METODOS };
const CON_UNA: RegistradasRespuesta = { registradas: [AJENA], metodos: METODOS };

describe("Empresas registradas", () => {
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
        <EmpresasRegistradas />
      </ContextoAplicacion.Provider>,
    );
  }

  const llamada = (i: number) => fetchFalso.mock.calls[i] as [string, RequestInit | undefined];
  const formulario = (i: number) => llamada(i)[1]?.body as FormData;
  const campoDeArchivo = (id: string) => document.getElementById(id) as HTMLInputElement;
  const clave = () => new File(['{"formato":"silice-clave"}'], "clave-publica.silice-clave");

  test("lista las empresas con las columnas de la clásica y el método en español", async () => {
    fetchFalso.mockResolvedValueOnce(json(CON_UNA));
    montar();
    const tabla = await screen.findByRole("table", { name: "Empresas registradas" });
    // Cada encabezado termina con su título (Carbon antepone la ayuda de ordenar).
    const titulos = ["Empresa", "Huella", "Estado", "Comprobada con", "Método"];
    const encabezados = within(tabla).getAllByRole("columnheader");
    expect(encabezados).toHaveLength(titulos.length);
    encabezados.forEach((c, i) => expect(c.textContent?.endsWith(titulos[i])).toBe(true));
    expect(within(tabla).getByText("Contratista Ajena Demo, C.A.")).toBeInTheDocument();
    expect(within(tabla).getByText("K7QF-M9XR-A2PT-W4HN-C8DV")).toBeInTheDocument();
    expect(within(tabla).getByText("teléfono")).toBeInTheDocument();
    expect(llamada(0)[0]).toBe("/v1/admin/empresas-registradas");
  });

  test("sin empresas: estado vacío y sin la sección de retirar o revocar", async () => {
    fetchFalso.mockResolvedValueOnce(json(VACIA));
    montar();
    expect(await screen.findByText("Todavía no hay empresas registradas")).toBeInTheDocument();
    expect(screen.queryByText("Retirar o revocar la clave de una empresa registrada")).toBeNull();
    expect(screen.getByRole("heading", { name: "Registrar la clave de otra empresa" })).toBeInTheDocument();
  });

  test("elegir el archivo lo lee en la API y muestra la empresa declarada y la huella calculada", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValueOnce(json(VACIA));
    fetchFalso.mockResolvedValueOnce(json({ empresa: "Contratista Ajena Demo, C.A.", huella: "K7QF-M9XR-A2PT-W4HN-C8DV" }));
    montar();
    await screen.findByText("Todavía no hay empresas registradas");
    expect(screen.queryByLabelText("Huella leída por otro canal")).toBeNull();
    const archivo = clave();
    await usuario.upload(campoDeArchivo("adm-subir-clave"), archivo);
    expect(await screen.findByText("Contratista Ajena Demo, C.A.")).toBeInTheDocument();
    expect(screen.getByText(/Empresa declarada en el archivo/)).toBeInTheDocument();
    expect(screen.getByText(/Huella calculada del archivo/)).toHaveTextContent("K7QF-M9XR-A2PT-W4HN-C8DV");
    expect(screen.getByText(/Pida a la otra empresa que le lea su huella por teléfono/)).toBeInTheDocument();
    expect(llamada(1)[0]).toBe("/v1/admin/empresas-registradas/leer");
    expect(llamada(1)[1]?.method).toBe("POST");
    expect(formulario(1).get("archivo")).toBe(archivo);
    expect(new Headers(llamada(1)[1]?.headers).get("X-Silice-CSRF")).toBe("tok");
    expect(screen.getByLabelText("Huella leída por otro canal")).toBeInTheDocument();
  });

  test("un archivo que no es una clave muestra el detalle de la API y no ofrece registrar", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValueOnce(json(VACIA));
    fetchFalso.mockResolvedValueOnce(json({ detalle: "no es un archivo de clave publica de Silice" }, 400));
    montar();
    await screen.findByText("Todavía no hay empresas registradas");
    await usuario.upload(campoDeArchivo("adm-subir-clave"), clave());
    expect(await screen.findByText("no es un archivo de clave publica de Silice")).toBeInTheDocument();
    expect(screen.queryByLabelText("Huella leída por otro canal")).toBeNull();
  });

  test("registra con la huella leída por otro canal, con quién y cómo; luego limpia el formulario", async () => {
    const usuario = userEvent.setup();
    fetchFalso.mockResolvedValueOnce(json(VACIA));
    fetchFalso.mockResolvedValueOnce(json({ empresa: "Contratista Ajena Demo, C.A.", huella: "K7QF-M9XR-A2PT-W4HN-C8DV" }));
    fetchFalso.mockResolvedValueOnce(json(CON_UNA));
    montar();
    await screen.findByText("Todavía no hay empresas registradas");
    const archivo = clave();
    await usuario.upload(campoDeArchivo("adm-subir-clave"), archivo);
    await usuario.type(await screen.findByLabelText("Huella leída por otro canal"), "k7qf m9xr a2pt w4hn c8dv");
    await usuario.type(screen.getByLabelText("Comprobada con (persona)"), "Pedro Pérez");
    expect(screen.getByLabelText("Cómo se comprobó")).toHaveValue("telefono");
    await usuario.selectOptions(screen.getByLabelText("Cómo se comprobó"), "en persona");
    await usuario.click(screen.getByRole("button", { name: "Registrar la empresa" }));
    expect(await screen.findByText("Empresa registrada.")).toBeInTheDocument();
    expect(llamada(2)[0]).toBe("/v1/admin/empresas-registradas");
    const enviado = formulario(2);
    expect(enviado.get("archivo")).toBe(archivo);
    expect(enviado.get("huella")).toBe("k7qf m9xr a2pt w4hn c8dv");
    expect(enviado.get("comprobada_con")).toBe("Pedro Pérez");
    expect(enviado.get("metodo")).toBe("en persona");
    expect(screen.getByRole("table", { name: "Empresas registradas" })).toHaveTextContent("Contratista Ajena Demo, C.A.");
    expect(screen.queryByLabelText("Huella leída por otro canal")).toBeNull();
  });

  test("una huella que no coincide muestra el mensaje de la API y conserva lo escrito", async () => {
    const usuario = userEvent.setup();
    const detalle = "La huella leída no coincide con la de la clave (K7QF-M9XR-A2PT-W4HN-C8DV). No se registró nada.";
    fetchFalso.mockResolvedValueOnce(json(VACIA));
    fetchFalso.mockResolvedValueOnce(json({ empresa: "Contratista Ajena Demo, C.A.", huella: "K7QF-M9XR-A2PT-W4HN-C8DV" }));
    fetchFalso.mockResolvedValueOnce(json({ detalle }, 400));
    montar();
    await screen.findByText("Todavía no hay empresas registradas");
    await usuario.upload(campoDeArchivo("adm-subir-clave"), clave());
    await usuario.type(await screen.findByLabelText("Huella leída por otro canal"), "0000-0000-0000-0000-0000");
    await usuario.type(screen.getByLabelText("Comprobada con (persona)"), "Pedro");
    await usuario.click(screen.getByRole("button", { name: "Registrar la empresa" }));
    expect(await screen.findByText(detalle)).toBeInTheDocument();
    expect(screen.getByLabelText("Huella leída por otro canal")).toHaveValue("0000-0000-0000-0000-0000");
  });

  describe("retirar o revocar", () => {
    test("marcar como retirada manda la fecha elegida (hoy por omisión) tras confirmar", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockResolvedValueOnce(json(CON_UNA));
      fetchFalso.mockResolvedValueOnce(json({ ...CON_UNA, registradas: [{ ...AJENA, estado: "retirada" }] }));
      montar();
      expect(await screen.findByText(/Retirada: la empresa avisó que cambió de clave/)).toBeInTheDocument();
      const fecha = screen.getByLabelText("Fecha del retiro");
      expect((fecha as HTMLInputElement).value).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      await usuario.clear(fecha);
      await usuario.type(fecha, "2026-10-01");
      await usuario.click(screen.getByRole("button", { name: "Marcar como retirada" }));
      expect(fetchFalso).toHaveBeenCalledTimes(1);
      await usuario.click(screen.getByRole("button", { name: "Sí, marcar como retirada" }));
      expect(await screen.findByText("Clave marcada como retirada.")).toBeInTheDocument();
      expect(llamada(1)[0]).toBe("/v1/admin/empresas-registradas/4/retirar");
      expect(JSON.parse(String(llamada(1)[1]?.body))).toEqual({ fecha: "2026-10-01" });
      expect(screen.getByRole("table", { name: "Empresas registradas" })).toHaveTextContent("retirada");
    });

    test("revocar sin motivo ni aviso dice lo de la clásica y no llega a la API", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockResolvedValueOnce(json(CON_UNA));
      montar();
      await usuario.click(await screen.findByRole("button", { name: "Revocar" }));
      expect(await screen.findByText("Escriba el motivo o suba el aviso de revocación.")).toBeInTheDocument();
      expect(fetchFalso).toHaveBeenCalledTimes(1);
    });

    test("revocar con el motivo escrito lo manda tras confirmar", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockResolvedValueOnce(json(CON_UNA));
      fetchFalso.mockResolvedValueOnce(json({ ...CON_UNA, registradas: [{ ...AJENA, estado: "revocada" }] }));
      montar();
      await usuario.type(await screen.findByLabelText("Motivo de la revocación"), "clave expuesta");
      await usuario.click(screen.getByRole("button", { name: "Revocar" }));
      await usuario.click(screen.getByRole("button", { name: "Sí, revocar" }));
      expect(await screen.findByText("Clave revocada: los paquetes con ella ya no verifican.")).toBeInTheDocument();
      expect(llamada(1)[0]).toBe("/v1/admin/empresas-registradas/4/revocar");
      expect(formulario(1).get("motivo")).toBe("clave expuesta");
      expect(formulario(1).get("aviso")).toBeNull();
      expect(screen.getByLabelText("Motivo de la revocación")).toHaveValue("");
    });

    test("revocar con el aviso firmado lo sube aunque no haya motivo", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockResolvedValueOnce(json(CON_UNA));
      fetchFalso.mockResolvedValueOnce(json({ ...CON_UNA, registradas: [{ ...AJENA, estado: "revocada" }] }));
      montar();
      await screen.findByRole("button", { name: "Revocar" });
      const aviso = new File(['{"formato":"silice-revocacion"}'], "revocacion.silice-revocacion");
      await usuario.upload(campoDeArchivo("adm-ajena-aviso"), aviso);
      expect(screen.getByText(/revocacion\.silice-revocacion/)).toBeInTheDocument();
      await usuario.click(screen.getByRole("button", { name: "Revocar" }));
      await usuario.click(screen.getByRole("button", { name: "Sí, revocar" }));
      await screen.findByText("Clave revocada: los paquetes con ella ya no verifican.");
      expect(formulario(1).get("aviso")).toBe(aviso);
    });

    test("cancelar la confirmación no manda nada", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockResolvedValueOnce(json(CON_UNA));
      montar();
      await usuario.click(await screen.findByRole("button", { name: "Marcar como retirada" }));
      await usuario.click(screen.getByRole("button", { name: "Cancelar" }));
      expect(screen.getByRole("button", { name: "Marcar como retirada" })).toBeInTheDocument();
      expect(fetchFalso).toHaveBeenCalledTimes(1);
    });

    // VB-12: la confirmacion en linea reemplaza al boton y el foco caia a <body>; el lector de pantalla no la anunciaba.
    test("al pedir la confirmación el foco va a «Cancelar» y, al cancelar, vuelve al botón que la abrió", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockResolvedValueOnce(json(CON_UNA));
      montar();
      await usuario.click(await screen.findByRole("button", { name: "Marcar como retirada" }));
      expect(screen.getByRole("group", { name: "Confirmar" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Cancelar" })).toHaveFocus();
      await usuario.click(screen.getByRole("button", { name: "Cancelar" }));
      expect(screen.getByRole("button", { name: "Marcar como retirada" })).toHaveFocus();
    });

    test("con «Revocar» pasa igual: foco a «Cancelar» y de vuelta a «Revocar»", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockResolvedValueOnce(json(CON_UNA));
      montar();
      await usuario.type(await screen.findByLabelText("Motivo de la revocación"), "clave expuesta");
      await usuario.click(screen.getByRole("button", { name: "Revocar" }));
      expect(screen.getByRole("button", { name: "Cancelar" })).toHaveFocus();
      await usuario.keyboard("{Enter}");
      expect(screen.getByRole("button", { name: "Revocar" })).toHaveFocus();
    });

    // VB-22: sobre una clave ya revocada no hay nada que retirar ni que revocar.
    test("con la clave ya revocada, «Marcar como retirada» y «Revocar» quedan deshabilitados y se explica", async () => {
      fetchFalso.mockResolvedValueOnce(json({ ...CON_UNA, registradas: [{ ...AJENA, estado: "revocada" }] }));
      montar();
      expect(await screen.findByText(/Esta clave ya está revocada/)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Marcar como retirada" })).toBeDisabled();
      expect(screen.getByRole("button", { name: "Revocar" })).toBeDisabled();
    });

    // Punto 5 de la ronda 1: al confirmar, el boton de origen queda deshabilitado y el foco caia a <body>.
    test("tras confirmar «Sí, revocar» el foco queda en la lista de empresas, no en <body>", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockResolvedValueOnce(json(CON_UNA));
      fetchFalso.mockResolvedValueOnce(json({ ...CON_UNA, registradas: [{ ...AJENA, estado: "revocada" }] }));
      montar();
      await usuario.type(await screen.findByLabelText("Motivo de la revocación"), "clave expuesta");
      await usuario.click(screen.getByRole("button", { name: "Revocar" }));
      await usuario.click(screen.getByRole("button", { name: "Sí, revocar" }));
      await screen.findByText("Clave revocada: los paquetes con ella ya no verifican.");
      await waitFor(() => expect(screen.getByRole("combobox", { name: "Empresa" })).toHaveFocus());
    });

    test("tras confirmar «Sí, marcar como retirada» el foco queda en la lista de empresas", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockResolvedValueOnce(json(CON_UNA));
      fetchFalso.mockResolvedValueOnce(json({ ...CON_UNA, registradas: [{ ...AJENA, estado: "retirada" }] }));
      montar();
      await usuario.click(await screen.findByRole("button", { name: "Marcar como retirada" }));
      await usuario.click(screen.getByRole("button", { name: "Sí, marcar como retirada" }));
      await screen.findByText("Clave marcada como retirada.");
      await waitFor(() => expect(screen.getByRole("combobox", { name: "Empresa" })).toHaveFocus());
    });

    test("la explicación de la clave revocada es la descripción accesible de los botones deshabilitados", async () => {
      fetchFalso.mockResolvedValueOnce(json({ ...CON_UNA, registradas: [{ ...AJENA, estado: "revocada" }] }));
      montar();
      await screen.findByText(/Esta clave ya está revocada/);
      expect(screen.getByRole("button", { name: "Revocar" })).toHaveAccessibleDescription(/ya está revocada/);
      expect(screen.getByRole("button", { name: "Marcar como retirada" })).toHaveAccessibleDescription(/ya está revocada/);
    });

    test("con la clave activa los dos botones siguen disponibles y no hay explicación", async () => {
      fetchFalso.mockResolvedValueOnce(json(CON_UNA));
      montar();
      await screen.findByRole("button", { name: "Revocar" });
      expect(screen.getByRole("button", { name: "Revocar" })).toBeEnabled();
      expect(screen.queryByText(/ya está revocada/)).not.toBeInTheDocument();
    });

    test("un rechazo de la API se muestra con su detalle", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockResolvedValueOnce(json(CON_UNA));
      fetchFalso.mockResolvedValueOnce(json({ detalle: "El aviso de revocación no es válido para esta clave." }, 400));
      montar();
      await screen.findByRole("button", { name: "Revocar" });
      await usuario.upload(campoDeArchivo("adm-ajena-aviso"), new File(["{}"], "otro.silice-revocacion"));
      await usuario.click(screen.getByRole("button", { name: "Revocar" }));
      await usuario.click(screen.getByRole("button", { name: "Sí, revocar" }));
      expect(await screen.findByText("El aviso de revocación no es válido para esta clave.")).toBeInTheDocument();
    });
  });

  test("una sesión vencida avisa al marco", async () => {
    fetchFalso.mockResolvedValueOnce(json({ detalle: "Su sesión terminó." }, 401));
    montar();
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });
});
