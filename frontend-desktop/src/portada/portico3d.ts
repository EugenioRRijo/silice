// Motor isometrico 3D ligero en Canvas2D para el Portico Estructural de la Portada (solo de pruebas).
// Cero dependencias externas, 100 % offline, respeta prefers-reduced-motion. Solo pide cuadros mientras el lienzo esta a
// la vista, la pestana visible y algo se mueve (giro, arrastre o una transicion de camara, modo o capa).
// Las cifras son un ejemplo con datos ficticios (no las calcula el nucleo); las capas suman el total al centimo y sus
// porcentajes el 100,0 % (portico3d.test.ts).

export type Modo3D = "despiece" | "radiografia" | "ensamblado";
export type Camara3D = "isometrica" | "corte" | "planta";
export type Capa3D = "all" | "concreto" | "acero" | "encofrado" | "equipos" | "indirectos";
// Las capas con pieza en el modelo; los indirectos y la utilidad no tienen volumen y se reparten sobre todas.
type CapaFisica = Exclude<Capa3D, "all" | "indirectos">;

interface Punto3D {
  x: number;
  y: number;
  z: number;
}

interface Caja3D {
  cx: number;
  cy: number;
  cz: number;
  w: number;
  h: number;
  d: number;
  capa: CapaFisica;
  color: string;
  borde: string;
  alpha?: number;
  offsetDespiece?: number;
}

interface CaraProyectada {
  pts: [number, number][];
  depth: number;
  fill: string;
  stroke: string;
  alpha: number;
}

export const METADATOS_CAPA: Record<Capa3D, { titulo: string; desc: string; costo: string }> = {
  all: {
    titulo: "Pórtico estructural · Despiece APU",
    desc: "Elevación vertical ordenada de losa, parrilla de cabillas, columnas y apuntalamiento H20.",
    costo: "242,64 USD/m³ total APU",
  },
  concreto: {
    titulo: "01 · Concreto f'c 250 kg/cm²",
    desc: "Zapatas, vigas de riostra, columnas estructurales, vigas de carga y losa vaciada (1,05 m³).",
    costo: "96,20 USD · 39,6 % del APU",
  },
  acero: {
    titulo: "02 · Cabillas y estribos Fy 4200",
    desc: "Armadura longitudinal en columnas, estribos dorados y parrilla superior de losa ½\".",
    costo: "42,20 USD · 17,4 % del APU",
  },
  encofrado: {
    titulo: "03 · Encofrado y mano de obra",
    desc: "Vigas H20 de madera, puntales telescópicos metálicos y formaleta con sargentos.",
    costo: "34,21 USD · 14,1 % del APU",
  },
  equipos: {
    titulo: "04 · Equipos de vaciado y nivelación",
    desc: "Tubería de bombeo de concreto, regla vibratoria y nivel láser de control en sitio.",
    costo: "21,85 USD · 9,0 % del APU",
  },
  indirectos: {
    titulo: "05 · Indirectos y utilidad",
    desc: "Administración, imprevistos y utilidad: no tienen pieza en el modelo y se reparten sobre todas las partidas.",
    costo: "48,18 USD · 19,9 % del APU",
  },
};

function construirPortico(): Caja3D[] {
  const cajas: Caja3D[] = [];
  const colX = 2.0;
  const colZ = 1.6;
  const esquinas: [number, number, boolean][] = [
    [-colX, -colZ, false],
    [colX, -colZ, false],
    [-colX, colZ, false],
    [colX, colZ, true],
  ];

  // Plinto base
  cajas.push({
    cx: 0,
    cy: 0.12,
    cz: 0,
    w: 6.2,
    h: 0.24,
    d: 5.2,
    capa: "concreto",
    color: "#2b303a",
    borde: "rgba(255,255,255,0.22)",
    offsetDespiece: 0,
  });

  // Zapatas y columnas
  for (const [cx, cz, corte] of esquinas) {
    cajas.push({
      cx,
      cy: 0.36,
      cz,
      w: 1.15,
      h: 0.24,
      d: 1.15,
      capa: "concreto",
      color: "#c5c1b7",
      borde: "#3f4550",
      offsetDespiece: 0,
    });
    const altoCol = corte ? 0.95 : 2.6;
    cajas.push({
      cx,
      cy: 0.48 + altoCol / 2,
      cz,
      w: 0.46,
      h: altoCol,
      d: 0.46,
      capa: "concreto",
      color: "#d9d5cc",
      borde: "#3f4550",
      offsetDespiece: 0.15,
    });
    // Armadura interna de columna (cabillas + estribos dorados)
    cajas.push({
      cx,
      cy: 2.05,
      cz,
      w: 0.28,
      h: 2.95,
      d: 0.28,
      capa: "acero",
      color: "#8f9dad",
      borde: "#f5c842",
      offsetDespiece: 0.45,
    });
    for (let s = 0; s < 5; s++) {
      cajas.push({
        cx,
        cy: 0.9 + s * 0.55,
        cz,
        w: 0.34,
        h: 0.05,
        d: 0.34,
        capa: "acero",
        color: "#f5c842",
        borde: "#1e2125",
        offsetDespiece: 0.45,
      });
    }
  }

  // Vigas superiores y losa en L (exponiendo esquina frontal derecha)
  cajas.push(
    { cx: 0, cy: 3.35, cz: -colZ, w: 4.5, h: 0.36, d: 0.44, capa: "concreto", color: "#c2beb4", borde: "#3b4049", offsetDespiece: 1.35 },
    { cx: -colX, cy: 3.35, cz: 0, w: 0.44, h: 0.36, d: 3.65, capa: "concreto", color: "#c2beb4", borde: "#3b4049", offsetDespiece: 1.35 },
    { cx: -0.45, cy: 3.35, cz: colZ, w: 3.3, h: 0.36, d: 0.44, capa: "concreto", color: "#c2beb4", borde: "#3b4049", offsetDespiece: 1.35 },
    { cx: 0, cy: 3.66, cz: -0.95, w: 5.0, h: 0.24, d: 2.25, capa: "concreto", color: "#dedad1", borde: "#3b4049", offsetDespiece: 1.5 },
    { cx: -1.15, cy: 3.66, cz: 1.12, w: 2.7, h: 0.24, d: 1.95, capa: "concreto", color: "#dedad1", borde: "#3b4049", offsetDespiece: 1.5 },
  );

  // Parrilla superior de acero
  for (let z = -1.55; z <= 1.56; z += 0.62) {
    cajas.push({
      cx: 0,
      cy: 3.45,
      cz: z,
      w: 4.6,
      h: 0.05,
      d: 0.05,
      capa: "acero",
      color: "#a7b4c4",
      borde: "#f5c842",
      offsetDespiece: 0.85,
    });
  }
  for (let x = -2.0; x <= 2.01; x += 0.8) {
    cajas.push({
      cx: x,
      cy: 3.5,
      cz: 0,
      w: 0.05,
      h: 0.05,
      d: 3.6,
      capa: "acero",
      color: "#f5c842",
      borde: "#1e2125",
      offsetDespiece: 0.85,
    });
  }

  // Encofrado: Vigas H20 + puntales metalicos + formaleta de columna
  for (const bx of [-1.2, -0.3]) {
    cajas.push({
      cx: bx,
      cy: 2.95,
      cz: 0,
      w: 0.16,
      h: 0.22,
      d: 2.9,
      capa: "encofrado",
      color: "#d99b38",
      borde: "#5d4635",
      offsetDespiece: 0.5,
    });
    for (const pz of [-0.95, 0.95]) {
      cajas.push({
        cx: bx,
        cy: 1.55,
        cz: pz,
        w: 0.1,
        h: 2.55,
        d: 0.1,
        capa: "encofrado",
        color: "#6b7380",
        borde: "#1e2125",
        offsetDespiece: 0.3,
      });
    }
  }
  cajas.push({
    cx: -colX - 0.04,
    cy: 1.5,
    cz: colZ + 0.04,
    w: 0.62,
    h: 1.45,
    d: 0.62,
    capa: "encofrado",
    color: "#6c513e",
    borde: "#d99b38",
    offsetDespiece: 0.35,
  });

  // Equipos: tuberia de bombeo amarilla + nivel laser en esquina
  cajas.push(
    { cx: 2.75, cy: 2.0, cz: -0.9, w: 0.2, h: 3.6, d: 0.2, capa: "equipos", color: "#f5c842", borde: "#1e2125", offsetDespiece: 0.65 },
    { cx: 1.5, cy: 3.95, cz: -0.9, w: 2.6, h: 0.2, d: 0.2, capa: "equipos", color: "#f5c842", borde: "#1e2125", offsetDespiece: 1.1 },
    { cx: 2.65, cy: 1.1, cz: 1.9, w: 0.28, h: 1.45, d: 0.28, capa: "equipos", color: "#252a32", borde: "#f5c842", offsetDespiece: 0.25 },
    { cx: 2.65, cy: 1.95, cz: 1.9, w: 0.34, h: 0.32, d: 0.34, capa: "equipos", color: "#f5c842", borde: "#1e2125", offsetDespiece: 0.25 },
  );

  return cajas;
}

const CARAS: [number, number, number, number, number][] = [
  [0, 1, 2, 3, 0.86], // front
  [5, 4, 7, 6, 0.72], // back
  [4, 0, 3, 7, 0.78], // left
  [1, 5, 6, 2, 0.92], // right
  [3, 2, 6, 7, 1.05], // top
  [4, 5, 1, 0, 0.64], // bottom
];

function sombrear(hex: string, factor: number): string {
  if (!hex.startsWith("#") || hex.length !== 7) return hex;
  const r = Math.min(255, Math.max(0, Math.round(parseInt(hex.slice(1, 3), 16) * factor)));
  const g = Math.min(255, Math.max(0, Math.round(parseInt(hex.slice(3, 5), 16) * factor)));
  const b = Math.min(255, Math.max(0, Math.round(parseInt(hex.slice(5, 7), 16) * factor)));
  return `rgb(${r}, ${g}, ${b})`;
}

export function iniciarPortico3D(canvas: HTMLCanvasElement) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;

  const cajas = construirPortico();
  const reducido =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  let modo: Modo3D = "despiece";
  let capaActiva: Capa3D = "all";
  let rotando = !reducido;
  let yaw = 0.68;
  let pitch = 0.42;
  let targetYaw = yaw;
  let targetPitch = pitch;
  let despieceFactor = 1;
  let arrastrando = false;
  let ultX = 0;
  let ultY = 0;

  function ajustarTamano() {
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.max(320, Math.round(rect.width));
    const h = Math.max(360, Math.round(rect.height));
    if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
      canvas.width = w * dpr;
      canvas.height = h * dpr;
    }
    ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { w, h };
  }

  function proyectar(p: Punto3D, w: number, h: number, cosY: number, sinY: number, cosP: number, sinP: number) {
    const x1 = p.x * cosY - p.z * sinY;
    const z1 = p.x * sinY + p.z * cosY;
    const y2 = (p.y - 2.2) * cosP - z1 * sinP;
    const z2 = (p.y - 2.2) * sinP + z1 * cosP;
    const dist = 14.2;
    const escala = Math.min(w, h) * 1.18;
    const factor = escala / Math.max(3.5, dist - z2);
    return {
      sx: w * 0.58 + x1 * factor,
      sy: h * 0.5 - y2 * factor,
      depth: z2,
    };
  }

  function dibujar() {
    const { w, h } = ajustarTamano();
    ctx!.fillStyle = "#14171c";
    ctx!.fillRect(0, 0, w, h);

    // Rejilla isometrica de plano tecnico
    const cosY = Math.cos(yaw);
    const sinY = Math.sin(yaw);
    const cosP = Math.cos(pitch);
    const sinP = Math.sin(pitch);

    ctx!.lineWidth = 1;
    for (let g = -6; g <= 6; g += 1) {
      const esMayor = g % 3 === 0;
      ctx!.strokeStyle = esMayor ? "rgba(245, 200, 66, 0.14)" : "rgba(255, 255, 255, 0.05)";
      const a1 = proyectar({ x: g, y: 0, z: -6 }, w, h, cosY, sinY, cosP, sinP);
      const a2 = proyectar({ x: g, y: 0, z: 6 }, w, h, cosY, sinY, cosP, sinP);
      ctx!.beginPath();
      ctx!.moveTo(a1.sx, a1.sy);
      ctx!.lineTo(a2.sx, a2.sy);
      ctx!.stroke();

      const b1 = proyectar({ x: -6, y: 0, z: g }, w, h, cosY, sinY, cosP, sinP);
      const b2 = proyectar({ x: 6, y: 0, z: g }, w, h, cosY, sinY, cosP, sinP);
      ctx!.beginPath();
      ctx!.moveTo(b1.sx, b1.sy);
      ctx!.lineTo(b2.sx, b2.sy);
      ctx!.stroke();
    }

    despieceFactor += (objetivoDespiece() - despieceFactor) * (reducido ? 1 : 0.14);

    const caras: CaraProyectada[] = [];
    for (const caja of cajas) {
      const cy = caja.cy + (caja.offsetDespiece ?? 0) * despieceFactor;
      const hw = caja.w / 2;
      const hh = caja.h / 2;
      const hd = caja.d / 2;
      const verts: Punto3D[] = [
        { x: caja.cx - hw, y: cy - hh, z: caja.cz + hd },
        { x: caja.cx + hw, y: cy - hh, z: caja.cz + hd },
        { x: caja.cx + hw, y: cy + hh, z: caja.cz + hd },
        { x: caja.cx - hw, y: cy + hh, z: caja.cz + hd },
        { x: caja.cx - hw, y: cy - hh, z: caja.cz - hd },
        { x: caja.cx + hw, y: cy - hh, z: caja.cz - hd },
        { x: caja.cx + hw, y: cy + hh, z: caja.cz - hd },
        { x: caja.cx - hw, y: cy + hh, z: caja.cz - hd },
      ];
      const proy = verts.map((v) => proyectar(v, w, h, cosY, sinY, cosP, sinP));

      let alpha = caja.alpha ?? 1;
      if (modo === "radiografia" && caja.capa === "concreto") alpha = 0.22;
      if (capaActiva === "indirectos") alpha *= 0.35;
      else if (capaActiva !== "all" && caja.capa !== capaActiva) alpha *= 0.18;

      for (const [i0, i1, i2, i3, shade] of CARAS) {
        const p0 = proy[i0]!;
        const p1 = proy[i1]!;
        const p2 = proy[i2]!;
        const p3 = proy[i3]!;
        caras.push({
          pts: [
            [p0.sx, p0.sy],
            [p1.sx, p1.sy],
            [p2.sx, p2.sy],
            [p3.sx, p3.sy],
          ],
          depth: (p0.depth + p1.depth + p2.depth + p3.depth) / 4,
          fill: sombrear(caja.color, shade),
          stroke: caja.borde,
          alpha,
        });
      }
    }

    caras.sort((a, b) => a.depth - b.depth);

    for (const cara of caras) {
      ctx!.save();
      ctx!.globalAlpha = cara.alpha;
      ctx!.beginPath();
      ctx!.moveTo(cara.pts[0]![0], cara.pts[0]![1]);
      ctx!.lineTo(cara.pts[1]![0], cara.pts[1]![1]);
      ctx!.lineTo(cara.pts[2]![0], cara.pts[2]![1]);
      ctx!.lineTo(cara.pts[3]![0], cara.pts[3]![1]);
      ctx!.closePath();
      ctx!.fillStyle = cara.fill;
      ctx!.fill();
      ctx!.strokeStyle = cara.stroke;
      ctx!.lineWidth = 1;
      ctx!.stroke();
      ctx!.restore();
    }
  }

  // Bucle a demanda: un cuadro pide el siguiente solo si algo se mueve. Fuera de la vista (IntersectionObserver) o con
  // la pestana oculta (visibilitychange) no se pide ninguno; al volver, se retoma.
  const EPSILON = 1e-3;
  let raf = 0;
  let aLaVista = true;
  let destruido = false;

  function objetivoDespiece() {
    return modo === "despiece" ? 1 : 0;
  }
  function sigueMoviendose() {
    return (
      (rotando && !arrastrando) ||
      Math.abs(targetYaw - yaw) > EPSILON ||
      Math.abs(targetPitch - pitch) > EPSILON ||
      Math.abs(objetivoDespiece() - despieceFactor) > EPSILON
    );
  }
  function puedeDibujar() {
    return !destruido && aLaVista && !document.hidden;
  }
  function pedirCuadro() {
    if (raf === 0 && puedeDibujar()) raf = requestAnimationFrame(cuadro);
  }
  function pausar() {
    if (raf !== 0) cancelAnimationFrame(raf);
    raf = 0;
  }
  function cuadro() {
    raf = 0;
    if (rotando && !arrastrando) {
      targetYaw += 0.004;
    }
    yaw += (targetYaw - yaw) * (reducido ? 1 : 0.14);
    pitch += (targetPitch - pitch) * (reducido ? 1 : 0.14);
    dibujar();
    if (sigueMoviendose()) pedirCuadro();
  }

  const observador =
    typeof IntersectionObserver === "function"
      ? new IntersectionObserver((entradas) => {
          aLaVista = entradas.some((e) => e.isIntersecting);
          if (aLaVista) pedirCuadro();
          else pausar();
        })
      : null;
  observador?.observe(canvas);
  const alCambiarVisibilidad = () => (document.hidden ? pausar() : pedirCuadro());
  document.addEventListener("visibilitychange", alCambiarVisibilidad);
  window.addEventListener("resize", pedirCuadro);
  pedirCuadro();

  const alPresionar = (e: PointerEvent) => {
    arrastrando = true;
    ultX = e.clientX;
    ultY = e.clientY;
    if (e.pointerId !== undefined) canvas.setPointerCapture?.(e.pointerId);
    pedirCuadro();
  };
  const alMover = (e: PointerEvent) => {
    if (!arrastrando) return;
    targetYaw += (e.clientX - ultX) * 0.008;
    targetPitch = Math.max(0.12, Math.min(1.25, targetPitch + (e.clientY - ultY) * 0.006));
    ultX = e.clientX;
    ultY = e.clientY;
    pedirCuadro();
  };
  const soltar = () => {
    arrastrando = false;
    pedirCuadro();
  };
  canvas.addEventListener("pointerdown", alPresionar);
  canvas.addEventListener("pointermove", alMover);
  canvas.addEventListener("pointerup", soltar);
  canvas.addEventListener("pointercancel", soltar);

  return {
    setModo(m: Modo3D) {
      modo = m;
      pedirCuadro();
    },
    setCamara(c: Camara3D) {
      if (c === "isometrica") {
        targetYaw = 0.68;
        targetPitch = 0.42;
      } else if (c === "corte") {
        targetYaw = 0.06;
        targetPitch = 0.18;
      } else {
        targetYaw = 0.55;
        targetPitch = 1.18;
      }
      pedirCuadro();
    },
    setCapa(capa: Capa3D) {
      capaActiva = capa;
      pedirCuadro();
    },
    toggleRotar(): boolean {
      rotando = !rotando;
      pedirCuadro();
      return rotando;
    },
    estaRotando(): boolean {
      return rotando;
    },
    centrar() {
      modo = "despiece";
      capaActiva = "all";
      targetYaw = 0.68;
      targetPitch = 0.42;
      rotando = !reducido;
      pedirCuadro();
    },
    destruir() {
      destruido = true;
      pausar();
      observador?.disconnect();
      document.removeEventListener("visibilitychange", alCambiarVisibilidad);
      window.removeEventListener("resize", pedirCuadro);
      canvas.removeEventListener("pointerdown", alPresionar);
      canvas.removeEventListener("pointermove", alMover);
      canvas.removeEventListener("pointerup", soltar);
      canvas.removeEventListener("pointercancel", soltar);
    },
  };
}
