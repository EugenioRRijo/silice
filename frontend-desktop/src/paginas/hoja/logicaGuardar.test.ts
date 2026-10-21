import { describe, expect, test } from "vitest";
import { ErrorDeApi } from "../../api/cliente";
import {
  cambiosDeRespuesta,
  clasificarErrorDeGuardado,
  cuerpoDeGuardado,
  motivoParaNoGuardar,
  rutaDeCambios,
  rutaDeGuardar,
  textoDeCambiosAGuardar,
  textoDeExito,
  usuarioDeSesion,
} from "./logicaGuardar";

// Guardar versión (3d-1: S1 del diseño §4.5 y E9 del §4.4). Los valores esperados están escritos a mano desde el contrato y
// la clásica (ui/hoja.py:1786-1799, 1882-1894; ui/paginas/hoja.py:497-500, 539-544), no se leen del código bajo prueba.
const ID = "id-borrador-aaaaaaaaaaaa";
const MAS_NUEVA =
  "Otra persona guardó la versión 004 después de que usted abrió la 003. Si guarda, su versión saldrá de la 003 y quedará como vigente sin lo de la 004.";

describe("rutas y cuerpo de S1 y E9", () => {
  test("rutas", () => {
    expect(rutaDeGuardar(ID)).toBe(`/v1/hoja/borradores/${ID}/guardar`);
    expect(rutaDeCambios(ID)).toBe(`/v1/hoja/borradores/${ID}/cambios`);
  });

  test("el cuerpo lleva rev y fuente; `confirmar_version_mas_nueva` solo si se confirmó; nunca un responsable (RF-82)", () => {
    expect(cuerpoDeGuardado(3, "Acta 12", false)).toEqual({ rev: 3, fuente: "Acta 12" });
    expect(cuerpoDeGuardado(3, "Acta 12", true)).toEqual({ rev: 3, fuente: "Acta 12", confirmar_version_mas_nueva: true });
    expect(Object.keys(cuerpoDeGuardado(3, "x", true))).not.toContain("responsable");
  });
});

describe("la lista de cambios (E9)", () => {
  const cambio = { objeto: "cantidad", clave: "AF-LLAVE|esp_puntos:P1", campo: "cantidad", antes: "3", despues: "5" };
  test("acepta la lista sola o envuelta en `cambios`", () => {
    expect(cambiosDeRespuesta([cambio])).toEqual([cambio]);
    expect(cambiosDeRespuesta({ cambios: [cambio] })).toEqual([cambio]);
  });
  test.each([[null], [undefined], ["x"], [{}], [{ cambios: "no" }], [7]])("%s no es una lista: null", (r) => {
    expect(cambiosDeRespuesta(r)).toBeNull();
  });
  test("una fila mal formada se ignora", () => {
    expect(cambiosDeRespuesta([cambio, { objeto: 1 }, null])).toEqual([cambio]);
  });
});

describe("por qué no se puede guardar todavía", () => {
  const base = { fuente: "Acta 12", primera: false, cambios: 2, soloLectura: false };
  test("sin cambios (H:1795)", () => {
    expect(motivoParaNoGuardar({ ...base, cambios: 0 })).toBe("No hay cambios para guardar: edite alguna celda primero.");
  });
  test("sin fuente del cambio, o solo espacios (H:1797)", () => {
    const texto = "Escriba la fuente del cambio: por qué se cambia y con qué respaldo.";
    expect(motivoParaNoGuardar({ ...base, fuente: "" })).toBe(texto);
    expect(motivoParaNoGuardar({ ...base, fuente: "   " })).toBe(texto);
  });
  test("primera versión: pide la fuente de la medida (H:1892) y no exige cambios (el servidor mira si la hoja está vacía)", () => {
    const p = { ...base, primera: true, cambios: 0 };
    expect(motivoParaNoGuardar({ ...p, fuente: "" })).toBe("Escriba la fuente de la medida: de dónde salen los datos (un plano, un acta).");
    expect(motivoParaNoGuardar(p)).toBeNull();
  });
  test("solo lectura (H:1842): la hoja no se guarda", () => {
    expect(motivoParaNoGuardar({ ...base, soloLectura: true })).toBe(
      "Esta versión está en solo lectura: alguna partida ya no tiene composición vigente en el catálogo.",
    );
  });
  test("con fuente y cambios se puede", () => {
    expect(motivoParaNoGuardar(base)).toBeNull();
  });
});

describe("textos", () => {
  test("cambios a guardar, en singular y plural", () => {
    expect(textoDeCambiosAGuardar(1)).toBe("1 cambio");
    expect(textoDeCambiosAGuardar(3)).toBe("3 cambios");
  });
  test("éxito de una versión (P:497-500, con tildes)", () => {
    const r = { codigo: "004", cambios: 3, total: { texto: "2703.86", exacto: "2703.860232" }, primera: false, mensaje: "x" };
    expect(textoDeExito(r, "OF-001")).toBe("Se guardó la versión 004 con 3 cambios registrados.");
    expect(textoDeExito({ ...r, cambios: 1 }, "OF-001")).toBe("Se guardó la versión 004 con 1 cambio registrado.");
  });
  test("éxito de la primera versión (P:539-544), con el total en es-VE", () => {
    const r = { codigo: "001", cambios: 1, total: { texto: "2703.86", exacto: "2703.860232" }, primera: true, mensaje: "x" };
    expect(textoDeExito(r, "OF-001")).toBe(
      "Se guardó la primera versión 001 del proyecto OF-001 (total 2.703,86). Quedó registrada su creación, con su fuente y su responsable.",
    );
  });
  test("el responsable es «Nombre <login>» (RF-82)", () => {
    expect(usuarioDeSesion({ nombre: "Ana Pérez", login: "ana" })).toBe("Ana Pérez <ana>");
  });
});

describe("qué le pasó al guardar", () => {
  const e = (estado: number, detalle: string, cuerpo: unknown = null) => new ErrorDeApi(estado, detalle, null, cuerpo);

  test("409 versión más nueva: nunca se sobrescribe en silencio; trae la versión nueva", () => {
    expect(clasificarErrorDeGuardado(e(409, MAS_NUEVA))).toEqual({ clase: "mas-nueva", mensaje: MAS_NUEVA, version: "004" });
  });
  test("409 versión más nueva: la versión sale del campo `version_mas_nueva` del contrato (3d-1) y, sin él, del texto", () => {
    expect(clasificarErrorDeGuardado(e(409, MAS_NUEVA, { detalle: MAS_NUEVA, version_mas_nueva: "007" })).version).toBe("007");
    expect(clasificarErrorDeGuardado(e(409, MAS_NUEVA, { detalle: MAS_NUEVA })).version).toBe("004");
  });
  test("409 rev viejo", () => {
    const d = "El borrador cambió en otra ventana: vuelva a cargarlo.";
    expect(clasificarErrorDeGuardado(e(409, d))).toEqual({ clase: "rev", mensaje: d, version: null });
  });
  test("409 ya se guardó como la versión {c}: trae la versión", () => {
    const d = "Este borrador ya se guardó como la versión 004; abra esa versión para seguir.";
    expect(clasificarErrorDeGuardado(e(409, d))).toEqual({ clase: "ya-guardado", mensaje: d, version: "004" });
  });
  test("409 de otro caso: no hay nada que recargar, solo abrir de nuevo", () => {
    const d = "El caso cambió desde que abrió este borrador: ábralo de nuevo en el caso actual.";
    expect(clasificarErrorDeGuardado(e(409, d)).clase).toBe("ausente");
  });
  test("409 de solo lectura u otro: el detalle tal cual", () => {
    const d = "Esta version esta en solo lectura: alguna de sus partidas ya no tiene composicion vigente en el catalogo.";
    expect(clasificarErrorDeGuardado(e(409, d))).toEqual({ clase: "otro", mensaje: d, version: null });
  });
  test("404 de borrador ausente (§3.1)", () => {
    const d =
      "Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). Lo que no guardó se perdió: abra la versión otra vez.";
    expect(clasificarErrorDeGuardado(e(404, d)).clase).toBe("ausente");
  });
  test("403 con el texto de la API", () => {
    const d = "La hoja del proyecto se edita y se guarda con una cuenta; la clave de API no sirve.";
    expect(clasificarErrorDeGuardado(e(403, d))).toEqual({ clase: "permiso", mensaje: d, version: null });
  });
  test("422 con el detalle (forma o dominio)", () => {
    const d = "Escriba la fuente del cambio: por que se cambia y con que respaldo.";
    expect(clasificarErrorDeGuardado(e(422, d))).toEqual({ clase: "rechazo", mensaje: d, version: null });
  });
  test("503: el mensaje fijo de la API, o el fijo del cliente si no trae", () => {
    const d = "No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro programa.";
    expect(clasificarErrorDeGuardado(e(503, d))).toEqual({ clase: "base", mensaje: d, version: null });
    expect(clasificarErrorDeGuardado(e(503, "")).mensaje).toBe(d);
  });
  test("lo que no es de la API no deja pasar su mensaje", () => {
    expect(clasificarErrorDeGuardado(new Error("SELECT * FROM x")).mensaje).toBe("Ocurrió un error inesperado. Inténtelo de nuevo.");
  });
});
