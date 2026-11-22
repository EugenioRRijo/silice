import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

// main.ts cablea la portada sobre el pórtico; aquí el pórtico es falso para mirar solo ese cableado.
const falso = vi.hoisted(() => ({
  rotando: false,
  setModo: vi.fn(),
  setCamara: vi.fn(),
  setCapa: vi.fn(),
  toggleRotar: vi.fn(),
  centrar: vi.fn(),
  destruir: vi.fn(),
}));

vi.mock("./portico3d", async (original) => ({
  ...(await original<typeof import("./portico3d")>()),
  iniciarPortico3D: () => ({
    setModo: falso.setModo,
    setCamara: falso.setCamara,
    setCapa: falso.setCapa,
    toggleRotar: () => {
      falso.rotando = !falso.rotando;
      return falso.rotando;
    },
    centrar: falso.centrar,
    estaRotando: () => falso.rotando,
    destruir: falso.destruir,
  }),
}));

const MARCADO = `
  <canvas id="portico-canvas"></canvas>
  <p id="hud-titulo"></p><p id="hud-desc"></p><strong id="hud-costo"></strong>
  <button type="button" id="btn-pausa">Pausar</button>
  <button type="button" id="btn-centrar">Centrar</button>
  <button type="button" data-layer="all">Todas</button>
  <button type="button" data-layer="indirectos">Indirectos</button>
`;

async function montar(rotando: boolean) {
  falso.rotando = rotando;
  document.body.innerHTML = MARCADO;
  vi.resetModules();
  await import("./main");
}

describe("cableado de la portada (main.ts)", () => {
  // Cada import de main.ts deja sus oyentes en window: se quitan al terminar para que una prueba no vea los de otra.
  let oyentes: [string, EventListenerOrEventListenerObject][] = [];
  beforeEach(() => {
    vi.clearAllMocks();
    const agregar = window.addEventListener.bind(window);
    vi.spyOn(window, "addEventListener").mockImplementation((tipo, oyente, opciones) => {
      if (oyente) oyentes.push([tipo, oyente]);
      agregar(tipo, oyente, opciones);
    });
  });
  afterEach(() => {
    vi.restoreAllMocks();
    for (const [tipo, oyente] of oyentes) window.removeEventListener(tipo, oyente);
    oyentes = [];
    document.body.innerHTML = "";
  });

  test("el botón de pausa dice lo que pasa: «Rotar» si el pórtico está quieto (movimiento reducido)", async () => {
    await montar(false);
    expect(document.getElementById("btn-pausa")?.textContent).toBe("Rotar");
    document.getElementById("btn-pausa")?.click();
    expect(document.getElementById("btn-pausa")?.textContent).toBe("Pausar");
  });

  test("«Centrar» deja el texto del botón según el pórtico, no siempre «Pausar»", async () => {
    await montar(false);
    document.getElementById("btn-centrar")?.click();
    expect(falso.centrar).toHaveBeenCalled();
    expect(document.getElementById("btn-pausa")?.textContent).toBe("Rotar");
  });

  test("elegir la capa de indirectos la pasa al pórtico y pone su ficha en el HUD", async () => {
    const { METADATOS_CAPA } = await import("./portico3d");
    await montar(true);
    document.querySelector<HTMLButtonElement>('[data-layer="indirectos"]')?.click();
    expect(falso.setCapa).toHaveBeenCalledWith("indirectos");
    expect(document.getElementById("hud-costo")?.textContent).toBe(METADATOS_CAPA.indirectos.costo);
  });

  test("al dejar la página (pagehide) se destruye el pórtico", async () => {
    await montar(true);
    expect(falso.destruir).not.toHaveBeenCalled();
    window.dispatchEvent(new Event("pagehide"));
    expect(falso.destruir).toHaveBeenCalledTimes(1);
  });
});
