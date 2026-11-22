import "./portada.scss";
import { iniciarPortico3D, METADATOS_CAPA } from "./portico3d";
import type { Camara3D, Capa3D, Modo3D } from "./portico3d";

const canvas = document.getElementById("portico-canvas") as HTMLCanvasElement | null;
const portico = canvas ? iniciarPortico3D(canvas) : null;

const hudTitulo = document.getElementById("hud-titulo");
const hudDesc = document.getElementById("hud-desc");
const hudCosto = document.getElementById("hud-costo");

function marcarActivo(botones: NodeListOf<HTMLButtonElement>, elegido: HTMLButtonElement) {
  for (const b of botones) b.classList.toggle("is-active", b === elegido);
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
    const meta = METADATOS_CAPA[capa];
    if (hudTitulo) hudTitulo.textContent = meta.titulo;
    if (hudDesc) hudDesc.textContent = meta.desc;
    if (hudCosto) hudCosto.textContent = meta.costo;
  });
}

const btnPausa = document.getElementById("btn-pausa") as HTMLButtonElement | null;
if (btnPausa && portico) {
  btnPausa.addEventListener("click", () => {
    const sigue = portico.toggleRotar();
    btnPausa.textContent = sigue ? "Pausar" : "Rotar";
  });
}

const btnCentrar = document.getElementById("btn-centrar") as HTMLButtonElement | null;
if (btnCentrar && portico) {
  btnCentrar.addEventListener("click", () => {
    portico.centrar();
    if (botonesModo[0]) marcarActivo(botonesModo, botonesModo[0]);
    if (botonesCam[0]) marcarActivo(botonesCam, botonesCam[0]);
    if (botonesCapa[0]) marcarActivo(botonesCapa, botonesCapa[0]);
    const meta = METADATOS_CAPA.all;
    if (hudTitulo) hudTitulo.textContent = meta.titulo;
    if (hudDesc) hudDesc.textContent = meta.desc;
    if (hudCosto) hudCosto.textContent = meta.costo;
    if (btnPausa) btnPausa.textContent = "Pausar";
  });
}

// Accion del boton de descarga de Windows en #descargar
const btnDescargarWin = document.getElementById("btn-descargar-win") as HTMLButtonElement | null;
const descargaEstado = document.getElementById("descarga-estado");
if (btnDescargarWin && descargaEstado) {
  btnDescargarWin.addEventListener("click", () => {
    descargaEstado.className = "descarga-estado is-info";
    descargaEstado.textContent =
      "El instalador de escritorio para Windows (x64) está en preparación final. Mientras tanto, puedes usar el entorno web de prueba (/app/) con el mismo motor local FastAPI + SQLite.";
  });
}
