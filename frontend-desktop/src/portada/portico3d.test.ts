import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { METADATOS_CAPA, iniciarPortico3D } from "./portico3d";

// Las cifras del pórtico son un ejemplo con datos ficticios (no salen del núcleo): aquí solo se exige que cuadren,
// como cuadraría un APU de Sílice. Montos con coma decimal y punto de miles (NORMAS).
function centimos(texto: string): number {
  const m = /(\d{1,3}(?:\.\d{3})*),(\d{2}) USD/.exec(texto);
  if (!m) throw new Error(`sin monto en «${texto}»`);
  return Number(m[1].replaceAll(".", "")) * 100 + Number(m[2]);
}
function decimas(texto: string): number {
  const m = /(\d{1,3}),(\d) %/.exec(texto);
  if (!m) throw new Error(`sin porcentaje en «${texto}»`);
  return Number(m[1]) * 10 + Number(m[2]);
}

describe("cifras de ejemplo del pórtico", () => {
  const capas = Object.entries(METADATOS_CAPA).filter(([capa]) => capa !== "all");
  const total = centimos(METADATOS_CAPA.all.costo);

  test("las capas suman el total del APU al céntimo", () => {
    expect(total).toBe(24264);
    expect(capas.reduce((suma, [, meta]) => suma + centimos(meta.costo), 0)).toBe(total);
  });

  test("cada porcentaje es su monto sobre el total, a una décima, y entre todos dan 100,0 %", () => {
    for (const [capa, meta] of capas) {
      expect(decimas(meta.costo), capa).toBe(Math.round((centimos(meta.costo) * 1000) / total));
    }
    expect(capas.reduce((suma, [, meta]) => suma + decimas(meta.costo), 0)).toBe(1000);
  });

  test("lo que no tiene pieza en el modelo (indirectos y utilidad) también es una capa", () => {
    expect(METADATOS_CAPA.indirectos.titulo).toBe("05 · Indirectos y utilidad");
  });
});

// Un lienzo 2D falso: jsdom no dibuja. Cualquier método es un no-op y cualquier propiedad se acepta.
function contextoFalso(): CanvasRenderingContext2D {
  return new Proxy({} as Record<string, unknown>, {
    get: (destino, clave) => (clave in destino ? destino[clave as string] : () => undefined),
    set: (destino, clave, valor) => {
      destino[clave as string] = valor;
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
}

describe("animación del pórtico", () => {
  let cola: Map<number, FrameRequestCallback>;
  let siguiente: number;
  let observadores: { alCambiar: IntersectionObserverCallback; observe: ReturnType<typeof vi.fn>; disconnect: ReturnType<typeof vi.fn> }[];
  let reducido: boolean;
  let lienzo: HTMLCanvasElement;

  const cuadrosPendientes = () => cola.size;
  function correrCuadros(veces = 1) {
    for (let i = 0; i < veces; i++) {
      const pendientes = [...cola.entries()];
      cola.clear();
      for (const [, cb] of pendientes) cb(performance.now());
    }
  }
  function verse(aLaVista: boolean) {
    const o = observadores.at(-1)!;
    o.alCambiar([{ isIntersecting: aLaVista } as IntersectionObserverEntry], {} as IntersectionObserver);
  }
  function ocultarPestana(oculta: boolean) {
    Object.defineProperty(document, "hidden", { configurable: true, get: () => oculta });
    document.dispatchEvent(new Event("visibilitychange"));
  }

  beforeEach(() => {
    cola = new Map();
    siguiente = 1;
    observadores = [];
    reducido = false;
    vi.stubGlobal(
      "requestAnimationFrame",
      vi.fn((cb: FrameRequestCallback) => {
        const id = siguiente++;
        cola.set(id, cb);
        return id;
      }),
    );
    vi.stubGlobal(
      "cancelAnimationFrame",
      vi.fn((id: number) => {
        cola.delete(id);
      }),
    );
    vi.stubGlobal(
      "IntersectionObserver",
      class {
        observe = vi.fn();
        disconnect = vi.fn();
        unobserve = vi.fn();
        constructor(alCambiar: IntersectionObserverCallback) {
          observadores.push({ alCambiar, observe: this.observe, disconnect: this.disconnect });
        }
      },
    );
    vi.stubGlobal("matchMedia", (consulta: string) => ({ matches: reducido && consulta.includes("reduce"), media: consulta }));
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation((() => contextoFalso()) as never);
    lienzo = document.createElement("canvas");
    document.body.append(lienzo);
  });

  afterEach(() => {
    lienzo.remove();
    Object.defineProperty(document, "hidden", { configurable: true, get: () => false });
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  test("observa su lienzo y dibuja mientras está a la vista; fuera de ella no pide cuadros", () => {
    const portico = iniciarPortico3D(lienzo)!;
    expect(observadores).toHaveLength(1);
    expect(observadores[0]!.observe).toHaveBeenCalledWith(lienzo);
    verse(true);
    expect(cuadrosPendientes()).toBe(1);
    correrCuadros(3);
    expect(cuadrosPendientes()).toBe(1); // gira: sigue pidiendo
    verse(false);
    expect(cuadrosPendientes()).toBe(0);
    portico.setModo("radiografia");
    expect(cuadrosPendientes()).toBe(0); // un cambio fuera de la vista no despierta el bucle
    verse(true);
    expect(cuadrosPendientes()).toBe(1);
    portico.destruir();
  });

  test("con la pestaña oculta se detiene y al volver sigue", () => {
    const portico = iniciarPortico3D(lienzo)!;
    verse(true);
    ocultarPestana(true);
    expect(cuadrosPendientes()).toBe(0);
    ocultarPestana(false);
    expect(cuadrosPendientes()).toBe(1);
    portico.destruir();
  });

  test("con movimiento reducido no gira y deja de pedir cuadros cuando la escena queda quieta", () => {
    reducido = true;
    const portico = iniciarPortico3D(lienzo)!;
    expect(portico.estaRotando()).toBe(false);
    verse(true);
    correrCuadros(5);
    expect(cuadrosPendientes()).toBe(0);
    portico.setCapa("acero");
    expect(cuadrosPendientes()).toBe(1); // un cambio pide un cuadro
    correrCuadros(5);
    expect(cuadrosPendientes()).toBe(0);
    portico.destruir();
  });

  test("destruir corta el bucle, desconecta el observador y suelta los oyentes", () => {
    const portico = iniciarPortico3D(lienzo)!;
    verse(true);
    portico.destruir();
    expect(cuadrosPendientes()).toBe(0);
    expect(observadores[0]!.disconnect).toHaveBeenCalled();
    ocultarPestana(false);
    window.dispatchEvent(new Event("resize"));
    lienzo.dispatchEvent(new Event("pointerdown"));
    portico.setCamara("planta");
    expect(cuadrosPendientes()).toBe(0);
  });
});
