import { describe, expect, test } from "vitest";
import {
  AVISO_TEMPORAL,
  CONFIRMACIONES,
  contrasenaValida,
  errorDeContrasena,
  formatearFecha,
  notaAccesos,
  puedeCrear,
  PESTANAS,
  avisoDeRoles,
  etiquetaDeRol,
  fechaDeHoy,
  filasDeAccesos,
  filasDeCuentas,
  filasDeRegistradas,
  puedeRevocarRegistrada,
  rolesEnTexto,
  textoDeLaClaveDeIA,
  topeParaEditar,
} from "./logica";
import type { AsistenteEstado } from "./logica";

describe("logica de Administracion", () => {
  test("las siete pestanas de Streamlit en su orden, todas migradas", () => {
    expect(PESTANAS.map((p) => p.titulo)).toEqual([
      "Cuentas",
      "Empresa y clave de firma",
      "Empresas registradas",
      "Claves de API",
      "Asistente de IA",
      "Accesos",
      "Instalación",
    ]);
    expect(PESTANAS.filter((p) => p.migrada).map((p) => p.id)).toEqual([
      "cuentas",
      "empresa",
      "registradas",
      "api",
      "asistente",
      "accesos",
      "instalacion",
    ]);
  });

  test("rotulos de roles como los de Streamlit; un rol desconocido se muestra tal cual", () => {
    expect(etiquetaDeRol("arma")).toBe("arma presupuestos (arma)");
    expect(etiquetaDeRol("revisa")).toBe("revisa paquetes (revisa)");
    expect(etiquetaDeRol("administrador")).toBe("administra la instalación (administrador)");
    expect(etiquetaDeRol("otro")).toBe("otro");
    expect(rolesEnTexto(["arma", "revisa"])).toBe("arma, revisa");
  });

  test("el aviso solo sale con arma y revisa a la vez", () => {
    expect(avisoDeRoles(["arma", "revisa"], "AVISO")).toBe("AVISO");
    expect(avisoDeRoles(["arma"], "AVISO")).toBeNull();
    expect(avisoDeRoles(["revisa", "administrador"], "AVISO")).toBeNull();
  });

  test("filas de cuentas: Usuario, Nombre, Roles, Activa si/no", () => {
    expect(
      filasDeCuentas([
        { id: 2, login: "ana", nombre: "Ana", roles: ["arma"], activa: true },
        { id: 3, login: "luis", nombre: "Luis", roles: ["arma", "revisa"], activa: false },
      ]),
    ).toEqual([
      { id: "2", usuario: "ana", nombre: "Ana", roles: "arma", activa: "sí" },
      { id: "3", usuario: "luis", nombre: "Luis", roles: "arma, revisa", activa: "no" },
    ]);
  });

  test("filas de accesos con la fecha legible", () => {
    expect(
      filasDeAccesos([{ id: 9, fecha_hora: "2026-11-10 09:00:00", tipo: "fallo", usuario: "ana", ip: "10.0.0.7", detalle: "" }]),
    ).toEqual([{ id: "9", fecha: "10 nov 2026, 09:00", evento: "fallo", usuario: "ana", ip: "10.0.0.7", detalle: "" }]);
  });

  test("textos fijos de Streamlit", () => {
    expect(notaAccesos(200)).toBe("Los 200 últimos eventos de acceso; este registro solo se agrega, no se edita.");
    expect(notaAccesos(50)).toContain("Los 50 últimos");
    expect(notaAccesos(null)).toContain("Los últimos eventos");
    expect(AVISO_TEMPORAL).toBe("La persona deberá cambiar la contraseña al entrar.");
  });

  test("fecha legible sin zonas horarias; lo raro se deja tal cual", () => {
    expect(formatearFecha("2026-10-18 14:32:05")).toBe("18 oct 2026, 14:32");
    expect(formatearFecha("2026-01-05T09:07:00")).toBe("5 ene 2026, 09:07");
    expect(formatearFecha("ayer")).toBe("ayer");
    expect(formatearFecha("2026-13-01 10:00:00")).toBe("2026-13-01 10:00:00");
  });

  test("la contrasena valida tiene de 10 a 128 caracteres", () => {
    expect(contrasenaValida("a".repeat(9))).toBe(false);
    expect(contrasenaValida("a".repeat(10))).toBe(true);
    expect(contrasenaValida("a".repeat(128))).toBe(true);
    expect(contrasenaValida("a".repeat(129))).toBe(false);
    expect(errorDeContrasena("")).toBeNull();
    expect(errorDeContrasena("corta")).toBe("La contraseña debe tener entre 10 y 128 caracteres.");
    expect(errorDeContrasena("a".repeat(10))).toBeNull();
  });

  test("crear exige usuario, nombre y contrasena valida", () => {
    const buena = "a".repeat(10);
    expect(puedeCrear("ana", "Ana", buena)).toBe(true);
    expect(puedeCrear(" ", "Ana", buena)).toBe(false);
    expect(puedeCrear("ana", "  ", buena)).toBe(false);
    expect(puedeCrear("ana", "Ana", "corta")).toBe(false);
  });

  test("la confirmacion advierte cuando la cuenta es la propia", () => {
    expect(CONFIRMACIONES.desactivar.propia).toMatch(/^Es su propia cuenta/);
    expect(CONFIRMACIONES.restablecer.propia).toMatch(/^Es su propia cuenta/);
  });

  test("filas de empresas registradas con las columnas de la clasica y el metodo dicho en espanol", () => {
    const metodos = [
      { valor: "telefono", etiqueta: "teléfono" },
      { valor: "qr", etiqueta: "código QR" },
    ];
    expect(
      filasDeRegistradas(
        [
          { id: 4, empresa: "Ajena Demo", huella: "AB12-CD34", estado: "activa", comprobada_con: "Pedro", metodo: "telefono" },
          { id: 5, empresa: "Otra Demo", huella: "EF56-GH78", estado: "revocada", comprobada_con: "Rosa", metodo: "desconocido" },
        ],
        metodos,
      ),
    ).toEqual([
      { id: "4", empresa: "Ajena Demo", huella: "AB12-CD34", estado: "activa", comprobada_con: "Pedro", metodo: "teléfono" },
      { id: "5", empresa: "Otra Demo", huella: "EF56-GH78", estado: "revocada", comprobada_con: "Rosa", metodo: "desconocido" },
    ]);
  });

  test("revocar una registrada exige el motivo escrito o el aviso firmado, como la clasica", () => {
    expect(puedeRevocarRegistrada("", false)).toBe(false);
    expect(puedeRevocarRegistrada("   ", false)).toBe(false);
    expect(puedeRevocarRegistrada("clave expuesta", false)).toBe(true);
    expect(puedeRevocarRegistrada("", true)).toBe(true);
  });

  test("la fecha de hoy en AAAA-MM-DD es la del reloj local, sin zona horaria", () => {
    expect(fechaDeHoy(new Date(2026, 0, 5, 23, 59))).toBe("2026-01-05");
    expect(fechaDeHoy(new Date(2026, 10, 30, 0, 1))).toBe("2026-11-30");
  });

  describe("asistente de IA", () => {
    const BASE: AsistenteEstado = {
      activo: true,
      proveedor: "claude",
      proveedores: [],
      modelo_claude: "claude-opus-5-5",
      modelo_local: "",
      anfitrion_ollama: "http://127.0.0.1:11434",
      tope_usd: "2.50",
      clave_registrada: null,
      clave_guardada: false,
      pide_contrasena: false,
      falta_el_componente: null,
      aviso_de_nube: "",
      sensible: { permitida: true, motivo: "" },
    };

    test("dice la clave registrada como la clasica: enmascarada, ninguna, guardada sin cargar o en el respaldo", () => {
      expect(textoDeLaClaveDeIA({ ...BASE, clave_registrada: "…5678" })).toBe("Clave registrada: …5678");
      expect(textoDeLaClaveDeIA(BASE)).toBe("Clave registrada: ninguna");
      expect(textoDeLaClaveDeIA({ ...BASE, activo: false, clave_guardada: true })).toBe(
        "Clave registrada: hay una guardada, pero no se carga mientras el asistente esté apagado (se carga al activarlo).",
      );
      expect(textoDeLaClaveDeIA({ ...BASE, pide_contrasena: true })).toBe(
        "Clave registrada: hay una en el respaldo cifrado (el almacén de credenciales no la tiene); escriba la contraseña del respaldo para cargarla.",
      );
    });

    test("el tope se edita con coma decimal y sin convertirlo en numero", () => {
      expect(topeParaEditar("2.50")).toBe("2,50");
      expect(topeParaEditar("2")).toBe("2");
      expect(topeParaEditar("0.0000001")).toBe("0,0000001");
    });
  });
});
