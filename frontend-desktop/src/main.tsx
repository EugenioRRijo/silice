import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./estilos/app.scss";
import { aplicarTamanoLetra, leerTamanoLetra } from "./comun/preferenciaDeLetra";

// Antes de pintar: sin esperar a que cargue la sesion, la letra ya es la que la persona eligio.
aplicarTamanoLetra(leerTamanoLetra());

const raiz = document.getElementById("raiz");
if (!raiz) throw new Error("Falta el elemento #raiz en index.html");

createRoot(raiz).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
