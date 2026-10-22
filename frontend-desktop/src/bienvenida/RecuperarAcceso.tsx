import { Button } from "@carbon/react";
import { useTituloDelDocumento } from "../comun/tituloDelDocumento";
import { FormularioDeReclamo } from "./FormularioDeReclamo";
import type { CuerpoDeReclamo, Politica } from "./FormularioDeReclamo";
import type { EstadoPrimerArranque } from "./usePrimerArranque";

interface Props {
  // Null si la API no contestó el estado: entonces se dan las dos formas de pedir el código y la política de siempre.
  info: EstadoPrimerArranque | null;
  onReclamar: (cuerpo: CuerpoDeReclamo) => Promise<void>;
  alVolver: () => void;
}

const POLITICA_POR_OMISION: Politica = { minimo: 10, maximo: 128 };
const ORDEN_DEL_PRODUCTO = "python -m operacion restablecer-administrador";
const ORDEN_DE_DESARROLLO = "uv run python scripts/restablecer_administrador.py";

// Con cuentas creadas: el código de restablecimiento lo emite un administrador del equipo (§3.4). La misma forma que la
// bienvenida, con otro texto. Sin un código pendiente la API responde como con un código errado: no revela si hay cuentas.
export function RecuperarAcceso({ info, onReclamar, alVolver }: Props) {
  useTituloDelDocumento("Recuperar el acceso");
  const modo = info?.modo;

  return (
    <main className="silice-entrada silice-bienvenida">
      <h1 className="cds--type-heading-04">Recuperar el acceso de administrador</h1>
      <p className="silice-entrada__texto cds--type-body-compact-01">
        Un administrador con acceso al equipo ejecuta el restablecimiento y le da un código nuevo de 20 caracteres. El
        código sirve una sola vez y vence a las 24 horas.
      </p>

      <section className="silice-bienvenida__seccion" aria-labelledby="recuperar-paso1">
        <h2 id="recuperar-paso1" className="cds--type-heading-compact-02">
          Paso 1: pida el código nuevo
        </h2>
        {modo !== "desarrollo" && (
          <p className="cds--type-body-compact-01">
            En Sílice instalado: el acceso directo «Sílice: recuperar acceso de administrador» del menú Inicio, o esta orden:{" "}
            <code className="silice-codigo silice-bienvenida__ruta">{ORDEN_DEL_PRODUCTO}</code>
          </p>
        )}
        {modo !== "producto" && (
          <p className="cds--type-body-compact-01">
            Desde la carpeta del programa:{" "}
            <code className="silice-codigo silice-bienvenida__ruta">{ORDEN_DE_DESARROLLO}</code>
          </p>
        )}
      </section>

      <section className="silice-bienvenida__seccion" aria-labelledby="recuperar-paso2">
        <h2 id="recuperar-paso2" className="cds--type-heading-compact-02">
          Paso 2: escriba el código y elija una contraseña nueva
        </h2>
        <p className="cds--type-body-compact-01">
          Si el usuario ya existe, recupera su acceso y queda como administrador; si no existe, se crea. En los dos casos se
          cierran sus sesiones abiertas.
        </p>
        <FormularioDeReclamo
          variante="recuperar"
          politica={info?.politica ?? POLITICA_POR_OMISION}
          onReclamar={onReclamar}
        />
      </section>

      <Button kind="ghost" size="sm" type="button" onClick={alVolver}>
        Volver a Entrar
      </Button>
    </main>
  );
}
