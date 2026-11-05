import { EstadoVacio } from "../comun/EstadoVacio";

// Los avisos de siempre cuando la cuenta no puede usar una pantalla: el marco los pinta en el lienzo, con su barra arriba, y
// nunca deja una pantalla en blanco (contrato de rutas §1; diseño visual §5). Un solo lugar para el texto.
export const MENSAJE_SIN_PERMISO = "Su cuenta no tiene permiso para esta pantalla o acción.";
export const MENSAJE_APAGADA = "Esta función está apagada en esta instalación. Quien administra puede encenderla en Administración.";

export function AvisoSinPermiso() {
  return (
    <div className="silice-pagina-aviso">
      <EstadoVacio titulo="Sin permiso" descripcion={MENSAJE_SIN_PERMISO} />
    </div>
  );
}

export function AvisoApagada() {
  return (
    <div className="silice-pagina-aviso">
      <EstadoVacio titulo="Apagada" descripcion={MENSAJE_APAGADA} />
    </div>
  );
}
