import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ErrorDeApi } from "../api/cliente";
import { alertaConTexto } from "../test/ayudas";
import { Bienvenida } from "./Bienvenida";
import type { EstadoPrimerArranque } from "./usePrimerArranque";

const info: EstadoPrimerArranque = {
  sin_cuentas: true,
  archivo_presente: true,
  modo: "producto",
  politica: { minimo: 10, maximo: 128 },
};

// Un código de mentira con la forma de uno real (20 caracteres en cuatro grupos), y una contraseña de prueba.
const CODIGO = "ABCD-EFGH-JKLM-NPQR-STUV";
const CLAVE = "una frase larga y tranquila";

type Usuario = ReturnType<typeof userEvent.setup>;

async function llenar(usuario: Usuario, opciones: { repetida?: string } = {}) {
  await usuario.type(screen.getByLabelText("Código de instalación"), CODIGO);
  await usuario.type(screen.getByLabelText("Su nombre"), "Ana Pérez");
  await usuario.type(screen.getByLabelText("Usuario"), "ana");
  await usuario.type(screen.getByLabelText("Contraseña"), CLAVE);
  await usuario.type(screen.getByLabelText("Repita la contraseña"), opciones.repetida ?? CLAVE);
}

const crear = () => screen.getByRole("button", { name: /Crear la cuenta y entrar|Creando la cuenta|Espere/ });
const valorDe = (etiqueta: string) => (screen.getByLabelText(etiqueta) as HTMLInputElement).value;

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("Bienvenida: página y texto (F2)", () => {
  test("un solo h1 «Bienvenida a Sílice» en heading-04, dentro de main, y el título del documento", () => {
    render(<Bienvenida info={info} onReclamar={vi.fn()} />);
    const h1s = screen.getAllByRole("heading", { level: 1 });
    expect(h1s).toHaveLength(1);
    expect(h1s[0]).toHaveTextContent("Bienvenida a Sílice");
    expect(h1s[0].className).toContain("cds--type-heading-04");
    expect(screen.getByRole("main")).toContainElement(h1s[0]);
    expect(document.title).toBe("Bienvenida a Sílice");
  });

  test("dice qué es Sílice en pocas líneas y que todo se guarda en este equipo", () => {
    render(<Bienvenida info={info} onReclamar={vi.fn()} />);
    expect(screen.getByText(/calcular cuánto cuesta una obra, partida por partida/)).toBeInTheDocument();
    expect(screen.getByText(/Todo se guarda en este equipo/)).toBeInTheDocument();
  });

  test("tiene los campos con su etiqueta visible y la casilla desmarcada", () => {
    render(<Bienvenida info={info} onReclamar={vi.fn()} />);
    for (const etiqueta of ["Código de instalación", "Su nombre", "Usuario", "Contraseña", "Repita la contraseña"]) {
      expect(screen.getByLabelText(etiqueta)).toBeInTheDocument();
    }
    const casilla = screen.getByRole("checkbox", { name: "Usaré esta cuenta también para armar presupuestos" });
    expect(casilla).not.toBeChecked();
    expect(screen.getByText(/Si usted trabaja solo, márquelo/)).toBeInTheDocument();
  });

  test("los atributos del navegador: código visible y sin ayudas, usuario, contraseñas nuevas", () => {
    render(<Bienvenida info={info} onReclamar={vi.fn()} />);
    const codigo = screen.getByLabelText("Código de instalación");
    expect(codigo).toHaveAttribute("type", "text"); // visible: se copia y pega, es de un solo uso
    expect(codigo).toHaveAttribute("autocomplete", "off");
    expect(codigo).toHaveAttribute("spellcheck", "false");
    expect(codigo).toHaveAttribute("autocapitalize", "characters");
    expect(screen.getByLabelText("Usuario")).toHaveAttribute("autocomplete", "username");
    expect(screen.getByLabelText("Usuario")).toHaveAttribute("autocapitalize", "none");
    expect(screen.getByLabelText("Contraseña")).toHaveAttribute("type", "password");
    expect(screen.getByLabelText("Contraseña")).toHaveAttribute("autocomplete", "new-password");
    expect(screen.getByLabelText("Repita la contraseña")).toHaveAttribute("type", "password");
    expect(screen.getByLabelText("Repita la contraseña")).toHaveAttribute("autocomplete", "new-password");
  });

  test("la política de la contraseña está siempre escrita, sale de la API y se enlaza al campo", () => {
    render(<Bienvenida info={{ ...info, politica: { minimo: 12, maximo: 64 } }} onReclamar={vi.fn()} />);
    const politica = screen.getByRole("group", { name: "Cómo debe ser la contraseña" });
    expect(politica).toHaveTextContent("De 12 a 64 caracteres");
    expect(politica).toHaveTextContent("No hace falta mezclar mayúsculas, números o símbolos");
    expect(politica).toHaveTextContent("Sílice no puede recuperarla");
    const descrito = screen.getByLabelText("Contraseña").getAttribute("aria-describedby") ?? "";
    expect(descrito.split(" ")).toContain(politica.id);
  });

  test("el contador dice cuántos caracteres lleva de los que pide la API", async () => {
    const usuario = userEvent.setup();
    render(<Bienvenida info={info} onReclamar={vi.fn()} />);
    expect(screen.getByText("0 de 10 caracteres como mínimo")).toBeInTheDocument();
    await usuario.type(screen.getByLabelText("Contraseña"), "abcd");
    expect(screen.getByText("4 de 10 caracteres como mínimo")).toBeInTheDocument();
  });

  test("explica qué pasa después; la frase de la casilla aparece solo si se marca", async () => {
    const usuario = userEvent.setup();
    render(<Bienvenida info={info} onReclamar={vi.fn()} />);
    expect(screen.getByRole("heading", { level: 2, name: "Qué pasa después" })).toBeInTheDocument();
    expect(screen.getByText(/El código se borra al usarse y no sirve otra vez/)).toBeInTheDocument();
    expect(screen.queryByText("Su cuenta ya puede hacerlo.")).not.toBeInTheDocument();
    await usuario.click(screen.getByRole("checkbox", { name: /armar presupuestos/ }));
    expect(screen.getByText("Su cuenta ya puede hacerlo.")).toBeInTheDocument();
  });

  test("en el producto instalado dice dónde está el archivo y que la ventana queda minimizada", () => {
    render(<Bienvenida info={info} onReclamar={vi.fn()} />);
    expect(screen.getByText(/minimizada/)).toBeInTheDocument();
    expect(screen.getByText("codigo_instalacion.txt", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("%LOCALAPPDATA%\\Silice\\datos\\codigo_instalacion.txt")).toBeInTheDocument();
    expect(screen.queryByText("data\\codigo_instalacion.txt", { exact: false })).not.toBeInTheDocument();
  });

  test("en desarrollo dice la ruta de la carpeta del programa", () => {
    render(<Bienvenida info={{ ...info, modo: "desarrollo" }} onReclamar={vi.fn()} />);
    expect(screen.getByText("data\\codigo_instalacion.txt", { exact: false })).toBeInTheDocument();
    expect(screen.queryByText("%LOCALAPPDATA%\\Silice\\datos\\codigo_instalacion.txt")).not.toBeInTheDocument();
  });

  test("si el archivo no está, lo dice y qué hacer; si está, no lo menciona", () => {
    const { unmount } = render(<Bienvenida info={{ ...info, archivo_presente: false }} onReclamar={vi.fn()} />);
    expect(screen.getByText(/No encuentro el archivo/)).toBeInTheDocument();
    expect(screen.getByText(/Cierre Sílice y ábralo otra vez/)).toBeInTheDocument();
    unmount();
    render(<Bienvenida info={info} onReclamar={vi.fn()} />);
    expect(screen.queryByText(/No encuentro el archivo/)).not.toBeInTheDocument();
  });

  test("no ofrece «Perdí el acceso»: sin cuentas no hay a qué volver", () => {
    render(<Bienvenida info={info} onReclamar={vi.fn()} />);
    expect(screen.queryByText(/Perdí el acceso/)).not.toBeInTheDocument();
  });
});

describe("Bienvenida: validación en el cliente (F2)", () => {
  test("dos contraseñas distintas dicen «Las dos contraseñas no coinciden.» y no llaman a la API", async () => {
    const usuario = userEvent.setup();
    const onReclamar = vi.fn();
    render(<Bienvenida info={info} onReclamar={onReclamar} />);
    await llenar(usuario, { repetida: "otra frase distinta" });
    await usuario.click(crear());
    expect((await alertaConTexto()).textContent).toContain("Las dos contraseñas no coinciden.");
    expect(onReclamar).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Repita la contraseña")).toHaveAttribute("aria-invalid", "true");
  });

  test("con campos vacíos no llama, marca cada campo y pasa el foco al resumen de errores", async () => {
    const usuario = userEvent.setup();
    const onReclamar = vi.fn();
    render(<Bienvenida info={info} onReclamar={onReclamar} />);
    await usuario.click(crear());
    expect(onReclamar).not.toHaveBeenCalled();
    const resumen = await alertaConTexto();
    expect(resumen).toHaveFocus();
    for (const texto of ["código de instalación", "nombre", "usuario", "contraseña"]) {
      expect(resumen.textContent?.toLowerCase()).toContain(texto);
    }
    expect(screen.getByLabelText("Código de instalación")).toHaveAttribute("aria-invalid", "true");
  });

  test("el foco va al resumen solo la primera vez; después solo se anuncia", async () => {
    const usuario = userEvent.setup();
    render(<Bienvenida info={info} onReclamar={vi.fn()} />);
    await usuario.click(crear());
    const resumen = await alertaConTexto();
    expect(resumen).toHaveFocus();
    await usuario.click(crear());
    expect(resumen).not.toHaveFocus(); // el foco se queda donde estaba: en el botón que se pulsó
    expect(crear()).toHaveFocus();
  });
});

describe("Bienvenida: el reclamo (F3)", () => {
  test("manda exactamente {codigo, usuario, nombre, contrasena, tambien_arma} y nunca la repetida", async () => {
    const usuario = userEvent.setup();
    const onReclamar = vi.fn().mockResolvedValue(undefined);
    render(<Bienvenida info={info} onReclamar={onReclamar} />);
    await llenar(usuario);
    await usuario.click(crear());
    expect(onReclamar).toHaveBeenCalledTimes(1);
    expect(onReclamar).toHaveBeenCalledWith({
      codigo: CODIGO,
      usuario: "ana",
      nombre: "Ana Pérez",
      contrasena: CLAVE,
      tambien_arma: false,
    });
    expect(Object.keys(onReclamar.mock.calls[0][0]).sort()).toEqual(
      ["codigo", "contrasena", "nombre", "tambien_arma", "usuario"],
    );
  });

  test("la casilla marcada manda tambien_arma: true", async () => {
    const usuario = userEvent.setup();
    const onReclamar = vi.fn().mockResolvedValue(undefined);
    render(<Bienvenida info={info} onReclamar={onReclamar} />);
    await llenar(usuario);
    await usuario.click(screen.getByRole("checkbox", { name: /armar presupuestos/ }));
    await usuario.click(crear());
    expect(onReclamar.mock.calls[0][0].tambien_arma).toBe(true);
  });

  test("quita los espacios alrededor del código pegado, del usuario y del nombre", async () => {
    const usuario = userEvent.setup();
    const onReclamar = vi.fn().mockResolvedValue(undefined);
    render(<Bienvenida info={info} onReclamar={onReclamar} />);
    await usuario.type(screen.getByLabelText("Código de instalación"), `  ${CODIGO}  `);
    await usuario.type(screen.getByLabelText("Su nombre"), "  Ana Pérez ");
    await usuario.type(screen.getByLabelText("Usuario"), " ana ");
    await usuario.type(screen.getByLabelText("Contraseña"), CLAVE);
    await usuario.type(screen.getByLabelText("Repita la contraseña"), CLAVE);
    await usuario.click(crear());
    expect(onReclamar).toHaveBeenCalledWith(
      expect.objectContaining({ codigo: CODIGO, nombre: "Ana Pérez", usuario: "ana" }),
    );
  });

  test("la contraseña no se recorta: los espacios alrededor son parte de ella", async () => {
    const usuario = userEvent.setup();
    const onReclamar = vi.fn().mockResolvedValue(undefined);
    render(<Bienvenida info={info} onReclamar={onReclamar} />);
    await usuario.type(screen.getByLabelText("Código de instalación"), CODIGO);
    await usuario.type(screen.getByLabelText("Su nombre"), "Ana");
    await usuario.type(screen.getByLabelText("Usuario"), "ana");
    await usuario.type(screen.getByLabelText("Contraseña"), " frase larga con espacios ");
    await usuario.type(screen.getByLabelText("Repita la contraseña"), " frase larga con espacios ");
    await usuario.click(crear());
    expect(onReclamar.mock.calls[0][0].contrasena).toBe(" frase larga con espacios ");
  });

  test("una sola petición en vuelo: mientras espera el botón dice «Creando la cuenta…» y no repite", async () => {
    const usuario = userEvent.setup();
    let resolver: () => void = () => {};
    const onReclamar = vi.fn().mockReturnValue(
      new Promise<void>((r) => {
        resolver = r;
      }),
    );
    render(<Bienvenida info={info} onReclamar={onReclamar} />);
    await llenar(usuario);
    await usuario.click(crear());
    const boton = screen.getByRole("button", { name: /Creando la cuenta/ });
    expect(boton).toBeDisabled();
    await usuario.click(boton);
    fireEnter(screen.getByLabelText("Usuario"));
    expect(onReclamar).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("status")).toHaveTextContent("Creando la cuenta…");
    await act(async () => resolver());
  });

  test("un 401 muestra el detalle tal cual y borra el código y las contraseñas, no el nombre ni el usuario", async () => {
    const usuario = userEvent.setup();
    const detalle = "El código no es válido o ya se usó.";
    const onReclamar = vi.fn().mockRejectedValue(new ErrorDeApi(401, detalle));
    render(<Bienvenida info={info} onReclamar={onReclamar} />);
    await llenar(usuario);
    await usuario.click(crear());
    expect(await alertaConTexto()).toHaveTextContent(detalle);
    expect(valorDe("Código de instalación")).toBe("");
    expect(valorDe("Contraseña")).toBe("");
    expect(valorDe("Repita la contraseña")).toBe("");
    expect(valorDe("Su nombre")).toBe("Ana Pérez");
    expect(valorDe("Usuario")).toBe("ana");
    expect(screen.getByLabelText("Código de instalación")).toHaveFocus();
    expect(crear()).toBeEnabled();
  });

  test("un 423 muestra el bloqueo tal cual y borra código y contraseñas", async () => {
    const usuario = userEvent.setup();
    const detalle = "Demasiados intentos con el código. Espere 15 minutos.";
    const onReclamar = vi.fn().mockRejectedValue(new ErrorDeApi(423, detalle));
    render(<Bienvenida info={info} onReclamar={onReclamar} />);
    await llenar(usuario);
    await usuario.click(crear());
    expect(await alertaConTexto()).toHaveTextContent(detalle);
    expect(valorDe("Código de instalación")).toBe("");
    expect(valorDe("Contraseña")).toBe("");
  });

  test("un 422 muestra la política de la API tal cual; borra el código y deja las contraseñas para corregir", async () => {
    const usuario = userEvent.setup();
    const detalle = "Revise el usuario, el nombre y la contraseña: la contraseña es muy conocida.";
    const onReclamar = vi.fn().mockRejectedValue(new ErrorDeApi(422, detalle));
    render(<Bienvenida info={info} onReclamar={onReclamar} />);
    await llenar(usuario);
    await usuario.click(crear());
    expect(await alertaConTexto()).toHaveTextContent(detalle);
    expect(valorDe("Código de instalación")).toBe("");
    expect(valorDe("Contraseña")).toBe(CLAVE);
  });

  test("un 503 y un fallo de red dicen su texto fijo y se puede reintentar", async () => {
    const usuario = userEvent.setup();
    const onReclamar = vi
      .fn()
      .mockRejectedValueOnce(new ErrorDeApi(503, "La base de datos está ocupada. Pruebe de nuevo en unos segundos."))
      .mockRejectedValueOnce(new ErrorDeApi(0, "No se pudo hablar con el programa de Sílice. Compruebe que esté encendido."));
    render(<Bienvenida info={info} onReclamar={onReclamar} />);
    await llenar(usuario);
    await usuario.click(crear());
    expect(await alertaConTexto()).toHaveTextContent("La base de datos está ocupada.");
    await usuario.type(screen.getByLabelText("Código de instalación"), CODIGO);
    await usuario.click(crear());
    expect(await screen.findByText(/No se pudo hablar con el programa de Sílice/)).toBeInTheDocument();
  });

  test("un 403 por equipo ajeno muestra su texto", async () => {
    const usuario = userEvent.setup();
    const detalle = "Esta operación solo se hace desde el propio equipo.";
    const onReclamar = vi.fn().mockRejectedValue(new ErrorDeApi(403, detalle));
    render(<Bienvenida info={info} onReclamar={onReclamar} />);
    await llenar(usuario);
    await usuario.click(crear());
    expect(await alertaConTexto()).toHaveTextContent(detalle);
  });

  test("un error que no es de la API se dice en español y no se traga", async () => {
    const usuario = userEvent.setup();
    const onReclamar = vi.fn().mockRejectedValue(new Error("boom con C:\\ruta\\interna"));
    render(<Bienvenida info={info} onReclamar={onReclamar} />);
    await llenar(usuario);
    await usuario.click(crear());
    const alerta = await alertaConTexto();
    expect(alerta).toHaveTextContent(/inesperado/i);
    expect(alerta.textContent).not.toContain("interna");
  });
});

describe("Bienvenida: un 429 con Retry-After (F3)", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  test("deshabilita el botón esos segundos, lo anuncia y lo habilita al terminar", async () => {
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const onReclamar = vi.fn().mockRejectedValue(new ErrorDeApi(429, "Demasiados intentos fallidos en este equipo.", 3));
    render(<Bienvenida info={info} onReclamar={onReclamar} />);
    await llenar(usuario);
    await usuario.click(crear());
    const alerta = await alertaConTexto();
    expect(alerta).toHaveTextContent("Demasiados intentos fallidos en este equipo.");
    expect(alerta).toHaveTextContent("Espere 3 segundos");
    expect(screen.getByRole("button", { name: /Espere 3 s/ })).toBeDisabled();
    await act(async () => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.getByRole("button", { name: /Espere 2 s/ })).toBeDisabled();
    await act(async () => {
      vi.advanceTimersByTime(2100);
    });
    expect(screen.getByRole("button", { name: "Crear la cuenta y entrar" })).toBeEnabled();
    expect(screen.getByRole("status")).toHaveTextContent("Ya puede volver a intentarlo.");
  });

  test("durante la espera, enviar con Intro tampoco llama a la API", async () => {
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const onReclamar = vi.fn().mockRejectedValue(new ErrorDeApi(429, "Demasiados intentos.", 5));
    render(<Bienvenida info={info} onReclamar={onReclamar} />);
    await llenar(usuario);
    await usuario.click(crear());
    await alertaConTexto();
    await usuario.type(screen.getByLabelText("Código de instalación"), CODIGO);
    fireEnter(screen.getByLabelText("Usuario"));
    expect(onReclamar).toHaveBeenCalledTimes(1);
  });
});

describe("Bienvenida: ningún secreto queda fuera del estado (F4)", () => {
  test("ni el código ni la contraseña van a localStorage, sessionStorage, el título ni la URL", async () => {
    const usuario = userEvent.setup();
    const espia = vi.spyOn(Storage.prototype, "setItem");
    const onReclamar = vi.fn().mockRejectedValue(new ErrorDeApi(401, "No."));
    render(<Bienvenida info={info} onReclamar={onReclamar} />);
    await llenar(usuario);
    await usuario.click(crear());
    await alertaConTexto();
    expect(espia).not.toHaveBeenCalled();
    for (const secreto of [CODIGO, CLAVE]) {
      expect(document.title).not.toContain(secreto);
      expect(window.location.href).not.toContain(secreto);
      expect(document.body.textContent).not.toContain(secreto);
    }
  });

  test("tras el éxito los campos de código y contraseña quedan vacíos en el DOM", async () => {
    const usuario = userEvent.setup();
    const onReclamar = vi.fn().mockResolvedValue(undefined);
    render(<Bienvenida info={info} onReclamar={onReclamar} />);
    await llenar(usuario);
    await usuario.click(crear());
    await screen.findByRole("button", { name: "Crear la cuenta y entrar" });
    expect(valorDe("Código de instalación")).toBe("");
    expect(valorDe("Contraseña")).toBe("");
    expect(valorDe("Repita la contraseña")).toBe("");
    for (const campo of document.querySelectorAll("input")) {
      expect(campo.getAttribute("value") ?? "").not.toContain(CLAVE);
      expect(campo.getAttribute("value") ?? "").not.toContain(CODIGO);
    }
  });
});

function fireEnter(campo: HTMLElement) {
  const formulario = campo.closest("form");
  if (!formulario) throw new Error("sin formulario");
  act(() => {
    formulario.requestSubmit();
  });
}
