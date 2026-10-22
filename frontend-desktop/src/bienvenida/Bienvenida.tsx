import { useState } from "react";
import { useTituloDelDocumento } from "../comun/tituloDelDocumento";
import { FormularioDeReclamo } from "./FormularioDeReclamo";
import type { CuerpoDeReclamo } from "./FormularioDeReclamo";
import type { EstadoPrimerArranque } from "./usePrimerArranque";

interface Props {
  info: EstadoPrimerArranque;
  onReclamar: (cuerpo: CuerpoDeReclamo) => Promise<void>;
}

// Dónde queda el archivo del código, según cómo se instaló Sílice (§3.5 del diseño).
const RUTA_DEL_ARCHIVO = {
  producto: "%LOCALAPPDATA%\\Silice\\datos\\codigo_instalacion.txt",
  desarrollo: "data\\codigo_instalacion.txt",
} as const;

// Primera vez (sin cuentas): una página, no un diálogo. Dice qué es Sílice, dónde está el código de un solo uso, pide los
// datos de la primera cuenta (administradora) y explica qué pasa después. Sin «Perdí el acceso»: sin cuentas no hay a qué volver.
export function Bienvenida({ info, onReclamar }: Props) {
  useTituloDelDocumento("Bienvenida a Sílice");
  const [tambienArma, setTambienArma] = useState(false);

  return (
    <main className="silice-entrada silice-bienvenida">
      <h1 className="cds--type-heading-04">Bienvenida a Sílice</h1>
      <p className="silice-entrada__texto cds--type-body-compact-01">
        Sílice le ayuda a calcular cuánto cuesta una obra, partida por partida, y a revisar presupuestos hechos en Excel.
      </p>
      <p className="silice-entrada__texto cds--type-body-compact-01">
        Todo se guarda en este equipo, en la carpeta de datos de Sílice. Nada sale de aquí sin que usted lo envíe.
      </p>

      <section className="silice-bienvenida__seccion" aria-labelledby="bienvenida-paso1">
        <h2 id="bienvenida-paso1" className="cds--type-heading-compact-02">
          Paso 1: busque su código de instalación
        </h2>
        <p className="cds--type-body-compact-01">
          Sílice dejó un código de un solo uso para crear la primera cuenta. Está en dos sitios:
        </p>
        <ul className="silice-bienvenida__lista cds--type-body-compact-01">
          <li>
            en el Bloc de notas que Sílice abrió solo la primera vez, y en la ventana del servidor, que el acceso directo
            deja minimizada (búsquela en la barra de tareas y busque «Código de instalación»), y
          </li>
          <li>
            en el archivo de texto de la carpeta de datos de Sílice:{" "}
            <code className="silice-codigo silice-bienvenida__ruta">{RUTA_DEL_ARCHIVO[info.modo]}</code>
            {info.modo === "desarrollo" && " (dentro de la carpeta del programa)"}
          </li>
        </ul>
        <p className="cds--type-body-compact-01">
          Son 20 letras y números en grupos de cuatro, por ejemplo XXXX-XXXX-XXXX-XXXX-XXXX. Cópielo y péguelo abajo.
        </p>
        {!info.archivo_presente && (
          <p className="silice-bienvenida__nota cds--type-body-compact-01">
            No encuentro el archivo. Cierre Sílice y ábralo otra vez: se crea un código nuevo al arrancar. Si sigue sin
            aparecer, un administrador del equipo ejecuta «Sílice: recuperar acceso de administrador».
          </p>
        )}
      </section>

      <section className="silice-bienvenida__seccion" aria-labelledby="bienvenida-paso2">
        <h2 id="bienvenida-paso2" className="cds--type-heading-compact-02">
          Paso 2: cree la cuenta del administrador
        </h2>
        <FormularioDeReclamo
          variante="bienvenida"
          politica={info.politica}
          onReclamar={onReclamar}
          tambienArma={tambienArma}
          alCambiarTambienArma={setTambienArma}
        />
      </section>

      <section className="silice-bienvenida__seccion" aria-labelledby="bienvenida-despues">
        <h2 id="bienvenida-despues" className="cds--type-heading-compact-02">
          Qué pasa después
        </h2>
        <p className="cds--type-body-compact-01">
          Entrará con esa cuenta. Esta cuenta administra Sílice: crea las demás cuentas, la empresa y las copias de seguridad.
        </p>
        <p className="cds--type-body-compact-01">
          Para armar presupuestos hace falta una cuenta con el rol «Arma».
          {tambienArma && <span> Su cuenta ya puede hacerlo.</span>}
        </p>
        <p className="cds--type-body-compact-01">El código se borra al usarse y no sirve otra vez.</p>
      </section>
    </main>
  );
}
