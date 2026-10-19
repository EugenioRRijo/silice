import { describe, expect, test } from "vitest";
import {
  AVISO_TEMPORAL,
  NOTA_ACCESOS,
  PESTANAS,
  avisoDeRoles,
  etiquetaDeRol,
  filasDeAccesos,
  filasDeCuentas,
  rolesEnTexto,
} from "./logica";

describe("logica de Administracion", () => {
  test("las siete pestanas de Streamlit en su orden; solo Cuentas y Accesos estan migradas", () => {
    expect(PESTANAS.map((p) => p.titulo)).toEqual([
      "Cuentas",
      "Empresa y clave de firma",
      "Empresas registradas",
      "Claves de API",
      "Asistente de IA",
      "Accesos",
      "Instalación",
    ]);
    expect(PESTANAS.filter((p) => p.migrada).map((p) => p.id)).toEqual(["cuentas", "accesos"]);
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

  test("filas de accesos conservan la fecha tal como llega", () => {
    expect(
      filasDeAccesos([{ id: 9, fecha_hora: "2026-11-10 09:00:00", tipo: "fallo", usuario: "ana", ip: "10.0.0.7", detalle: "" }]),
    ).toEqual([{ id: "9", fecha: "2026-11-10 09:00:00", evento: "fallo", usuario: "ana", ip: "10.0.0.7", detalle: "" }]);
  });

  test("textos fijos de Streamlit", () => {
    expect(NOTA_ACCESOS).toBe("Los 200 últimos eventos de acceso; este registro solo se agrega, no se edita.");
    expect(AVISO_TEMPORAL).toBe("La persona deberá cambiar la contraseña al entrar.");
  });
});
