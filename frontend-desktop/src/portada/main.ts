// Portada web de pruebas (solo con npm run build:portada y SILICE_PORTADA_WEB=1): cablea los controles del pórtico 3D.
import "./portada.scss";
import { iniciarPortico3D, METADATOS_CAPA } from "./portico3d";
import type { Camara3D, Capa3D, Modo3D } from "./portico3d";

const canvas = document.getElementById("portico-canvas") as HTMLCanvasElement | null;
const portico = canvas ? iniciarPortico3D(canvas) : null;

const hudTitulo = document.getElementById("hud-titulo");
const hudDesc = document.getElementById("hud-desc");
const hudCosto = document.getElementById("hud-costo");
const btnPausa = document.getElementById("btn-pausa") as HTMLButtonElement | null;

function marcarActivo(botones: NodeListOf<HTMLButtonElement>, elegido: HTMLButtonElement) {
  for (const b of botones) b.classList.toggle("is-active", b === elegido);
}

// El botón dice lo que hará: «Pausar» si gira, «Rotar» si está quieto (también con movimiento reducido).
function rotularPausa() {
  if (btnPausa && portico) btnPausa.textContent = portico.estaRotando() ? "Pausar" : "Rotar";
}

function mostrarCapa(capa: Capa3D) {
  const meta = METADATOS_CAPA[capa];
  if (hudTitulo) hudTitulo.textContent = meta.titulo;
  if (hudDesc) hudDesc.textContent = meta.desc;
  if (hudCosto) hudCosto.textContent = meta.costo;
}

const botonesModo = document.querySelectorAll<HTMLButtonElement>("[data-mode]");
for (const btn of botonesModo) {
  btn.addEventListener("click", () => {
    const modo = btn.dataset.mode as Modo3D | undefined;
    if (!modo || !portico) return;
    portico.setModo(modo);
    marcarActivo(botonesModo, btn);
  });
}

const botonesCam = document.querySelectorAll<HTMLButtonElement>("[data-cam]");
for (const btn of botonesCam) {
  btn.addEventListener("click", () => {
    const cam = btn.dataset.cam as Camara3D | undefined;
    if (!cam || !portico) return;
    portico.setCamara(cam);
    marcarActivo(botonesCam, btn);
  });
}

const botonesCapa = document.querySelectorAll<HTMLButtonElement>("[data-layer]");
for (const btn of botonesCapa) {
  btn.addEventListener("click", () => {
    const capa = btn.dataset.layer as Capa3D | undefined;
    if (!capa || !portico) return;
    portico.setCapa(capa);
    marcarActivo(botonesCapa, btn);
    mostrarCapa(capa);
  });
}

if (btnPausa && portico) {
  rotularPausa();
  btnPausa.addEventListener("click", () => {
    portico.toggleRotar();
    rotularPausa();
  });
}

const btnCentrar = document.getElementById("btn-centrar") as HTMLButtonElement | null;
if (btnCentrar && portico) {
  btnCentrar.addEventListener("click", () => {
    portico.centrar();
    if (botonesModo[0]) marcarActivo(botonesModo, botonesModo[0]);
    if (botonesCam[0]) marcarActivo(botonesCam, botonesCam[0]);
    if (botonesCapa[0]) marcarActivo(botonesCapa, botonesCapa[0]);
    mostrarCapa("all");
    rotularPausa();
  });
}

// Al dejar la página se suelta el pórtico (bucle, observador y oyentes). Si la página queda en la caché de ida y vuelta
// (`persisted`) no se destruye: al volver, visibilitychange retoma el bucle.
window.addEventListener("pagehide", (evento) => {
  if (!(evento as PageTransitionEvent).persisted) portico?.destruir();
});
