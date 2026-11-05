import { EstadoVacio } from "../comun/EstadoVacio";

// Los avisos de siempre cuando la cuenta no puede usar una pantalla: el marco los pinta en el lienzo, con su barra arriba, y
// nunca deja una pantalla en blanco (contrato de rutas §1; diseño visual §5). Un solo lugar para el texto.
export const MENSAJE_SIN_PERMISO = "Su cuenta no tiene permiso para esta pantalla o acción.";
export const MENSAJE_APAGADA = "Esta función está apagada en esta instalación. Quien administra puede encenderla en la Cuenta, sección «Especialidades, IA e instalación».";

// El aviso es el título de la pantalla que sustituye: el único h1 de la página (pasada en el navegador de F6, H9). Donde la página
// ya trae el suyo (la Cuenta, con el h1 de la sección), `nivel` lo baja.
interface Props {
  nivel?: 1 | 2 | 3;
}

export function AvisoSinPermiso({ nivel = 1 }: Props) {
  return (
    <div className="silice-pagina-aviso">
      <EstadoVacio nivel={nivel} titulo="Sin permiso" descripcion={MENSAJE_SIN_PERMISO} />
    </div>
  );
}

export function AvisoApagada({ nivel = 1 }: Props) {
  return (
    <div className="silice-pagina-aviso">
      <EstadoVacio nivel={nivel} titulo="Apagada" descripcion={MENSAJE_APAGADA} />
    </div>
  );
}
