import { FileUploaderDropContainer, InlineNotification } from "@carbon/react";
import { useState } from "react";

interface Props {
  // Lo que se le dice a la persona: «Suelte aquí el libro .xlsx, o haga clic para elegirlo».
  etiqueta: string;
  // Con punto y en minuscula: [".xlsx"].
  extensiones: string[];
  alElegir: (archivo: File) => void;
  deshabilitada?: boolean;
  id?: string;
}

function dichas(extensiones: string[]): string {
  return extensiones.join(" o ");
}

function tieneExtension(archivo: File, extensiones: string[]): boolean {
  const nombre = archivo.name.toLowerCase();
  return extensiones.some((e) => nombre.endsWith(e.toLowerCase()));
}

// Zona para soltar o elegir un archivo. Valida la extension aqui (el navegador a veces deja pasar otra cosa al
// arrastrar) y entrega solo archivos permitidos; el contenido lo valida la API.
export function SubidaArchivo({ etiqueta, extensiones, alElegir, deshabilitada = false, id }: Props) {
  const [rechazo, setRechazo] = useState<string | null>(null);

  const alAgregar = (_evento: unknown, { addedFiles }: { addedFiles: File[] }) => {
    const elegido = addedFiles.find((a) => tieneExtension(a, extensiones));
    if (!elegido) {
      setRechazo(`Solo se aceptan archivos ${dichas(extensiones)}.`);
      return;
    }
    setRechazo(null);
    alElegir(elegido);
  };

  return (
    <div className="silice-subida">
      <FileUploaderDropContainer
        id={id}
        accept={extensiones}
        labelText={etiqueta}
        multiple={false}
        disabled={deshabilitada}
        onAddFiles={alAgregar}
      />
      {rechazo && (
        <InlineNotification kind="error" role="alert" title="Archivo no válido" subtitle={rechazo} lowContrast hideCloseButton />
      )}
    </div>
  );
}
