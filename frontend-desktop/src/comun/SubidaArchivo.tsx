import { FileUploaderDropContainer } from "@carbon/react";
import { InlineNotification } from "./carbonEs";
import { useEffect, useRef, useState } from "react";

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
//
// Un solo texto accesible (pasada en navegador de la ola 2, D12): Carbon pinta la etiqueta en el botón y otra vez en un
// <label> oculto para el <input type="file">, que no recibe el foco (tabIndex -1) y solo lo abre el botón. Un lector de
// pantalla oía la etiqueta dos veces y el campo era otro «botón» con el mismo nombre: los dos van con aria-hidden y queda
// el botón, que es lo que se usa. El archivo sigue llegando por el mismo campo.
export function SubidaArchivo({ etiqueta, extensiones, alElegir, deshabilitada = false, id }: Props) {
  const [rechazo, setRechazo] = useState<string | null>(null);
  const zona = useRef<HTMLDivElement>(null);
  useEffect(() => {
    zona.current?.querySelectorAll('.cds--file > label, .cds--file > input[type="file"]').forEach((e) => e.setAttribute("aria-hidden", "true"));
  }, [etiqueta, deshabilitada]);

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
    <div className="silice-subida" ref={zona}>
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
