import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";
import { ErrorDeApi } from "../api/cliente";
import { alertaConTexto } from "../test/ayudas";
import { RecuperarAcceso } from "./RecuperarAcceso";
import type { EstadoPrimerArranque } from "./usePrimerArranque";

const info: EstadoPrimerArranque = {
  sin_cuentas: false,
  archivo_presente: false,
  modo: "producto",
  politica: { minimo: 10, maximo: 128 },
};

const CODIGO = "WXYZ-2345-6789-ABCD-EFGH";
const CLAVE = "otra frase larga y tranquila";

async function llenar(usuario: ReturnType<typeof userEvent.setup>) {
  await usuario.type(screen.getByLabelText("Código de restablecimiento"), CODIGO);
  await usuario.type(screen.getByLabelText("Usuario del administrador"), "admin");
  await usuario.type(screen.getByLabelText("Su nombre"), "Ana Pérez");
  await usuario.type(screen.getByLabelText("Contraseña nueva"), CLAVE);
  await usuario.type(screen.getByLabelText("Repita la contraseña nueva"), CLAVE);
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("RecuperarAcceso", () => {
  test("un solo h1, título del documento y sin la casilla de armar presupuestos", () => {
    render(<RecuperarAcceso info={info} onReclamar={vi.fn()} alVolver={vi.fn()} />);
    const h1s = screen.getAllByRole("heading", { level: 1 });
    expect(h1s).toHaveLength(1);
    expect(h1s[0]).toHaveTextContent("Recuperar el acceso de administrador");
    expect(h1s[0].className).toContain("cds--type-heading-04");
    expect(document.title).toBe("Recuperar el acceso · Sílice");
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  test("explica quién da el código nuevo y que dura 24 horas", () => {
    render(<RecuperarAcceso info={info} onReclamar={vi.fn()} alVolver={vi.fn()} />);
    expect(screen.getByText(/Un administrador con acceso al equipo/)).toBeInTheDocument();
    expect(screen.getByText(/código nuevo de 20 caracteres/)).toBeInTheDocument();
    expect(screen.getByText(/24 horas/)).toBeInTheDocument();
  });

  test("en el producto instalado dice el acceso directo y la orden; en desarrollo, el script", () => {
    const { unmount } = render(<RecuperarAcceso info={info} onReclamar={vi.fn()} alVolver={vi.fn()} />);
    expect(screen.getByText(/Sílice: recuperar acceso de administrador/)).toBeInTheDocument();
    expect(screen.getByText("python -m operacion restablecer-administrador")).toBeInTheDocument();
    expect(screen.queryByText("uv run python scripts/restablecer_administrador.py")).not.toBeInTheDocument();
    unmount();
    render(<RecuperarAcceso info={{ ...info, modo: "desarrollo" }} onReclamar={vi.fn()} alVolver={vi.fn()} />);
    expect(screen.getByText("uv run python scripts/restablecer_administrador.py")).toBeInTheDocument();
    expect(screen.queryByText("python -m operacion restablecer-administrador")).not.toBeInTheDocument();
  });

  test("si no se pudo leer el estado de la instalación, da las dos formas", () => {
    render(<RecuperarAcceso info={null} onReclamar={vi.fn()} alVolver={vi.fn()} />);
    expect(screen.getByText("python -m operacion restablecer-administrador")).toBeInTheDocument();
    expect(screen.getByText("uv run python scripts/restablecer_administrador.py")).toBeInTheDocument();
  });

  test("avisa qué pasa si el usuario ya existe y si no existe", () => {
    render(<RecuperarAcceso info={info} onReclamar={vi.fn()} alVolver={vi.fn()} />);
    expect(screen.getByText(/Si el usuario ya existe/)).toBeInTheDocument();
    expect(screen.getByText(/si no existe, se crea/)).toBeInTheDocument();
  });

  test("tiene la política de la contraseña siempre escrita", () => {
    render(<RecuperarAcceso info={null} onReclamar={vi.fn()} alVolver={vi.fn()} />);
    expect(screen.getByRole("group", { name: "Cómo debe ser la contraseña" })).toHaveTextContent(
      "De 10 a 128 caracteres",
    );
  });

  test("manda el mismo cuerpo que el reclamo, con tambien_arma en falso y sin repetida", async () => {
    const usuario = userEvent.setup();
    const onReclamar = vi.fn().mockResolvedValue(undefined);
    render(<RecuperarAcceso info={info} onReclamar={onReclamar} alVolver={vi.fn()} />);
    await llenar(usuario);
    await usuario.click(screen.getByRole("button", { name: "Restablecer y entrar" }));
    expect(onReclamar).toHaveBeenCalledWith({
      codigo: CODIGO,
      usuario: "admin",
      nombre: "Ana Pérez",
      contrasena: CLAVE,
      tambien_arma: false,
    });
  });

  test("dos contraseñas distintas no llaman a la API", async () => {
    const usuario = userEvent.setup();
    const onReclamar = vi.fn();
    render(<RecuperarAcceso info={info} onReclamar={onReclamar} alVolver={vi.fn()} />);
    await usuario.type(screen.getByLabelText("Código de restablecimiento"), CODIGO);
    await usuario.type(screen.getByLabelText("Usuario del administrador"), "admin");
    await usuario.type(screen.getByLabelText("Su nombre"), "Ana");
    await usuario.type(screen.getByLabelText("Contraseña nueva"), CLAVE);
    await usuario.type(screen.getByLabelText("Repita la contraseña nueva"), "no es la misma");
    await usuario.click(screen.getByRole("button", { name: "Restablecer y entrar" }));
    expect((await alertaConTexto()).textContent).toContain("Las dos contraseñas no coinciden.");
    expect(onReclamar).not.toHaveBeenCalled();
  });

  test("un 401 sin código pendiente dice lo mismo que un código errado y borra el código", async () => {
    const usuario = userEvent.setup();
    const detalle = "El código no es válido o ya se usó.";
    const onReclamar = vi.fn().mockRejectedValue(new ErrorDeApi(401, detalle));
    render(<RecuperarAcceso info={info} onReclamar={onReclamar} alVolver={vi.fn()} />);
    await llenar(usuario);
    await usuario.click(screen.getByRole("button", { name: "Restablecer y entrar" }));
    expect(await alertaConTexto()).toHaveTextContent(detalle);
    expect((screen.getByLabelText("Código de restablecimiento") as HTMLInputElement).value).toBe("");
    expect((screen.getByLabelText("Contraseña nueva") as HTMLInputElement).value).toBe("");
  });

  test("«Volver a Entrar» llama a alVolver", async () => {
    const usuario = userEvent.setup();
    const alVolver = vi.fn();
    render(<RecuperarAcceso info={info} onReclamar={vi.fn()} alVolver={alVolver} />);
    await usuario.click(screen.getByRole("button", { name: "Volver a Entrar" }));
    expect(alVolver).toHaveBeenCalledTimes(1);
  });
});
