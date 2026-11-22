import { describe, expect, test } from "vitest";
import { METADATOS_CAPA } from "./portico3d";

// La portada web es solo de pruebas (Eugenio, 2026-11-22), pero se sirve con la misma CSP que /app: aquí se lee el
// fuente (portada.html y src/portada) y se exige lo mismo que verificar_dist.mjs al dist (RNF-08, RNF-22).
interface Fs {
  readdirSync(carpeta: string, opciones: { recursive: true }): string[];
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs };
  }
).process;
const fs = nodo.getBuiltinModule("node:fs");
const raiz = nodo.cwd();
const html = fs.readFileSync(`${raiz}/portada.html`, "utf-8");
const doc = new DOMParser().parseFromString(html, "text/html");
const archivosDePortada = fs.readdirSync(`${raiz}/src/portada`, { recursive: true }).map((n) => n.replaceAll("\\", "/"));
const fuentes = archivosDePortada
  .filter((n) => /\.(ts|scss)$/.test(n) && !/\.test\.ts$/.test(n))
  .map((n) => [n, fs.readFileSync(`${raiz}/src/portada/${n}`, "utf-8")] as const);
const textoVisible = (doc.body.textContent ?? "").replace(/\s+/g, " ");

describe("portada de pruebas: nada externo ni guiones en línea (RNF-08)", () => {
  test("ni portada.html ni src/portada piden nada a otro anfitrión", () => {
    expect(fuentes.length).toBeGreaterThanOrEqual(3);
    for (const [nombre, texto] of [["portada.html", html] as const, ...fuentes]) {
      expect(texto, nombre).not.toMatch(/(?:https?|wss?):\/\//i);
      expect(texto, nombre).not.toMatch(/\b(?:src|href)\s*=\s*["']\/\//i);
      expect(texto, nombre).not.toMatch(/(?:url\(\s*|@import\s+)["']?\/\//i);
    }
  });

  test("un solo guion, de módulo y con src; ningún manejador on* ni javascript:", () => {
    const guiones = [...doc.querySelectorAll("script")].map((g) => [g.getAttribute("type"), g.getAttribute("src"), g.textContent?.trim()]);
    expect(guiones).toEqual([["module", "/src/portada/main.ts", ""]]);
    const conManejador = [...doc.querySelectorAll("*")].filter((el) => [...el.attributes].some((a) => /^on/i.test(a.name)));
    expect(conManejador).toEqual([]);
    expect(html).not.toMatch(/javascript:/i);
  });
});

describe("portada de pruebas: sin imágenes ajenas ni promesas falsas", () => {
  // Auditoría del 2026-11-21: las cuatro webp traían marcas ajenas (AECOM, CAT, Panasonic, POTAIN) y un texto
  // alternativo que mostraba a Sílice donde no estaba.
  test("ningún archivo de imagen en src/portada ni <img> en la página", () => {
    expect(archivosDePortada.filter((n) => /\.(webp|png|jpe?g|gif|avif|svg)$/i.test(n))).toEqual([]);
    expect(doc.querySelectorAll("img, picture, source")).toHaveLength(0);
    expect(html).not.toContain("imagenes/");
  });

  test("la ventana de Sílice está hecha en código y cada una se rotula «Ejemplo con datos ficticios»", () => {
    const ventanas = [...doc.querySelectorAll("figure.ventana")];
    expect(doc.querySelector(".hero figure.ventana")).not.toBeNull();
    expect(ventanas.length).toBeGreaterThanOrEqual(3);
    for (const ventana of ventanas) {
      expect(ventana.querySelector("figcaption")?.textContent).toContain("Ejemplo con datos ficticios");
    }
  });

  test("no promete lo que el sistema no cumple", () => {
    for (const falso of [
      /0 conexiones salientes/i,
      /\.exe\b/i,
      /descarg/i,
      /nativa/i,
      /sin navegador/i,
      /nunca salen/i,
      /cero env[ií]o/i,
      /datos enviados a la nube/i,
      /quien arma no revisa/i,
      /quien elabora no aprueba/i,
      /separaci[oó]n estricta/i,
      /respaldos autom[aá]ticos/i,
      /L1[–-]L7/,
    ]) {
      expect(textoVisible).not.toMatch(falso);
    }
    expect(doc.getElementById("btn-descargar-win")).toBeNull();
    for (const [nombre, texto] of fuentes) expect(texto, nombre).not.toMatch(/btn-descargar|instalador/i);
  });
});

describe("portada de pruebas: el pórtico 3D", () => {
  test("es un ejemplo con datos ficticios y lo dice en su ficha y en su lienzo", () => {
    expect(doc.querySelector(".stage3d__hud-card")?.textContent).toContain("Ejemplo con datos ficticios");
    const lienzo = doc.getElementById("portico-canvas");
    expect(lienzo?.getAttribute("role")).toBe("img");
    expect(lienzo?.getAttribute("aria-label")).toContain("datos ficticios");
  });

  test("los botones de capas son los de METADATOS_CAPA y repiten sus montos y porcentajes", () => {
    const botones = [...doc.querySelectorAll<HTMLButtonElement>("[data-layer]")];
    expect(botones.map((b) => b.dataset.layer)).toEqual(Object.keys(METADATOS_CAPA));
    for (const boton of botones) {
      const meta = METADATOS_CAPA[boton.dataset.layer as keyof typeof METADATOS_CAPA];
      const precio = boton.querySelector(".layer-btn__price")?.textContent ?? "";
      const monto = /^([\d.]+,\d{2}) USD/.exec(precio)?.[1];
      expect(monto, boton.dataset.layer).toBeDefined();
      expect(meta.costo, boton.dataset.layer).toContain(`${monto} USD`);
      const porcentaje = /(\d+,\d) %/.exec(boton.querySelector(".layer-btn__code")?.textContent ?? "")?.[1];
      if (boton.dataset.layer !== "all") expect(meta.costo, boton.dataset.layer).toContain(`${porcentaje} %`);
    }
  });
});
