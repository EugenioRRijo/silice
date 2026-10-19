import { Button } from "@carbon/react";
import { Download } from "@carbon/icons-react";
import { useState } from "react";
import { ErrorDeApi, pedirBinario } from "../api/cliente";
import { AvisoError } from "./AvisoError";

interface Props {
  ruta: string;
  metodo?: "GET" | "POST";
  cuerpo?: object;
  etiqueta: string;
  // Nombre si la API no manda Content-Disposition.
  nombrePorOmision: string;
  // La API contesto 401: la sesion vencio.
  alExpirar?: () => void;
  kind?: "primary" | "secondary" | "tertiary" | "ghost";
  // Tamano del boton: "sm" (32 px, densidad de las tablas) o "md".
  size?: "sm" | "md";
}

// Guarda un blob en la carpeta de descargas. El enlace se crea y se descarta sin tocar la pagina.
export function guardarBlob(blob: Blob, nombre: string): void {
  const direccion = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = direccion;
  enlace.download = nombre;
  enlace.rel = "noopener";
  enlace.click();
  URL.revokeObjectURL(direccion);
}

// Boton que baja una respuesta binaria de la API (PDF, xlsx, zip) con el nombre que ella propone.
export function DescargaArchivo({
  ruta,
  metodo = "GET",
  cuerpo,
  etiqueta,
  nombrePorOmision,
  alExpirar,
  kind = "tertiary",
  size = "md",
}: Props) {
  const [bajando, setBajando] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function bajar() {
    setBajando(true);
    setError(null);
    try {
      const { blob, nombre } = await pedirBinario(ruta, { metodo, cuerpo, respaldo: nombrePorOmision });
      guardarBlob(blob, nombre);
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar?.();
      setError(e);
    } finally {
      setBajando(false);
    }
  }

  return (
    <div className="silice-descarga">
      <Button kind={kind} size={size} renderIcon={Download} disabled={bajando} onClick={() => void bajar()}>
        {bajando ? "Descargando…" : etiqueta}
      </Button>
      <AvisoError error={error} titulo="No se pudo descargar" alCerrar={() => setError(null)} />
    </div>
  );
}
