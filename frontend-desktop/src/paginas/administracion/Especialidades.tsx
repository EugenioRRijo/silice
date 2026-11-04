import { Toggle } from "@carbon/react";
import { useCallback, useEffect, useState } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { fijarModulo, leerModulos } from "../../api/modulos";
import type { ModuloRespuesta } from "../../api/modulos";
import { AvisoError } from "../../comun/AvisoError";
import { EsqueletoPagina } from "../../comun/EsqueletoPagina";
import { useAplicacion } from "../../shell/contexto";

const primeraEnMayuscula = (texto: string) => texto.charAt(0).toUpperCase() + texto.slice(1);

// Pestaña «Especialidades» (plan vial, Tarea 19): qué partes del programa usa esta instalación. Apagar una no borra nada:
// deja de ofrecerse y de contestar, y al encenderla todo vuelve igual. Solo el administrador la ve (`activar_modulos`).
export default function Especialidades() {
  const { alExpirar, recargarModulos } = useAplicacion();
  const [modulos, setModulos] = useState<ModuloRespuesta[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [ocupada, setOcupada] = useState(false);

  const fallar = useCallback(
    (e: unknown) => {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      setError(e);
    },
    [alExpirar],
  );

  useEffect(() => {
    leerModulos().then((r) => setModulos(r.modulos), fallar);
  }, [fallar]);

  async function cambiar(clave: string, activo: boolean) {
    setOcupada(true);
    setError(null);
    try {
      const r = await fijarModulo(clave, activo);
      setModulos(r.modulos);
      recargarModulos?.();
    } catch (e) {
      fallar(e);
    } finally {
      setOcupada(false);
    }
  }

  if (modulos === null) return error ? <AvisoError error={error} /> : <EsqueletoPagina />;

  return (
    <div className="silice-adm__secciones">
      <AvisoError error={error} alCerrar={() => setError(null)} />
      <section className="silice-adm__seccion" aria-label="Especialidades de esta instalación">
        <p className="cds--type-body-compact-01">
          Elija qué partes del programa usa esta instalación. Apagar una no borra nada: deja de ofrecerse y, al encenderla,
          todo vuelve como estaba.
        </p>
        {modulos.map((m) => (
          <Toggle
            key={m.clave}
            id={`especialidad-${m.clave}`}
            labelText={primeraEnMayuscula(m.nombre)}
            labelA="Apagada"
            labelB="Encendida"
            toggled={m.activo}
            disabled={ocupada}
            onToggle={(encendida: boolean) => void cambiar(m.clave, encendida)}
          />
        ))}
        {modulos.some((m) => m.cambiado_por !== null) && (
          <ul className="silice-adm__nota cds--type-label-01">
            {modulos
              .filter((m) => m.cambiado_por !== null)
              .map((m) => (
                <li key={m.clave}>{`${primeraEnMayuscula(m.nombre)}: cambiada por ${m.cambiado_por} el ${m.cambiado_el?.replace("T", " ").slice(0, 16)}`}</li>
              ))}
          </ul>
        )}
      </section>
    </div>
  );
}
